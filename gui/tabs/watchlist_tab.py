# -*- coding: utf-8 -*-
"""
Watchlist Tab (V2.0) - Professional Swing Trade Tracking UI
Comprehensive watchlist display with status labels, alerts, and archive
"""
import logging
from datetime import datetime
from typing import Optional, Dict, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QLabel, QSplitter,
    QTabWidget, QComboBox, QLineEdit, QCheckBox, QSpinBox,
    QGroupBox, QFormLayout, QTextEdit, QDialog, QDialogButtonBox,
    QFrame, QScrollArea, QMenu, QAction
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QBrush, QCursor

from watchlist import WatchlistManager, PerformanceAnalyzer
from ..utils.translations import translate, format_trend_turkish, format_strength_turkish
from ..workers.watchlist_worker import WatchlistUpdateWorker
from ..widgets.risk_analysis_dialog import RiskAnalysisDialog

logger = logging.getLogger(__name__)


# =============================================================================
# RENK KODLARI
# =============================================================================

class WatchlistColors:
    """Watchlist renk şeması"""
    # Durum renkleri
    STOP_NEAR = QColor(255, 100, 100)       # 🔴 Stop yakın (<5%)
    CONSOLIDATION = QColor(255, 255, 150)   # 🟡 Konsolidasyon
    TARGET_NEAR = QColor(100, 255, 100)     # 🟢 Hedef yakın (<5%)
    NEW_ENTRY = QColor(100, 200, 255)       # 🔵 Yeni eklenen (24h)
    EXPIRED = QColor(180, 180, 180)         # ⚫ Süresi dolmuş (>14 gün)
    
    # Trend renkleri
    TREND_UP = QColor(0, 150, 0)
    TREND_DOWN = QColor(200, 0, 0)
    TREND_SIDEWAYS = QColor(150, 150, 0)
    
    # Genel
    POSITIVE = QColor(0, 150, 0)
    NEGATIVE = QColor(200, 0, 0)
    NEUTRAL = QColor(100, 100, 100)
    WARNING = QColor(255, 165, 0)
    
    # Arka plan
    ROW_ALT = QColor(248, 248, 248)
    ROW_SELECTED = QColor(220, 240, 255)


# =============================================================================
# ANA WATCHLIST TAB
# =============================================================================

