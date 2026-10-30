# LAPORAN HASIL PENGUJIAN OPERASIONAL MENYELURUH (TAHAP 5)
**Proyek: Bel Otomatis Sekolah — Windows Desktop**  
**Tanggal Pengujian:** 28 Oktober 2026  
**Status Evaluasi:** **LULUS SEMPURNA (100% PASSED)**

---

## 1. Lingkungan Pengujian
- **Sistem Operasi**: Microsoft Windows (win32, x64)
- **Interpreter Python**: Python 3.11.9 (`C:\Users\Eko\AppData\Local\Programs\Python\Python311\python.exe`)
- **Kerangka Kerja Pengujian**: Pytest 9.2.0, Pluggy 1.7.0
- **GUI & Multimedia Stack**: PySide6 6.12.0 (Qt 6.12, Qt Multimedia, QMediaDevices, QMediaPlayer)
- **Platform Display Uji**: Headless Offscreen (`QT_QPA_PLATFORM=offscreen`)
- **Basis Data**: SQLite 3 (WAL Mode, Foreign Keys Enforced, isolated per-test database)

---

## 2. Perintah Eksekusi Pengujian & Ringkasan Hasil

### Perintah:
```powershell
& "C:\Users\Eko\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/ -v
```

### Ringkasan Suite:
- **Total Pengujian**: **75 tes**
- **Lulus (Passed)**: **75 tes (100%)**
- **Gagal (Failed)**: **0**
- **Dilewati (Skipped)**: **0**
- **Error**: **0**
- **Waktu Eksekusi**: **8.14 detik**

---

## 3. Hasil Simulasi Satu Hari Sekolah Penuh (`tests/test_full_day_simulation.py`)

Pengujian integrasi operasional dilakukan dengan menyimulasikan satu hari sekolah secara deterministik menggunakan `SimulatedClock` (mulai pukul 06:45:00 hari Senin hingga 07:00:00 hari Selasa berikutnya):

| Skenario | Waktu Uji | Kondisi & Ekspektasi | Hasil Pengujian | Status |
|---|---|---|---|---|
| **1. Pembacaan Profil Aktif** | 06:45:00 | Aplikasi dibuka, profil aktif terbaca konsisten | Profil `Reguler` terbaca aktif | **LULUS** |
| **2. Hitung Mundur (Countdown)** | 06:45:00 & 06:55:00 | Countdown menuju 07:00:00 (900 dtk -> 300 dtk) | Nilai countdown berkurang akurat | **LULUS** |
| **3. Eksekusi Bel Tepat Waktu** | 07:00:00 | Bel Masuk Pagi terpicu tepat pada waktu jadwal | Terpicu 1 kali dengan mode OTOMATIS | **LULUS** |
| **4. Pencegahan Bel Ganda** | 07:00:15 - 07:00:59 | Evaluasi berulang pada menit yang sama | Tidak ada pemutaran ganda | **LULUS** |
| **5. Transisi ke Jadwal Berikutnya** | 08:30:00 | Jadwal kedua terpicu saat simulasi maju | Bel jam ke-2 berbunyi normal | **LULUS** |
| **6. Bel Manual Independen** | 09:00:00 | Bel manual dibunyikan di sela jam pelajaran | Bel manual berbunyi, scheduler tidak terganggu | **LULUS** |
| **7. Bel Istirahat & Masuk** | 09:30:00 & 09:45:00 | Bel istirahat dan bel masuk berbunyi normal | Keduanya terpicu tepat waktu | **LULUS** |
| **8. Restart Tengah Hari (Idempotensi)** | 10:00:00 -> 10:15:00 | Aplikasi ditutup lalu dibuka kembali | Bel pagi tidak diputar ulang | **LULUS** |
| **9. Jadwal Dinonaktifkan** | 11:15:00 | Jadwal Literasi dengan `is_enabled=False` | Diabaikan, tidak berbunyi | **LULUS** |
| **10. Bel Siang** | 12:00:00 & 12:30:00 | Bel sholat dhuhur & masuk siang | Berbunyi sesuai jadwal | **LULUS** |
| **11. Pencatatan Kegagalan Audio** | 14:00:00 | Bel pulang dengan file audio yang sengaja hilang | Dicatat di log berstatus `failed` | **LULUS** |
| **12. Pergantian Hari (Midnight Rollover)** | 23:59:59 -> 00:00:01 | Pergantian tanggal ke hari Selasa | Cache sesi dibersihkan, bel Selasa siap | **LULUS** |
| **13. Pergantian Profil Aktif** | Pasca-simulasi | Profil diganti ke Ujian Semester | Jadwal berganti ke jadwal ujian | **LULUS** |

