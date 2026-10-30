from PySide6.QtGui import QImage, QColor, QPainter, QLinearGradient
from PySide6.QtCore import QRect, QPoint

def process():
    main_img = QImage(r"D:\BelOtomatisSekolah\assets\ref_main_mockup.png")

    # Lonceng emas:
    # Mari kita cek dari y=40 sampai y=130 di x=40..130
    # Kita cari bounding box warna emas lonceng
    badge = main_img.copy(QRect(52, 45, 66, 68))
    badge.save(r"D:\BelOtomatisSekolah\assets\bell_badge.png")

    # Bersihkan teks jam di clock_box_frame.png untuk menjadi background template jam yang dinamis:
    clock_box = QImage(r"D:\BelOtomatisSekolah\assets\clock_box_frame.png")
    # Bagian teks ada di x=120..420, y=10..115
    # Ambil sample tekstur latar hijau gelap di sekitarnya
    p = QPainter(clock_box)
    grad = QLinearGradient(120, 0, 420, 0)
    # Latar gradien hijau zamrud gelap pegunungan
    grad.setColorAt(0.0, QColor(9, 53, 40, 245))
    grad.setColorAt(0.5, QColor(7, 47, 35, 245))
    grad.setColorAt(1.0, QColor(9, 53, 40, 245))
    p.setBrush(grad)
    p.setPen(QColor(0, 0, 0, 0)) # No border
    p.drawRoundedRect(QRect(110, 10, 314, 106), 6, 6)
    p.end()
    clock_box.save(r"D:\BelOtomatisSekolah\assets\clock_bg_clean.png")

    print("Badge and clean clock bg generated.")

if __name__ == "__main__":
    process()
