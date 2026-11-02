# LAPORAN RESMI REBRANDING IDENTITAS APLIKASI KRONABEL v1.2.4
**Tanggal Rilis**: 2 November 2026  
**Status**: Produksi / Rilis Stabil  
**OS Target**: Windows 10 & Windows 11 (64-bit)  
**Lingkungan Build**: Python 3.11.9, PySide6 6.12.0 (Qt 6), Inno Setup 6.4.2  

---

## 1. Rangkuman Rebranding & Penyelarasan Identitas

Aplikasi desktop telah resmi diperbarui identitasnya menjadi **Kronabel** (versi **1.2.4**). Seluruh titik identitas di sistem operasi Windows, penginstal (*installer*), pintasan (*shortcuts*), metadata biner, antarmuka pengguna, serta website resmi telah diselaraskan secara konsisten.

### Identitas Produk Resmi
- **Nama Aplikasi Windows / Installed Apps**: `Kronabel version 1.2.4`
- **Control Panel / Add or Remove Programs**: `Kronabel version 1.2.4`
- **Keterangan Produk**: `Aplikasi Bel Otomatis Sekolah`
- **Pintasan Start Menu & Desktop**: `Kronabel`
- **Nama Berkas Biner Executable**: `KRONABEL.exe`
- **Merek Visual & Judul Jendela Desktop**: `KRONABEL v1.2.4`
- **Posisi Logo Dashboard**: Berada tepat di tengah horizontal panel kiri (sejajar vertikal dengan pusat jam digital di bawahnya).
- **Pengaturan Checkbox Installer**: Kedua opsi (*Create a desktop shortcut* dan *Jalankan KRONABEL saat komputer Windows dinyalakan*) aktif secara default (*checked by default*) dengan kebebasan bagi pengguna untuk menghapus centang jika tidak diinginkan.

---

## 2. Kompatibilitas Upgrade & Preservasi Data (Zero Data Loss)

1. **Inno Setup AppId Tidak Berubah**:
   `AppId={{C47F892A-3D5E-4B91-81FE-B9E4F5712A80}` dipertahankan secara utuh. Ketika pengguna menginstal `KRONABEL_Setup_v1.2.4.exe` di atas instalasi lama (v1.2.3 atau sebelumnya), Windows Installer secara otomatis memperbarui entri yang ada tanpa membuat entri ganda pada daftar *Installed Apps* maupun *Add or Remove Programs*.

2. **Preservasi & Migrasi Database Persisten**:
   Fungsi `get_user_data_dir()` di `src/core/config.py` secara otomatis memeriksa apakah data lama di `%APPDATA%\BelOtomatisSekolah` tersedia. Jika folder baru `%APPDATA%\KRONABEL` belum memiliki database, seluruh subdirektori penting (`data\bel_sekolah.db`, `sounds\`, dan `backups\`) disalin secara transparan tanpa pernah menghapus folder lama. Pengguna lama tidak akan kehilangan jadwal bel, profil jam pelajaran, rekaman audio kustom, kata sandi, maupun riwayat bel.

3. **Migrasi Registri Startup Windows (Autostart)**:
   Modul `src/core/autostart.py` kini mendaftarkan autostart pada kunci registri `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` dengan nama `KRONABEL`, sekaligus membersihkan entri usang `BelOtomatisSekolah`.

---

## 3. Pemeliharaan Fitur Audio Eksternal (v1.2.3)

Seluruh perbaikan audio dari v1.2.3 tetap aktif 100%:
- Perutean otomatis ke speaker eksternal saat kabel jack audio 3,5 mm dicolokkan ke komputer.
- Pemindai perangkat dinamis melalui `QMediaDevices.audioOutputsChanged`.
- Opsi pemilihan perangkat audio otomatis maupun manual di menu Pengaturan.
- Tombol **Segarkan Perangkat** dan tombol fisik **Tes Suara** untuk menguji pengeras suara secara langsung.
- Arsitektur *Single Active Audio Controller* untuk mencegah bentrokan suara ganda.

---

## 4. Hasil Pengujian Otomatis

Rangkaian 143 pengujian (*pytest suite*) dijalankan pada biner mandiri dan seluruh modul aplikasi:
- **Total Test**: 143
- **Passed**: 143 (100% PASS)
- **Failed**: 0

---

## 5. Rincian Artefak Distribusi v1.2.4

| Artefak | Jalur Berkas | Ukuran | Checksum SHA-256 |
|---|---|---|---|
| **Standalone Binary** | `D:\BelOtomatisSekolah\dist\KRONABEL\KRONABEL.exe` | 1.88 MB (1.975.155 bytes) | `50238907b7944d68c6689580edfa35fb9890d6274e9902f89b045d5b5bbc356f` |
| **Setup Installer** | `D:\BelOtomatisSekolah\release\KRONABEL_Setup_v1.2.4.exe` | 45.64 MB (47.852.146 bytes) | `d0357d41e21ba1d8b862bce1e539962d051274ecde6b5535fd5e436021f163ab` |
| **Portable ZIP** | `D:\BelOtomatisSekolah\release\KRONABEL_Portable_v1.2.4.zip` | 79.80 MB (83.677.286 bytes) | `82a82b4c6dbd282d382319e973de5c9bd0461a6d8ab7c4aba1eaea7fba6b7761` |

### Metadata Windows Executable (KRONABEL.exe)
- **Product Name**: `Kronabel`
- **File Description**: `Kronabel — Aplikasi Bel Otomatis Sekolah`
- **File Version**: `1.2.4.0`
- **Product Version**: `1.2.4.0`
- **Original Filename**: `KRONABEL.exe`
- **Company Name**: `Pengembang Kronabel`
- **Legal Copyright**: `Hak Cipta (C) 2026 KRONABEL`

---

## 6. Pembaruan Website Resmi KRONABEL

- **Repositori**: `https://github.com/EkoSartika/kronabel-website.git`
- **Branch**: `main`
- **Status Produksi Vercel**: `https://kronabel.vercel.app` (HTTP 200 OK — Live)
- **Halaman Terdampak**: Beranda, Pusat Unduhan (`/unduh`), Riwayat Versi (`/riwayat-versi`), Panduan (`/panduan`), dan Metadata SEO JSON-LD.
