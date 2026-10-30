# Bel Otomatis Sekolah (Windows Desktop)

Aplikasi desktop Windows untuk membunyikan bel sekolah secara otomatis sesuai jadwal harian, dilengkapi antarmuka modern, pemutar audio MP3/WAV, jam digital, hitung mundur, dan pencatatan riwayat pembunyian bel.

## Fitur Utama

1. **Jadwal Bel Harian (Senin–Sabtu)**: Pengaturan waktu, kegiatan, dan file audio bel dengan validasi benturan jadwal otomatis.
2. **Profil Jam Pelajaran**: Mendukung pergantian profil (Reguler, Ramadan, Ujian, Kustom) tanpa menimpa data jadwal lain.
3. **Pemutar Audio MP3 & WAV**: Pemutaran audio lokal berkualitas tinggi menggunakan Qt Multimedia.
4. **Hitung Mundur & Jam Digital**: Tampilan waktu nyata Windows dan countdown akurat ke bel berikutnya.
5. **Tombol Kontrol Manual & Tes Audio**: Kemampuan membunyikan bel seketika tanpa merusak jadwal otomatis.
6. **Riwayat Pembunyian Bel**: Pencatatan status eksekusi dengan idempotensi (mencegah bel ganda setelah restart).
7. **Offline-First & Windows Native**: Berjalan 100% offline tanpa ketergantungan cloud atau internet.

## Persyaratan Sistem

- Windows 10 / 11 (64-bit)
- Python 3.11+
- PySide6 (Qt 6)
- SQLite3

## Struktur Direktori

```text
BelOtomatisSekolah/
  main.py                # Titik masuk utama aplikasi desktop
  requirements.txt       # Dependensi Python
  README.md              # Dokumentasi proyek
  assets/                # Aset ikon dan suara bawaan
  src/
    core/                # Konfigurasi path data persisten Windows
    database/            # SQLite connection, schema, repositories
    models/              # Dataclass entitas dan validasi data
    services/            # Scheduler, audio player, clock service
    ui/                  # Antarmuka PySide6 modular
  tests/                 # Suite pengujian otomatis (pytest)
  installer/             # Skrip packaging PyInstaller & Inno Setup
  docs/                  # Dokumentasi teknis & panduan operator
```

## Menjalankan Aplikasi

```powershell
# Jalankan aplikasi
python main.py
```

## Menjalankan Pengujian

```powershell
python -m pytest tests/ -v
```
