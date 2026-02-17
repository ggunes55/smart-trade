# -*- coding: utf-8 -*-
"""
Control Panel Widget - Kontrol paneli widget'ı
"""
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QProgressBar,
    QLabel,
)
from ..utils.styles import SUCCESS_BUTTON, STOP_BUTTON, STATUS_LABEL


class ControlPanel(QGroupBox):
    """Kontrol paneli widget'ı"""

    def __init__(self, parent=None):
        super().__init__("🎮 Kontrol Paneli", parent)
        self.init_ui()

    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout()

        # Butonlar
        button_layout = QHBoxLayout()

        self.run_btn = QPushButton("▶️ Taramayı Başlat")
        self.run_btn.setStyleSheet(SUCCESS_BUTTON)

        self.stop_btn = QPushButton("⏸️ Durdur")
        self.stop_btn.setStyleSheet(STOP_BUTTON)
        self.stop_btn.setEnabled(False)

        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.stop_btn)

        # İlerleme
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { height: 25px; }")

        self.status_label = QLabel("⏳ Beklemede...")
        self.status_label.setStyleSheet(STATUS_LABEL)

        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def set_scanning(self, is_scanning):
        """Tarama durumunu ayarla"""
        self.run_btn.setEnabled(not is_scanning)
        self.stop_btn.setEnabled(is_scanning)

        if is_scanning:
            self.run_btn.setText("⏳ Tarama Sürüyor...")
            self.status_label.setText("🔍 Tarama başladı...")
        else:
            self.run_btn.setText("▶️ Taramayı Başlat")

    def update_progress(self, percent, message):
        """İlerlemeyi güncelle"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def reset(self):
        """Paneli sıfırla"""
        self.progress_bar.setValue(0)
        self.status_label.setText("⏳ Beklemede...")
        self.set_scanning(False)