class WatchlistTab(QWidget):
    """
    Watchlist Tab Widget (V2.0)
    - Sekmeli arayüz (Ana Liste, Alarmlar, Arşiv)
    - Kapsamlı sütunlar ve renk kodlaması
    - Durum etiketleri ve filtreler
    """
    
    # Signal: Hisse seçildiğinde emit edilir
    symbol_selected = pyqtSignal(str, str)  # symbol, exchange
    
    def __init__(self, scanner=None, parent=None):
        super().__init__(parent)
        
        self.scanner = scanner
        self.config = scanner.cfg if scanner else {}
        
        # Watchlist manager
        db_path = self.config.get('watchlist_db_path', 'watchlist.db')
        logger.info(f"Initializing WatchlistManager with db_path: {db_path}")
        
        # Database başlat
        from watchlist.database import init_db
        try:
            init_db(db_path)
            logger.info(f"✅ Database initialized: {db_path}")
        except Exception as e:
            logger.error(f"❌ Database init error: {e}")
        
        self.manager = WatchlistManager(db_path)
        self.analyzer = PerformanceAnalyzer(self.manager)
        
        self.current_comparison: Optional[Dict] = None
        self.current_filter = None  # Status filter
        
        # Async worker
        self._update_worker: Optional[WatchlistUpdateWorker] = None
        self._is_refreshing = False
        
        self._init_ui()
        
        # Load watchlist after UI is ready
        try:
            self._load_watchlist()
            logger.info(f"✅ Watchlist loaded successfully")
        except Exception as e:
            logger.error(f"❌ Error loading watchlist: {e}", exc_info=True)
    
    def _init_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Header bar
        header = self._create_header()
        layout.addWidget(header)
        
        # Ana sekme widget
        self.tabs = QTabWidget()
        
        # Tab 1: Ana Watchlist
        self.main_tab = self._create_main_tab()
        self.tabs.addTab(self.main_tab, "📋 Takip Listesi")
        
        # Tab 2: Alarmlar
        self.alerts_tab = self._create_alerts_tab()
        self.tabs.addTab(self.alerts_tab, "🔔 Alarmlar")
        
        # Tab 3: Arşiv
        self.archive_tab = self._create_archive_tab()
        self.tabs.addTab(self.archive_tab, "📦 Arşiv")
        
        layout.addWidget(self.tabs)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QWidget:
        """Header bar with controls"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Title
        title = QLabel("📊 Profesyonel Swing Trade Takip Listesi")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1a237e;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Status filter
        filter_label = QLabel("Filtre:")
        layout.addWidget(filter_label)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems([
            "Tümü",
            "🟢 Aktif",
            "🟡 Bekle",
            "🔵 Alarm Bekliyor",
            "🔴 Pasif"
        ])
        self.status_filter.currentTextChanged.connect(self._on_filter_changed)
        self.status_filter.setMinimumWidth(120)
        layout.addWidget(self.status_filter)
        
        layout.addSpacing(20)
        
        # Buttons
        refresh_btn = QPushButton("🔄 Güncelle")
        refresh_btn.setToolTip("Tüm sembolleri güncelle")
        refresh_btn.clicked.connect(self._refresh_all)
        refresh_btn.setStyleSheet("padding: 5px 15px;")
        self.refresh_btn = refresh_btn  # Store reference
        layout.addWidget(refresh_btn)
        
        # Cancel button (hidden by default)
        cancel_btn = QPushButton("⏹️ İptal")
        cancel_btn.setToolTip("Güncellemeyi iptal et")
        cancel_btn.clicked.connect(self._cancel_refresh)
        cancel_btn.setStyleSheet("padding: 5px 15px; background-color: #9e9e9e; color: white;")
        cancel_btn.setVisible(False)
        self.cancel_btn = cancel_btn
        layout.addWidget(cancel_btn)
        
        # Progress label (hidden by default)
        progress_label = QLabel("")
        progress_label.setStyleSheet("color: #1565c0; font-weight: bold;")
        progress_label.setVisible(False)
        self.progress_label = progress_label
        layout.addWidget(progress_label)
        
        stats_btn = QPushButton("📈 İstatistikler")
        stats_btn.setToolTip("Performans istatistikleri")
        stats_btn.clicked.connect(self._show_statistics)
        stats_btn.setStyleSheet("padding: 5px 15px;")
        layout.addWidget(stats_btn)
        
        cleanup_btn = QPushButton("🧹 Otomatik Temizle")
        cleanup_btn.setToolTip("Kuralları uygula ve temizle")
        cleanup_btn.clicked.connect(self._auto_cleanup)
        cleanup_btn.setStyleSheet("padding: 5px 15px; background-color: #ff9800; color: white;")
        layout.addWidget(cleanup_btn)
        
        delete_btn = QPushButton("🗑️ Seçilenleri Sil")
        delete_btn.setToolTip("Seçili sembolleri sil")
        delete_btn.clicked.connect(self._bulk_delete)
        delete_btn.setStyleSheet("padding: 5px 15px; background-color: #f44336; color: white;")
        layout.addWidget(delete_btn)
        
        widget.setLayout(layout)
        widget.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        return widget
    
    def _create_main_tab(self) -> QWidget:
        """Ana watchlist sekmesi"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Splitter: Table + Details panel
        splitter = QSplitter(Qt.Vertical)
        
        # Main table
        self.table = self._create_table()
        splitter.addWidget(self.table)
        
        # Details panel
        self.details_panel = self._create_details_panel()
        splitter.addWidget(self.details_panel)
        
        # Initial sizes (75% table, 25% details)
        splitter.setSizes([750, 250])
        
        layout.addWidget(splitter)
        widget.setLayout(layout)
        return widget
    
    def _create_table(self) -> QTableWidget:
        """Ana watchlist tablosu - kapsamlı sütunlar"""
        table = QTableWidget()
        
        # Sütun grupları - Boş sütunlar kaldırıldı (Sektör, Endeks, Likidite)
        columns = [
            # Kimlik
            "Sembol", "Borsa",
            # Trend
            "Trend", "Güç", "Setup",
            # Teknik
            # Teknik
            "Trend Skor", "Risk Skor", "RSI", "ADX", "RVOL",
            # Trade Plan
            "Giriş", "Stop", "H1", "H2", "R:R",
            # Durum
            "Fiyat", "Fiyat Δ%", "SL Uzak%", "H1 Uzak%",
            # Timing
            "Setup Dur.", "Gün",
            # Status
            "Durum"
        ]
        
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        
        # Header styling
        header = table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #1a237e;
                color: white;
                padding: 5px;
                font-weight: bold;
            }
        """)
        
        # Column widths
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Sembol
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Borsa
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # Setup
        header.setDefaultSectionSize(70)
        
        # Row selection
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setAlternatingRowColors(True)
        
        # Context menu
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_table_context_menu)
        
        # Click event
        table.itemSelectionChanged.connect(self._on_row_selected)
        table.doubleClicked.connect(self._on_row_double_clicked)
        
        return table
    
    def _create_details_panel(self) -> QWidget:
        """Detay paneli - seçili sembol bilgileri"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
            }
        """)
        layout = QVBoxLayout()
        
        # Title
        self.details_title = QLabel("📊 Detaylar için bir sembol seçin")
        self.details_title.setStyleSheet("font-weight: bold; font-size: 12pt; color: #1a237e;")
        layout.addWidget(self.details_title)
        
        # Content area with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        content_layout = QHBoxLayout()
        
        # Left: Price/Technical info
        left_group = QGroupBox("Teknik Bilgiler")
        left_layout = QFormLayout()
        
        self.detail_labels = {}
        detail_fields = [
            ("price", "Güncel Fiyat"),
            ("entry", "Giriş Fiyatı"),
            ("stop", "Stop Loss"),
            ("target1", "Hedef 1"),
            ("target2", "Hedef 2"),
            ("target3", "Hedef 3"),
            ("rr_ratio", "Risk/Reward"),
            ("rsi", "RSI"),
            ("adx", "ADX"),
            ("macd", "MACD"),
            ("trend_score", "Trend Skoru"),
        ]
        
        for key, label in detail_fields:
            lbl = QLabel("-")
            lbl.setStyleSheet("font-weight: bold;")
            self.detail_labels[key] = lbl
            left_layout.addRow(f"{label}:", lbl)
        
        left_group.setLayout(left_layout)
        content_layout.addWidget(left_group)
        
        # Right: Status/Analysis
        right_group = QGroupBox("Analiz & Durum")
        right_layout = QFormLayout()
        
        detail_fields2 = [
            ("main_trend", "Ana Trend"),
            ("setup_type", "Setup Tipi"),
            ("tv_signal", "TV Sinyal"),
            ("ml_quality", "ML Kalite"),
            ("squeeze", "Squeeze"),
            ("divergence", "Divergence"),
            ("rs_rating", "RS Rating"),
            ("sharpe", "Sharpe"),
            ("volatility", "Volatilite"),
            ("added_date", "Eklenme"),
            ("days_in_list", "Listede (gün)"),
        ]
        
        for key, label in detail_fields2:
            lbl = QLabel("-")
            lbl.setStyleSheet("font-weight: bold;")
            self.detail_labels[key] = lbl
            right_layout.addRow(f"{label}:", lbl)
        
        right_group.setLayout(right_layout)
        content_layout.addWidget(right_group)
        
        # Far right: Actions
        action_group = QGroupBox("Hızlı İşlemler")
        action_layout = QVBoxLayout()
        
        self.btn_set_ready = QPushButton("✅ Hazır İşaretle")
        self.btn_set_ready.clicked.connect(lambda: self._set_setup_status("READY"))
        action_layout.addWidget(self.btn_set_ready)
        
        self.btn_set_wait = QPushButton("⏳ Bekle İşaretle")
        self.btn_set_wait.clicked.connect(lambda: self._update_status("WAIT"))
        action_layout.addWidget(self.btn_set_wait)
        
        self.btn_add_alert = QPushButton("🔔 Alarm Ekle")
        self.btn_add_alert.clicked.connect(self._show_add_alert_dialog)
        action_layout.addWidget(self.btn_add_alert)
        
        self.btn_edit_trade = QPushButton("✏️ Trade Plan Düzenle")
        self.btn_edit_trade.clicked.connect(self._show_edit_trade_dialog)
        action_layout.addWidget(self.btn_edit_trade)
        
        self.btn_view_chart = QPushButton("📈 Grafik Göster")
        self.btn_view_chart.clicked.connect(self._view_chart)
        action_layout.addWidget(self.btn_view_chart)
        
        action_layout.addStretch()
        action_group.setLayout(action_layout)
        content_layout.addWidget(action_group)
        
        content.setLayout(content_layout)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        widget.setLayout(layout)
        return widget
    
    def _create_alerts_tab(self) -> QWidget:
        """Alarmlar sekmesi"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("🔔 Aktif Alarmlar"))
        header_layout.addStretch()
        
        add_alert_btn = QPushButton("➕ Yeni Alarm")
        add_alert_btn.clicked.connect(self._show_add_alert_dialog)
        header_layout.addWidget(add_alert_btn)
        
        layout.addLayout(header_layout)
        
        # Alerts table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(7)
        self.alerts_table.setHorizontalHeaderLabels([
            "Sembol", "Borsa", "Tip", "Koşul", "Değer", "Oluşturma", "İşlem"
        ])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.alerts_table)
        
        widget.setLayout(layout)
        return widget
    
    def _create_archive_tab(self) -> QWidget:
        """Arşiv sekmesi"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("📦 Arşivlenmiş Kayıtlar"))
        header_layout.addStretch()
        
        # Days filter
        header_layout.addWidget(QLabel("Son:"))
        self.archive_days = QComboBox()
        self.archive_days.addItems(["7 gün", "30 gün", "90 gün", "Tümü"])
        self.archive_days.currentTextChanged.connect(self._load_archive)
        header_layout.addWidget(self.archive_days)
        
        layout.addLayout(header_layout)
        
        # Archive table
        self.archive_table = QTableWidget()
        self.archive_table.setColumnCount(7)
        self.archive_table.setHorizontalHeaderLabels([
            "Sembol", "Borsa", "Eklenme", "Arşivlenme", "Neden", "Gün", "Son Fiyat"
        ])
        self.archive_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.archive_table)
        
        widget.setLayout(layout)
        return widget
    
    # =========================================================================
    # DATA LOADING
    # =========================================================================
    
    def _load_watchlist(self):
        """Watchlist'i yükle ve tabloya doldur"""
        try:
            # Filter
            status_filter = None
            filter_text = self.status_filter.currentText() if hasattr(self, 'status_filter') else "Tümü"
            
            if "Aktif" in filter_text:
                status_filter = "ACTIVE"
            elif "Bekle" in filter_text:
                status_filter = "WAIT"
            elif "Alarm" in filter_text:
                status_filter = "ALARM"
            elif "Pasif" in filter_text:
                status_filter = "PASSIVE"
            
            watchlist = self.manager.get_active_watchlist(status_filter)
            
            self.table.setRowCount(len(watchlist))
            
            for row, entry in enumerate(watchlist):
                self._populate_row(row, entry)
            
            logger.info(f"✅ Watchlist loaded: {len(watchlist)} items")
            
            # Load alerts too
            self._load_alerts()
            
        except Exception as e:
            logger.error(f"❌ Error loading watchlist: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Watchlist yüklenemedi:\n{e}")
    
    def _populate_row(self, row: int, entry: Dict):
        """Tek satırı doldur"""
        symbol = entry['symbol']
        exchange = entry['exchange']
        
        # Snapshot data
        latest = entry.get('latest_snapshot', {}) or {}
        first = entry.get('first_snapshot', {}) or {}
        
        # Değerleri al
        current_price = latest.get('price') or latest.get('close', 0)
        # Entry price için fallback zinciri - 0 olmasını önle
        entry_price = first.get('entry_price') or latest.get('entry_price') or current_price
        stop_loss = latest.get('stop_loss') or first.get('stop_loss')
        target1 = latest.get('target1') or first.get('target1')
        target2 = latest.get('target2') or first.get('target2')
        
        # Hesaplamalar - sıfır bölme ve -100% hatasını önle
        price_change_pct = 0
        if entry_price > 0 and current_price > 0:
            price_change_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            price_change_pct = 0  # Veri yoksa 0 göster, -100% değil
        
        distance_to_stop = latest.get('distance_to_stop_pct', 0) or 0
        distance_to_t1 = latest.get('distance_to_target1_pct', 0) or 0
        
        # Row background color
        row_color = None
        days = entry.get('days_in_list', 0)
        
        if days <= 1:
            row_color = WatchlistColors.NEW_ENTRY
        elif days > 14:
            row_color = WatchlistColors.EXPIRED
        elif distance_to_stop is not None and 0 < distance_to_stop < 5:
            row_color = WatchlistColors.STOP_NEAR
        elif distance_to_t1 is not None and 0 < distance_to_t1 < 5:
            row_color = WatchlistColors.TARGET_NEAR
        
        col = 0
        
        # Kimlik - Sektör, Endeks, Likidite kaldırıldı çünkü boş geliyordu
        self._set_cell(row, col, symbol); col += 1
        self._set_cell(row, col, exchange); col += 1
        
        # Trend
        main_trend = latest.get('main_trend', '-')
        trend_item = self._set_cell(row, col, format_trend_turkish(main_trend) or '-')
        if main_trend == "UP":
            trend_item.setForeground(WatchlistColors.TREND_UP)
        elif main_trend == "DOWN":
            trend_item.setForeground(WatchlistColors.TREND_DOWN)
        col += 1
        
        self._set_cell(row, col, format_strength_turkish(latest.get('trend_strength', '-')) or '-'); col += 1
        self._set_cell(row, col, translate(latest.get('setup_type', '-')) or '-'); col += 1
        
        # Teknik
        # Teknik
        trend_score = latest.get('trend_score')
        score_item = self._set_cell(row, col, f"{trend_score:.0f}" if trend_score else "-")
        if trend_score:
            if trend_score >= 70:
                score_item.setForeground(WatchlistColors.POSITIVE)
            elif trend_score < 50:
                score_item.setForeground(WatchlistColors.NEGATIVE)
        col += 1
        
        # Risk Score (V3.0)
        risk_score = entry.get('risk_score') or latest.get('risk_score')
        risk_item = self._set_cell(row, col, f"{risk_score:.0f}" if risk_score is not None else "-")
        if risk_score is not None:
            if risk_score < 30:
                risk_item.setForeground(WatchlistColors.POSITIVE)  # Low Risk (Green)
            elif risk_score > 70:
                risk_item.setForeground(WatchlistColors.NEGATIVE)  # High Risk (Red)
            elif risk_score > 50:
                risk_item.setForeground(WatchlistColors.WARNING)   # Medium Risk (Orange)
        col += 1
        
        rsi = latest.get('rsi')
        rsi_item = self._set_cell(row, col, f"{rsi:.1f}" if rsi else "-")
        if rsi:
            if rsi > 70:
                rsi_item.setForeground(WatchlistColors.NEGATIVE)
            elif rsi < 30:
                rsi_item.setForeground(WatchlistColors.POSITIVE)
        col += 1
        
        adx = latest.get('adx')
        self._set_cell(row, col, f"{adx:.1f}" if adx else "-"); col += 1
        
        rvol = latest.get('rvol') or latest.get('volume_ratio')
        rvol_item = self._set_cell(row, col, f"{rvol:.1f}x" if rvol else "-")
        if rvol and rvol >= 2.0:
            rvol_item.setForeground(WatchlistColors.POSITIVE)
        col += 1
        
        # Trade Plan
        self._set_cell(row, col, f"{entry_price:.2f}" if entry_price else "-"); col += 1
        self._set_cell(row, col, f"{stop_loss:.2f}" if stop_loss else "-"); col += 1
        self._set_cell(row, col, f"{target1:.2f}" if target1 else "-"); col += 1
        self._set_cell(row, col, f"{target2:.2f}" if target2 else "-"); col += 1
        
        rr = latest.get('rr_ratio')
        rr_item = self._set_cell(row, col, f"1:{rr:.1f}" if rr else "-")
        if rr:
            if rr >= 2.0:
                rr_item.setForeground(WatchlistColors.POSITIVE)
            elif rr < 1.5:
                rr_item.setForeground(WatchlistColors.NEGATIVE)
        col += 1
        
        # Durum
        self._set_cell(row, col, f"{current_price:.2f}" if current_price else "-"); col += 1
        
        price_item = self._set_cell(row, col, f"{price_change_pct:+.2f}%")
        if price_change_pct > 0:
            price_item.setForeground(WatchlistColors.POSITIVE)
        elif price_change_pct < 0:
            price_item.setForeground(WatchlistColors.NEGATIVE)
        col += 1
        
        sl_item = self._set_cell(row, col, f"{distance_to_stop:.1f}%" if distance_to_stop else "-")
        if distance_to_stop and distance_to_stop < 5:
            sl_item.setBackground(WatchlistColors.STOP_NEAR)
        col += 1
        
        t1_item = self._set_cell(row, col, f"{distance_to_t1:.1f}%" if distance_to_t1 else "-")
        if distance_to_t1 and distance_to_t1 < 5:
            t1_item.setBackground(WatchlistColors.TARGET_NEAR)
        col += 1
        
        # Timing
        self._set_cell(row, col, translate(entry.get('setup_status', '-')) or '-'); col += 1
        self._set_cell(row, col, str(days)); col += 1
        
        # Status - ⚠️ ve İşlemler sütunları kaldırıldı
        status_emoji = entry.get('status_emoji', '⚪')
        self._set_cell(row, col, status_emoji); col += 1
        
        # Apply row background
        if row_color:
            for c in range(self.table.columnCount() - 1):
                item = self.table.item(row, c)
                if item:
                    item.setBackground(row_color)
    
    def _set_cell(self, row: int, col: int, text: str) -> QTableWidgetItem:
        """Hücre oluştur ve yerleştir"""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, col, item)
        return item
    
    def _load_alerts(self):
        """Alarmları yükle"""
        try:
            alerts = self.manager.get_active_alerts()
            
            self.alerts_table.setRowCount(len(alerts))
            
            for row, alert in enumerate(alerts):
                self.alerts_table.setItem(row, 0, QTableWidgetItem(alert['symbol']))
                self.alerts_table.setItem(row, 1, QTableWidgetItem(alert['exchange']))
                self.alerts_table.setItem(row, 2, QTableWidgetItem(alert['alert_type']))
                self.alerts_table.setItem(row, 3, QTableWidgetItem(alert['condition']))
                self.alerts_table.setItem(row, 4, QTableWidgetItem(str(alert['trigger_value'])))
                self.alerts_table.setItem(row, 5, QTableWidgetItem(
                    alert['created_date'].strftime('%Y-%m-%d') if alert['created_date'] else '-'
                ))
                
                # Delete button
                del_btn = QPushButton("🗑️")
                del_btn.clicked.connect(lambda checked, aid=alert['id']: self._delete_alert(aid))
                self.alerts_table.setCellWidget(row, 6, del_btn)
                
        except Exception as e:
            logger.error(f"Error loading alerts: {e}")
    
    def _load_archive(self):
        """Arşivi yükle"""
        try:
            days_text = self.archive_days.currentText()
            days = 0
            if "7" in days_text:
                days = 7
            elif "30" in days_text:
                days = 30
            elif "90" in days_text:
                days = 90
            
            archived = self.manager.get_archived_entries(days)
            
            self.archive_table.setRowCount(len(archived))
            
            for row, entry in enumerate(archived):
                self.archive_table.setItem(row, 0, QTableWidgetItem(entry['symbol']))
                self.archive_table.setItem(row, 1, QTableWidgetItem(entry['exchange']))
                self.archive_table.setItem(row, 2, QTableWidgetItem(
                    entry['added_date'].strftime('%Y-%m-%d') if entry['added_date'] else '-'
                ))
                self.archive_table.setItem(row, 3, QTableWidgetItem(
                    entry['archived_date'].strftime('%Y-%m-%d') if entry['archived_date'] else '-'
                ))
                self.archive_table.setItem(row, 4, QTableWidgetItem(entry['archive_reason'] or '-'))
                self.archive_table.setItem(row, 5, QTableWidgetItem(str(entry['days_in_list'] or 0)))
                self.archive_table.setItem(row, 6, QTableWidgetItem(
                    f"{entry['final_price']:.2f}" if entry['final_price'] else '-'
                ))
                
        except Exception as e:
            logger.error(f"Error loading archive: {e}")
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _on_filter_changed(self, text: str):
        """Filtre değişti"""
        self._load_watchlist()
    
    def _on_row_selected(self):
        """Satır seçildi - detayları göster"""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        symbol = self.table.item(row, 0).text()
        exchange = self.table.item(row, 1).text()
        
        # Detayları yükle
        try:
            entry_data = self.manager.get_entry_with_all_snapshots(symbol, exchange)
            
            if entry_data and entry_data.get('snapshots'):
                latest = entry_data['snapshots'][-1]
                first = entry_data['snapshots'][0]
                
                self.details_title.setText(f"📊 {symbol} ({exchange}) Detayları")
                
                # Left column
                self.detail_labels['price'].setText(f"{latest.get('price', 0):.2f}")
                self.detail_labels['entry'].setText(f"{first.get('entry_price') or latest.get('entry_price') or '-'}")
                self.detail_labels['stop'].setText(f"{latest.get('stop_loss') or '-'}")
                self.detail_labels['target1'].setText(f"{latest.get('target1') or '-'}")
                self.detail_labels['target2'].setText(f"{latest.get('target2') or '-'}")
                self.detail_labels['target3'].setText(f"{latest.get('target3') or '-'}")
                
                rr = latest.get('rr_ratio')
                self.detail_labels['rr_ratio'].setText(f"1:{rr:.2f}" if rr else "-")
                
                self.detail_labels['rsi'].setText(f"{latest.get('rsi') or '-'}")
                self.detail_labels['adx'].setText(f"{latest.get('adx') or '-'}")
                self.detail_labels['macd'].setText(f"{latest.get('macd') or '-'}")
                self.detail_labels['trend_score'].setText(f"{latest.get('trend_score') or '-'}")
                
                # Right column
                self.detail_labels['main_trend'].setText(str(latest.get('main_trend') or '-'))
                self.detail_labels['setup_type'].setText(str(latest.get('setup_type') or '-'))
                self.detail_labels['tv_signal'].setText(str(latest.get('tv_signal') or '-'))
                self.detail_labels['ml_quality'].setText(str(latest.get('ml_quality') or '-'))
                self.detail_labels['squeeze'].setText(str(latest.get('squeeze_status') or '-'))
                self.detail_labels['divergence'].setText(str(latest.get('divergence_info') or '-'))
                self.detail_labels['rs_rating'].setText(f"{latest.get('rs_rating') or '-'}")
                self.detail_labels['sharpe'].setText(f"{latest.get('sharpe_ratio') or '-'}")
                self.detail_labels['volatility'].setText(f"{latest.get('volatility_annualized') or '-'}%")
                self.detail_labels['added_date'].setText(
                    entry_data['added_date'].strftime('%Y-%m-%d') if entry_data.get('added_date') else '-'
                )
                days = (datetime.now() - entry_data['added_date']).days if entry_data.get('added_date') else 0
                self.detail_labels['days_in_list'].setText(str(days))
                
                # Signal emit
                self.symbol_selected.emit(symbol, exchange)
                
        except Exception as e:
            logger.error(f"Error loading details: {e}")
    
    def _on_row_double_clicked(self, index):
        """Çift tıklama - grafik göster"""
        self._view_chart()
    
    def _show_context_menu(self, symbol: str, exchange: str):
        """Context menu göster"""
        # Basit bir mesaj kutusu ile seçenekler
        reply = QMessageBox.question(
            self,
            f"{symbol} İşlemleri",
            f"{symbol} için ne yapmak istiyorsunuz?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Cancel
        )
        # TODO: Proper context menu implementation

    def _show_table_context_menu(self, position):
        """Tablo icin sag tik context menu"""
        item = self.table.itemAt(position)
        if not item:
            return
        
        row = item.row()
        symbol = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
        exchange = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        
        if not symbol:
            return
        
        menu = QMenu(self)
        
        action_chart = menu.addAction("Grafik Goster")
        action_analysis = menu.addAction("Risk Analizi Detayı") # V3.0
        action_detailed = menu.addAction("Detayli Analiz")
        action_refresh = menu.addAction("Guncelle")
        action_alert = menu.addAction("Alarm Ekle")
        menu.addSeparator()
        action_ready = menu.addAction("Hazir Isaretle")
        action_wait = menu.addAction("Bekle Isaretle")
        menu.addSeparator()
        action_archive = menu.addAction("Arsivle")
        action_delete = menu.addAction("Sil")
        
        action = menu.exec_(self.table.viewport().mapToGlobal(position))
        
        if action == action_chart:
            self._view_chart()
        elif action == action_analysis:
            self._show_risk_dialog(symbol, exchange)
        elif action == action_detailed:
            self._open_detailed_analysis(symbol, exchange)
        elif action == action_refresh:
            self._refresh_single_symbol(symbol, exchange)
        elif action == action_alert:
            self._show_add_alert_dialog()
        elif action == action_ready:
            self.manager.update_setup_status(symbol, exchange, "READY")
            self._load_watchlist()
        elif action == action_wait:
            self.manager.update_status_label(symbol, exchange, "WAIT")
            self._load_watchlist()
        elif action == action_archive:
            self.manager.remove_from_watchlist(symbol, exchange, "Manual archive")
            self._load_watchlist()
            self._load_archive()
        elif action == action_delete:
            reply = QMessageBox.question(self, "Silme Onayi", f"{symbol} silinsin mi?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.manager.remove_from_watchlist(symbol, exchange, "Deleted")
                self._load_watchlist()
    
    
    def _open_detailed_analysis(self, symbol, exchange):
        """Detayli analiz sekmesini ac"""
        parent_window = self.window()
        if hasattr(parent_window, 'analysis_tab'):
            parent_window.analysis_tab.symbol_input.setText(symbol)
            parent_window.analysis_tab._run_analysis()
            if hasattr(parent_window, 'tabs'):
                for i in range(parent_window.tabs.count()):
                    tab_text = parent_window.tabs.tabText(i)
                    if 'Analiz' in tab_text or 'Analysis' in tab_text:
                        parent_window.tabs.setCurrentIndex(i)
                        break
        else:
            QMessageBox.warning(self, "Uyari", "Detayli analiz sekmesi bulunamadi.")
    def _refresh_single_symbol(self, symbol, exchange):
        """Tek sembolu guncelle"""
        if not self.scanner or not hasattr(self.scanner, 'symbol_analyzer'):
            QMessageBox.warning(self, "Uyari", "Scanner bagli degil.")
            return
        
        try:
            result = self.scanner.symbol_analyzer.analyze_symbol(symbol, skip_filters=True)
            if result:
                scan_result = self._convert_result_to_snapshot(result)
                if self.manager.create_snapshot(symbol, exchange, scan_result):
                    self._load_watchlist()
                    QMessageBox.information(self, "Basarili", f"{symbol} guncellendi.")
                else:
                    QMessageBox.warning(self, "Hata", f"{symbol} guncellenemedi.")
            else:
                QMessageBox.warning(self, "Hata", f"{symbol} icin analiz sonucu alinamadi.")
        except Exception as e:
            logger.error(f"Error refreshing {symbol}: {e}")
            QMessageBox.critical(self, "Hata", f"Guncelleme hatasi: {e}")
    
    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def _refresh_all(self):
        """Tüm sembolleri asenkron güncelle - UI donmaz"""
        try:
            if self._is_refreshing:
                QMessageBox.warning(self, "Uyarı", "Güncelleme zaten devam ediyor.")
                return
            
            if not self.scanner:
                QMessageBox.warning(self, "Uyarı", "Scanner bağlı değil.")
                return
            
            watchlist = self.manager.get_active_watchlist()
            if not watchlist:
                QMessageBox.information(self, "Bilgi", "Watchlist boş.")
                return
            
            # Prepare symbols list
            symbols = [{'symbol': e['symbol'], 'exchange': e['exchange']} for e in watchlist]
            
            # Create and setup worker
            self._update_worker = WatchlistUpdateWorker(self)
            self._update_worker.setup(symbols, self.scanner, self.manager)
            
            # Connect signals
            self._update_worker.progress_updated.connect(self._on_refresh_progress)
            self._update_worker.symbol_updated.connect(self._on_symbol_refreshed)
            self._update_worker.all_finished.connect(self._on_refresh_finished)
            self._update_worker.error_occurred.connect(self._on_refresh_error)
            
            # Update UI state
            self._is_refreshing = True
            self.refresh_btn.setEnabled(False)
            self.cancel_btn.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_label.setText(f"0/{len(symbols)} başlatılıyor...")
            
            # Start worker
            self._update_worker.start()
            logger.info(f"🔄 Async güncelleme başladı: {len(symbols)} sembol")
            
        except Exception as e:
            logger.error(f"Error starting refresh: {e}")
            self._reset_refresh_ui()
            QMessageBox.critical(self, "Hata", f"Güncelleme başarısız: {e}")
    
    def _cancel_refresh(self):
        """Devam eden güncellemeyi iptal et"""
        if self._update_worker and self._is_refreshing:
            self._update_worker.cancel()
            self.progress_label.setText("⏹️ İptal ediliyor...")
    
    def _on_refresh_progress(self, current: int, total: int, symbol: str):
        """Güncelleme ilerleme callback'i"""
        self.progress_label.setText(f"{current}/{total} - {symbol}")
    
    def _on_symbol_refreshed(self, symbol: str, exchange: str, data: dict):
        """Tek sembol güncellendi callback'i - tabloyu anlık güncelle"""
        # Find the row for this symbol and update it
        for row in range(self.table.rowCount()):
            if (self.table.item(row, 0) and self.table.item(row, 0).text() == symbol and
                self.table.item(row, 1) and self.table.item(row, 1).text() == exchange):
                # Update just the price column for now (quick visual feedback)
                price = data.get('current_price', 0)
                if price > 0:
                    price_item = self.table.item(row, 14)  # Fiyat column
                    if price_item:
                        price_item.setText(f"{price:.2f}")
                break
    
    def _on_refresh_error(self, symbol: str, error_msg: str):
        """Güncelleme hatası callback'i"""
        logger.warning(f"⚠️ {symbol} güncelleme hatası: {error_msg}")
    
    def _on_refresh_finished(self, success_count: int, fail_count: int):
        """Tüm güncelleme tamamlandı callback'i"""
        self._reset_refresh_ui()
        
        # Reload full watchlist to get all updated data
        self._load_watchlist()
        
        QMessageBox.information(
            self,
            "Güncelleme Tamamlandı",
            f"✅ Güncellenen: {success_count}\n❌ Başarısız: {fail_count}"
        )
        
        logger.info(f"✅ Async güncelleme tamamlandı: {success_count} başarılı, {fail_count} başarısız")
    
    def _reset_refresh_ui(self):
        """Güncelleme UI'ını sıfırla"""
        self._is_refreshing = False
        self.refresh_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.progress_label.setVisible(False)
        self.progress_label.setText("")
        
        # Clean up worker
        if self._update_worker:
            self._update_worker.deleteLater()
            self._update_worker = None

    
    def _convert_result_to_snapshot(self, result: dict) -> dict:
        """Analiz sonucunu snapshot formatına çevir"""
        return {
            'current_price': result.get('current_price', 0),
            'entry': result.get('entry'),
            'stop': result.get('stop'),
            'target1': result.get('target1'),
            'target2': result.get('target2'),
            'target3': result.get('target3'),
            'rsi': result.get('rsi'),
            'macd': result.get('macd'),
            'adx': result.get('adx'),
            'trend_score': result.get('trend_score'),
            'volume_ratio': result.get('volume_ratio'),
            'rvol': result.get('rvol') or result.get('volume_ratio'),
            'sharpe': result.get('sharpe'),
            'swing_efficiency': result.get('swing_efficiency'),
            'volatility_status': result.get('volatility_status'),
            'market_regime': result.get('market_regime'),
            'signal_type': result.get('signal_type', 'REFRESH'),
            'confidence': result.get('confidence', 0.5),
            'confirmations': result.get('confirmations', 0),
            'main_trend': result.get('main_trend'),
            'trend_strength': result.get('trend_strength'),
            'setup_type': result.get('setup_type'),
            'rs_data': result.get('rs_data'),
            'squeeze_data': result.get('squeeze_data'),
            'tv_signal_details': result.get('tv_signal_details'),
            'ml_prediction': result.get('ml_prediction'),
            'confirmation_data': result.get('confirmation_data'),
            'entry_recommendation': result.get('entry_recommendation'),
        }
    
    def _auto_cleanup(self):
        """Otomatik temizleme kurallarını uygula"""
        reply = QMessageBox.question(
            self,
            'Otomatik Temizlik',
            'Şu kurallar uygulanacak:\n\n'
            '• Trend bozulan hisseler\n'
            '• Stop seviyesi çalışan hisseler\n'
            '• 14 günden fazla bekleyen setup\'lar\n\n'
            'Devam edilsin mi?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            result = self.manager.auto_cleanup()
            
            self._load_watchlist()
            self._load_archive()
            
            reasons_text = "\n".join([f"• {k}: {v}" for k, v in result['reasons'].items()])
            
            QMessageBox.information(
                self,
                "Temizlik Tamamlandı",
                f"✅ Arşivlenen: {result['cleaned']}\n\nNedenler:\n{reasons_text or 'Yok'}"
            )
            
        except Exception as e:
            logger.error(f"Error in auto_cleanup: {e}")
            QMessageBox.critical(self, "Hata", f"Temizlik başarısız: {e}")
    
    def _bulk_delete(self):
        """Seçili sembolleri sil"""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Silmek için en az bir sembol seçin.")
            return
        
        symbols = []
        for idx in selected_rows:
            row = idx.row()
            symbol = self.table.item(row, 0).text()
            exchange = self.table.item(row, 1).text()
            symbols.append((symbol, exchange))
        
        reply = QMessageBox.question(
            self,
            'Toplu Silme',
            f'{len(symbols)} sembol silinecek:\n\n' +
            '\n'.join([f"• {s[0]} ({s[1]})" for s in symbols[:5]]) +
            (f'\n... ve {len(symbols) - 5} diğer' if len(symbols) > 5 else ''),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        deleted = 0
        for symbol, exchange in symbols:
            if self.manager.remove_from_watchlist(symbol, exchange, "Manual bulk delete"):
                deleted += 1
        
        self._load_watchlist()
        self._load_archive()
        
        QMessageBox.information(
            self,
            "Silme Tamamlandı",
            f"✅ Silinen: {deleted}"
        )
    
    def _show_statistics(self):
        """İstatistikleri göster"""
        try:
            stats = self.analyzer.calculate_win_rate()
            best = self.analyzer.get_best_performers(days=30, top_n=3)
            worst = self.analyzer.get_worst_performers(days=30, top_n=3)
            
            text = f"""
📊 Genel İstatistikler:

Toplam: {stats['total_items']}
Kazanan: {stats['winners']}
Kaybeden: {stats['losers']}

Win Rate: {stats['win_rate']:.1f}%
Hedef 1: {stats['target1_hit_rate']:.1f}%
Hedef 2: {stats['target2_hit_rate']:.1f}%
Stop: {stats['stop_hit_rate']:.1f}%

📈 En İyi (30 gün):
"""
            for i, p in enumerate(best, 1):
                text += f"\n{i}. {p['symbol']}: {p['price_change_pct']:+.2f}%"
            
            text += "\n\n📉 En Kötü (30 gün):"
            for i, p in enumerate(worst, 1):
                text += f"\n{i}. {p['symbol']}: {p['price_change_pct']:+.2f}%"
            
            QMessageBox.information(self, "📊 İstatistikler", text)
            
        except Exception as e:
            logger.error(f"Error showing statistics: {e}")
            QMessageBox.critical(self, "Hata", f"İstatistikler yüklenemedi: {e}")
    
    def _set_setup_status(self, status: str):
        """Setup durumunu değiştir"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        symbol = self.table.item(row, 0).text()
        exchange = self.table.item(row, 1).text()
        
        self.manager.update_setup_status(symbol, exchange, status)
        self._load_watchlist()
    
    def _update_status(self, status: str):
        """Durum etiketini değiştir"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        symbol = self.table.item(row, 0).text()
        exchange = self.table.item(row, 1).text()
        
        self.manager.update_status_label(symbol, exchange, status)
        self._load_watchlist()
    
    def _show_add_alert_dialog(self):
        """Alarm ekleme dialogu"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Önce bir sembol seçin.")
            return
        
        row = selected_rows[0].row()
        symbol = self.table.item(row, 0).text()
        exchange = self.table.item(row, 1).text()
        
        # Simple dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"🔔 {symbol} için Alarm Ekle")
        dialog.setMinimumWidth(300)
        
        layout = QFormLayout()
        
        type_combo = QComboBox()
        type_combo.addItems([
            "PRICE_ABOVE", "PRICE_BELOW",
            "VOLUME_SPIKE", "RSI_OVERSOLD", "RSI_OVERBOUGHT",
            "STOP_PROXIMITY", "TARGET_PROXIMITY"
        ])
        layout.addRow("Tip:", type_combo)
        
        value_spin = QSpinBox()
        value_spin.setRange(0, 100000)
        value_spin.setValue(100)
        layout.addRow("Değer:", value_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            alert_type = type_combo.currentText()
            value = value_spin.value()
            
            success = self.manager.create_alert(
                symbol, exchange, alert_type, float(value)
            )
            
            if success:
                QMessageBox.information(self, "Başarılı", "Alarm oluşturuldu!")
                self._load_alerts()
                self._load_watchlist()
            else:
                QMessageBox.warning(self, "Hata", "Alarm oluşturulamadı.")
    
    def _show_edit_trade_dialog(self):
        """Trade plan düzenleme dialogu"""
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Uyarı", "Lütfen düzenlemek için bir sembol seçin")
            return
        row = selected[0].row()
        symbol = self.table.item(row, 0).text()
        
        # Basit bir bilgi mesajı - tam implementasyon için dialog eklenebilir
        QMessageBox.information(
            self, 
            "Trade Plan Düzenleme", 
            f"{symbol} için trade plan düzenleme özelliği yakında eklenecek.\n\n"
            "Şu anda manuel olarak giriş, stop ve hedef değerlerini\n"
            "veritabanında güncelleyebilirsiniz."
        )
    
    def _view_chart(self):
        """Grafik göster - Düzeltilmiş implementasyon"""
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Uyarı", "Lütfen grafik için bir sembol seçin")
            return
        row = selected[0].row()
        symbol = self.table.item(row, 0).text()
        exchange = self.table.item(row, 1).text()
        
        # MainWindow'a chart tab'ı bul ve göster
        parent_window = self.window()
        if hasattr(parent_window, 'chart_tab'):
            parent_window.chart_tab.show_chart(symbol, exchange)
            # Chart sekmesine geç
            if hasattr(parent_window, 'tabs'):
                for i in range(parent_window.tabs.count()):
                    tab_text = parent_window.tabs.tabText(i)
                    if 'Grafik' in tab_text or 'Chart' in tab_text:
                        parent_window.tabs.setCurrentIndex(i)
                        break
        else:
            # Fallback: signal emit et
            self.symbol_selected.emit(symbol, exchange)
            QMessageBox.information(self, "Bilgi", f"{symbol} grafiği yükleniyor...")
    
    def _delete_alert(self, alert_id: int):
        """Alarmı sil"""
        if self.manager.delete_alert(alert_id):
            self._load_alerts()

    def _show_risk_dialog(self, symbol: str, exchange: str):
        """
        Risk analizi detay pencresini göster (V3.0)
        """
        try:
            # Verileri hesapla/getir
            QMessageBox.information(self, "Analiz", f"{symbol} için risk analizi hesaplanıyor, lütfen bekleyin...")
            
            # Bu işlem biraz sürebilir, thread içinde yapılabilir ama
            # şimdilik basit tutuyoruz (bloklayan çağrı)
            risk_data = self.manager.get_risk_analysis(symbol, exchange)
            
            if not risk_data:
                QMessageBox.warning(self, "Uyarı", f"{symbol} için risk verisi hesaplanamadı (yetersiz veri).")
                return
            
            # Dialog'u aç
            dialog = RiskAnalysisDialog(symbol, risk_data, self)
            dialog.exec_()
            
        except Exception as e:
            logger.error(f"Error showing risk dialog: {e}")
            QMessageBox.critical(self, "Hata", f"Risk analizi açılamadı:\n{e}")

    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def add_from_scan_result(self, symbol: str, exchange: str, scan_result: Dict):
        """Tarama sonucundan watchlist'e ekle"""
        try:
            # Extract identity_info from scan_result
            identity_info = {
                'sector': scan_result.get('sector'),
                'index_membership': scan_result.get('index_membership'),
                'liquidity_score': scan_result.get('liquidity_score'),
            }
            
            # Remove identity fields from scan_result to avoid duplication
            scan_result_clean = {k: v for k, v in scan_result.items() 
                                if k not in ['sector', 'index_membership', 'liquidity_score']}
            
            success = self.manager.add_to_watchlist(
                symbol, 
                exchange, 
                scan_result_clean,
                identity_info=identity_info
            )
            
            if success:
                logger.info(f"✅ {symbol} added to watchlist")
                self._load_watchlist()
                return True
            else:
                logger.warning(f"⚠️ {symbol} already in watchlist")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error adding {symbol} to watchlist: {e}")
            return False

