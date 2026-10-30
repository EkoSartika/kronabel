# PANDUAN BUILD, INSTALASI, DAN PEMELIHARAAN SISTEM
**Proyek: Bel Otomatis Sekolah (Windows 10 & Windows 11 Desktop 64-bit)**  
**Versi: 1.2.0 (Rilis & Installer Resmi Windows 10/11)**

---

## 1. Persyaratan Lingkungan Build
Untuk mengompilasi aplikasi dari kode sumber ke paket biner dan installer:
- **Sistem Operasi**: Windows 10 atau Windows 11 (64-bit).
- **Python**: Python 3.11.x (Direkomendasikan Python 3.11.9).
- **PyInstaller**: Versi 6.22.3 atau lebih baru.
- **Inno Setup**: Inno Setup 6 (ISCC.exe) untuk menghasilkan berkas setup `.exe`.
- **Dependensi Utama**: `PySide6==6.12.0` (Qt Multimedia, QtCore, QtGui, QtWidgets, QtNetwork).

---

## 2. Struktur Artefak Distribusi

Setelah proses build dijalankan melalui skrip `build_release.py`:
- `dist/BelOtomatisSekolah/`: Folder distribusi biner standalone (`onedir`).
  - `BelOtomatisSekolah.exe`: Berkas biner utama aplikasi (GUI Windows tanpa konsol hitam).
  - `_internal/`: Pustaka Python, runtime DLL, dan plugin PySide6/Qt Multimedia.
  - `assets/`: Berkas ikon aplikasi (`app_icon.png`, `app_icon.ico`).
- `release/`: Paket rilis akhir untuk distribusi pengguna Windows 10/11.
  - `BelOtomatisSekolah_Setup_v1.2.0.exe`: Installer Windows lengkap (Inno Setup 6).
  - `BelOtomatisSekolah_Portable_v1.2.0.zip`: Paket portabel siap pakai tanpa instalasi.
  - `RELEASE_INFO.txt`: Informasi rilis resmi, stempel waktu, dan checksum SHA-256.

---

## 3. Langkah Kompilasi (Build Otomatis)

1. Buka terminal PowerShell di root direktori proyek (`D:\BelOtomatisSekolah`).
2. Jalankan skrip rilis terpadu:
   ```powershell
   & "C:\Users\Eko\AppData\Local\Programs\Python\Python311\python.exe" build_release.py
   ```
3. Skrip akan secara otomatis:
   - Membersihkan cache build lama.
   - Menjalankan PyInstaller menggunakan `BelOtomatisSekolah.spec`.
   - Memverifikasi kelengkapan folder `dist` dan ikon aplikasi.
   - Menjalankan Inno Setup Compiler (`ISCC.exe`) untuk membangun `release/BelOtomatisSekolah_Setup_v1.0.0.exe`.
   - Menghasilkan checksum SHA-256 dan ringkasan ukuran berkas.

---

## 4. Lokasi Data Pengguna Persisten (Keamanan Data)

Aplikasi menerapkan pemisahan ketat antara **berkas program instalasi** dan **data pengguna**:

