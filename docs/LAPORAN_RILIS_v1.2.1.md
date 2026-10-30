# LAPORAN RILIS RESMI: BEL OTOMATIS SEKOLAH v1.2.1

**Tanggal Rilis:** 29 Oktober 2026  
**Target Sistem Operasi:** Windows 10 & Windows 11 (64-bit)  
**Lingkungan Runtime:** Python 3.11.9 + PySide6 6.12.0 (Qt 6.12 Native)  
**Status Pengujian:** 130 Pengujian Lulus (100% PASS, 0 Fail, 0 Skip)

---

## 1. Ringkasan Pembaruan (Update v1.2.1)

Pembaruan versi **v1.2.1** berfokus pada implementasi **Sistem Interupsi dan Prioritas Audio Bel Terpusat** (*Single Active Audio Controller*) pada aplikasi **Bel Otomatis Sekolah**. Pembaruan ini mengatasi keterbatasan pemutaran audio pada versi sebelumnya di mana pemutaran audio baru ditolak jika ada audio yang sedang aktif, sehingga operator tidak dapat langsung mengganti lagu bel manual atau menginterupsi bel otomatis.

### Perilaku Sistem Baru:
1. **Single Active Audio Controller:** Maksimal tepat satu audio bel yang dapat berbunyi pada satu waktu. Audio tidak pernah bertumpuk, bercampur suara (*overlapping*), atau membiarkan dua pemutar aktif bersamaan.
2. **Interupsi Bel Otomatis oleh Bel Manual:** Ketika bel otomatis sedang berbunyi dan operator menekan tombol bel manual, audio otomatis langsung dihentikan secara bersih, dicatat sebagai `interrupted` pada riwayat log, dan audio manual langsung dimainkan seketika tanpa penundaan.
3. **Interupsi Antar-Bel Manual (A -> B):** Ketika bel manual A sedang berbunyi dan tombol bel manual B ditekan, audio A langsung dihentikan dan audio B langsung dimainkan.
4. **Mulai Ulang dari Awal (Same Button Pressed Twice):** Jika tombol bel manual yang sama ditekan kembali saat audio tersebut masih berjalan, pemutaran sebelumnya dihentikan dan dimulai ulang dari awal (`position = 0`).
5. **Tombol Stop Universal:** Tombol `Stop` (baik di panel utama maupun dialog pustaka) menghentikan audio apa pun yang sedang aktif (otomatis maupun manual) dan langsung membersihkan status audio secara tuntas.
6. **Token Sesi Pemutaran (*Session ID*):** Setiap perintah pemutaran memiliki nomor sesi inkremental unik (`active_session_id`). Sinyal atau *callback* terlambat (*stale callbacks*) dari pemutar audio lama yang sudah dihentikan diabaikan sepenuhnya dan tidak dapat merusak atau mengubah status audio yang baru.
7. **Independensi Scheduler Otomatis:** Interupsi audio manual sama sekali tidak menonaktifkan scheduler otomatis (status ON/OFF mesin penjadwal tetap independen dari status pemutar audio). Jadwal otomatis yang terinterupsi tidak diulang kembali pada hari yang sama, dan jadwal otomatis berikutnya tetap berjalan normal sesuai jamnya.
8. **Kebijakan Konflik Deterministik:** Jika jam jadwal otomatis tiba ketika bel manual masih aktif berbunyi, aplikasi tidak memotong bel manual secara diam-diam; peristiwa jadwal tersebut dicatat secara eksplisit di database `bell_logs` dengan status `missed` dan pesan alasan konflik, sementara bel manual tetap dibiarkan selesai dengan aman.
9. **Konsistensi Tampilan UI:** Panel kontrol utama, dashboard, dan pustaka lagu langsung menyinkronkan label, status badge, dan tooltip tombol `Stop` dengan status pemutar aktif riil. Setelah audio berhenti, selesai, gagal, atau diinterupsi, status UI langsung kembali bersih (`IDLE` / tidak ada audio aktif).

---

## 2. Berkas yang Diubah / Ditambahkan

