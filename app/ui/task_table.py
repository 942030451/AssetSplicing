"""任务队列表格组件。"""

from pathlib import Path
from typing import Dict, List, Optional, Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QHBoxLayout,
)

from app.core.pipeline import PipelineBuilder
from app.core.probe import MediaInfo
from app.core.worker import BatchTask


class TaskTable(QTableWidget):
    """展示批量处理任务的表格控件。"""

    sig_tasks_changed = Signal()

    COL_FILENAME = 0
    COL_TYPE = 1
    COL_ORIG_RES = 2
    COL_TARGET_RES = 3
    COL_STATUS = 4
    COL_ACTION = 5

    HEADERS = ["文件名", "类型", "原分辨率", "拼接后规格", "状态 / 进度", "操作"]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(0, len(self.HEADERS), parent)
        self._task_items: Dict[str, dict] = {}
        self._actions_enabled: bool = True
        self._init_ui()

    def _init_ui(self) -> None:
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(self.COL_FILENAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_ORIG_RES, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_TARGET_RES, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(self.COL_STATUS, 160)
        header.setSectionResizeMode(self.COL_ACTION, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(self.COL_ACTION, 80)

    def calculate_target_resolution(self, media_info: MediaInfo, split_ratio: int) -> str:
        """根据原分辨率和分切比例计算输出拼接分辨率。"""
        try:
            w_part = PipelineBuilder.calculate_part_width(media_info.width, split_ratio)
            h_eff = (media_info.height // 2 * 2) if media_info.is_video else media_info.height
            target_h = h_eff * split_ratio
            return f"{w_part} × {target_h}"
        except Exception:
            return "规格无效"

    def add_task_item(
        self,
        file_path: Union[str, Path],
        media_info: MediaInfo,
        split_ratio: int = 2,
    ) -> Optional[str]:
        """向表格添加一个媒体任务。若已存在则返回 None。"""
        p = Path(file_path).resolve()
        task_id = str(p)
        if task_id in self._task_items:
            return None

        row = self.rowCount()
        self.insertRow(row)

        # 文件名
        item_name = QTableWidgetItem(p.name)
        item_name.setToolTip(str(p))
        item_name.setData(Qt.ItemDataRole.UserRole, task_id)
        self.setItem(row, self.COL_FILENAME, item_name)

        # 类型
        type_str = "视频" if media_info.is_video else "图片"
        item_type = QTableWidgetItem(type_str)
        item_type.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, self.COL_TYPE, item_type)

        # 原分辨率
        orig_res_str = f"{media_info.width} × {media_info.height}"
        item_orig = QTableWidgetItem(orig_res_str)
        item_orig.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, self.COL_ORIG_RES, item_orig)

        # 拼接后规格
        target_res_str = self.calculate_target_resolution(media_info, split_ratio)
        item_target = QTableWidgetItem(target_res_str)
        item_target.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, self.COL_TARGET_RES, item_target)

        # 状态 / 进度
        item_status = QTableWidgetItem("等待中")
        item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_status.setForeground(Qt.GlobalColor.gray)
        self.setItem(row, self.COL_STATUS, item_status)

        # 操作：移除按钮
        btn_remove = QPushButton("移除")
        btn_remove.setEnabled(self._actions_enabled)
        btn_remove.setStyleSheet(
            "QPushButton { background-color: #3f3f46; color: #f4f4f5; border: none; padding: 2px 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #ef4444; color: #ffffff; }"
        )
        btn_remove.clicked.connect(lambda checked=False, tid=task_id: self.remove_task(tid))

        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(btn_remove)
        self.setCellWidget(row, self.COL_ACTION, action_widget)

        self._task_items[task_id] = {
            "task_id": task_id,
            "path": p,
            "info": media_info,
            "split_ratio": split_ratio,
            "status": "waiting",
            "status_text": "等待中",
            "progress": 0.0,
            "error": "",
            "output_path": None,
        }

        self.sig_tasks_changed.emit()
        return task_id

    def get_row_by_task_id(self, task_id: str) -> int:
        for r in range(self.rowCount()):
            item = self.item(r, self.COL_FILENAME)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                return r
        return -1

    def get_task_id_by_row(self, row: int) -> Optional[str]:
        item = self.item(row, self.COL_FILENAME)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def get_target_resolution_text(self, row: int) -> str:
        item = self.item(row, self.COL_TARGET_RES)
        return item.text() if item else ""

    def get_task_status_text(self, task_id: str) -> str:
        if task_id in self._task_items:
            return self._task_items[task_id].get("status_text", "")
        return ""

    def set_actions_enabled(self, enabled: bool) -> None:
        """启用或禁用所有行内的操作按钮。"""
        self._actions_enabled = enabled
        for r in range(self.rowCount()):
            widget = self.cellWidget(r, self.COL_ACTION)
            if widget:
                btn = widget.findChild(QPushButton)
                if btn:
                    btn.setEnabled(enabled)

    def update_split_ratio(self, split_ratio: int) -> None:
        """更新未完成任务的目标比例规格显示。"""
        for r in range(self.rowCount()):
            task_id = self.get_task_id_by_row(r)
            if task_id and task_id in self._task_items:
                item_data = self._task_items[task_id]
                if item_data.get("status") != "completed":
                    item_data["split_ratio"] = split_ratio
                    media_info = item_data["info"]
                    target_str = self.calculate_target_resolution(media_info, split_ratio)
                    item = self.item(r, self.COL_TARGET_RES)
                    if item:
                        item.setText(target_str)

    def remove_task(self, task_id: str) -> None:
        if not self._actions_enabled:
            return
        row = self.get_row_by_task_id(task_id)
        if row != -1:
            self.remove_row_by_index(row)

    def remove_row_by_index(self, row: int) -> None:
        if 0 <= row < self.rowCount():
            task_id = self.get_task_id_by_row(row)
            if task_id and task_id in self._task_items:
                del self._task_items[task_id]
            self.removeRow(row)
            self.sig_tasks_changed.emit()

    def clear_tasks(self) -> None:
        self.setRowCount(0)
        self._task_items.clear()
        self.sig_tasks_changed.emit()

    def set_task_started(self, task_id: str) -> None:
        if task_id not in self._task_items:
            return
        self._task_items[task_id]["status"] = "processing"
        self._task_items[task_id]["status_text"] = "处理中 (0.0%)"
        self._task_items[task_id]["progress"] = 0.0

        row = self.get_row_by_task_id(task_id)
        if row != -1:
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setFormat("处理中 0.0%")
            progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setCellWidget(row, self.COL_STATUS, progress_bar)

    def set_task_progress(self, task_id: str, percent: float) -> None:
        if task_id not in self._task_items:
            return
        percent = max(0.0, min(100.0, percent))
        self._task_items[task_id]["progress"] = percent
        self._task_items[task_id]["status_text"] = f"处理中 ({percent:.1f}%)"

        row = self.get_row_by_task_id(task_id)
        if row != -1:
            widget = self.cellWidget(row, self.COL_STATUS)
            if isinstance(widget, QProgressBar):
                widget.setValue(int(percent))
                widget.setFormat(f"处理中 {percent:.1f}%")
            else:
                progress_bar = QProgressBar()
                progress_bar.setRange(0, 100)
                progress_bar.setValue(int(percent))
                progress_bar.setFormat(f"处理中 {percent:.1f}%")
                progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setCellWidget(row, self.COL_STATUS, progress_bar)

    def set_task_completed(self, task_id: str, output_path: str) -> None:
        if task_id not in self._task_items:
            return
        self._task_items[task_id]["status"] = "completed"
        self._task_items[task_id]["status_text"] = "已完成"
        self._task_items[task_id]["progress"] = 100.0
        self._task_items[task_id]["output_path"] = Path(output_path)

        row = self.get_row_by_task_id(task_id)
        if row != -1:
            self.removeCellWidget(row, self.COL_STATUS)
            item = QTableWidgetItem("已完成")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(Qt.GlobalColor.green)
            item.setToolTip(f"输出文件：{output_path}")
            self.setItem(row, self.COL_STATUS, item)

    def set_task_failed(self, task_id: str, error_msg: str) -> None:
        if task_id not in self._task_items:
            return
        self._task_items[task_id]["status"] = "failed"
        self._task_items[task_id]["status_text"] = f"失败: {error_msg}"
        self._task_items[task_id]["error"] = error_msg

        row = self.get_row_by_task_id(task_id)
        if row != -1:
            self.removeCellWidget(row, self.COL_STATUS)
            btn_failed = QPushButton("失败 (点击查看)")
            btn_failed.setStyleSheet(
                "QPushButton { background-color: #7f1d1d; color: #fecaca; border: 1px solid #b91c1c; border-radius: 4px; padding: 2px 4px; font-size: 11px; }"
                "QPushButton:hover { background-color: #991b1b; }"
            )
            btn_failed.setToolTip(error_msg)
            btn_failed.clicked.connect(lambda checked=False, em=error_msg: self._show_error_dialog(em))

            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(4, 2, 4, 2)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(btn_failed)
            self.setCellWidget(row, self.COL_STATUS, container)

            item = self.item(row, self.COL_STATUS)
            if item:
                item.setText("失败")
                item.setToolTip(error_msg)

    def _show_error_dialog(self, error_msg: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("任务处理失败详情")
        box.setIcon(QMessageBox.Icon.Critical)
        box.setText("当前任务处理出错，详细日志如下：")
        box.setDetailedText(error_msg)
        box.exec()

    def get_pending_tasks(
        self,
        split_ratio: int,
        output_dir: Optional[Path] = None,
    ) -> List[BatchTask]:
        """获取所有待处理的任务列表（等待中、失败或处理中的任务）。"""
        tasks: List[BatchTask] = []
        for r in range(self.rowCount()):
            task_id = self.get_task_id_by_row(r)
            if not task_id or task_id not in self._task_items:
                continue
            item_data = self._task_items[task_id]
            if item_data["status"] != "completed":
                in_path = item_data["path"]
                out_path = PipelineBuilder.generate_output_path(
                    in_path,
                    split_ratio,
                    output_dir=output_dir,
                )
                tasks.append(
                    BatchTask(
                        task_id=task_id,
                        input_path=in_path,
                        output_path=out_path,
                        media_info=item_data["info"],
                        split_ratio=split_ratio,
                    )
                )
        return tasks
