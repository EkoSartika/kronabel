from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import QRect, QPoint

def inspect_coords():
    main_img = QImage(r"D:\BelOtomatisSekolah\assets\ref_main_mockup.png")
    admin_img = QImage(r"D:\BelOtomatisSekolah\assets\ref_admin_mockup.png")

    print(f"Main: {main_img.width()}x{main_img.height()}")
    # Kotak jam digital pada main_img:
    # Mari kita cek dari y=90 sampai y=240, x=80 sampai x=640
    # Kita cari bounding box kotak hijau jam
    # Kotak hijau jam memiliki warna hijau gelap (R < 30, G > 40, B > 30)
    # Bell badge ada di kiri atas sekitar x=50..120, y=55..125

    # Crop bell badge yang sempurna: x=51, y=60, w=64, h=64
    badge = main_img.copy(QRect(52, 60, 64, 64))
    badge.save(r"D:\BelOtomatisSekolah\assets\bell_badge.png")

    # Crop kotak jam digital utuh: x=96, y=192, w=534, h=124
    # Tunggu, di gambar sebelumnya y=190 kena tombol ON/OFF di bawahnya!
    # Mari kita cari y awal kotak jam:
    # Mari kita crop y=100 sampai 228
    clock_box = main_img.copy(QRect(96, 103, 534, 126))
    clock_box.save(r"D:\BelOtomatisSekolah\assets\clock_box_frame.png")

    # Crop logo sunda admin: x=34, y=58, w=56, h=56
    sunda = admin_img.copy(QRect(33, 56, 56, 56))
    sunda.save(r"D:\BelOtomatisSekolah\assets\sunda_logo.png")

    # Header admin panorama (tanpa teks jika bisa, atau banner atas utuh):
    # Banner atas dari y=35 (bawah titlebar) sampai y=152, x=18 sampai x=1006
    admin_banner = admin_img.copy(QRect(18, 38, 988, 114))
    admin_banner.save(r"D:\BelOtomatisSekolah\assets\admin_banner.png")

    # Header jadwal panel kanan di MainWindow:
    # x=670, y=38, w=316, h=95
    sched_header = main_img.copy(QRect(670, 38, 316, 95))
    sched_header.save(r"D:\BelOtomatisSekolah\assets\main_schedule_header_bg.png")

    print("Coordinates adjusted and saved.")

if __name__ == "__main__":
    inspect_coords()
