"""素材分割拼接效果预览对话框。"""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
from typing import Optional, Union

from PySide6.QtCore import Qt
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

        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(f"效果预览 - {self.file_name}")
        self.resize(760, 820)
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
            "background-color: #1e1e24; border: 1px solid #2e2e38; border-radius: 8px; padding: 10px;"
        )
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(10, 6, 10, 6)

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
        lbl_spec.setStyleSheet("font-size: 13px; color: #e4e4e7;")
        info_layout.addWidget(lbl_spec)
        info_layout.addStretch()

        type_tag = QLabel("【单帧拼接预览】" if self.media_info.is_video else "【图片拼接预览】", info_widget)
        type_tag.setStyleSheet("color: #a1a1aa; font-weight: bold;")
        info_layout.addWidget(type_tag)

        layout.addWidget(info_widget)

        # 2. 图像展示区 (带滚动支持)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #2e2e38; background-color: #0d0d11; border-radius: 8px; }")

        self.lbl_image = QLabel(self.scroll_area)
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(str(self.temp_image_path))
        if not pixmap.isNull():
            self.lbl_image.setPixmap(pixmap)
        else:
            self.lbl_image.setText("预览图像加载失败")
            self.lbl_image.setStyleSheet("color: #ef4444; font-size: 14px;")

        self.scroll_area.setWidget(self.lbl_image)
        layout.addWidget(self.scroll_area, 1)

        # 3. 底部操作栏
        bottom_layout = QHBoxLayout()
        hint_label = QLabel("提示：此预览为依据当前分割比例实时合成的单帧/图片效果", self)
        hint_label.setStyleSheet("color: #71717a; font-size: 12px;")
        bottom_layout.addWidget(hint_label)
        bottom_layout.addStretch()

        btn_close = QPushButton("关闭预览", self)
        btn_close.setObjectName("primaryButton")
        btn_close.setFixedWidth(110)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)

        layout.addLayout(bottom_layout)

    def closeEvent(self, event):
        """窗口关闭时清理临时预览图片。"""
        try:
            if self.temp_image_path.is_file():
                self.temp_image_path.unlink()
        except Exception:
            pass
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
        """极速生成单帧/图片预览并弹出预览窗口。"""
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
        dlg.exec()
        return dlg
