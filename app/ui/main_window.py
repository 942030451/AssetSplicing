"""主窗口界面实现。"""

import os
from pathlib import Path
import shutil
import sys
from typing import List, Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.probe import MediaProbe
from app.core.worker import BatchProcessorThread
from app.ui.drop_zone import DropZone
from app.ui.preview_dialog import PreviewDialog
from app.ui.task_table import TaskTable


def resolve_tool_path(tool_name: str) -> str:
    """按优先级定位 ffmpeg / ffprobe 工具路径。"""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "tools" / f"{tool_name}.exe",
        Path(sys.executable).parent / "tools" / f"{tool_name}.exe",
        Path.cwd() / "tools" / f"{tool_name}.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    found_in_path = shutil.which(tool_name)
    if found_in_path:
        return found_in_path

    return str(candidates[0])


def resolve_app_icon() -> Optional[QIcon]:
    """定位应用程序窗口图标。"""
    candidates = [
        Path(__file__).resolve().parent.parent / "resources" / "icon.png",
        Path(__file__).resolve().parent.parent / "resources" / "icon.ico",
        Path(sys.executable).parent / "app" / "resources" / "icon.png",
        Path.cwd() / "app" / "resources" / "icon.png",
    ]
    for c in candidates:
        if c.is_file():
            return QIcon(str(c))
    return None