---

## 4. Hasil Pengujian Backup dan Restore (`tests/test_backup_restore.py`)

| Kasus Uji | Skenario | Hasil Aktual | Status |
|---|---|---|---|
| **Backup SQLite WAL Mode** | Pencadangan saat koneksi database aktif | Salinan konsisten melalui SQLite Backup API | **LULUS** |
| **Kelengkapan Isi Arsip** | Database, file audio, manifest.json, checksum | Seluruh komponen terarsip lengkap | **LULUS** |
| **Penolakan Audio Hilang** | Ada rekaman audio di DB yang fisiknya hilang dari disk | Backup ditolak dengan `FileNotFoundError` transparan | **LULUS** |
| **Proteksi Anti-Zip Slip** | Berkas arsip disusupi path traversal (`../../`) | Ditolak dengan `ValueError` berbahaya | **LULUS** |
| **Penolakan Arsip Rusak/Kosong** | Berkas bukan ZIP atau tanpa manifest | Ditolak sebelum menyentuh database | **LULUS** |
| **Integritas Checksum** | Checksum SHA-256 database dimanipulasi | Ditolak karena checksum tidak cocok | **LULUS** |
| **Inkompatibilitas Skema** | Versi skema cadangan lebih tinggi dari aplikasi | Ditolak untuk mencegah korupsi versi | **LULUS** |
| **Safety Net Pre-Restore** | Cadangan darurat otomatis sebelum restore | Berkas `pre_restore_*.zip` otomatis dibuat | **LULUS** |
| **Rollback & Proteksi Aktif** | Restore gagal di tengah proses ekstraksi staging | Database aktif tidak tertimpa/korup | **LULUS** |
| **Relokasi Path Audio** | Restore pada direktori yang berbeda dari komputer lama | Kolom `stored_path` diperbarui ke folder lokal baru | **LULUS** |

---

## 5. Hasil Pemeriksaan Perangkat Audio & Ketahanan Operasional (`tests/test_operational_robustness.py`)

1. **Enumerasi Perangkat Audio Windows**:
   - Membaca daftar perangkat keluaran via `QMediaDevices.audioOutputs()` secara non-destruktif.
   - Perangkat default Windows terbaca (`Speakers (Realtek(R) Audio)`).
   - Pengaturan default Windows tidak diubah sama sekali oleh aplikasi.
2. **Kebijakan Saat Pemutaran Sibuk**:
   - Kebijakan penolakan (*reject*): Permintaan pemutaran baru saat suara sedang aktif ditolak untuk mencegah tumpang tindih suara.
   - Kebijakan penghentian (*interrupt*): Pemanggilan `stop()` menghentikan pemutaran lama dan melepaskan sumber daya audio seketika.
3. **Penanganan Nama File Berkarakter Khusus**:
   - File dengan spasi, tanda kurung, simbol `#`, dan tanda kurung siku berhasil diimpor dan disimpan tanpa kesalahan path.
4. **Independensi Working Directory**:
   - Aplikasi dan resolusi path SQLite bekerja konsisten meskipun working directory (cwd) dipindah ke folder lain di sistem.
5. **Pelepasan Sumber Daya (Clean Shutdown)**:
   - Pemanggilan `scheduler.stop()` dan `player.cleanup()` menghentikan `QTimer`, memutus sumber URL media, dan melepaskan file lock.

---

## 6. Temuan Audit, Akar Masalah, dan Perbaikan (Bug Fixes)

