# LAPORAN RILIS RESMI: BEL OTOMATIS SEKOLAH (KRONABEL) v1.2.3
**Investigasi dan Perbaikan Menyeluruh Sistem Audio Output & Dynamic Device Routing**

**Tanggal Rilis:** 2 November 2026  
**Target Sistem Operasi:** Windows 10 & Windows 11 (64-bit)  
**Lingkungan Runtime:** Python 3.11.9 + PySide6 6.12.0 (Qt 6 Native)  
**Status Pengujian:** 143 Pengujian Lulus (100% PASS, 0 Fail, 0 Skip)

---

## 1. Penyebab Masalah yang Ditemukan (Investigasi Audio Output)

Setelah investigasi mendalam terhadap implementasi audio pada `src/services/audio_player.py`, ditemukan penyebab mengapa suara YouTube dapat keluar melalui speaker eksternal jack 3,5 mm namun suara bel KRONABEL tetap tidak keluar ke speaker eksternal:

1. **Pengikatan Statis Endpoint Audio saat Startup Aplikasi:**
   - Objek `QAudioOutput(self)` dibuat sekali pada saat inisialisasi aplikasi (`AudioPlayer.__init__`).
   - Pada Qt 6 Multimedia, konstruktor default `QAudioOutput` mengikatkan diri ke endpoint default Windows yang aktif *pada saat objek dibuat* (yaitu speaker internal laptop sebelum jack 3,5 mm dicolokkan).
   - Berbeda dengan browser modern (seperti Chrome/Edge) yang memanfaatkan antarmuka WASAPI `IMMNotificationClient::OnDefaultDeviceChanged` untuk mengalirkan audio secara dinamis ke endpoint default baru, objek `QAudioOutput` di Qt 6 **tidak secara otomatis memperbarui atau mengalihkan endpoint fisiknya** jika Windows mengganti perangkat default setelah aplikasi berjalan.

2. **Ketiadaan Listener Sinyal Perubahan Perangkat Audio (`QMediaDevices`):**
   - Sebelumnya, aplikasi sama sekali tidak membuat instans `QMediaDevices` dan tidak menghubungkan sinyal `audioOutputsChanged`.
   - Akibatnya, saat kabel jack speaker eksternal dipasang ke laptop, Windows mengirimkan sinyal perubahan topologi audio ke OS, tetapi aplikasi KRONABEL tidak mendeteksi kejadian tersebut dan tetap mempertahankan handle perangkat lama.

3. **Tidak Ada Sinkronisasi Perangkat Sebelum Pemutaran Audio:**
   - Metode `play_file()` langsung mengeksekusi `player.play()` tanpa memeriksa apakah perangkat output aktif pada `QAudioOutput` masih relevan dengan endpoint default Windows saat itu.
   - Jika kabel speaker eksternal dicolokkan setelah KRONABEL dibuka, audio bel tetap dipaksa keluar melalui jalur perangkat internal yang mungkin sudah dibisukan (*muted*) atau dinonaktifkan oleh driver audio Windows (misal Realtek Audio Jack Detection).

4. **Ketiadaan Antarmuka Pengaturan & Pemilihan Perangkat Audio di Pengaturan:**
   - Halaman Pengaturan (`SettingsPage`) sebelumnya hanya menyediakan penggeser Volume Master dan Kebijakan Pemutaran Saat Sibuk.
   - Pengguna tidak memiliki visibilitas untuk melihat perangkat audio apa yang sedang digunakan aplikasi, tidak dapat memilih perangkat secara manual, serta tidak ada tombol untuk menyegarkan daftar perangkat maupun melakukan tes suara langsung ke speaker yang dipilih.

---

## 2. File Kode yang Diperbaiki