| No | Berkas | Deskripsi Perubahan |
|---|---|---|
| 1 | [`src/services/audio_player.py`](file:///d:/BelOtomatisSekolah/src/services/audio_player.py) | Mengimplementasikan *Single Active Audio Controller* dengan `active_session_id`, `start_count`, `current_mode`, `current_audio_id`, sinyal `playback_interrupted`, parameter `interrupt=True` (default) pada `play_file` & `play_audio_id`, pencegahan callback usang (`_suppress_callbacks`), penanganan `QMediaPlayer.MediaStatus.InvalidMedia`, dan pembersihan metadata aktif `_clear_active_metadata()`. |
| 2 | [`src/services/scheduler.py`](file:///d:/BelOtomatisSekolah/src/services/scheduler.py) | Menghubungkan sinyal `playback_interrupted`, mengimplementasikan kebijakan konflik deterministik (`status="missed"` saat bel manual aktif), memperbarui `trigger_manual_bell` untuk menginterupsi audio aktif secara teratur tanpa mengubah `is_active`, dan memastikan jadwal berikutnya tetap berjalan normal. |
| 3 | [`src/database/repositories.py`](file:///d:/BelOtomatisSekolah/src/database/repositories.py) | Memperbarui klausa kueri `is_schedule_executed_today` pada `BellLogRepository` untuk menyertakan status `'interrupted'` dan `'missed'`, sehingga jadwal otomatis yang terinterupsi atau terlewati karena konflik tidak pernah dieksekusi ulang secara keliru. |
| 4 | [`src/ui/main_window.py`](file:///d:/BelOtomatisSekolah/src/ui/main_window.py) | Menghubungkan seluruh sinyal status `AudioPlayer` (`status_changed`, `playback_started`, `playback_completed`, `playback_failed`, `playback_interrupted`), menyinkronkan tooltip `btn_stop_audio`, dan mengarahkan penekanan tombol manual melalui `self.scheduler.trigger_manual_bell`. |
| 5 | [`src/ui/audio_code_page.py`](file:///d:/BelOtomatisSekolah/src/ui/audio_code_page.py) | Menyinkronkan tombol putar uji tabel pustaka dengan status pemutar audio terpusat via `status_changed`, membersihkan `playing_audio_id` saat diinterupsi oleh bel lain, dan mengirimkan `mode="PREVIEW"`. |
| 6 | [`src/ui/dashboard.py`](file:///d:/BelOtomatisSekolah/src/ui/dashboard.py) | Memperbarui badge dan tooltip status audio operasional pada dashboard agar mencerminkan judul audio aktif riil secara akurat. |
| 7 | [`src/__init__.py`](file:///d:/BelOtomatisSekolah/src/__init__.py) | Menaikkan versi aplikasi menjadi `1.2.1`. |
| 8 | [`src/core/config.py`](file:///d:/BelOtomatisSekolah/src/core/config.py) | Menetapkan konstanta `APP_VERSION = "1.2.1"`. |
| 9 | [`installer/BelOtomatisSekolah.iss`](file:///d:/BelOtomatisSekolah/installer/BelOtomatisSekolah.iss) | Memperbarui versi installer Inno Setup menjadi `1.2.1`. |
| 10 | [`build_release.py`](file:///d:/BelOtomatisSekolah/build_release.py) | Memperbarui skrip otomatisasi rilis ke versi `1.2.1`. |
| 11 | [`tests/test_audio_player.py`](file:///d:/BelOtomatisSekolah/tests/test_audio_player.py) | Memperbarui tes konkurensi untuk memvalidasi kebijakan default `interrupt=True` vs penolakan eksplisit `interrupt=False`. |
| 12 | [`tests/test_operational_robustness.py`](file:///d:/BelOtomatisSekolah/tests/test_operational_robustness.py) | Memperbarui pengujian ketahanan pemutaran sibuk dengan kedua kebijakan. |
| 13 | [`tests/test_installed_executable.py`](file:///d:/BelOtomatisSekolah/tests/test_installed_executable.py) | Menyesuaikan nama paket rilis resmi target ke `v1.2.1`. |
| 14 | [`tests/test_audio_interruption_priority.py`](file:///d:/BelOtomatisSekolah/tests/test_audio_interruption_priority.py) | **Berkas Pengujian Baru**: Pengujian otomatis komprehensif mencakup ke-15 skenario sistem interupsi audio dan kebijakan prioritas. |

---

## 3. Hasil Pengujian Otomatis (Test Suite)

Seluruh test suite dijalankan menggunakan Python 3.11.9:
```text
pytest tests/ -v
============================ 130 passed in 27.72s =============================
```

### Verifikasi 15 Skenario Wajib (Semua Lulus):
1. **Skenario 1 (Bel Otomatis -> Manual):** Bel otomatis pukul 07:00 diinterupsi oleh bel manual BEL B -> audio otomatis berhenti dan dicatat `interrupted`, audio manual langsung berbunyi (`status='playing'`). (**LULUS**)
2. **Skenario 2 (Manual A -> Manual B):** Bel manual A diinterupsi oleh bel manual B -> audio A berhenti, sesi bertambah, audio B langsung berbunyi. (**LULUS**)
3. **Skenario 3 (Same Manual Repeated):** Tombol manual yang sama ditekan dua kali -> audio berhenti dan dimulai ulang dari posisi 0. (**LULUS**)
4. **Skenario 4 (Stop Otomatis):** Tombol Stop menghentikan bel otomatis seketika dan membersihkan metadata aktif menjadi kosong/None. (**LULUS**)
5. **Skenario 5 (Stop Manual):** Tombol Stop menghentikan bel manual dan status kembali bersih. (**LULUS**)
6. **Skenario 6 (Selesai Normal):** Pemutaran audio selesai normal (`EndOfMedia`) -> status berubah menjadi `COMPLETED` dan metadata aktif dibersihkan. (**LULUS**)
7. **Skenario 7 (Kegagalan Media):** Berkas rusak/tidak valid (`InvalidMedia`) -> ditangani aman, status berubah menjadi `FAILED`, dan aplikasi tidak mengalami crash. (**LULUS**)
8. **Skenario 8 (Scheduler Tetap ON):** Interupsi manual maupun penekanan tombol Stop tidak mematikan scheduler (`scheduler.is_active` tetap `True` dan timer tetap berjalan). (**LULUS**)
9. **Skenario 9 (Scheduler OFF Tidak Menghalangi Manual):** Saat scheduler dimatikan (`OFF`), tombol bel manual tetap dapat dibunyikan dan saling menginterupsi dengan normal. (**LULUS**)
10. **Skenario 10 (Jadwal Berikutnya Berjalan & Anti-Duplikasi):** Jadwal yang terinterupsi tidak diulang kembali pada hari yang sama, dan jadwal berikutnya pada jam berikutnya (07:40) tetap berbunyi tepat waktu. (**LULUS**)
11. **Skenario 11 (Perintah Beruntun Single Active):** Dua pemutaran berurutan tanpa jeda waktu menghasilkan pergantian sesi teratur, memastikan hanya ada tepat satu pemutar aktif. (**LULUS**)
12. **Skenario 12 (Kekebalan Callback Usang):** Sinyal callback yang membawa nomor sesi lama diabaikan secara ketat dan tidak mengganggu status pemutaran baru. (**LULUS**)
13. **Skenario 13 (Berkas Hilang / Path Tidak Valid):** Pemanggilan audio dengan path yang tidak ada ditolak dengan aman, dicatat `failed`, dan pemutaran audio valid berikutnya tetap langsung berfungsi normal. (**LULUS**)
14. **Skenario 14 (Pergantian Cepat Berulang):** Menekan 10 pergantian tombol bel manual secara cepat menghasilkan 10 kali `playback_started` dan 9 kali `playback_interrupted` tanpa kebocoran sinyal atau crash. (**LULUS**)
15. **Skenario 15 (Kebijakan Konflik Deterministik & Integrasi UI MainWindow):** Jika waktu jadwal otomatis tiba saat bel manual masih berbunyi, bel manual tidak terpotong diam-diam, jadwal dicatat `missed`, dan tombol UI MainWindow terverifikasi sinkron. (**LULUS**)

---

## 4. Artefak Distribusi Rilis v1.2.1

Seluruh paket distribusi telah dikompilasi ulang secara bersih untuk Windows 10 & Windows 11 (64-bit) dan disimpan di folder `release/` dan `dist/`:

| Tipe Artefak | Nama Berkas & Lokasi | Ukuran | Checksum SHA-256 |
|---|---|---|---|
| **Installer Setup EXE** | [`release/BelOtomatisSekolah_Setup_v1.2.1.exe`](file:///d:/BelOtomatisSekolah/release/BelOtomatisSekolah_Setup_v1.2.1.exe) | 45.62 MB (47.838.991 bytes) | `025d579da67eb4978e0c3147ab5f1fd3e1afae307b2fce160b0da24f2ad5b231` |
| **Paket Portable ZIP** | [`release/BelOtomatisSekolah_Portable_v1.2.1.zip`](file:///d:/BelOtomatisSekolah/release/BelOtomatisSekolah_Portable_v1.2.1.zip) | 79.80 MB (83.672.255 bytes) | `ef938e751074ad0b4b073a91ccab263c87fc604804aac123de7a723815fd246e` |
| **Standalone Binary EXE** | [`dist/BelOtomatisSekolah/BelOtomatisSekolah.exe`](file:///d:/BelOtomatisSekolah/dist/BelOtomatisSekolah/BelOtomatisSekolah.exe) | 1.87 MB (1.963.634 bytes) | `ff22d685a782203036b2b3d78a867cad89bab63ea393941d751d6dfeb0e864ef` |

### Verifikasi Paket Terpasang & Portable:
- Paket Portable ZIP telah diuji diekstrak ke direktori terisolasi temporer dan diverifikasi dapat meluncurkan aplikasi, menginisialisasi database SQLite mandiri, menyalin 15 audio bawaan, dan membaca log sistem secara 100% mandiri.
- Standalone Executable hasil instalasi pada folder simulasi terverifikasi berjalan bersih tanpa dependensi sistem luar.

---

## 5. Catatan Keterbatasan & Pengujian Lapangan

> [!IMPORTANT]
> **Catatan Pengujian Perangkat Keras Fisik Sekolah:**
> Pengujian otomatis di atas telah memvalidasi seluruh logika perangkat lunak, pemanggilan API audio PySide6 / WinMM, penanganan status, pencatatan database, integrasi antarmuka, dan paket distribusi secara deterministik.
> Namun demikian, pengujian kenyaringan suara fisik, kestabilan jack/kabel amplifier, dan output speaker lorong sekolah tetap harus diuji secara langsung oleh operator saat aplikasi dijalankan pada komputer fisik sekolah yang terhubung ke sound system sekolah.

