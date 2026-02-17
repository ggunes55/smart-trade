# -*- coding: utf-8 -*-
"""
Market Tab - Piyasa analizi ve backtest sekmesi
"""
import logging
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QSpinBox,
)
from PyQt5.QtCore import pyqtSignal
from ..utils.styles import BLUE_BUTTON, MARKET_DETAILS
from ..utils.helpers import get_market_strategy, format_backtest_results


class MarketTab(QWidget):
    """Piyasa analizi ve backtest sekmesi"""

    refresh_market = pyqtSignal()  # Piyasa yenileme sinyali
    start_backtest = pyqtSignal(dict)  # Backtest başlat sinyali

    def __init__(self, parent=None):
        super().__init__(parent)
        self.market_analysis = None
        self.init_ui()

    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)

        # Piyasa durumu grubu
        market_group = self._create_market_group()
        layout.addWidget(market_group)

        # Backtest grubu
        backtest_group = self._create_backtest_group()
        layout.addWidget(backtest_group, 1)

    def _create_market_group(self):
        """Piyasa durumu grubu"""
        group = QGroupBox("📈 Canlı Piyasa Durumu")
        layout = QVBoxLayout()

        self.market_status_label = QLabel("🔄 Piyasa analizi yapılıyor...")
        self.market_status_label.setStyleSheet(
            "font-size: 12pt; padding: 10px; background-color: #e3f2fd; border-radius: 4px;"
        )
        self.market_status_label.setWordWrap(True)

        self.market_details = QTextEdit()
        self.market_details.setReadOnly(True)
        self.market_details.setMaximumHeight(150)
        self.market_details.setStyleSheet(MARKET_DETAILS)

        # Yenile butonu
        btn_layout = QHBoxLayout()
        self.refresh_market_btn = QPushButton("🔄 Piyasa Analizini Yenile")
        self.refresh_market_btn.clicked.connect(lambda: self.refresh_market.emit())
        self.refresh_market_btn.setStyleSheet(BLUE_BUTTON)

        btn_layout.addWidget(self.refresh_market_btn)
        btn_layout.addStretch()

        layout.addWidget(self.market_status_label)
        layout.addWidget(self.market_details)
        layout.addLayout(btn_layout)

        group.setLayout(layout)
        return group

    def _create_backtest_group(self):
        """Backtest grubu"""
        group = QGroupBox("🎯 Gelişmiş Backtest")
        layout = QVBoxLayout()

        # Ayarlar
        settings_layout = QHBoxLayout()

        settings_layout.addWidget(QLabel("Gün:"))
        self.backtest_days = QSpinBox()
        self.backtest_days.setRange(30, 730)
        self.backtest_days.setValue(180)
        settings_layout.addWidget(self.backtest_days)

        settings_layout.addWidget(QLabel("Sermaye:"))
        self.initial_capital = QSpinBox()
        self.initial_capital.setRange(1000, 100000)
        self.initial_capital.setValue(10000)
        self.initial_capital.setSuffix(" TL")
        settings_layout.addWidget(self.initial_capital)

        settings_layout.addStretch()

        # Başlat butonu
        self.backtest_btn = QPushButton("▶️ Backtest Başlat")
        self.backtest_btn.clicked.connect(self.on_backtest_clicked)
        self.backtest_btn.setStyleSheet(BLUE_BUTTON + " padding: 10px;")

        # Sonuçlar
        self.backtest_results_text = QTextEdit()
        self.backtest_results_text.setReadOnly(True)
        self.backtest_results_text.setStyleSheet(
            "font-family: 'Courier New'; font-size: 9pt; background-color: #f5f5f5;"
        )

        layout.addLayout(settings_layout)
        layout.addWidget(self.backtest_btn)
        layout.addWidget(self.backtest_results_text, 1)

        group.setLayout(layout)
        return group

    def on_backtest_clicked(self):
        """Backtest butonuna tıklandığında"""
        config = {
            "days": self.backtest_days.value(),
            "initial_capital": self.initial_capital.value(),
            "commission_rate": 0.2,
        }
        self.start_backtest.emit(config)

    def update_market_analysis(self, analysis):
        """Piyasa analizini güncelle"""
        self.market_analysis = analysis

        # Renk kodları
        color = "#4CAF50"
        if analysis.regime == "bearish":
            color = "#f44336"
        elif analysis.regime == "volatile":
            color = "#FF9800"
        elif analysis.regime == "sideways":
            color = "#2196F3"

        self.market_status_label.setText(
            f"📈 Piyasa Durumu: <span style='color: {color}; font-weight: bold;'>"
            f"{analysis.regime.upper()}</span> - {analysis.recommendation}"
        )

        # Detaylı bilgi
        details = f"""
📊 PİYASA ANALİZ RAPORU
{'='*40}
📈 Trend Gücü: {analysis.trend_strength}/100
📉 Volatilite: {analysis.volatility}%
📊 Hacim Trendi: {analysis.volume_trend:.2f}x
⭐ Piyasa Skoru: {analysis.market_score}/100

💡 ÖNERİ: {analysis.recommendation}

📋 STRATEJİ:
{get_market_strategy(analysis.regime)}
"""
        self.market_details.setText(details)

        logging.info(f"✅ Piyasa analizi tamamlandı: {analysis.regime}")

    def update_market_error(self, error_message):
        """Piyasa analizi hatasını göster"""
        self.market_status_label.setText("❌ Piyasa analizi başarısız")
        self.market_details.setText(
            f"Hata: {error_message}\n\n"
            "Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin."
        )
        logging.error(f"Piyasa analizi hatası: {error_message}")

    def set_backtest_running(self, is_running):
        """Backtest durumunu ayarla"""
        self.backtest_btn.setEnabled(not is_running)
        if is_running:
            self.backtest_btn.setText("⏳ Backtest Sürüyor...")
        else:
            self.backtest_btn.setText("▶️ Backtest Başlat")

    def update_backtest_results(self, results):
        """Backtest sonuçlarını güncelle"""
        formatted_results = format_backtest_results(results)
        self.backtest_results_text.setPlainText(formatted_results)