| Komponen | Lokasi di Sistem Windows | Sifat & Perilaku |
|---|---|---|
| **Program Aplikasi** | `C:\Program Files\Bel Otomatis Sekolah` (atau folder pilihan operator) | Bersifat *read-only* saat dijalankan; dapat di-update atau di-uninstall tanpa hak administrator harian. |
| **Basis Data SQLite** | `%APPDATA%\BelOtomatisSekolah\data\bel_sekolah.db` | **Persisten**. Tidak berada di folder instalasi dan **TIDAK AKAN PERNAH DIHAPUS** saat aplikasi di-update atau di-uninstall. |
| **Pustaka Audio Bel** | `%APPDATA%\BelOtomatisSekolah\sounds\` | **Persisten**. Seluruh file MP3/WAV tersimpan aman di folder pengguna. |
| **Cadangan (Backup)** | `%APPDATA%\BelOtomatisSekolah\backups\` (atau folder pilihan operator) | **Persisten**. Cadangan darurat pra-restore dan arsip backup tersimpan aman. |
| **Berkas Log** | `%APPDATA%\BelOtomatisSekolah\app.log` | Mencatat riwayat operasional teknis dan diagnosis kesalahan. |

---

## 5. Prosedur Instalasi di Komputer Sekolah

### Menggunakan Installer (`BelOtomatisSekolah_Setup_v1.0.0.exe`):
1. Salin berkas `BelOtomatisSekolah_Setup_v1.0.0.exe` ke komputer sekolah target (melalui flashdisk atau jaringan lokal). Komputer target **TIDAK MEMERLUKAN PYTHON**.
2. Klik dua kali pada berkas installer.
3. Ikuti wizard instalasi:
   - Pilih direktori instalasi (default: `C:\Program Files\Bel Otomatis Sekolah` atau folder Program Files pengguna).
   - Centang opsi *Buat shortcut di Desktop* jika operator menginginkan ikon di layar utama.
   - Klik **Install**.
4. Setelah instalasi selesai, centang *Jalankan Bel Otomatis Sekolah* lalu klik **Finish**.
5. Aplikasi akan otomatis menginisialisasi database baru di `%APPDATA%\BelOtomatisSekolah` jika ini adalah instalasi pertama kali.

### Menggunakan Paket Portabel (`dist/BelOtomatisSekolah`):
1. Salin folder `BelOtomatisSekolah` dari folder `dist/` ke lokasi mana saja (misalnya `D:\AplikasiSekolah\BelOtomatisSekolah`).
2. Buat shortcut dari `BelOtomatisSekolah.exe` ke Desktop.
3. Klik dua kali shortcut untuk menjalankan aplikasi.

---

## 6. Prosedur Pembaruan Versi (Update)

1. Unduh installer versi baru.
2. Jalankan installer langsung di komputer yang sudah terpasang versi sebelumnya.
3. Installer akan menimpa berkas program biner lama dengan versi terbaru.
4. **Jaminan Keamanan**: Database jadwal, profil, riwayat pembunyian, dan file audio di `%APPDATA%\BelOtomatisSekolah` **TIDAK AKAN TERTAMPAI ATAU TERHAPUS**, sehingga sekolah dapat langsung melanjutkan operasional tanpa perlu memasukkan jadwal ulang.

---

## 7. Prosedur Penghapusan Aplikasi (Uninstalasi)

1. Buka *Windows Settings* -> *Apps* -> *Installed Apps* (atau *Control Panel* -> *Programs and Features*).
2. Cari **Bel Otomatis Sekolah**, lalu klik **Uninstall**.
3. Wizard uninstalasi akan menghapus seluruh berkas program dan shortcut dari komputer.
4. **Proteksi Data Pengguna**: Seluruh basis data jadwal, riwayat, dan arsip audio di `%APPDATA%\BelOtomatisSekolah` tetap utuh. Jika suatu saat aplikasi dipasang kembali, seluruh data sekolah akan langsung terbaca seperti semula.
5. Jika operator ingin menghapus seluruh data secara permanen, operator dapat menghapus folder `%APPDATA%\BelOtomatisSekolah` secara manual dengan sengaja.

---

## 8. Verifikasi Pasca-Instalasi (Checklist Operator)

Setelah instalasi selesai di komputer sekolah:
- [ ] Buka aplikasi melalui shortcut Desktop atau Start Menu.
- [ ] Pastikan jendela utama muncul dengan tema modern dan jam digital aktif berdetak.
- [ ] Buka menu **Audio Bel** dan klik tombol **Tes Suara** untuk menguji speaker monitor komputer.
- [ ] Sambungkan kabel audio ke amplifier sekolah dan lakukan tes suara fisik sesuai panduan di `PANDUAN_OPERATOR.md`.
- [ ] Buka menu **Pengaturan**, klik tombol **Cadangkan Data (Backup)** untuk membuat cadangan awal.
