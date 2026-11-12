from pathlib import Path
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPainter, QColor, QLinearGradient, QBrush, QPen, QPainterPath

def generate():
    res_dir = Path("app/resources")
    res_dir.mkdir(parents=True, exist_ok=True)

    size = 256
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 1. 外部圆角矩形背景（科技蓝渐变）
    bg_path = QPainterPath()
    bg_path.addRoundedRect(QRectF(8, 8, 240, 240), 48, 48)

    gradient = QLinearGradient(0, 0, 256, 256)
    gradient.setColorAt(0.0, QColor("#3b82f6"))
    gradient.setColorAt(1.0, QColor("#1e1b4b"))
    p.fillPath(bg_path, QBrush(gradient))

    pen = QPen(QColor("#93c5fd"), 5)
    p.setPen(pen)
    p.drawPath(bg_path)

    # 2. 内部绘制代表“切分与垂直拼接”的两个色块卡片
    top_card = QPainterPath()
    top_card.addRoundedRect(QRectF(48, 38, 160, 78), 16, 16)
    p.fillPath(top_card, QBrush(QColor("#38bdf8")))
    p.setPen(QPen(QColor("#ffffff"), 3))
    p.drawPath(top_card)

    bottom_card = QPainterPath()
    bottom_card.addRoundedRect(QRectF(48, 140, 160, 78), 16, 16)
    p.fillPath(bottom_card, QBrush(QColor("#6366f1")))
    p.setPen(QPen(QColor("#ffffff"), 3))
    p.drawPath(bottom_card)

    # 3. 中间虚线示意切开拼接
    p.setPen(QPen(QColor("#ffffff"), 3, Qt.PenStyle.DashLine))
    p.drawLine(128, 116, 128, 140)

    p.end()

    png_path = res_dir / "icon.png"
    ico_path = res_dir / "icon.ico"

    img.save(str(png_path), "PNG")
    img.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation).save(str(ico_path), "ICO")
    print(f"Icon generated at {png_path} and {ico_path}")

if __name__ == "__main__":
    generate()
