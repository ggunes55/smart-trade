"""
Fundamental Analysis Widget - Temel analiz paneli
"""

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QGroupBox,
    QPushButton,
    QDialog,
)
from .fundamental_analysis import FundamentalAnalysis


class FundamentalPanel(QWidget):
    """
    Temel analiz özet paneli (sol tarafta)
    - Özet bilgiler
    - Detay butonu
    - Geliştirilmiş hata yönetimi ve retry mekanizması
    """

    def __init__(self, symbol: str, exchange: str = "BIST", parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.exchange = exchange
        self.fundamentals = None
        self.retry_count = 0
        self.max_retries = 2
        self.setMaximumWidth(580)  # Panelin maksimum genişliği
        self._build_ui()

    def _build_ui(self):
        """UI oluştur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Başlık
        title = QLabel("📈 TEMEL ANALİZ")
        title.setStyleSheet("font-weight: bold; font-size: 11px; padding: 5px;")
        layout.addWidget(title)

        # Verileri yükle (exchange-aware) - Retry mekanizması ile
        self.fundamentals = self._load_fundamentals_with_retry()

        if not self.fundamentals:
            self._build_error_ui(layout)
            return

        # Şirket adı
        company_name = self.fundamentals["company_info"]["name"]
        name_label = QLabel(f"<b>{company_name}</b>")
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-size: 10px; padding: 5px;")
        layout.addWidget(name_label)

        # Sektör
        sector = self.fundamentals["company_info"]["sector"]
        sector_label = QLabel(f"🏢 {sector}")
        sector_label.setStyleSheet("font-size: 9px; padding: 3px;")
        layout.addWidget(sector_label)

        # Önemli oranlar
        ratios = self.fundamentals["financial_ratios"]

        # F/K Oranı
        pe = ratios["pe_ratio"]
        pe_analysis = FundamentalAnalysis.get_pe_analysis(pe)
        pe_text = f"{pe:.2f}" if pe else "N/A"
        pe_label = QLabel(f"{pe_analysis['emoji']} F/K: {pe_text}")
        pe_label.setStyleSheet("font-size: 9px; padding: 2px;")
        pe_label.setToolTip(pe_analysis["description"])
        layout.addWidget(pe_label)

        # PD/DD Oranı
        pb = ratios["pb_ratio"]
        pb_analysis = FundamentalAnalysis.get_pb_analysis(pb)
        pb_text = f"{pb:.2f}" if pb else "N/A"
        pb_label = QLabel(f"{pb_analysis['emoji']} PD/DD: {pb_text}")
        pb_label.setStyleSheet("font-size: 9px; padding: 2px;")
        pb_label.setToolTip(pb_analysis["description"])
        layout.addWidget(pb_label)

        # ROE
        prof = self.fundamentals["profitability"]
        roe = prof["roe"]
        roe_analysis = FundamentalAnalysis.get_roe_analysis(roe)
        roe_text = FundamentalAnalysis.format_percentage(roe)
        roe_label = QLabel(f"{roe_analysis['emoji']} ROE: {roe_text}")
        roe_label.setStyleSheet("font-size: 9px; padding: 2px;")
        roe_label.setToolTip(roe_analysis["description"])
        layout.addWidget(roe_label)

        # Temettü Verimi
        div = self.fundamentals["dividend"]
        div_yield = div["dividend_yield"]
        if div_yield:
            div_text = FundamentalAnalysis.format_percentage(div_yield)
            div_emoji = "💰" if div_yield > 0.03 else "💵"
            div_label = QLabel(f"{div_emoji} Temettü: {div_text}")
            div_label.setStyleSheet("font-size: 9px; padding: 2px;")
            layout.addWidget(div_label)

        # Detay butonu
        detail_btn = QPushButton("📊 Detaylı Analiz")
        detail_btn.clicked.connect(self.show_detailed_analysis)
        detail_btn.setStyleSheet(
            """
            QPushButton {
                padding: 8px;
                border: 1px solid #2196F3;
                border-radius: 4px;
                background: white;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #e3f2fd;
            }
        """
        )
        layout.addWidget(detail_btn)

        layout.addStretch()

    def _load_fundamentals_with_retry(self):
        """Retry mekanizması ile verileri yükle"""
        import logging
        import time
        
        for attempt in range(self.max_retries + 1):
            try:
                fundamentals = FundamentalAnalysis.get_fundamentals(self.symbol, self.exchange)
                if fundamentals:
                    logging.info(f"✅ {self.symbol} ({self.exchange}): Temel analiz başarıyla yüklendi")
                    return fundamentals
                else:
                    logging.warning(f"⚠️ {self.symbol} ({self.exchange}): Temel analiz verisi bulunamadı")
            except Exception as e:
                logging.error(f"❌ {self.symbol} ({self.exchange}): Temel analiz hatası - {str(e)}")
                if attempt < self.max_retries:
                    time.sleep(1)  # 1 saniye bekle
                    continue
        
        return None

    def _build_error_ui(self, layout: QVBoxLayout):
        """Hata durumu için UI oluştur"""
        # Hata mesajı
        error_label = QLabel(
            f"⚠️ {self.symbol} ({self.exchange}) için\ntemel analiz verisi alınamadı"
        )
        error_label.setStyleSheet(
            "color: #F44336; padding: 10px; background: #FFEBEE; "
            "border-radius: 4px; font-size: 9px;"
        )
        error_label.setWordWrap(True)
        layout.addWidget(error_label)
        
        # Yardımcı bilgi
        info_label = QLabel(
            "Olası nedenler:\n"
            "• İnternet bağlantısı sorunu\n"
            "• yfinance kütüphanesi eksik\n"
            "• Symbol yanlış formatında"
        )
        info_label.setStyleSheet(
            "color: #666; padding: 8px; font-size: 8px; "
            "background: #F5F5F5; border-radius: 4px;"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Yeniden dene butonu
        retry_btn = QPushButton("🔄 Yeniden Dene")
        retry_btn.setStyleSheet(
            """
            QPushButton {
                padding: 6px;
                border: 1px solid #FF9800;
                border-radius: 4px;
                background: white;
                font-size: 9px;
                font-weight: bold;
                color: #FF9800;
            }
            QPushButton:hover {
                background: #FFF3E0;
            }
        """
        )
        retry_btn.clicked.connect(self._retry_load)
        layout.addWidget(retry_btn)
        
        layout.addStretch()

    def _retry_load(self):
        """Verileri yeniden yüklemeyi dene"""
        import logging
        
        logging.info(f"🔄 {self.symbol} ({self.exchange}): Temel analiz yeniden yükleniyor...")
        
        # Mevcut layout'u temizle
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Yeniden oluştur
        self._build_ui()

    def show_detailed_analysis(self):
        """Detaylı analiz dialogunu aç"""
        if not self.fundamentals:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Uyarı",
                f"{self.symbol} için temel analiz verisi bulunamadı.\n\n"
                "Lütfen internet bağlantınızı kontrol edin ve yeniden deneyin."
            )
            return
        
        dialog = FundamentalDetailDialog(self.symbol, self.fundamentals, self)
        dialog.exec_()


class FundamentalDetailDialog(QDialog):
    """
    Detaylı temel analiz dialogu
    - Tüm finansal oranlar
    - Şirket bilgileri
    - Piyasa verileri
    """

    def __init__(self, symbol: str, fundamentals: dict, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.fundamentals = fundamentals
        self.setWindowTitle(f"📊 {symbol} - Detaylı Temel Analiz")
        self.resize(700, 800)
        self._build_ui()

    def _build_ui(self):
        """UI oluştur"""
        layout = QVBoxLayout(self)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)

        # 1. Şirket Bilgileri
        content_layout.addWidget(self._create_company_info_group())

        # 2. Finansal Oranlar
        content_layout.addWidget(self._create_financial_ratios_group())

        # 3. Karlılık Metrikleri
        content_layout.addWidget(self._create_profitability_group())

        # 4. Temettü Bilgileri
        content_layout.addWidget(self._create_dividend_group())

        # 5. Piyasa Verileri
        content_layout.addWidget(self._create_market_data_group())

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _create_company_info_group(self) -> QGroupBox:
        """Şirket bilgileri grubu"""
        group = QGroupBox("🏢 Şirket Bilgileri")
        layout = QVBoxLayout()

        info = self.fundamentals["company_info"]

        items = [
            ("Şirket", info["name"]),
            ("Sektör", info["sector"]),
            ("Endüstri", info["industry"]),
            ("Ülke", info["country"]),
            ("Şehir", info["city"]),
            (
                "Çalışan Sayısı",
                f"{info['employees']:,}" if info["employees"] else "N/A",
            ),
            ("Website", info["website"]),
        ]

        for label, value in items:
            text = f"<b>{label}:</b> {value}"
            label_widget = QLabel(text)
            label_widget.setWordWrap(True)
            layout.addWidget(label_widget)

        group.setLayout(layout)
        return group

    def _create_financial_ratios_group(self) -> QGroupBox:
        """Finansal oranlar grubu"""
        group = QGroupBox("💹 Finansal Oranlar")
        layout = QVBoxLayout()

        ratios = self.fundamentals["financial_ratios"]

        # F/K
        pe = ratios["pe_ratio"]
        pe_analysis = FundamentalAnalysis.get_pe_analysis(pe)
        pe_text = f"{pe:.2f}" if pe else "N/A"
        pe_label = QLabel(
            f"{pe_analysis['emoji']} <b>F/K (P/E):</b> {pe_text} - "
            f"<i>{pe_analysis['description']}</i>"
        )
        pe_label.setWordWrap(True)
        layout.addWidget(pe_label)

        # PD/DD
        pb = ratios["pb_ratio"]
        pb_analysis = FundamentalAnalysis.get_pb_analysis(pb)
        pb_text = f"{pb:.2f}" if pb else "N/A"
        pb_label = QLabel(
            f"{pb_analysis['emoji']} <b>PD/DD (P/B):</b> {pb_text} - "
            f"<i>{pb_analysis['description']}</i>"
        )
        pb_label.setWordWrap(True)
        layout.addWidget(pb_label)

        # Diğer oranlar
        other_ratios = [
            ("F/S (P/S)", ratios["ps_ratio"], lambda x: f"{x:.2f}" if x else "N/A"),
            ("PEG", ratios["peg_ratio"], lambda x: f"{x:.2f}" if x else "N/A"),
            (
                "Borç/Özkaynak",
                ratios["debt_to_equity"],
                lambda x: f"{x:.2f}" if x else "N/A",
            ),
            (
                "Cari Oran",
                ratios["current_ratio"],
                lambda x: f"{x:.2f}" if x else "N/A",
            ),
            (
                "Asit-Test Oranı",
                ratios["quick_ratio"],
                lambda x: f"{x:.2f}" if x else "N/A",
            ),
        ]

        for name, value, formatter in other_ratios:
            text = f"<b>{name}:</b> {formatter(value)}"
            layout.addWidget(QLabel(text))

        group.setLayout(layout)
        return group

    def _create_profitability_group(self) -> QGroupBox:
        """Karlılık metrikleri grubu"""
        group = QGroupBox("📈 Karlılık Metrikleri")
        layout = QVBoxLayout()

        prof = self.fundamentals["profitability"]

        # ROE
        roe = prof["roe"]
        roe_analysis = FundamentalAnalysis.get_roe_analysis(roe)
        roe_text = FundamentalAnalysis.format_percentage(roe)
        roe_label = QLabel(
            f"{roe_analysis['emoji']} <b>ROE (Özkaynak Karlılığı):</b> {roe_text} - "
            f"<i>{roe_analysis['description']}</i>"
        )
        roe_label.setWordWrap(True)
        layout.addWidget(roe_label)

        # Diğer karlılık metrikleri
        metrics = [
            ("ROA (Aktif Karlılığı)", prof["roa"]),
            ("Net Kar Marjı", prof["profit_margin"]),
            ("Faaliyet Kar Marjı", prof["operating_margin"]),
            ("Brüt Kar Marjı", prof["gross_margin"]),
            ("Gelir Büyümesi", prof["revenue_growth"]),
            ("Kazanç Büyümesi", prof["earnings_growth"]),
        ]

        for name, value in metrics:
            text = f"<b>{name}:</b> {FundamentalAnalysis.format_percentage(value)}"
            layout.addWidget(QLabel(text))

        group.setLayout(layout)
        return group

    def _create_dividend_group(self) -> QGroupBox:
        """Temettü bilgileri grubu"""
        group = QGroupBox("💰 Temettü Bilgileri")
        layout = QVBoxLayout()

        div = self.fundamentals["dividend"]

        items = [
            (
                "Temettü Verimi",
                FundamentalAnalysis.format_percentage(div["dividend_yield"]),
            ),
            (
                "Temettü Tutarı",
                f"${div['dividend_rate']:.2f}" if div["dividend_rate"] else "N/A",
            ),
            ("Ödeme Oranı", FundamentalAnalysis.format_percentage(div["payout_ratio"])),
            (
                "5 Yıl Ort. Verim",
                FundamentalAnalysis.format_percentage(
                    div["five_year_avg_dividend_yield"]
                ),
            ),
        ]

        for label, value in items:
            text = f"<b>{label}:</b> {value}"
            layout.addWidget(QLabel(text))

        group.setLayout(layout)
        return group

    def _create_market_data_group(self) -> QGroupBox:
        """Piyasa verileri grubu"""
        group = QGroupBox("📊 Piyasa Verileri")
        layout = QVBoxLayout()

        market = self.fundamentals["market_data"]

        items = [
            (
                "Piyasa Değeri",
                FundamentalAnalysis.format_large_number(market["market_cap"]),
            ),
            (
                "Şirket Değeri",
                FundamentalAnalysis.format_large_number(market["enterprise_value"]),
            ),
            (
                "Dolaşımdaki Hisse",
                FundamentalAnalysis.format_large_number(market["shares_outstanding"]),
            ),
            ("Beta", f"{market['beta']:.2f}" if market["beta"] else "N/A"),
            (
                "52 Hafta Yüksek",
                (
                    f"${market['fifty_two_week_high']:.2f}"
                    if market["fifty_two_week_high"]
                    else "N/A"
                ),
            ),
            (
                "52 Hafta Düşük",
                (
                    f"${market['fifty_two_week_low']:.2f}"
                    if market["fifty_two_week_low"]
                    else "N/A"
                ),
            ),
            (
                "Ortalama Hacim",
                FundamentalAnalysis.format_large_number(market["avg_volume"]),
            ),
        ]

        for label, value in items:
            text = f"<b>{label}:</b> {value}"
            layout.addWidget(QLabel(text))

        group.setLayout(layout)
        return group
