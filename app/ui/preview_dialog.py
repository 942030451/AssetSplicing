"""素材分割拼接效果预览对话框。"""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
from typing import Optional, Union

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.pipeline import PipelineBuilder
from app.core.probe import MediaInfo


class PreviewDialog(QDialog):
    """展示分割与上下拼接效果的对话框。"""

    def __init__(
        self,
        image_path: Union[str, Path],
        file_name: str,
        media_info: MediaInfo,
        split_ratio: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.temp_image_path = Path(image_path)
        self.file_name = file_name
        self.media_info = media_info
        self.split_ratio = split_ratio
        self.is_fit_mode: bool = True  # 默认为“适应窗口（整体预览）”模式，无需滚动
        self._temp_cleaned: bool = False

        self.original_pixmap = QPixmap(str(self.temp_image_path))

        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(f"效果预览 - {self.file_name}")
        self.resize(760, 840)
        self.setMinimumSize(540, 600)

        icon_path = Path(__file__).resolve().parent.parent / "resources" / "icon.png"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # 1. 顶部信息卡片
        info_widget = QWidget(self)
        info_widget.setStyleSheet(
            "background-color: #27272a; border: 1px solid #3f3f46; border-radius: 8px; padding: 10px;"
        )
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(12, 6, 12, 6)

        w_part = PipelineBuilder.calculate_part_width(self.media_info.width, self.split_ratio)
        h_eff = (self.media_info.height // 2 * 2) if self.media_info.is_video else self.media_info.height
        target_res = f"{w_part} × {h_eff * self.split_ratio}"

        lbl_spec = QLabel(
            f"<b>原分辨率:</b> {self.media_info.width} × {self.media_info.height} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>分割比例:</b> 1/{self.split_ratio} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>拼接后规格:</b> <span style='color: #38bdf8; font-weight: bold;'>{target_res}</span>",
            info_widget,
        )
        lbl_spec.setTextFormat(Qt.TextFormat.RichText)
        lbl_spec.setStyleSheet("font-size: 13px; color: #f4f4f5; background: transparent;")
        info_layout.addWidget(lbl_spec)
        info_layout.addStretch()

        type_tag = QLabel("【单帧拼接整体预览】" if self.media_info.is_video else "【图片拼接整体预览】", info_widget)
        type_tag.setStyleSheet("color: #a1a1aa; font-weight: bold; background: transparent;")
        info_layout.addWidget(type_tag)

        layout.addWidget(info_widget)

        # 2. 图像展示区（默认适应窗口居中整体呈现）
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: 1px solid #3f3f46; background-color: #121214; border-radius: 8px; }"
        )

        self.lbl_image = QLabel(self.scroll_area)
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setStyleSheet("background: transparent;")

        self.scroll_area.setWidget(self.lbl_image)
        layout.addWidget(self.scroll_area, 1)

        # 3. 底部操作栏
        bottom_layout = QHBoxLayout()

        self.btn_toggle_mode = QPushButton("切换为 1:1 原始大图", self)
        self.btn_toggle_mode.setStyleSheet(
            "QPushButton { background-color: #27272a; color: #e4e4e7; border: 1px solid #52525b; border-radius: 6px; padding: 6px 14px; font-size: 12px; }"
            "QPushButton:hover { background-color: #3f3f46; }"
        )
        self.btn_toggle_mode.clicked.connect(self.toggle_view_mode)
        bottom_layout.addWidget(self.btn_toggle_mode)

        hint_label = QLabel("提示：当前默认为【适应窗口】模式，可直接一览拼接全貌效果", self)
        hint_label.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent;")
        bottom_layout.addWidget(hint_label)
        bottom_layout.addStretch()

        btn_close = QPushButton("关闭预览", self)
        btn_close.setObjectName("primaryButton")
        btn_close.setFixedWidth(110)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)

        layout.addLayout(bottom_layout)

        # 初次显示后根据真实视口比例进行自适应全图缩放渲染
        QTimer.singleShot(30, self.update_display)

    def update_display(self) -> None:
        """根据当前视图模式（适应窗口全貌 vs 1:1 原始比例）刷新图像展示。"""
        if self.original_pixmap.isNull():
            self.lbl_image.setText("预览图像加载失败")
            self.lbl_image.setStyleSheet("color: #ef4444; font-size: 14px; background: transparent;")
            return

        if self.is_fit_mode:
            # 整体效果模式：隐藏滚动条，按视口大小无损等比平滑缩放
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            vp = self.scroll_area.viewport().size()
            avail_w = max(100, vp.width() - 16)
            avail_h = max(100, vp.height() - 16)

            scaled = self.original_pixmap.scaled(
                avail_w,
                avail_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_image.setPixmap(scaled)
            self.lbl_image.resize(scaled.size())
            self.btn_toggle_mode.setText("切换为 1:1 原始大图")
        else:
            # 1:1 细节模式：显示滚动条，呈现真实像素
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

            self.lbl_image.setPixmap(self.original_pixmap)
            self.lbl_image.resize(self.original_pixmap.size())
            self.btn_toggle_mode.setText("适应窗口 (整体预览)")

    def toggle_view_mode(self) -> None:
        """在适应窗口整体预览与 1:1 原始比例间切换。"""
        self.is_fit_mode = not self.is_fit_mode
        self.update_display()

    def resizeEvent(self, event) -> None:
        """窗口大小调整时实时重新缩放全图，保持最佳视口拟合。"""
        super().resizeEvent(event)
        if self.is_fit_mode:
            self.update_display()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.is_fit_mode:
            QTimer.singleShot(20, self.update_display)

    def cleanup_temp_file(self) -> None:
        """安全可靠清理临时生成的单帧预览图片。"""
        if self._temp_cleaned:
            return
        try:
            if hasattr(self, "temp_image_path") and self.temp_image_path and self.temp_image_path.is_file():
                self.temp_image_path.unlink(missing_ok=True)
            self._temp_cleaned = True
        except Exception:
            pass

    def done(self, r: int) -> None:
        """对话框正常或异常完成时立即清理临时文件。"""
        self.cleanup_temp_file()
        super().done(r)

    def closeEvent(self, event) -> None:
        """点击窗口右上角关闭按钮时立即清理临时文件。"""
        self.cleanup_temp_file()
        super().closeEvent(event)

    @classmethod
    def generate_and_show(
        cls,
        parent: QWidget,
        ffmpeg_bin: str,
        file_path: Union[str, Path],
        media_info: MediaInfo,
        split_ratio: int,
    ) -> Optional["PreviewDialog"]:
        """极速生成单帧/图片预览并在弹窗中全貌呈现，生命周期结束后保障清理。"""
        p = Path(file_path)
        temp_dir = Path(tempfile.gettempdir())
        preview_out = temp_dir / f"assetsplicer_preview_{uuid.uuid4().hex[:8]}.jpg"

        # 确定截帧时间点：若为视频取 1 秒处（若视频不足 1 秒则取 0 秒）
        seek_sec = 1.0 if media_info.is_video and media_info.duration > 1.2 else 0.0

        cmd = PipelineBuilder.build_preview_command(
            ffmpeg_bin=ffmpeg_bin,
            input_path=str(p),
            preview_output_path=str(preview_out),
            orig_w=media_info.width,
            orig_h=media_info.height,
            n=split_ratio,
            is_video=media_info.is_video,
            seek_sec=seek_sec,
        )

        run_kwargs = {
            "capture_output": True,
            "text": True,
            "timeout": 15,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if sys.platform == "win32":
            run_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        try:
            res = subprocess.run(cmd, check=False, **run_kwargs)
            if res.returncode != 0 or not preview_out.is_file():
                err_text = res.stderr[-300:] if res.stderr else "生成预览图失败"
                QMessageBox.warning(parent, "生成预览失败", f"无法生成素材预览图：\n{err_text}")
                return None
        except Exception as e:
            QMessageBox.warning(parent, "预览错误", f"调用 FFmpeg 失败: {e}")
            return None

        dlg = cls(
            image_path=preview_out,
            file_name=p.name,
            media_info=media_info,
            split_ratio=split_ratio,
            parent=parent,
        )

        # 使用 try-finally 确保无论是 accept、reject、X 号关闭还是异常崩溃，临时文件均被 100% 清理
        try:
            dlg.exec()
        finally:
            dlg.cleanup_temp_file()

        return dlg