| No | Berkas | Deskripsi Perubahan |
|---|---|---|
| 1 | [`src/services/audio_player.py`](file:///d:/BelOtomatisSekolah/src/services/audio_player.py) | **Inti Perbaikan Audio Output:**<br>• Mengintegrasikan `QMediaDevices` dan menghubungkan sinyal `audioOutputsChanged`.<br>• Menyediakan mode perutean otomatis (`auto`) dan manual (`manual`).<br>• Menambahkan fungsi `refresh_audio_device()` yang menyinkronkan `QAudioOutput.setDevice()` secara dinamis setiap kali perangkat berubah maupun sesaat sebelum pemutaran audio dijalankan di `play_file()`.<br>• Menambahkan penanganan fallback cerdas jika perangkat manual dilepas/tidak tersedia agar otomatis jatuh ke default Windows tanpa merusak konfigurasi tersimpan.<br>• Memancarkan sinyal `audio_devices_changed` dan `audio_device_switched(str)`. |
| 2 | [`src/ui/settings_page.py`](file:///d:/BelOtomatisSekolah/src/ui/settings_page.py) | **Antarmuka Pengaturan Perangkat Audio Baru:**<br>• Menambahkan dropdown pilihan perangkat: *🔊 Otomatis mengikuti output Windows (default)* dan daftar seluruh speaker/headphone aktif.<br>• Menambahkan tombol **Segarkan Perangkat** untuk pemindaian ulang perangkat fisik Windows secara instan.<br>• Menambahkan tombol **Tes Suara** yang benar-benar memutar suara bel ke perangkat target yang dipilih (bukan sekadar dialog notifikasi).<br>• Menambahkan label status informatif yang menerangkan perutean output aktif.<br>• Menyimpan preferensi ke tabel `app_settings` (`audio_output_mode`, `audio_output_device_id`, `audio_output_device_name`). |
| 3 | [`src/core/config.py`](file:///d:/BelOtomatisSekolah/src/core/config.py) | Memperbarui versi aplikasi menjadi `APP_VERSION = "1.2.3"`. |
| 4 | [`src/__init__.py`](file:///d:/BelOtomatisSekolah/src/__init__.py) | Memperbarui versi paket menjadi `__version__ = "1.2.3"`. |
| 5 | [`installer/BelOtomatisSekolah.iss`](file:///d:/BelOtomatisSekolah/installer/BelOtomatisSekolah.iss) | Memperbarui konfigurasi Inno Setup ke `1.2.3`. |
| 6 | [`build_release.py`](file:///d:/BelOtomatisSekolah/build_release.py) | Memperbarui target kompilasi rilis dan packaging ke `v1.2.3`. |
| 7 | [`tests/test_history.py`](file:///d:/BelOtomatisSekolah/tests/test_history.py) | Memperbaiki pengujian filter tanggal pada riwayat agar independen terhadap pergeseran kalender kalender riil. |
| 8 | [`tests/test_installed_executable.py`](file:///d:/BelOtomatisSekolah/tests/test_installed_executable.py) | Menyesuaikan verifikasi paket executable dan portable ZIP rilis ke `v1.2.3`. |
| 9 | [`tests/test_audio_device_management.py`](file:///d:/BelOtomatisSekolah/tests/test_audio_device_management.py) | **Test Suite Baru (8 Pengujian):** Pengujian menyeluruh untuk enumerasi perangkat, mode otomatis, mode manual, fallback disconnect, runtime device switching, integritas Single Active Controller, dan pengujian UI tombol tes suara. |

---

## 3. Mekanisme Pemilihan Output Audio yang Diterapkan

1. **Mode Otomatis (Default):**
   - Secara default, aplikasi selalu menyelaraskan diri dengan perangkat output default Windows (`QMediaDevices.defaultAudioOutput()`).
   - Ketika kabel jack 3,5 mm speaker eksternal dicolokkan ke laptop, Windows mengalihkan default audio endpoint ke jack eksternal.
   - Sinyal `QMediaDevices.audioOutputsChanged` segera ditangkap oleh `AudioPlayer._on_audio_outputs_changed`.
   - Fungsi `refresh_audio_device()` mendeteksi perbedaan ID perangkat antara endpoint lama dan endpoint default baru, lalu memanggil `self.audio_output.setDevice(new_default_device)` secara dinamis dan aman tanpa menghentikan atau merusak pemutar.
   - Sebagai proteksi ganda, tepat sebelum audio bel dimainkan di `play_file()`, `refresh_audio_device()` dipanggil kembali. Ini menjamin suara bel berikutnya PASTI dialirkan ke speaker eksternal meskipun kabel baru dicolokkan 1 detik sebelumnya.

2. **Mode Manual Terkunci:**
   - Operator dapat memilih speaker eksternal tertentu dari dropdown Pengaturan.
   - Pilihan disimpan secara persisten di database (`audio_output_mode="manual"`, `audio_output_device_id`, `audio_output_device_name`).
   - Selama speaker eksternal tersebut terhubung, aplikasi akan selalu menggunakan perangkat tersebut.
   - Jika speaker eksternal dilepas (kabel dicabut), aplikasi secara cerdas menggunakan default Windows sebagai **fallback darurat sementara**, sehingga bel tetap berbunyi melalui speaker internal dan tidak terjadi keheningan (*silence*). Ketika kabel dicolokkan kembali, aplikasi secara otomatis kembali mengunci perangkat pilihan operator.

3. **Tombol Tes Suara Fisik:**
   - Tombol *Tes Suara* memuat audio sampel bel (dari pustaka database atau suara bawaan `assets/sounds/chime_default.wav`), mengatur perutean ke perangkat yang dipilih, dan mengeksekusi pemutaran nyata melalui `audio_player.play_file()`.
   - Menggunakan aturan `interrupt=True` dan `mode="MANUAL"`, menjamin operator dapat memverifikasi output speaker secara instan.

4. **Kestabilan Single Active Audio Controller & Prioritas:**
   - Seluruh aturan Single Active Audio Controller v1.2.1 tetap 100% terjaga: maksimal 1 audio aktif, interupsi bel manual, session token aktif untuk menolak callback usang, dan scheduler bel otomatis tetap aman tanpa potensi crash atau suara ganda.

---

## 4. Hasil Seluruh Pengujian

Seluruh rangkaian pengujian unit, integrasi, simulasi hari penuh, dan peluncuran biner dijalankan dengan hasil **100% LULUS**:

```text
pytest tests/ -v
============================ 143 passed in 21.97s =============================
```

### Rincian Verifikasi Fitur Audio Output:
1. **Enumerasi Perangkat Audio:** Berhasil mendeteksi seluruh perangkat output fisik yang terhubung ke sistem Windows. (**LULUS**)
2. **Perutean Otomatis (Default Windows):** Terverifikasi selalu mengikuti default Windows dan mempertahankan volume master. (**LULUS**)
3. **Pemilihan Perangkat Manual & Persistensi:** Pilihan tersimpan aman di database SQLite dan tetap terpilih saat aplikasi dimuat ulang. (**LULUS**)
4. **Fallback Aman saat Perangkat Terputus:** Tidak terjadi crash; sistem jatuh ke default Windows sementara dan pulih saat perangkat terhubung kembali. (**LULUS**)
5. **Pergantian Perangkat Saat Runtime (Live Jack Insertion):** Sinyal `audioOutputsChanged` memicu pembaruan `QAudioOutput` seketika. (**LULUS**)
6. **Sinkronisasi Sebelum Pemutaran Bel:** `play_file()` selalu memperbarui target perangkat sebelum pemutaran dimulai. (**LULUS**)
7. **Pencegahan Suara Ganda & Interupsi Manual:** Maksimal 1 audio berbunyi; bel manual baru menghentikan audio lama secara bersih. (**LULUS**)
8. **Pengujian Antarmuka UI SettingsPage:** Dropdown perangkat terisi otomatis, tombol Segarkan memindai ulang perangkat, dan tombol Tes Suara benar-benar memicu pemutaran audio. (**LULUS**)
9. **Kualitas Kode Website & TypeScript:** Pemeriksaan lint dan TypeScript pada `D:\Kronabel-Website` menghasilkan `0 errors, 0 warnings`. (**LULUS**)

---

## 5. Versi Aplikasi Hasil Perbaikan

**Versi Resmi:** `v1.2.3`

---

## 6. Lokasi Executable dan Installer Final

Proses kompilasi dan pengemasan mandiri untuk Windows 10 & Windows 11 (64-bit) telah selesai dijalankan menggunakan Python 3.11.9 murni, PySide6 6.12.0, dan Inno Setup Compiler.

### Artefak Rilis:
1. **Windows Setup Installer (.exe) [Rekomendasi untuk PC Sekolah]:**
   - **Lokasi File:** `D:\BelOtomatisSekolah\release\BelOtomatisSekolah_Setup_v1.2.3.exe`
   - **Ukuran File:** `45.63 MB (47,850,894 bytes)`
   - **Checksum SHA-256:** `5e66fa7ed82894a7a0bcb6f0ca5d0531d2bb9d5fddd337fdbc01cd1f4bf86603`

2. **Paket Portable (.zip) [Tinggal Ekstrak Tanpa Perlu Hak Administrator]:**
   - **Lokasi File:** `D:\BelOtomatisSekolah\release\BelOtomatisSekolah_Portable_v1.2.3.zip`
   - **Ukuran File:** `79.81 MB (83,682,597 bytes)`
   - **Checksum SHA-256:** `bb6b0d925fc860f25e5407619d029a854a2e2671f726b7d0747f4c50dd76c0ba`

3. **Standalone Executable Folder (`onedir`):**
   - **Lokasi File:** `D:\BelOtomatisSekolah\dist\BelOtomatisSekolah\BelOtomatisSekolah.exe`
   - **Ukuran File:** `1.88 MB`
   - **Checksum SHA-256:** `0c39e4aeb948051b961a7176fea47041f3faabc1757899ec02effad78d8d923c`

