"""文件拖拽放置区组件。"""

from pathlib import Path
from typing import List, Set

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QVBoxLayout

SUPPORTED_EXTENSIONS: Set[str] = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".flv",
    ".webm",
    ".m4v",
    ".wmv",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
}

NORMAL_STYLE = """
QFrame#dropZone {
    background-color: #202024;
    border: 2px dashed #3f3f46;
    border-radius: 10px;
}
QFrame#dropZone:hover {
    border-color: #3b82f6;
    background-color: #232734;
}
QFrame#dropZone:disabled {
    background-color: #18181b;
    border: 2px dashed #27272a;
}
"""

DRAG_OVER_STYLE = """
QFrame#dropZone {
    background-color: #1e293b;
    border: 2px dashed #3b82f6;
    border-radius: 10px;
}
"""


class DropZone(QFrame):
    """支持拖拽文件和点击选择文件的放置区。"""

    sig_files_dropped = Signal(list)  # List[Path]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(NORMAL_STYLE)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        self.lbl_icon = QLabel("📁", self)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("font-size: 32px; background: transparent;")

        self.lbl_title = QLabel("将视频或图片拖拽至此处，或点击选择文件", self)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f4f4f5; background: transparent;")

        self.lbl_subtitle = QLabel(
            "支持格式：MP4, MOV, MKV, AVI, FLV, WebM, PNG, JPG, WebP, BMP", self
        )
        self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subtitle.setStyleSheet("font-size: 12px; color: #a1a1aa; background: transparent;")

        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_subtitle)

    def _extract_supported_files(self, mime_data) -> List[Path]:
        valid_paths: List[Path] = []
        if not mime_data.hasUrls():
            return valid_paths

        for url in mime_data.urls():
            if url.isLocalFile():
                p = Path(url.toLocalFile()).resolve()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                    valid_paths.append(p)
        return valid_paths

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not self.isEnabled():
            event.ignore()
            return
        if event.mimeData().hasUrls():
            valid_files = self._extract_supported_files(event.mimeData())
            if valid_files:
                self.setStyleSheet(DRAG_OVER_STYLE)
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if not self.isEnabled():
            event.ignore()
            return
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self.setStyleSheet(NORMAL_STYLE)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet(NORMAL_STYLE)
        if not self.isEnabled():
            event.ignore()
            return
        valid_files = self._extract_supported_files(event.mimeData())
        if valid_files:
            event.acceptProposedAction()
            self.sig_files_dropped.emit(valid_files)
        else:
            event.ignore()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.isEnabled():
            return
        if event.button() == Qt.MouseButton.LeftButton:
            ext_filter = (
                "媒体文件 (*.mp4 *.mov *.mkv *.avi *.flv *.webm *.m4v *.wmv *.jpg *.jpeg *.png *.webp *.bmp *.tiff);;"
                "所有文件 (*.*)"
            )
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "选择媒体文件",
                "",
                ext_filter,
            )
            if files:
                paths = [Path(f).resolve() for f in files if Path(f).is_file()]
                if paths:
                    self.sig_files_dropped.emit(paths)
        super().mousePressEvent(event)