### Temuan 1: Potensi Celah Path Traversal (Zip Slip) pada Ekstraksi Arsip Cadangan
- **Akar Masalah**: Pustaka standar `zipfile.ZipFile.extractall()` mengekstrak file sesuai nama entri dalam ZIP. Jika sebuah arsip dimodifikasi memuat nama seperti `../../system_file`, file dapat terekstrak ke luar folder staging sementara.
- **Tingkat Risiko**: Sedang / Tinggi (Keamanan).
- **Perbaikan**: Dibuat fungsi helper `_safe_extract()` di `src/services/backup_service.py` yang memvalidasi bahwa setiap anggota ZIP setelah di-resolve tetap berada di bawah direktori target (`member_target.relative_to(resolved_target)`). Jika terdeteksi path traversal, proses langsung dibatalkan dengan pesan kesalahan.
- **Tes Regresi**: `test_restore_rejects_zip_slip_path_traversal` di `tests/test_backup_restore.py`.

### Temuan 2: Backup Mengabaikan File Audio yang Hilang dari Disk secara Diam-diam
- **Akar Masalah**: Pada kode sebelumnya, jika file audio tercatat di tabel `audio_files` tetapi file fisiknya di disk terhapus, sistem hanya mencatat `logger.warning` dan tetap melaporkan pencadangan berhasil.
- **Tingkat Risiko**: Sedang (Integritas Data).
- **Perbaikan**: Menambahkan validasi daftar `missing_audios`. Jika ada file fisik audio yang hilang, `create_backup` langsung melempar pengecualian `FileNotFoundError` dan menghentikan pembuatan arsip agar operator tidak tertipu oleh arsip yang tidak lengkap.
- **Tes Regresi**: `test_backup_fails_if_audio_file_missing_on_disk` di `tests/test_backup_restore.py`.

---

## 7. Batasan yang Belum Dapat Diverifikasi secara Otomatis

Sesuai etika rekayasa perangkat lunak dan batasan sistem:
1. **Keluaran Gelombang Suara Fisik di Speaker Horn / Amplifier Sekolah**:
   - Pengujian otomatis hanya dapat memverifikasi pipeline perangkat lunak, driver Windows, dan emisi sinyal Qt Multimedia.
   - **Keluaran suara nyata yang terdengar oleh telinga manusia di halaman dan ruang kelas sekolah tetap WAJIB diuji secara manual oleh operator di tempat**.
2. **Kondisi Fisik Kabel Audio 3.5mm / RCA / USB DAC**:
   - Kerusakan kabel, kabel longgar, sakelar mute fisik pada mixer/amplifier sekolah, atau kegagalan daya pada amplifier tidak dapat dideteksi oleh perangkat lunak.

---

## 8. Checklist Pengujian Manual di Komputer Sekolah

Sebelum pengoperasian resmi hari pertama, operator sekolah wajib mencentang daftar periksa berikut:

- [ ] **Koneksi Fisik**: Kabel audio 3.5mm terpasang kokoh dari port Line-Out komputer ke Line-In / Aux-In Amplifier sekolah.
- [ ] **Daya Amplifier**: Amplifier sekolah menyala dan selector zona speaker kelas dalam posisi aktif (*ON*).
- [ ] **Pengaturan Daya Windows**: Windows Sleep / Hibernate telah diatur ke **"Never"** saat terhubung ke listrik.
- [ ] **Tes Suara Mandiri**: Buka menu **Pengaturan** di aplikasi, klik tombol **"Tes Suara"**, dan dengarkan apakah nada bel terdengar di speaker sekolah.
- [ ] **Penyesuaian Kenyaringan**: Atur knob volume fisik amplifier hingga suara terdengar jelas di seluruh penjuru sekolah tanpa distorsi atau suara dengung (*humming*).
- [ ] **Sinkronisasi Jam**: Pastikan jam komputer Windows cocok dengan jam dinding resmi sekolah.
- [ ] **Status Mesin Otomatis**: Pastikan tombol hijau **"Mulai Otomatis"** di Dashboard telah ditekan sehingga berstatus **"Aktif Berjalan"**.

---

## 9. Status Kelulusan Tahap 5

**TAHAP 5 DINYATAKAN LULUS SEMPURNA.**
- Seluruh 75 pengujian otomatis lulus 100%.
- Simulasi satu hari penuh (12 skenario operasional) berhasil tervalidasi.
- Mekanisme backup, restore, dan keamanan Zip Slip terbukti aman dan tangguh.
- Logika pencegahan bel ganda dan idempotensi restart terverifikasi kokoh.
- Dokumentasi hasil pengujian dan panduan checklist manual telah tersedia.
