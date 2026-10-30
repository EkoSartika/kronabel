# PANDUAN OPERATOR SISTEM BEL OTOMATIS SEKOLAH
**Versi Aplikasi: 1.0.0 (Tahap 5 — Operasional Menyeluruh)**  
**Target Sistem: Windows Desktop (Offline Standalone)**

---

## DAFTAR ISI
1. [Pengantar & Persyaratan Sistem](#1-pengantar--persyaratan-sistem)
2. [Pemeriksaan Perangkat Output Audio](#2-pemeriksaan-perangkat-output-audio)
3. [Manajemen Pustaka Audio Bel](#3-manajemen-pustaka-audio-bel)
4. [Pengaturan Profil & Jadwal Bel](#4-pengaturan-profil--jadwal-bel)
5. [Pengoperasian Bel Otomatis & Bel Manual](#5-pengoperasian-bel-otomatis--bel-manual)
6. [Membaca & Memantau Riwayat Pembunyian](#6-membaca--memantau-riwayat-pembunyian)
7. [Pengaturan Preferensi Aplikasi](#7-pengaturan-preferensi-aplikasi)
8. [Cadangkan Data (Backup)](#8-cadangkan-data-backup)
9. [Pemulihan Data (Restore)](#9-pemulihan-data-restore)
10. [Prosedur Uji Manual Speaker & Amplifier Sekolah](#10-prosedur-uji-manual-speaker--amplifier-sekolah)
11. [Troubleshooting & Tanya Jawab (FAQ)](#11-troubleshooting--tanya-jawab-faq)

---

## 1. Pengantar & Persyaratan Sistem

**Bel Otomatis Sekolah** adalah aplikasi komputer Windows yang dirancang khusus untuk mengotomatisasi pemutaran bel sekolah sesuai jadwal kegiatan belajar mengajar (KBM) dari hari Senin hingga Sabtu. Aplikasi bekerja sepenuhnya secara **offline** tanpa memerlukan koneksi internet.

### Persyaratan Minimum:
- **Sistem Operasi**: Windows 10 atau Windows 11 (64-bit).
- **Prosesor**: Dual-core 1.5 GHz atau lebih tinggi.
- **RAM**: Minimum 2 GB (Disarankan 4 GB).
- **Penyimpanan**: Ruang kosong minimum 200 MB untuk aplikasi, database, dan arsip audio.
- **Kartu Suara / Audio Output**: Sound card onboard atau USB Sound Card yang terhubung ke sistem tata suara (Sound System / Amplifier) sekolah.
- **Kebijakan Daya Komputer**: Mode hemat daya / Sleep / Hibernasi **wajib dinonaktifkan** selama jam operasional sekolah.

---

## 2. Pemeriksaan Perangkat Output Audio

Sebelum mengaktifkan bel otomatis, operator wajib memastikan saluran keluaran audio Windows terarah ke perangkat pengeras suara sekolah:

1. Buka menu **Pengaturan Suara Windows** (klik kanan ikon speaker di pojok kanan bawah taskbar Windows -> *Sound settings* / *Pengaturan Suara*).
2. Periksa perangkat keluaran default (*Default Output Device*). Pastikan memilih perangkat yang tersambung ke amplifier (misalnya: `Speakers (Realtek Audio)` atau kabel audio 3.5mm).
3. Atur volume master Windows pada tingkat **70%–80%** untuk menghindari distorsi sinyal sebelum masuk ke amplifier.
4. Buka menu **Pengaturan** di aplikasi Bel Otomatis Sekolah, kemudian klik tombol **"Tes Suara"** untuk memastikan suara keluar dari speaker komputer operator.

---

## 3. Manajemen Pustaka Audio Bel

Aplikasi mendukung format audio standar **MP3** dan **WAV**. Seluruh file audio yang diimpor akan disalin secara otomatis ke folder penyimpanan aman aplikasi (`%APPDATA%\BelOtomatisSekolah\sounds`) sehingga jadwal tidak akan terganggu meskipun file asli di flashdisk atau folder unduhan dipindahkan/dihapus.

### Langkah Mengimpor File Audio Baru:
1. Buka bilah menu samping, pilih **Audio Bel**.
2. Klik tombol **"+ Tambah Audio"** di bagian atas.
3. Pada dialog yang muncul:
   - **Nama / Label Audio**: Masukkan label pengenal yang jelas (misalnya: *Bel Masuk Kelas*, *Bel Istirahat*, *Bel Pulang*, *Lagu Indonesia Raya*).
   - **File Audio**: Klik tombol **"Pilih File..."**, telusuri file berformat `.mp3` atau `.wav` di komputer Anda, lalu klik *Open*.
4. Klik tombol **"Simpan"**.
5. Uji file yang baru diimpor dengan menekan tombol **"▶ Putar"** pada baris audio tersebut. Jika ingin menghentikan sebelum selesai, klik tombol **"⏹ Hentikan"**.

---

## 4. Pengaturan Profil & Jadwal Bel

Aplikasi mengelompokkan jadwal berdasarkan **Profil Jam Pelajaran** (misalnya: *Jadwal Reguler*, *Jadwal Ujian Semester*, *Jadwal Bulan Ramadhan*). Hanya ada **satu profil aktif** pada satu waktu.

### A. Mengelola Profil:
1. Buka menu **Profil Jam Pelajaran**.
2. Untuk membuat profil baru, klik tombol **"+ Tambah Profil"**, ketik nama dan deskripsi, lalu klik *Simpan*.
3. Untuk mengaktifkan profil tertentu, klik tombol **"Aktifkan"** pada profil yang diinginkan. Status profil aktif akan langsung diperbarui di bagian header atas aplikasi.

### B. Mengatur Jadwal Harian:
1. Buka menu **Jadwal Bel**.
2. Pilih hari yang ingin diatur (tab: **Senin, Selasa, Rabu, Kamis, Jumat, Sabtu**).
3. Klik tombol **"+ Tambah Jadwal"**:
   - **Waktu Bel**: Masukkan jam dan menit dalam format 24 jam `HH:MM` (contoh: `07:00`, `09:30`, `12:15`).
   - **Nama Kegiatan**: Ketik deskripsi kegiatan (contoh: *Upacara Bendera*, *Istirahat Pertama*).
   - **File Audio Bel**: Pilih nada bel dari daftar audio yang sudah diimpor sebelumnya.
   - **Status Aktif**: Pastikan kotak centang *Aktifkan Jadwal Ini* tercentang.
4. Klik tombol **"Simpan"**.

> **Tips Salin Jadwal Antar-Hari:**  
> Jika jadwal hari Selasa sampai Kamis sama dengan hari Senin, Anda tidak perlu mengetik ulang satu per satu. Gunakan fitur **"Salin Jadwal Hari"** pada menu Jadwal Bel untuk menyalin seluruh jadwal dari hari Senin ke hari tujuan dalam satu klik.

---

## 5. Pengoperasian Bel Otomatis & Bel Manual

### A. Mengaktifkan & Menghentikan Bel Otomatis:
1. Buka menu **Dashboard**.
2. Periksa panel status **Mesin Otomatis**:
   - Jika berstatus **"Nonaktif (Standby)"** berwarna oranye, klik tombol hijau **"Mulai Otomatis"**.
   - Indikator akan berubah menjadi hijau **"Aktif Berjalan"**, dan panel hitung mundur akan menampilkan bel berikutnya yang akan dibunyikan beserta sisa waktu.
3. Untuk menghentikan sistem bel otomatis sementara (misalnya saat libur dadakan atau rapat guru), klik tombol abu-abu **"Hentikan Otomatis"**.

> **Proteksi Pencegahan Pembunyian Ganda & Restart:**  
> Mesin bel dilengkapi sistem idempotensi SQLite. Apabila aplikasi ditutup dan dibuka kembali di hari yang sama, jadwal yang sudah berbunyi **tidak akan pernah diputar ulang**. Jadwal yang terlewat saat komputer mati juga tidak akan dibunyikan secara serentak ketika aplikasi baru menyala.

### B. Membunyikan Bel Manual:
Jika ada pengumuman mendadak, pergantian jam khusus, atau keadaan darurat:
1. Buka menu **Dashboard** -> panel **Bel Manual**.
2. Pilih nada suara yang diinginkan dari menu dropdown.
3. Klik tombol merah **"🔔 Bunyikan Bel Sekarang"**.
4. Konfirmasi pada kotak dialog yang muncul (dapat dinonaktifkan di menu Pengaturan jika diinginkan).
5. Pembunyian bel manual akan dicatat ke dalam riwayat dengan status metode `MANUAL`.

---

## 6. Membaca & Memantau Riwayat Pembunyian

Seluruh aktivitas bel (baik otomatis maupun manual) dicatat ke dalam database SQLite secara persisten.

1. Buka menu **Riwayat Bel**.
2. Tabel riwayat menampilkan kolom:
   - **Tanggal & Waktu**: Waktu pencatatan log.
   - **Nama Kegiatan**: Nama agenda bel.
   - **Jadwal**: Waktu yang direncanakan (`HH:MM`).
   - **Eksekusi**: Waktu nyata pemutaran suara.
   - **Metode**: Badge **OTOMATIS** (biru) atau **MANUAL** (ungu).
   - **Status**:
     - `Berhasil (completed)`: Suara selesai diputar tanpa gangguan.
     - `Gagal (failed)`: File audio hilang atau audio player mengalami kesalahan perangkat.
     - `Terlewat (missed)`: Jadwal terlewati saat komputer/aplikasi dalam keadaan mati.
     - `Terpotong (interrupted)`: Pemutaran dihentikan manual oleh operator sebelum audio selesai.
     - `Memutar (playing)`: Suara sedang berlangsung.
   - **Keterangan**: Rincian teknis status eksekusi.
3. **Fitur Filter & Pencarian:**
   - Centang **Filter Tanggal** untuk memilih rentang tanggal tertentu.
   - Gunakan menu pilihan **Metode** dan **Status** untuk menyaring data spesifik.
   - Ketik kata kunci pada kotak **Cari Kegiatan** (contoh: *Upacara* atau *Istirahat*).
   - Gunakan tombol paginasi di bawah tabel (**Sebelumnya / Berikutnya**) untuk berpindah halaman secara cepat dan ringan.

---

## 7. Pengaturan Preferensi Aplikasi

Buka menu **Pengaturan** untuk menyesuaikan preferensi:
- **Volume Suara Master**: Mengatur tingkat kekerasan suara aplikasi (0%–100%).
- **Kebijakan Saat Audio Sibuk**: Menentukan tindakan saat bel baru dipicu ketika suara sebelumnya masih berbunyi:
  - *Tolak pemutaran baru (Default)*: Mencegah suara tumpang tindih.
  - *Hentikan audio lama dan segera putar yang baru*.
  - *Antrekan suara baru*.
- **Konfirmasi Bel Manual**: Menampilkan atau menonaktifkan kotak dialog pertanyaan sebelum bel manual berbunyi.
- **Profil Aktif**: Mengganti profil jam pelajaran yang berlaku saat ini.
- **Windows Startup**: Opsi agar aplikasi otomatis terbuka saat Windows menyala.  
  *(Operator wajib menyetujui konfirmasi eksplisit. Peringatan: Komputer harus tetap menyala dan tidak boleh masuk mode Sleep).*

---

## 8. Cadangkan Data (Backup)

Pencadangan rutin disarankan dilakukan setiap ada perubahan jadwal atau minimal sebulan sekali.

### Langkah Membuat Cadangan:
1. Buka menu **Pengaturan**, gulir ke kartu **Cadangkan & Pulihkan Data**.
2. Klik tombol **"📦 Cadangkan Data (Backup)"**.
3. Pilih lokasi penyimpanan yang aman (misalnya: di drive `D:\`, folder dokumen, atau flashdisk eksternal). Nama file otomatis memuat tanggal dan waktu (contoh: `Cadangan_Bel_Sekolah_20261028_104500.zip`).
4. Klik **"Save"**.
5. Aplikasi akan menggunakan SQLite Backup API yang aman (tidak terpengaruh mode WAL yang aktif), menghitung checksum SHA-256, menyalin seluruh file audio ke dalam arsip, dan membuat `manifest.json`.
6. Kotak dialog keberhasilan akan menampilkan jumlah jadwal, profil, riwayat, dan file audio yang berhasil dicadangkan.

---

## 9. Pemulihan Data (Restore)

Fitur ini digunakan saat komputer berganti, database perlu dipulihkan ke tanggal sebelumnya, atau saat memasang aplikasi di komputer baru.

### Langkah Memulihkan Data:
1. Buka menu **Pengaturan** -> kartu **Cadangkan & Pulihkan Data**.
2. Klik tombol **"📥 Pulihkan Data (Restore)"**.
3. Pilih file arsip cadangan (`.zip`) yang telah dibuat sebelumnya.
4. **Validasi Otomatis & Pratinjau**: Sistem akan memeriksa integritas arsip, kesesuaian checksum database, dan versi skema. Jika file rusak atau bukan cadangan resmi, pemulihan akan langsung ditolak.
5. Jika valid, sistem menampilkan ringkasan data cadangan (tanggal pembuatan, jumlah profil, jadwal, log, dan audio).
6. **Safety Net**: Sebelum data aktif ditimpa, sistem secara otomatis membuat cadangan darurat kondisi saat ini di folder cadangan internal (`pre_restore_YYYYMMDD_HHMMSS.zip`).
7. Klik **"Yes"** untuk mengonfirmasi. Seluruh data aktif dan file audio akan dipulihkan, dan tampilan antarmuka akan langsung disegarkan.

---

## 10. Prosedur Uji Manual Speaker & Amplifier Sekolah

Dalam pengujian perangkat audio, terdapat tiga tingkatan hasil yang tidak boleh disamakan:

| Tingkatan Uji | Deskripsi | Status Verifikasi |
|---|---|---|
| **1. Pengujian Otomatis (Pytest)** | Menjalankan suite kode unit/integrasi untuk memastikan fungsi pemutar audio, database, dan antarmuka bekerja sesuai kode. | **Terverifikasi 100% Lulus (67 Tes)** |
| **2. Pengujian Pipeline Audio Windows** | Memeriksa ketersediaan driver sound card Windows dan antarmuka Qt Multimedia. | **Terverifikasi (Perangkat Output Terdeteksi)** |
| **3. Pengujian Suara Fisik (Speaker Sekolah)** | Mendengarkan secara langsung keluaran gelombang suara dari horn speaker / speaker kelas di lingkungan sekolah. | **Wajib Uji Manual oleh Operator di Lokasi** |

### Prosedur Uji Manual Fisik (Langkah Lapangan):
1. **Sambungkan Kabel Fisik**: Hubungkan kabel audio jack 3.5mm dari port audio komputer/laptop operator ke input `AUX IN` atau `LINE IN` pada unit Amplifier / Mixer sekolah.
2. **Nyalakan Amplifier**: Pastikan power switch amplifier menyala dan selector speaker kelas dalam posisi aktif (*ON*).
3. **Atur Master Volume Amplifier**: Mulai dari posisi rendah (arah jam 9) untuk mencegah lonjakan suara mendadak yang dapat merusak speaker.
4. **Buka Aplikasi**: Pada halaman **Dashboard** atau **Pengaturan**, klik tombol **"Tes Suara"**.
5. **Dengarkan Suara Fisik**:
   - Jika terdengar di speaker sekolah, naikkan volume amplifier secara bertahap hingga tingkat kenyaringan yang mencakup seluruh area sekolah tanpa distorsi/pecah.
   - Jika tidak terdengar, periksa konektor kabel, pastikan kabel tidak longgar, periksa sakelar *Mute* pada mixer/amplifier, dan periksa pengaturan keluaran Windows.
6. Catat hasil pengujian fisik pada formulir pemeriksaan fasilitas sekolah.

---

## 11. Troubleshooting & Tanya Jawab (FAQ)

**T: Mengapa bel tidak berbunyi pada jam yang sudah dijadwalkan?**  
*Jawab:*
1. Pastikan status di Dashboard adalah **"Aktif Berjalan"** (tombol Mulai Otomatis sudah ditekan).
2. Periksa apakah hari ini termasuk hari yang memiliki jadwal pada tab Jadwal Bel.
3. Pastikan jam dan tanggal komputer Windows Anda akurat (cocokkan dengan jam dinding sekolah).
4. Pastikan komputer tidak masuk mode Sleep. Di Windows Settings -> *Power & Sleep*, atur *"When plugged in, PC goes to sleep after"* menjadi **Never (Jangan Pernah)**.

**T: Suara bel di speaker terdengar sangat kecil atau terlalu keras.**  
*Jawab:*  
Atur keseimbangan volume melalui 3 titik kontrol:
1. Slider volume di menu **Pengaturan** aplikasi Bel Otomatis Sekolah (atur ke 80%).
2. Volume master pada taskbar Windows (atur ke 70%–80%).
3. Knob volume master fisik pada amplifier sekolah (sesuaikan dengan kebutuhan jangkauan kelas).

**T: Komputer operator dimatikan saat jam istirahat. Apakah bel akan berbunyi saat komputer baru dinyalakan?**  
*Jawab:*  
Tidak. Sistem sengaja tidak membunyikan jadwal yang sudah terlewat agar tidak membingungkan warga sekolah. Jadwal yang terlewat akan dicatat di menu Riwayat Bel dengan status `Terlewat (missed)`. Bel akan kembali normal pada jam berikutnya yang sesuai.
