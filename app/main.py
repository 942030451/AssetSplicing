"""应用程序主入口点。"""

import sys
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def create_app(argv: Optional[List[str]] = None) -> QApplication:
    """初始化并配置 QApplication 实例。"""
    if argv is None:
        argv = sys.argv

    # 设置高 DPI 适配策略（Qt6 默认开启高分屏缩放）
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication.instance()
    if app is None:
        app = QApplication(argv)

    app.setApplicationName("Asset Splicer")
    app.setApplicationDisplayName("素材垂直分割与上下拼接小工具")
    app.setOrganizationName("AssetSplicing")

    apply_theme(app)
    return app


def main(argv: Optional[List[str]] = None) -> int:
    """程序主入口函数。"""
    app = create_app(argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
