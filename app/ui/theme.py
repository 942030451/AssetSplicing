"""现代化深色质感主题 QSS 样式定义与应用函数。"""

from typing import Union
from PySide6.QtWidgets import QApplication, QWidget

DARK_THEME = """
/* 全局基础设置 */
QWidget {
    background-color: #18181b;
    color: #f4f4f5;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Microsoft YaHei", sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* 主窗口与对话框 */
QMainWindow, QDialog {
    background-color: #18181b;
}

/* 配置卡片面板 */
QGroupBox {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 10px;
    margin-top: 18px;
    padding: 16px 14px 14px 14px;
    font-weight: 600;
    color: #f4f4f5;
}

QGroupBox QLabel, QGroupBox QRadioButton {
    background-color: transparent;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    background-color: #27272a;
    border-radius: 4px;
    color: #e4e4e7;
    font-weight: bold;
}

/* 按钮基础通用样式 */
QPushButton {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #3f3f46;
    border-color: #52525b;
}

QPushButton:pressed {
    background-color: #18181b;
}

QPushButton:disabled {
    background-color: #202023;
    color: #52525b;
    border-color: #27272a;
}

/* 核心行动强调按钮 (开始处理) */
QPushButton#primaryButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #3b82f6;
    border-color: #60a5fa;
}

QPushButton#primaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#primaryButton:disabled {
    background-color: #1e293b;
    color: #475569;
    border-color: #1e293b;
}

/* 危险/中止按钮 */
QPushButton#dangerButton {
    background-color: #991b1b;
    color: #ffffff;
    border: 1px solid #b91c1c;
    font-weight: 600;
}

QPushButton#dangerButton:hover {
    background-color: #dc2626;
    border-color: #ef4444;
}

QPushButton#dangerButton:pressed {
    background-color: #7f1d1d;
}

QPushButton#dangerButton:disabled {
    background-color: #2e1717;
    color: #592929;
    border-color: #2e1717;
}

/* 文本输入框 */
QLineEdit {
    background-color: #18181b;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 7px 12px;
    min-height: 20px;
}

QLineEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #202025;
}

QLineEdit:disabled {
    background-color: #18181b;
    color: #52525b;
    border-color: #27272a;
}

/* 单选框与选项 */
QRadioButton {
    background-color: transparent;
    spacing: 8px;
    color: #e4e4e7;
    font-size: 13px;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #52525b;
    background-color: #18181b;
}

QRadioButton::indicator:hover {
    border-color: #3b82f6;
}

QRadioButton::indicator:checked {
    border: 2px solid #3b82f6;
    background-color: #2563eb;
}

QRadioButton:disabled {
    color: #71717a;
}

QRadioButton::indicator:disabled {
    border: 2px solid #3f3f46;
    background-color: #18181b;
}

QRadioButton::indicator:checked:disabled {
    border: 2px solid #2563eb;
    background-color: #1d4ed8;
}

/* 任务队列表格控件 */
QTableWidget {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 8px;
    gridline-color: transparent;
    outline: none;
}

QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #27272a;
}

QTableWidget::item:selected {
    background-color: #272738;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #27272a;
    color: #a1a1aa;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #3f3f46;
    font-weight: 600;
}

/* 进度条 */
QProgressBar {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
    min-height: 18px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 3px;
}

/* 状态提示与标签 */
QStatusBar {
    background-color: #18181b;
    color: #a1a1aa;
    border-top: 1px solid #27272a;
}

QLabel {
    background-color: transparent;
    color: #f4f4f5;
}

QLabel#mutedLabel {
    color: #a1a1aa;
}

QLabel#statusLabel {
    color: #94a3b8;
    font-size: 12px;
}

/* 精致细滚动条 */
QScrollBar:vertical {
    border: none;
    background: #18181b;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3f3f46;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #52525b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #18181b;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #3f3f46;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: #52525b;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


def apply_theme(target: Union[QApplication, QWidget]) -> None:
    """向应用程序或顶层窗口应用深色质感主题。"""
    target.setStyleSheet(DARK_THEME)
