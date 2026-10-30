"""
Modul Verifikasi Backend Qt (PySide6 Native untuk Windows 10 & Windows 11).
Seluruh patch, shim PySide2/shiboken2, dan penyesuaian khusus Windows 7 telah dihentikan.
"""

from __future__ import annotations


def install_qt_compat() -> str:
    """
    Memastikan PySide6 tersedia secara native untuk Windows 10/11
    tanpa melakukan patch sys.modules, modifikasi PATH, atau penyesuaian Windows 7.
    """
    import PySide6  # noqa: F401

    return "PySide6"