class MainWindow(QMainWindow):
    """素材分割与上下拼接工具主界面。"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Asset Splicer-分割拼接工具")
        self.resize(1000, 720)
        self.setMinimumSize(850, 580)

        icon = resolve_app_icon()
        if icon:
            self.setWindowIcon(icon)

        # 核心工具路径与探测器
        self.ffmpeg_bin = resolve_tool_path("ffmpeg")
        self.ffprobe_bin = resolve_tool_path("ffprobe")
        self.probe = MediaProbe(ffprobe_bin=self.ffprobe_bin)

        self.worker: Optional[BatchProcessorThread] = None
        self._is_processing: bool = False

        self._init_ui()
        self.check_tools_exist()
        self.update_ui_state()

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # 1. 拖拽放置区
        self.drop_zone = DropZone(self)
        self.drop_zone.setFixedHeight(120)
        self.drop_zone.sig_files_dropped.connect(self.on_files_dropped)
        main_layout.addWidget(self.drop_zone)

        # 2. 分割与导出配置区
        config_group = QGroupBox("分割与导出配置", self)
        config_layout = QVBoxLayout(config_group)
        config_layout.setContentsMargins(16, 16, 16, 14)
        config_layout.setSpacing(10)

        # 2.1 比例选择（选项精简为 1/2, 1/3, 1/4）
        ratio_layout = QHBoxLayout()
        ratio_layout.setSpacing(16)
        ratio_label = QLabel("分割比例：", config_group)
        ratio_label.setStyleSheet("font-weight: 600; color: #94a3b8; background: transparent;")
        ratio_layout.addWidget(ratio_label)

        self.radio_ratio_2 = QRadioButton("1/2", config_group)
        self.radio_ratio_3 = QRadioButton("1/3", config_group)
        self.radio_ratio_4 = QRadioButton("1/4", config_group)
        self.radio_ratio_2.setStyleSheet("background: transparent;")
        self.radio_ratio_3.setStyleSheet("background: transparent;")
        self.radio_ratio_4.setStyleSheet("background: transparent;")
        self.radio_ratio_2.setChecked(True)

        self.ratio_group = QButtonGroup(self)
        self.ratio_group.addButton(self.radio_ratio_2, 2)
        self.ratio_group.addButton(self.radio_ratio_3, 3)
        self.ratio_group.addButton(self.radio_ratio_4, 4)

        self.radio_ratio_2.toggled.connect(self.on_ratio_changed)
        self.radio_ratio_3.toggled.connect(self.on_ratio_changed)
        self.radio_ratio_4.toggled.connect(self.on_ratio_changed)

        ratio_layout.addWidget(self.radio_ratio_2)
        ratio_layout.addWidget(self.radio_ratio_3)
        ratio_layout.addWidget(self.radio_ratio_4)
        ratio_layout.addStretch()
        config_layout.addLayout(ratio_layout)

        # 2.2 导出目录模式选择
        out_layout = QHBoxLayout()
        out_layout.setSpacing(16)
        out_label = QLabel("导出路径：", config_group)
        out_label.setStyleSheet("font-weight: 600; color: #94a3b8; background: transparent;")
        out_layout.addWidget(out_label)

        self.radio_out_source = QRadioButton("与原文件同目录", config_group)
        self.radio_out_custom = QRadioButton("自定义目录", config_group)
        self.radio_out_source.setStyleSheet("background: transparent;")
        self.radio_out_custom.setStyleSheet("background: transparent;")
        self.radio_out_source.setChecked(True)

        self.out_group = QButtonGroup(self)
        self.out_group.addButton(self.radio_out_source)
        self.out_group.addButton(self.radio_out_custom)

        out_layout.addWidget(self.radio_out_source)
        out_layout.addWidget(self.radio_out_custom)
        out_layout.addStretch()
        config_layout.addLayout(out_layout)

        # 2.3 自定义路径输入与浏览按钮（独占一行排布，彻底消除遮挡与紧绷感）
        custom_input_layout = QHBoxLayout()
        custom_input_layout.setContentsMargins(0, 0, 0, 0)
        custom_input_layout.setSpacing(10)

        self.edit_custom_dir = QLineEdit(config_group)
        self.edit_custom_dir.setPlaceholderText("请选择自定义输出目录...")
        self.edit_custom_dir.setEnabled(False)

        self.btn_browse_dir = QPushButton("浏览...", config_group)
        self.btn_browse_dir.setEnabled(False)
        self.btn_browse_dir.clicked.connect(self.on_browse_output_dir)

        self.radio_out_custom.toggled.connect(self.on_output_mode_changed)

        custom_input_layout.addWidget(self.edit_custom_dir, 1)
        custom_input_layout.addWidget(self.btn_browse_dir)
        config_layout.addLayout(custom_input_layout)

        main_layout.addWidget(config_group)

        # 3. 任务表格
        self.task_table = TaskTable(self)
        self.task_table.sig_tasks_changed.connect(self.update_ui_state)
        self.task_table.sig_preview_requested.connect(self.on_preview_task)
        main_layout.addWidget(self.task_table, 1)

        # 4. 底部控制栏
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        self.lbl_status = QLabel("就绪 (列表中共有 0 项)", self)
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-weight: 500;")

        self.btn_clear = QPushButton("清空列表", self)
        self.btn_clear.clicked.connect(self.clear_tasks)

        self.btn_open_dir = QPushButton("打开输出目录", self)
        self.btn_open_dir.clicked.connect(self.open_output_dir)

        self.btn_cancel = QPushButton("中止处理", self)
        self.btn_cancel.setObjectName("dangerButton")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_processing)

        self.btn_start = QPushButton("开始处理", self)
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_processing)

        bottom_layout.addWidget(self.lbl_status)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_clear)
        bottom_layout.addWidget(self.btn_open_dir)
        bottom_layout.addWidget(self.btn_cancel)
        bottom_layout.addWidget(self.btn_start)

        main_layout.addLayout(bottom_layout)

        # 隐藏默认状态栏以消除双重重叠显示，同时保留其接口供通知与测试使用
        self.statusBar().hide()
        self.statusBar().showMessage("准备就绪")

    @property
    def current_ratio(self) -> int:
        if self.radio_ratio_3.isChecked():
            return 3
        if self.radio_ratio_4.isChecked():
            return 4
        return 2

    @property
    def custom_output_dir(self) -> Optional[Path]:
        if self.radio_out_custom.isChecked():
            val = self.edit_custom_dir.text().strip()
            if val:
                return Path(val)
        return None

    def check_tools_exist(self, show_dialog: bool = True) -> bool:
        """检查核心编解码工具是否存在。"""
        ffmpeg_exists = Path(self.ffmpeg_bin).is_file()
        ffprobe_exists = Path(self.ffprobe_bin).is_file()

        if not (ffmpeg_exists and ffprobe_exists):
            if show_dialog:
                QMessageBox.warning(
                    self,
                    "核心工具缺失提醒",
                    f"未能在以下路径找到 ffmpeg 或 ffprobe：\n"
                    f"FFmpeg: {self.ffmpeg_bin}\n"
                    f"FFprobe: {self.ffprobe_bin}\n\n"
                    f"请确保 tools 目录下包含 ffmpeg.exe 和 ffprobe.exe，否则无法执行解析与转码。",
                )
            self.statusBar().showMessage("警告：未找到 FFmpeg/FFprobe 工具组件")
            return False
        return True

    def on_ratio_changed(self) -> None:
        self.task_table.update_split_ratio(self.current_ratio)

    def on_output_mode_changed(self, checked: bool) -> None:
        is_custom = self.radio_out_custom.isChecked()
        self.edit_custom_dir.setEnabled(is_custom)
        self.btn_browse_dir.setEnabled(is_custom)

    def on_browse_output_dir(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(self, "选择自定义输出目录", str(Path.home()))
        if selected_dir:
            self.edit_custom_dir.setText(selected_dir)

    def closeEvent(self, event: QCloseEvent) -> None:
        """窗口关闭时安全拦截并中止正在运行的转码任务。"""
        if self._is_processing and self.worker and self.worker.isRunning():
            self.cancel_processing()
            try:
                self.worker.wait(2000)
            except Exception:
                pass
        event.accept()

    def on_preview_task(self, task_id: str) -> None:
        """响应表格中某任务的预览请求，生成并展示分割上下拼接效果。"""
        if not self.check_tools_exist(show_dialog=True):
            return

        item = self.task_table.get_task_item(task_id)
        if not item:
            return

        PreviewDialog.generate_and_show(
            parent=self,
            ffmpeg_bin=self.ffmpeg_bin,
            file_path=item["path"],
            media_info=item["info"],
            split_ratio=self.current_ratio,
        )

    def on_files_dropped(self, paths: List[Path]) -> None:
        """接收拖拽或选择的文件并使用 probe 解析入队。"""
        new_valid_count = 0
        duplicate_count = 0
        unparsed_count = 0

        for p in paths:
            info = self.probe.probe(p)
            if info is not None:
                tid = self.task_table.add_task_item(p, info, split_ratio=self.current_ratio)
                if tid:
                    new_valid_count += 1
                else:
                    duplicate_count += 1
            else:
                unparsed_count += 1
            QApplication.processEvents()

        self.update_ui_state()

        total_items = self.task_table.rowCount()
        details: List[str] = []
        if duplicate_count > 0:
            details.append(f"跳过 {duplicate_count} 个重复文件")
        if unparsed_count > 0:
            details.append(f"跳过 {unparsed_count} 个无法解析的文件")

        if details:
            detail_str = "，".join(details)
            msg = f"已添加 {total_items} 个任务，{detail_str}"
        else:
            msg = f"已添加 {total_items} 个任务"

        self.statusBar().showMessage(msg)
        self.lbl_status.setText(f"{msg} (共 {total_items} 项)")

    def update_ui_state(self) -> None:
        is_processing = self._is_processing and (self.worker is not None and bool(self.worker.isRunning()))
        has_tasks = self.task_table.rowCount() > 0

        self.drop_zone.setEnabled(not is_processing)
        self.task_table.set_actions_enabled(not is_processing)

        self.btn_start.setEnabled(has_tasks and not is_processing)
        self.btn_cancel.setEnabled(is_processing)
        self.btn_clear.setEnabled(has_tasks and not is_processing)

        self.radio_ratio_2.setEnabled(not is_processing)
        self.radio_ratio_3.setEnabled(not is_processing)
        self.radio_ratio_4.setEnabled(not is_processing)
        self.radio_out_source.setEnabled(not is_processing)
        self.radio_out_custom.setEnabled(not is_processing)
        self.edit_custom_dir.setEnabled(not is_processing and self.radio_out_custom.isChecked())
        self.btn_browse_dir.setEnabled(not is_processing and self.radio_out_custom.isChecked())

        if is_processing:
            self.lbl_status.setText("正在批量处理任务...")
        else:
            self.lbl_status.setText(f"就绪 (列表中共有 {self.task_table.rowCount()} 项)")

    def start_processing(self) -> None:
        if not self.check_tools_exist(show_dialog=True):
            return

        pending_tasks = self.task_table.get_pending_tasks(
            split_ratio=self.current_ratio,
            output_dir=self.custom_output_dir,
        )
        if not pending_tasks:
            QMessageBox.information(self, "提示", "所有任务已完成或列表中无待处理任务。")
            return

        if self.worker and self.worker.isRunning():
            self.worker.wait(1000)

        self._is_processing = True
        self.worker = BatchProcessorThread(ffmpeg_bin=self.ffmpeg_bin, tasks=pending_tasks)
        self.worker.sig_task_started.connect(self.task_table.set_task_started)
        self.worker.sig_task_progress.connect(self.task_table.set_task_progress)
        self.worker.sig_task_completed.connect(self.task_table.set_task_completed)
        self.worker.sig_task_failed.connect(self.task_table.set_task_failed)
        self.worker.sig_all_finished.connect(self.on_processing_finished)

        self.worker.start()
        self.update_ui_state()

    def cancel_processing(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.lbl_status.setText("正在中止处理...")
            self.btn_cancel.setEnabled(False)

    def on_processing_finished(self) -> None:
        is_cancelled = bool(self.worker and getattr(self.worker, "_is_cancelled", False))
        self._is_processing = False
        self.update_ui_state()
        if is_cancelled:
            self.lbl_status.setText("处理已中止")
            self.statusBar().showMessage("用户已中止批量处理")
        else:
            self.lbl_status.setText("批量处理完成")
            self.statusBar().showMessage("所有任务处理完毕")

    def clear_tasks(self) -> None:
        self.task_table.clear_tasks()
        self.update_ui_state()

    def open_output_dir(self) -> None:
        """打开输出目录。优先打开自定义目录，否则尝试第一个任务的输出目录。"""
        target_dir: Optional[Path] = None

        if self.custom_output_dir and self.custom_output_dir.is_dir():
            target_dir = self.custom_output_dir
        else:
            # 查找已完成任务的输出目录或第一个任务的输入目录
            for item in self.task_table._task_items.values():
                if item.get("output_path") and item["output_path"].parent.is_dir():
                    target_dir = item["output_path"].parent
                    break
                elif item.get("path") and item["path"].parent.is_dir():
                    target_dir = item["path"].parent
                    break

        if not target_dir or not target_dir.is_dir():
            target_dir = Path.cwd()

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir)))
