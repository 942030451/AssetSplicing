"""应用程序主入口点。"""

import ctypes
from pathlib import Path
import sys
from typing import List, Optional

# 确保在直接作为脚本启动时，项目根目录位于 sys.path 首位
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def setup_windows_app_id() -> None:
    """在 Windows 平台上配置 AppUserModelID，使任务栏能够正确呈现独立应用小图标。"""
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("assetsplicer.app.1.0")
        except Exception:
            pass


def resolve_global_icon() -> Optional[QIcon]:
    """定位全局应用图标。"""
    candidates = [
        Path(__file__).resolve().parent / "resources" / "icon.png",
        Path(__file__).resolve().parent / "resources" / "icon.ico",
        Path(sys.executable).parent / "app" / "resources" / "icon.png",
        Path.cwd() / "app" / "resources" / "icon.png",
    ]
    for c in candidates:
        if c.is_file():
            return QIcon(str(c))
    return None


def create_app(argv: Optional[List[str]] = None) -> QApplication:
    """初始化并配置 QApplication 实例。"""
    setup_windows_app_id()

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
    app.setApplicationDisplayName("Asset Splicer-分割拼接工具")
    app.setOrganizationName("AssetSplicing")

    global_icon = resolve_global_icon()
    if global_icon:
        app.setWindowIcon(global_icon)

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
