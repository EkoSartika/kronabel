"""
Skrip Otomatisasi Build Release & Installer KRONABEL (Windows 10 & Windows 11).
Konfigurasi Resmi: Python 3.11 + PySide6 (Qt 6).
1. Memastikan isolasi lingkungan Python 3.11 + PySide6 (bebas dari Python 3.8 / PySide2).
2. Menjalankan PyInstaller dengan BelOtomatisSekolah.spec (menghasilkan dist/KRONABEL/KRONABEL.exe).
3. Memverifikasi struktur direktori dist/KRONABEL dan kemurnian dependensi biner.
4. Mengompilasi installer Windows (KRONABEL_Setup_v1.2.4.exe) menggunakan Inno Setup Compiler (ISCC.exe).
5. Membuat paket Portable ZIP (KRONABEL_Portable_v1.2.4.zip).
6. Menghasilkan ringkasan artefak distribusi dan checksum SHA-256.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_VERSION = "1.2.4"

DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build" / "KRONABEL"
RELEASE_DIR = BASE_DIR / "release"
SPEC_FILE = BASE_DIR / "BelOtomatisSekolah.spec"
ISS_FILE = BASE_DIR / "installer" / "BelOtomatisSekolah.iss"

DEFAULT_PY311_EXE = Path(r"C:\Users\Eko\AppData\Local\Programs\Python\Python311\python.exe")
PYTHON_EXE = str(DEFAULT_PY311_EXE if DEFAULT_PY311_EXE.exists() else Path(sys.executable))

# Jalur pencarian ISCC.exe
ISCC_CANDIDATES = [
    Path(r"C:\Users\Eko\AppData\Local\Programs\Antigravity IDE\resources\app\node_modules\innosetup\bin\ISCC.exe"),
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
]


def calculate_sha256(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def find_iscc() -> Path | None:
    for candidate in ISCC_CANDIDATES:
        if candidate.exists() and candidate.is_file():
            return candidate
    which_iscc = shutil.which("ISCC.exe") or shutil.which("iscc")
    if which_iscc:
        return Path(which_iscc)
    return None


def get_clean_py311_env() -> dict[str, str]:
    """
    Menghasilkan environment variables yang bersih dari referensi build_env_py38 / Python 3.8 / PySide2.
    """
    env = os.environ.copy()
    path_parts = env.get("PATH", "").split(os.pathsep)
    clean_parts = [
        p
        for p in path_parts
        if "build_env_py38" not in p.lower() and "python38" not in p.lower() and "pyside2" not in p.lower()
    ]
    py311_dir = str(Path(PYTHON_EXE).resolve().parent)
    py311_scripts = str(Path(PYTHON_EXE).resolve().parent / "Scripts")
    env["PATH"] = os.pathsep.join([py311_dir, py311_scripts] + clean_parts)
    env.pop("QT_PLUGIN_PATH", None)
    env.pop("PYTHONPATH", None)
    return env


def sync_bundled_sounds() -> None:
    """
    Memastikan seluruh file audio MP3/WAV bawaan tersimpan di folder assets/sounds
    sebelum dibundel ke dalam paket rilis mandiri (standalone).
    """
    assets_sounds = BASE_DIR / "assets" / "sounds"
    assets_sounds.mkdir(parents=True, exist_ok=True)
    appdata = os.environ.get("APPDATA")
    if appdata:
        copied = 0
        for folder_name in ["KRONABEL", "BelOtomatisSekolah"]:
            user_sounds = Path(appdata) / folder_name / "sounds"
            if user_sounds.exists():
                for audio_file in user_sounds.glob("*.*"):
                    if audio_file.suffix.lower() in (".mp3", ".wav"):
                        dst = assets_sounds / audio_file.name
                        if not dst.exists() or dst.stat().st_size != audio_file.stat().st_size:
                            shutil.copy2(audio_file, dst)
                            copied += 1
        if copied:
            print(f"Disinkronkan {copied} berkas audio bawaan ke {assets_sounds}")


def run_pyinstaller() -> bool:
    sync_bundled_sounds()
    print(f"\n[1/4] Menjalankan PyInstaller (Python 3.11 + PySide6) untuk v{APP_VERSION}...")

    dist_app = DIST_DIR / "KRONABEL"
    if dist_app.exists():
        shutil.rmtree(dist_app)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    cmd = [
        PYTHON_EXE,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        str(SPEC_FILE),
    ]
    print("Perintah:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(BASE_DIR), env=get_clean_py311_env())
    if res.returncode != 0:
        print("ERROR: PyInstaller gagal dengan kode:", res.returncode)
        return False

    exe_path = dist_app / "KRONABEL.exe"
    if not exe_path.exists():
        print("ERROR: Berkas executable tidak ditemukan di:", exe_path)
        return False

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"SUKSES: Executable berhasil dibuat: {exe_path} ({size_mb:.2f} MB)")
    return True


def verify_dist_structure() -> bool:
    print("\n[2/4] Memverifikasi integritas folder dist & isolasi dependensi Windows 10/11...")
    dist_app = DIST_DIR / "KRONABEL"
    exe_file = dist_app / "KRONABEL.exe"
    assets_folder = dist_app / "assets"
    internal_dir = dist_app / "_internal"

    if not exe_file.exists():
        print("ERROR: KRONABEL.exe tidak ada di dist.")
        return False

    if not assets_folder.exists() or not (assets_folder / "app_icon.png").exists():
        print("Menyalin seluruh folder assets (gambar & suara bawaan) ke folder dist...")
        if assets_folder.exists():
            shutil.rmtree(assets_folder)
        shutil.copytree(BASE_DIR / "assets", assets_folder)
    else:
        shutil.copytree(BASE_DIR / "assets", assets_folder, dirs_exist_ok=True)

    # Pastikan python311.dll dan PySide6 ada di _internal
    py311_dll = internal_dir / "python311.dll"
    pyside6_dir = internal_dir / "PySide6"
    if not py311_dll.exists():
        print(f"ERROR: python311.dll tidak ditemukan di {internal_dir}")
        return False
    if not pyside6_dir.exists():
        print(f"ERROR: Direktori PySide6 tidak ditemukan di {internal_dir}")
        return False

    # Pastikan TIDAK ADA artefak Python 3.8 / PySide2 / shiboken2 / Qt5
    forbidden_patterns = ("python38.dll", "pyside2", "shiboken2", "qt5core.dll", "qt5gui.dll", "qt5widgets.dll")
    contaminated = []
    for item in dist_app.rglob("*"):
        name_low = item.name.lower()
        if any(pat in name_low for pat in forbidden_patterns):
            contaminated.append(str(item.relative_to(dist_app)))

    if contaminated:
        print("ERROR: Ditemukan artefak Python 3.8 / PySide2 / Qt5 di dalam build Windows 10/11:", contaminated)
        return False

    print(f"Info: Runtime terverifikasi murni Python 3.11 ({py311_dll.name}) + PySide6 ({pyside6_dir}).")
    print("SUKSES: Struktur folder dist terverifikasi lengkap dan bebas dari dependensi Python 3.8/PySide2.")
    return True


def run_inno_setup() -> Path | None:
    print("\n[3/4] Menyiapkan Installer Windows 10/11 (Inno Setup)...")
    iscc = find_iscc()
    if not iscc:
        print("PERINGATAN: Inno Setup Compiler (ISCC.exe) tidak ditemukan di sistem.")
        return None

    print(f"Menggunakan compiler: {iscc}")
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [str(iscc), str(ISS_FILE)]
    print("Perintah:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(BASE_DIR / "installer"))
    if res.returncode != 0:
        print("ERROR: Kompilasi Inno Setup gagal dengan kode:", res.returncode)
        return None

    installer_exe = RELEASE_DIR / f"KRONABEL_Setup_v{APP_VERSION}.exe"
    if installer_exe.exists():
        size_mb = installer_exe.stat().st_size / (1024 * 1024)
        print(f"SUKSES: Installer Windows berhasil dibuat di: {installer_exe} ({size_mb:.2f} MB)")
        return installer_exe
    return None


def create_portable_zip() -> Path | None:
    print("\n[3.5/4] Membuat Paket Portable ZIP (Siap Copy ke Flashdisk / Komputer Lain)...")
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    dist_app = DIST_DIR / "KRONABEL"
    if not dist_app.exists():
        return None
    zip_base = RELEASE_DIR / f"KRONABEL_Portable_v{APP_VERSION}"
    archive_path = shutil.make_archive(str(zip_base), "zip", root_dir=str(DIST_DIR), base_dir="KRONABEL")
    out_zip = Path(archive_path)
    if out_zip.exists():
        size_mb = out_zip.stat().st_size / (1024 * 1024)
        print(f"SUKSES: Paket Portable ZIP berhasil dibuat di: {out_zip} ({size_mb:.2f} MB)")
        return out_zip
    return None


def generate_release_summary(installer_path: Path | None, portable_zip: Path | None = None) -> None:
    print("\n[4/4] Menghasilkan Ringkasan Artefak Distribusi...")
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    py_ver = subprocess.check_output([PYTHON_EXE, "-c", "import sys; print(sys.version.split()[0])"]).decode().strip()
    pyside_ver = (
        subprocess.check_output([PYTHON_EXE, "-c", "import PySide6; print(PySide6.__version__)"]).decode().strip()
    )
    build_time = subprocess.check_output(["powershell", "-Command", "Get-Date -Format s"]).decode().strip()

    lines = [
        "==================================================================",
        f"PAKET DISTRIBUSI RESMI: KRONABEL v{APP_VERSION} (WINDOWS 10/11 64-BIT)",
        "Aplikasi Bel Otomatis Sekolah",
        "==================================================================",
        f"Tanggal Build : {build_time}",
        f"Versi Python  : {py_ver} (Bundled Standalone - Tidak perlu install Python di PC tujuan)",
        f"Framework GUI : PySide6 {pyside_ver} (Qt 6 Native)",
        "Arsitektur    : Windows 64-bit (x64)",
        "Target OS     : Windows 10 & Windows 11 64-bit (100% Offline Standalone)",
        "",
        "ARTEFAK DISTRIBUSI (SIAP INSTAL DI KOMPUTER LAIN):",
    ]

    exe_file = DIST_DIR / "KRONABEL" / "KRONABEL.exe"
    if exe_file.exists():
        size_mb = exe_file.stat().st_size / (1024 * 1024)
        checksum = calculate_sha256(exe_file)
        lines.append("1. Standalone Executable Binary:")
        lines.append(f"   Lokasi  : {exe_file}")
        lines.append(f"   Ukuran  : {size_mb:.2f} MB ({exe_file.stat().st_size} bytes)")
        lines.append(f"   SHA-256 : {checksum}")

    if installer_path and installer_path.exists():
        size_mb = installer_path.stat().st_size / (1024 * 1024)
        checksum = calculate_sha256(installer_path)
        lines.append("\n2. Windows Setup Installer (.exe) [DIREKOMENDASIKAN UNTUK PC LAIN]:")
        lines.append(f"   Lokasi  : {installer_path}")
        lines.append(f"   Ukuran  : {size_mb:.2f} MB ({installer_path.stat().st_size} bytes)")
        lines.append(f"   SHA-256 : {checksum}")

    if portable_zip and portable_zip.exists():
        size_mb = portable_zip.stat().st_size / (1024 * 1024)
        checksum = calculate_sha256(portable_zip)
        lines.append("\n3. Paket Portable (.zip) [TINGGAL EKSTRAK TANPA INSTAL]:")
        lines.append(f"   Lokasi  : {portable_zip}")
        lines.append(f"   Ukuran  : {size_mb:.2f} MB ({portable_zip.stat().st_size} bytes)")
        lines.append(f"   SHA-256 : {checksum}")

    lines.append("\nDIREKTORI DATA PENGGUNA PERSISTEN (OTOMATIS DIBUAT DI PC TUJUAN):")
    lines.append("   %APPDATA%\\KRONABEL\\data\\bel_sekolah.db")
    lines.append("   %APPDATA%\\KRONABEL\\sounds\\")
    lines.append("   %APPDATA%\\KRONABEL\\backups\\")
    lines.append("   (Kompatibel dan memigrasikan %APPDATA%\\BelOtomatisSekolah otomatis)")
    lines.append("==================================================================")

    content = "\n".join(lines)
    (RELEASE_DIR / "RELEASE_INFO.txt").write_text(content, encoding="utf-8")
    (RELEASE_DIR / f"RELEASE_INFO_v{APP_VERSION}.txt").write_text(content, encoding="utf-8")
    print(content)


def main() -> None:
    if not run_pyinstaller():
        sys.exit(1)
    if not verify_dist_structure():
        sys.exit(1)
    installer_path = run_inno_setup()
    if installer_path is None:
        sys.exit(1)
    portable_zip = create_portable_zip()
    if portable_zip is None:
        sys.exit(1)
    generate_release_summary(installer_path, portable_zip)
    print("\nProses build dan packaging Windows 10/11 selesai dengan sukses!")


if __name__ == "__main__":
    main()
