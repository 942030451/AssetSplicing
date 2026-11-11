"""现代化深色主题 QSS 样式定义与应用函数。"""

from typing import Union
from PySide6.QtWidgets import QApplication, QWidget

DARK_THEME = """
/* 全局基础设置 */
QWidget {
    background-color: #18181b;
    color: #f4f4f5;
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* 主窗口与对话框 */
QMainWindow, QDialog {
    background-color: #18181b;
}

/* 卡片与分组面板 */
QGroupBox {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 8px;
    margin-top: 18px;
    padding: 14px 12px 12px 12px;
    font-weight: bold;
    color: #e4e4e7;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #27272a;
    border-radius: 4px;
}

/* 按钮通用 */
QPushButton {
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 6px 14px;
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

/* 主要操作强调按钮 */
QPushButton#primaryButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    font-weight: bold;
}

QPushButton#primaryButton:hover {
    background-color: #3b82f6;
    border-color: #2563eb;
}

QPushButton#primaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton#primaryButton:disabled {
    background-color: #1e3a5f;
    color: #64748b;
    border-color: #1e293b;
}

/* 危险/中止按钮 */
QPushButton#dangerButton {
    background-color: #991b1b;
    color: #ffffff;
    border: 1px solid #b91c1c;
}

QPushButton#dangerButton:hover {
    background-color: #dc2626;
}

QPushButton#dangerButton:pressed {
    background-color: #7f1d1d;
}

QPushButton#dangerButton:disabled {
    background-color: #331515;
    color: #7f3b3b;
    border-color: #3f1d1d;
}

/* 文本框与输入控件 */
QLineEdit {
    background-color: #1e1e24;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #23232b;
}

QLineEdit:disabled {
    background-color: #18181b;
    color: #52525b;
}

/* 单选框与复选框 */
QRadioButton {
    spacing: 8px;
    color: #e4e4e7;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #52525b;
    background-color: #1e1e24;
}

QRadioButton::indicator:hover {
    border-color: #3b82f6;
}

QRadioButton::indicator:checked {
    border: 2px solid #3b82f6;
    background-color: #2563eb;
}

QRadioButton:disabled {
    color: #52525b;
}

QRadioButton::indicator:disabled {
    border-color: #3f3f46;
    background-color: #18181b;
}

/* 表格控件 */
QTableWidget {
    background-color: #1e1e24;
    border: 1px solid #27272a;
    border-radius: 8px;
    gridline-color: #27272a;
    outline: none;
}

QTableWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #27272a;
}

QTableWidget::item:selected {
    background-color: #272738;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #27272a;
    color: #a1a1aa;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #3f3f46;
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
    min-height: 16px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 3px;
}

/* 状态栏与标签 */
QStatusBar {
    background-color: #18181b;
    color: #a1a1aa;
    border-top: 1px solid #27272a;
}

QLabel {
    color: #f4f4f5;
}

QLabel#mutedLabel {
    color: #a1a1aa;
}

/* 滚动条 */
QScrollBar:vertical {
    border: none;
    background: #18181b;
    width: 8px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: #3f3f46;
    min-height: 20px;
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
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background: #3f3f46;
    min-width: 20px;
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
