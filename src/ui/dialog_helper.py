"""
Helper untuk memastikan seluruh dialog QMessageBox tampil dengan kontras tinggi,
latar belakang putih solid, tombol biru/abu yang jelas, dan tidak terpengaruh
efek transparansi (WA_TranslucentBackground) dari window induk di Windows 11.
"""

from __future__ import annotations

import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

BOX_STYLESHEET = """
QMessageBox {
    background-color: #ffffff;
    color: #0f172a;
}
QMessageBox QLabel {
    color: #0f172a;
    background-color: transparent;
    font-size: 13px;
    font-weight: 500;
    font-family: 'Segoe UI', Arial, sans-serif;
    min-height: 38px;
}
QMessageBox QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1.5px solid #1d4ed8;
    border-radius: 6px;
    padding: 6px 22px;
    min-width: 80px;
    min-height: 28px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QMessageBox QPushButton:default {
    background-color: #2563eb;
    color: #ffffff;
    border: 1.5px solid #1d4ed8;
}
QMessageBox QPushButton:hover {
    background-color: #1d4ed8;
    border-color: #1e40af;
    color: #ffffff;
}
QMessageBox QPushButton:focus {
    background-color: #2563eb;
    color: #ffffff;
    border: 2px solid #60a5fa;
    outline: none;
}
QMessageBox QPushButton:pressed {
    background-color: #1e40af;
    color: #ffffff;
}
QMessageBox QPushButton:!default {
    background-color: #f1f5f9;
    color: #0f172a;
    border: 1.5px solid #cbd5e1;
}
QMessageBox QPushButton:!default:hover {
    background-color: #e2e8f0;
    border-color: #94a3b8;
    color: #0f172a;
}
QMessageBox QPushButton:!default:focus {
    background-color: #e2e8f0;
    color: #0f172a;
    border: 2px solid #2563eb;
}
"""


def _safe_exec_box(icon: QMessageBox.Icon, *args, **kwargs):
    parent = args[0] if len(args) > 0 else kwargs.get("parent", None)
    title = str(args[1]) if len(args) > 1 else str(kwargs.get("title", ""))
    text = str(args[2]) if len(args) > 2 else str(kwargs.get("text", ""))
    buttons = args[3] if len(args) > 3 else kwargs.get("buttons", QMessageBox.StandardButton.Ok)
    default_button = args[4] if len(args) > 4 else kwargs.get("defaultButton", QMessageBox.StandardButton.NoButton)

    box = QMessageBox(icon, title, text, buttons, parent)
    box.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    box.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
    box.setAutoFillBackground(True)
    if default_button != QMessageBox.StandardButton.NoButton:
        box.setDefaultButton(default_button)
    box.setStyleSheet(BOX_STYLESHEET)

    res = box.exec()
    clicked = box.clickedButton()
    if clicked:
        std = box.standardButton(clicked)
        if std != QMessageBox.StandardButton.NoButton:
            return std
    return res


def patch_qmessagebox():
    """Memasang patch aman agar seluruh static call QMessageBox selalu putih & jelas."""
    QMessageBox.information = staticmethod(lambda *a, **k: _safe_exec_box(QMessageBox.Icon.Information, *a, **k))
    QMessageBox.warning = staticmethod(lambda *a, **k: _safe_exec_box(QMessageBox.Icon.Warning, *a, **k))
    QMessageBox.critical = staticmethod(lambda *a, **k: _safe_exec_box(QMessageBox.Icon.Critical, *a, **k))
    QMessageBox.question = staticmethod(lambda *a, **k: _safe_exec_box(QMessageBox.Icon.Question, *a, **k))
