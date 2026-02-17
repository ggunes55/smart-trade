"""
GUI Chart Widget - MODULAR EDITION + SWING PATTERNS
Gelişmiş swing trade pattern'leri entegre edildi
"""

try:
    import pyqtgraph as pg

    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    print("⚠️ PyQtGraph kurulu değil. Grafik gösterilemeyecek!")

import json
import numpy as np
import pandas as pd
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QInputDialog,
    QScrollArea,
    QRadioButton,
    QButtonGroup,
    QFileDialog,
    QWidget,
    QCheckBox,
    QGroupBox,
    QTabWidget,
    QSplitter,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

# Modüler importlar
from .chart_components import (
    # Config
    THEMES,
    CURRENT_THEME,
    set_theme,
    # Core Components
    CandlestickItem,
    IndicatorCalculator,
    PatternRecognizer,
    VolumeProfile,
    FixedRangeVolumeProfile,
    PivotPointsCalculator,
    PriceAlert,
    RiskRewardTool,
    ScoreCardHUD,
    FundamentalPanel,
    # Drawing Tools
    MeasureTool,
    TrendLineTool,
    FibonacciTool,
    HorizontalLineTool,
    ChannelTool,
    RectangleTool,
    TextAnnotationTool,
    CrosshairCursor,
)

# Multi-Timeframe & Advanced Divergence
from .chart_components.multi_timeframe import (
    MultiTimeframeManager,
    MultiTimeframeAnalyzer,
)
from .chart_components.swing_divergence_analyzer import SwingDivergenceAnalyzer

# 🆕 SWING PATTERNS İMPORT
from .chart_components.swing_patterns import SwingPatternRecognizer

# PyQtGraph ayarları
if PYQTGRAPH_AVAILABLE:
    pg.setConfigOptions(antialias=True)
    pg.setConfigOption("background", "w")
    pg.setConfigOption("foreground", "k")


class IndicatorPanel(QWidget):
    """Gösterge paneli - checkbox'lar"""

    indicator_toggled = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.setMaximumWidth(580)  # Panelin maksimum genişliği

        # Fiyat Göstergeleri
        price_group = QGroupBox("💰 Fiyat Göstergeleri")
        price_layout = QVBoxLayout()

        self.indicators = {}

        price_indicators = [
            ("EMA9", "EMA 9", False),
            ("EMA20", "EMA 20", False),
            ("EMA50", "EMA 50", False),
            ("SMA200", "SMA 200", False),
            ("BB", "Bollinger Bands", False),
            ("BB_SQUEEZE", "BB Squeeze", False),
            ("VWAP", "VWAP", False),
            ("VOLUME_PROFILE", "Volume Profile", False),
            ("FIXED_VOLUME_PROFILE", "Sabit Aralık VP", False),
            ("PIVOTS", "Pivot Points", False),
        ]

        for key, label, default in price_indicators:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.stateChanged.connect(
                lambda state, k=key: self.indicator_toggled.emit(k, state == Qt.Checked)
            )
            price_layout.addWidget(cb)
            self.indicators[key] = cb

        price_group.setLayout(price_layout)
        layout.addWidget(price_group)

        # Momentum Göstergeleri
        momentum_group = QGroupBox("📊 Momentum")
        momentum_layout = QVBoxLayout()

        momentum_indicators = [
            ("RSI", "RSI", False),
            ("MACD", "MACD", False),
            ("STOCH", "Stochastic", False),
            ("ADX", "ADX", False),
        ]

        for key, label, default in momentum_indicators:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.stateChanged.connect(
                lambda state, k=key: self.indicator_toggled.emit(k, state == Qt.Checked)
            )
            momentum_layout.addWidget(cb)
            self.indicators[key] = cb

        momentum_group.setLayout(momentum_layout)
        layout.addWidget(momentum_group)

        # Sinyaller
        signals_group = QGroupBox("🎯 Sinyaller & Pattern")
        signals_layout = QVBoxLayout()

        signals_indicators = [
            ("SUPPORT", "Support", False),
            ("RESISTANCE", "Resistance", False),
            ("DIVERGENCES", "Uyumsuzluklar", False),
            ("SWING_POINTS", "Swing High/Low", False),
        ]

        for key, label, default in signals_indicators:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.stateChanged.connect(
                lambda state, k=key: self.indicator_toggled.emit(k, state == Qt.Checked)
            )
            signals_layout.addWidget(cb)
            self.indicators[key] = cb

        # Klasik Pattern'ler
        pattern_label = QLabel("<b>📊 Klasik Mum Pattern'leri:</b>")
        signals_layout.addWidget(pattern_label)

        classic_patterns = [
            ("PATTERN_HAMMER", "🔨 Hammer", False),
            ("PATTERN_SHOOTING_STAR", "⭐ Shooting Star", False),
            ("PATTERN_ENGULFING_BULLISH", "📈 Engulfing Bullish", False),
            ("PATTERN_ENGULFING_BEARISH", "📉 Engulfing Bearish", False),
            ("PATTERN_DOJI", "🎯 Doji", False),
            ("PATTERN_MORNING_STAR", "🌅 Morning Star", False),
            ("PATTERN_EVENING_STAR", "🌆 Evening Star", False),
        ]

        for key, label, default in classic_patterns:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.setStyleSheet("margin-left: 15px; font-size: 9px;")
            cb.stateChanged.connect(
                lambda state, k=key: self.indicator_toggled.emit(k, state == Qt.Checked)
            )
            signals_layout.addWidget(cb)
            self.indicators[key] = cb

        # 🆕 SWING PATTERNS
        swing_label = QLabel("<b>🚀 Swing Trade Pattern'leri:</b>")
        swing_label.setStyleSheet("color: #FF6F00; margin-top: 10px;")
        signals_layout.addWidget(swing_label)

        swing_patterns = [
            ("SWING_BULLISH_REVERSAL", "🔄 Bullish Reversal Combo", False),
            ("SWING_BEARISH_REVERSAL", "🔄 Bearish Reversal Combo", False),
            ("SWING_BULL_FLAG", "🚩 Bull Flag", False),
            ("SWING_BEAR_FLAG", "🚩 Bear Flag", False),
            ("SWING_BUYING_CLIMAX", "💥 Buying Climax", False),
            ("SWING_SELLING_CLIMAX", "💥 Selling Climax", False),
            ("SWING_KEY_REVERSAL_UP", "🔑 Key Reversal Up", False),
            ("SWING_KEY_REVERSAL_DOWN", "🔑 Key Reversal Down", False),
            ("SWING_BREAKOUT_UP", "💪 Breakout Up", False),
            ("SWING_BREAKDOWN", "📉 Breakdown", False),
        ]

        for key, label, default in swing_patterns:
            cb = QCheckBox(label)
            cb.setChecked(default)
            cb.setStyleSheet("margin-left: 15px; font-size: 9px; color: #FF6F00;")
            cb.stateChanged.connect(
                lambda state, k=key: self.indicator_toggled.emit(k, state == Qt.Checked)
            )
            signals_layout.addWidget(cb)
            self.indicators[key] = cb

        signals_group.setLayout(signals_layout)
        layout.addWidget(signals_group)

        layout.addStretch()


class SwingTradeChart(QDialog):
    """
    Ana grafik dialogu - MODULAR EDITION + SWING PATTERNS
        PDF/Excel raporlama ve plugin desteği eklendi
    """

    def __init__(
        self, df: pd.DataFrame, symbol: str, trade_info: dict = None, data_provider=None, exchange: str = "BIST"
    ):
        super().__init__()

        if not PYQTGRAPH_AVAILABLE:
            QMessageBox.critical(self, "Hata", "PyQtGraph kurulu değil!")
            self.reject()
            return

        self.symbol = symbol
        self.exchange = exchange
        self.plugins = []
        self.trade_info = trade_info or {}
        self.data_provider = data_provider
        self.current_timeframe = "1d"
        self.df = df.copy().reset_index(drop=True)

        # Multi-timeframe manager
        self.mtf_manager = MultiTimeframeManager
        self.mtf_analyzer = MultiTimeframeAnalyzer

        if "date" not in self.df.columns:
            self.df["date"] = pd.date_range(
                end=datetime.now(), periods=len(self.df), freq="D"
            )

        # Validasyon ve hesaplama
        progress = QProgressDialog("Göstergeler hesaplanıyor...", None, 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(20)

        try:
            IndicatorCalculator.validate_df(self.df)
        except ValueError as e:
            QMessageBox.critical(self, "Veri Hatası", str(e))
            progress.close()
            self.reject()
            return

        self.df = IndicatorCalculator.calculate(self.df)
        progress.setValue(40)

        self.signals = IndicatorCalculator.detect_signals(self.df)
        progress.setValue(50)

        # Klasik pattern'ler
        self.patterns = PatternRecognizer.detect_patterns(self.df)
        progress.setValue(60)

        # 🆕 SWING PATTERNS DETECT
        self.swing_patterns = SwingPatternRecognizer.detect_all_swing_patterns(self.df)
        progress.setValue(65)

        # COMPLETE Swing Divergence analizi
        swing_analysis = SwingDivergenceAnalyzer.analyze_complete(
            self.df, mtf_data=None, min_quality=50
        )
        self.divergences = swing_analysis["divergences"]
        self.swing_structure = swing_analysis["swing_structure"]
        self.high_prob_setups = swing_analysis.get("high_probability_setups", [])

        self.divergence_summary = {
            "total_count": sum(
                len(divs)
                for types in self.divergences.values()
                for divs in types.values()
            ),
            "by_indicator": {
                ind: sum(len(divs) for divs in types.values())
                for ind, types in self.divergences.items()
            },
            "strong_signals": self.high_prob_setups[:5],
        }
        progress.setValue(80)

        self.volume_profile_data = VolumeProfile.calculate(self.df)
        progress.setValue(90)

        self.price_alerts = PriceAlert()

        self._build_ui()
        self._build_plots()

        progress.setValue(100)
        progress.close()

    def _build_ui(self):
        """UI oluştur"""
        self.setWindowTitle(f"🚀 {self.symbol} - Swing Trade Chart")
        self.resize(2200, 1200)

        # QSplitter kullanarak sol paneli sürüklenebilir yap
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Sol Panel
        left_panel_scroll = QScrollArea()
        left_panel_scroll.setWidgetResizable(True)
        left_panel_scroll.setMinimumWidth(280)
        left_panel_scroll.setMaximumWidth(600)  # Maksimum genişlik
        left_panel_scroll.setStyleSheet("QScrollArea { border: none; }")

        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)

        # Temel Analiz (exchange-aware)
        self.fundamental_panel = FundamentalPanel(self.symbol, self.exchange, self)
        left_panel_layout.addWidget(self.fundamental_panel)

        # Gösterge Paneli
        self.indicator_panel = IndicatorPanel()
        self.indicator_panel.indicator_toggled.connect(self.toggle_indicator)
        left_panel_layout.addWidget(self.indicator_panel)

        left_panel_scroll.setWidget(left_panel_widget)
        splitter.addWidget(left_panel_scroll)

        # Sağ Panel
        right_panel_widget = QWidget()
        right_panel_widget.setMinimumWidth(900)
        right_layout = QVBoxLayout(right_panel_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Zaman Dilimi Seçici
        timeframe_layout = QHBoxLayout()
        timeframe_label = QLabel("⏰ Zaman Dilimi:")
        timeframe_label.setStyleSheet("font-weight: bold;")
        timeframe_layout.addWidget(timeframe_label)

        self.timeframe_group = QButtonGroup()

        available_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]

        for tf in available_timeframes:
            btn = QRadioButton(tf.upper())
            btn.setChecked(tf == "1d")
            btn.toggled.connect(
                lambda checked, t=tf: self.change_timeframe(t) if checked else None
            )
            self.timeframe_group.addButton(btn)
            timeframe_layout.addWidget(btn)

        # Analiz butonları
        self.btn_mtf_analysis = QPushButton("📊 MTF Analiz")
        self.btn_mtf_analysis.setToolTip("Çoklu zaman dilimi trend analizi")
        self.btn_mtf_analysis.clicked.connect(self.show_mtf_analysis)
        timeframe_layout.addWidget(self.btn_mtf_analysis)

        self.btn_div_analysis = QPushButton("⚠️ Divergence")
        self.btn_div_analysis.setToolTip("Gelişmiş uyumsuzluk analizi")
        self.btn_div_analysis.clicked.connect(self.show_divergence_analysis)
        timeframe_layout.addWidget(self.btn_div_analysis)

        # 🆕 SWING PATTERN ANALIZ BUTONU
        self.btn_swing_analysis = QPushButton("🚀 Swing Patterns")
        self.btn_swing_analysis.setToolTip("Gelişmiş swing trade pattern analizi")
        self.btn_swing_analysis.clicked.connect(self.show_swing_pattern_analysis)
        timeframe_layout.addWidget(self.btn_swing_analysis)

        timeframe_layout.addStretch()
        right_layout.addLayout(timeframe_layout)

        # Üst Kontroller
        controls = QHBoxLayout()

        # Çizim araçları
        self.btn_measure = QPushButton("📏 Ölçüm")
        self.btn_rr_long = QPushButton("💰 R/R Long")
        self.btn_rr_short = QPushButton("💸 R/R Short")
        self.btn_trend = QPushButton("📈 Trend")
        self.btn_fib_ret = QPushButton("📊 Fib-R")
        self.btn_fib_ext = QPushButton("📊 Fib-E")
        self.btn_fib_auto = QPushButton("🔢 Fib-A")
        self.btn_hline = QPushButton("─ Yatay")
        self.btn_channel = QPushButton("📉 Kanal")
        self.btn_rect = QPushButton("▭ Kutu")
        self.btn_text = QPushButton("📝 Not")
        self.btn_clear_draw = QPushButton("🗑️ Temizle")

        # Event'ler
        self.btn_measure.clicked.connect(lambda: self.handle_drawing_tool("measure"))
        self.btn_rr_long.clicked.connect(lambda: self.handle_drawing_tool("rr_long"))
        self.btn_rr_short.clicked.connect(lambda: self.handle_drawing_tool("rr_short"))
        self.btn_trend.clicked.connect(lambda: self.handle_drawing_tool("trendline"))
        self.btn_fib_ret.clicked.connect(
            lambda: self.handle_drawing_tool("fib_retracement")
        )
        self.btn_fib_ext.clicked.connect(
            lambda: self.handle_drawing_tool("fib_extension")
        )
        self.btn_fib_auto.clicked.connect(lambda: self.handle_drawing_tool("fib_auto"))
        self.btn_hline.clicked.connect(lambda: self.handle_drawing_tool("hline"))
        self.btn_channel.clicked.connect(lambda: self.handle_drawing_tool("channel"))
        self.btn_rect.clicked.connect(lambda: self.handle_drawing_tool("rectangle"))
        self.btn_text.clicked.connect(lambda: self.handle_drawing_tool("text"))
        self.btn_clear_draw.clicked.connect(
            lambda: self.handle_drawing_tool("clear_all")
        )

        # Diğer butonlar
        self.btn_alert = QPushButton("🔔 Alarm")
        self.btn_theme = QPushButton("🌓 Tema")
        self.btn_fullscreen = QPushButton("⛶ Tam Ekran")
        self.btn_stats = QPushButton("📊 İstatistik")
        self.btn_ha = QPushButton("🕯️ HA")  # Heikin Ashi Button
        self.btn_ha.setCheckable(True)
        self.btn_ha.setToolTip("Heikin Ashi Mumları")
        self.btn_export = QPushButton("💾 Kaydet")
        self.btn_save_layout = QPushButton("📋 Şablon Kaydet")
        self.btn_load_layout = QPushButton("📂 Şablon Yükle")
        self.btn_save_layout.setToolTip("Açık/kapalı indikatör ayarlarını şablon olarak kaydet")
        self.btn_load_layout.setToolTip("Kaydedilmiş indikatör şablonunu yükle")
        self.btn_close = QPushButton("❌ Kapat")

        self.btn_close.clicked.connect(self.accept)
        self.btn_save_layout.clicked.connect(self.save_indicator_layout)
        self.btn_load_layout.clicked.connect(self.load_indicator_layout)
        self.btn_alert.clicked.connect(self.add_price_alert)
        self.btn_theme.clicked.connect(self.toggle_theme)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        self.btn_export.clicked.connect(self.export_chart)
        self.btn_stats.clicked.connect(self.show_statistics)
        self.btn_ha.toggled.connect(self.toggle_heikin_ashi) # Signal connection

        # Butonları ekle
        for btn in (
            self.btn_measure,
            self.btn_rr_long,
            self.btn_rr_short,
            self.btn_trend,
            self.btn_fib_ret,
            self.btn_fib_ext,
            self.btn_fib_auto,
            self.btn_hline,
            self.btn_channel,
            self.btn_rect,
            self.btn_text,
            self.btn_clear_draw,
        ):
            controls.addWidget(btn)

        controls.addSpacing(15)

        for btn in (
            self.btn_alert,
            self.btn_theme,
            self.btn_fullscreen,
            self.btn_stats,
            self.btn_ha,
            self.btn_export,
            self.btn_save_layout,
            self.btn_load_layout,
        ):
            controls.addWidget(btn)

        controls.addStretch()
        controls.addWidget(self.btn_close)

        right_layout.addLayout(controls)

        self.graph = pg.GraphicsLayoutWidget()
        right_layout.addWidget(self.graph)

        splitter.addWidget(right_panel_widget)
        
        # Splitter ayarlarını düzelt
        splitter.setHandleWidth(12)
        splitter.setOpaqueResize(True)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
            }
            QSplitter::handle:hover {
                background-color: #2196F3;
            }
        """)
        splitter.setSizes([380, 1020])
        splitter.setStretchFactor(0, 0)  # Sol panel sabit boyut
        splitter.setStretchFactor(1, 1)  # Sağ panel esnek

        # Ana pencereye splitter ekle
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Çizim araçları
        self.hline_tool = None
        self.channel_tool = None
        self.rectangle_tool = None
        self.text_tool = None
        self.rr_tool = None
        self.score_card_hud = None

    def _build_plots(self):
        """Grafikleri oluştur"""
        df = self.df
        x = np.arange(len(df))

        # === PRICE PLOT ===
        self.price_plot = self.graph.addPlot(
            title=f"🚀 {self.symbol} - {self.current_timeframe.upper()}"
        )
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setLabel("left", "Fiyat", units="₺")
        self.price_plot.setLabel("bottom", "Bar Index")

        # Mum çubukları
        ohlc = df[["open", "high", "low", "close"]].values
        
        # Varsayılan olarak BB Squeeze kapalı başlasın
        init_df = df.copy()
        if "BB_Squeeze" in init_df.columns:
            init_df["BB_Squeeze"] = False
            
        self.candles = CandlestickItem(ohlc, init_df)
        self.price_plot.addItem(self.candles)

        # EMA'lar
        from .chart_components.config import EMA_CONFIG

        self.ema_items = {}
        for name, cfg in EMA_CONFIG.items():
            line = self.price_plot.plot(
                x,
                df[name],
                pen=pg.mkPen(cfg["color"], width=cfg["width"], style=cfg["style"]),
                name=name,
            )
            line.setVisible(False)
            self.ema_items[name] = line

        # VWAP
        if "VWAP" in df.columns:
            self.vwap_line = self.price_plot.plot(
                x,
                df["VWAP"],
                pen=pg.mkPen("#FF6F00", width=3, style=Qt.SolidLine),
                name="VWAP",
            )
            self.vwap_line.setVisible(False)
        else:
            self.vwap_line = None

        # BB
        self.bb_upper = self.price_plot.plot(
            x, df["BB_Upper"], pen=pg.mkPen("#2196F3", width=1, style=Qt.DashLine)
        )
        self.bb_middle = self.price_plot.plot(
            x, df["BB_Middle"], pen=pg.mkPen("#9E9E9E", width=1)
        )
        self.bb_lower = self.price_plot.plot(
            x, df["BB_Lower"], pen=pg.mkPen("#2196F3", width=1, style=Qt.DashLine)
        )
        self.bb_fill = pg.FillBetweenItem(
            self.bb_upper, self.bb_lower, brush=pg.mkBrush(33, 150, 243, 30)
        )
        self.price_plot.addItem(self.bb_fill)

        for item in [self.bb_upper, self.bb_middle, self.bb_lower, self.bb_fill]:
            item.setVisible(False)

        # Sinyaller
        self.buy_scatter = pg.ScatterPlotItem(
            size=14, pen=pg.mkPen(None), brush=pg.mkBrush(46, 125, 50, 220), symbol="t1"
        )
        self.sell_scatter = pg.ScatterPlotItem(
            size=14, pen=pg.mkPen(None), brush=pg.mkBrush(198, 40, 40, 220), symbol="t"
        )
        self.price_plot.addItem(self.buy_scatter)
        self.price_plot.addItem(self.sell_scatter)
        self.buy_scatter.setVisible(False)
        self.sell_scatter.setVisible(False)

        # Klasik Pattern'ler
        from .chart_components.config import PATTERN_CONFIG

        self.pattern_items = {}
        for pattern_name, positions in self.patterns.items():
            if not positions:
                continue
            config = PATTERN_CONFIG[pattern_name]
            pattern_x = [p[0] for p in positions]
            pattern_y = [p[1] for p in positions]
            scatter = pg.ScatterPlotItem(
                x=pattern_x,
                y=pattern_y,
                size=config["size"],
                pen=pg.mkPen(None),
                brush=pg.mkBrush(QColor(config["color"])),
                symbol=config["symbol"],
            )
            self.price_plot.addItem(scatter)
            scatter.setVisible(False)
            self.pattern_items[pattern_name] = {"scatter": scatter}

        # 🆕 SWING PATTERNS GÖRSELLEŞTİRME
        self.swing_pattern_items = {}

        # Pattern mapping (key -> config)
        swing_pattern_map = {
            "bullish_reversal_combo": ("SWING_BULLISH_REVERSAL", "o", "#4CAF50", 18),
            "bearish_reversal_combo": ("SWING_BEARISH_REVERSAL", "o", "#F44336", 18),
            "bullish_flag": ("SWING_BULL_FLAG", "t1", "#2E7D32", 16),
            "bearish_flag": ("SWING_BEAR_FLAG", "t", "#C62828", 16),
            "buying_climax": ("SWING_BUYING_CLIMAX", "s", "#FF9800", 20),
            "selling_climax": ("SWING_SELLING_CLIMAX", "s", "#FF5722", 20),
            "key_reversal_up": ("SWING_KEY_REVERSAL_UP", "d", "#00BCD4", 16),
            "key_reversal_down": ("SWING_KEY_REVERSAL_DOWN", "d", "#E91E63", 16),
            "breakout_up": ("SWING_BREAKOUT_UP", "t1", "#8BC34A", 18),
            "breakdown": ("SWING_BREAKDOWN", "t", "#D32F2F", 18),
        }

        for pattern_key, positions in self.swing_patterns.items():
            if not positions or pattern_key not in swing_pattern_map:
                continue

            config_key, symbol, color, size = swing_pattern_map[pattern_key]

            pattern_x = [p[0] for p in positions]
            pattern_y = [p[1] for p in positions]

            scatter = pg.ScatterPlotItem(
                x=pattern_x,
                y=pattern_y,
                size=size,
                pen=pg.mkPen(color, width=2),
                brush=pg.mkBrush(QColor(color).lighter(120)),
                symbol=symbol,
            )
            self.price_plot.addItem(scatter)
            scatter.setVisible(False)  # Varsayılan gizli
            self.swing_pattern_items[config_key] = scatter

            # Pattern etiketleri ekle (opsiyonel, önemli pattern'ler için)
            if pattern_key in [
                "buying_climax",
                "selling_climax",
                "breakout_up",
                "breakdown",
            ]:
                for idx, price, strength, context in positions[:5]:  # İlk 5 tanesi
                    text = pg.TextItem(
                        text=f"{SwingPatternRecognizer.SWING_PATTERNS[pattern_key]['emoji']}\n{strength:.0f}%",
                        color=color,
                        anchor=(0.5, 1),
                    )
                    text.setPos(idx, price)
                    self.price_plot.addItem(text)
                    text.setVisible(False)

        # Support/Resistance
        self.support_lines = []
        self.resistance_lines = []
        for level in self.signals["support"]:
            line = self.price_plot.addLine(
                y=level, pen=pg.mkPen("#4CAF50", width=1.5, style=Qt.DashLine)
            )
            line.setVisible(False)
            self.support_lines.append(line)
        for level in self.signals["resistance"]:
            line = self.price_plot.addLine(
                y=level, pen=pg.mkPen("#F44336", width=1.5, style=Qt.DashLine)
            )
            line.setVisible(False)
            self.resistance_lines.append(line)

        # Divergence'ler
        self.divergence_items = {}
        for div_type in ["bullish_rsi", "bearish_rsi"]:
            if self.divergences.get(div_type):
                div_x = [d[0] for d in self.divergences[div_type]]
                div_y = [d[1] for d in self.divergences[div_type]]
                color = "#4CAF50" if "bullish" in div_type else "#F44336"
                scatter = pg.ScatterPlotItem(
                    x=div_x,
                    y=div_y,
                    size=16,
                    pen=pg.mkPen(color, width=2),
                    brush=pg.mkBrush(QColor(color).lighter(150)),
                    symbol="o",
                )
                self.price_plot.addItem(scatter)
                scatter.setVisible(False)
                self.divergence_items[div_type] = scatter

        # Volume Profile
        self.volume_profile_items = []
        vp = self.volume_profile_data
        max_vol = vp["volume_at_price"].max()
        scale_factor = (x[-1] - x[0]) * 0.15 / max_vol

        for i, vol in enumerate(vp["volume_at_price"]):
            width = vol * scale_factor
            rect = pg.BarGraphItem(
                x=[x[-1] + 5],
                height=[vp["bins"][i + 1] - vp["bins"][i]],
                width=width,
                y=[vp["bins"][i]],
                brush=pg.mkBrush(33, 150, 243, 80),
            )
            self.price_plot.addItem(rect)
            rect.setVisible(False)
            self.volume_profile_items.append(rect)

        # POC, VAH, VAL
        self.poc_line = pg.InfiniteLine(
            angle=0,
            pos=vp["poc"],
            pen=pg.mkPen("#FF9800", width=2.5, style=Qt.SolidLine),
            label=f"POC: {vp['poc']:.2f}",
            labelOpts={"position": 0.95, "color": "#FF9800"},
        )
        self.price_plot.addItem(self.poc_line)
        self.poc_line.setVisible(False)

        # VAH - Value Area High (etiketli)
        self.vah_line = pg.InfiniteLine(
            angle=0,
            pos=vp["vah"],
            pen=pg.mkPen("#4CAF50", width=2, style=Qt.DotLine),
            label=f"VAH: {vp['vah']:.2f}",
            labelOpts={
                "position": 0.95,
                "color": "#4CAF50",
                "fill": pg.mkBrush(76, 175, 80, 150),
            },
        )
        self.price_plot.addItem(self.vah_line)

        # VAL - Value Area Low (etiketli)
        self.val_line = pg.InfiniteLine(
            angle=0,
            pos=vp["val"],
            pen=pg.mkPen("#F44336", width=2, style=Qt.DotLine),
            label=f"VAL: {vp['val']:.2f}",
            labelOpts={
                "position": 0.95,
                "color": "#F44336",
                "fill": pg.mkBrush(244, 67, 54, 150),
            },
        )
        self.price_plot.addItem(self.val_line)

        for line in [self.poc_line, self.vah_line, self.val_line]:
            line.setVisible(False)

        # Canlı fiyat çizgisi (WebSocket güncellemesi ile)
        last_close = float(self.df["close"].iloc[-1]) if len(self.df) else 0
        self.live_price_line = pg.InfiniteLine(
            angle=0,
            pos=last_close,
            pen=pg.mkPen("#00BCD4", width=2, style=Qt.DashLine),
            label="Canlı",
            labelOpts={"position": 0.02, "color": "#00BCD4", "fill": pg.mkBrush(0, 188, 212, 120)},
        )
        self.price_plot.addItem(self.live_price_line)
        self._live_price = last_close

        # Fixed VP (gizli)
        self.fixed_vp_items = []
        try:
            fixed_vp_profiles = FixedRangeVolumeProfile.calculate(df, num_ranges=3)
            for idx, profile in enumerate(fixed_vp_profiles):
                vp_data = profile["vp_data"]
                start_idx = profile["start_idx"]
                end_idx = profile["end_idx"]

                max_vol = vp_data["volume_at_price"].max()
                if max_vol == 0:
                    continue

                range_width = end_idx - start_idx
                scale_factor = range_width * 0.15 / max_vol

                for i, vol in enumerate(vp_data["volume_at_price"]):
                    if vol == 0:
                        continue

                    width = vol * scale_factor
                    x_pos = end_idx - width / 2

                    rect = pg.BarGraphItem(
                        x=[x_pos],
                        height=[vp_data["bins"][i + 1] - vp_data["bins"][i]],
                        width=width,
                        y=[vp_data["bins"][i]],
                        brush=pg.mkBrush(255, 87, 34, 60),
                    )
                    self.price_plot.addItem(rect)
                    rect.setVisible(False)
                    self.fixed_vp_items.append(rect)

                # POC için bu aralık (etiketli)
                poc_line = pg.InfiniteLine(
                    angle=0,
                    pos=vp_data["poc"],
                    pen=pg.mkPen("#FF6F00", width=2, style=Qt.SolidLine),
                    label=f"POC-{idx+1}: {vp_data['poc']:.2f}",
                    labelOpts={
                        "position": 0.05 + idx * 0.3,
                        "color": "#FF6F00",
                        "fill": pg.mkBrush(255, 111, 0, 100),
                    },
                )
                poc_line.setBounds([start_idx, end_idx])
                self.price_plot.addItem(poc_line)
                poc_line.setVisible(False)
                self.fixed_vp_items.append(poc_line)
        except Exception as e:
            print(f"Fixed VP hatası: {e}")

        # Pivot Points (gizli)
        self.pivot_lines = []
        pivots = PivotPointsCalculator.calculate_standard_pivots(df)
        if pivots:
            colors = {
                "P": ("#FF9800", "Pivot"),
                "R1": ("#F44336", "Direnç 1"),
                "R2": ("#D32F2F", "Direnç 2"),
                "S1": ("#4CAF50", "Destek 1"),
                "S2": ("#2E7D32", "Destek 2"),
            }
            for level, price in pivots.items():
                if level in colors:
                    color, label_text = colors[level]
                    line = pg.InfiniteLine(
                        angle=0,
                        pos=price,
                        pen=pg.mkPen(color, width=2, style=Qt.DashLine),
                        label=f"{label_text}: {price:.2f}",
                    )
                    self.price_plot.addItem(line)
                    line.setVisible(False)
                    self.pivot_lines.append(line)

        # Tools
        self.crosshair = CrosshairCursor(self.price_plot, df)
        self.fibonacci = FibonacciTool(self.price_plot, self)
        self.measure_tool = MeasureTool(self.price_plot, self)
        self.trend_tool = TrendLineTool(self.price_plot, self)

        # === VOLUME PLOT ===
        self.graph.nextRow()
        self.volume_plot = self.graph.addPlot(title="📊 Hacim")
        self.volume_plot.setMaximumHeight(150)
        colors = np.where(df["close"] >= df["open"], "#2E7D32", "#C62828")
        self.volume_bars = pg.BarGraphItem(
            x=x, height=df["volume"], width=0.8, brushes=colors
        )
        self.volume_plot.addItem(self.volume_bars)
        self.vma20 = self.volume_plot.plot(
            x, df["VMA20"], pen=pg.mkPen("#2196F3", width=1.5)
        )
        self.vma50 = self.volume_plot.plot(
            x, df["VMA50"], pen=pg.mkPen("#9C27B0", width=1.5)
        )

        # === RSI (gizli) ===
        self.graph.nextRow()
        self.rsi_plot = self.graph.addPlot(title="📈 RSI (14)")
        self.rsi_plot.setYRange(0, 100)
        self.rsi_plot.setLabel("left", "RSI")
        self.rsi_line = self.rsi_plot.plot(
            x, df["RSI"], pen=pg.mkPen("#673AB7", width=2)
        )
        self.rsi_ma = self.rsi_plot.plot(
            x, df["RSI_MA"], pen=pg.mkPen("#FF9800", width=1.5, style=Qt.DashLine)
        )
        for lvl, color in [(70, "#F44336"), (50, "#9E9E9E"), (30, "#4CAF50")]:
            self.rsi_plot.addLine(y=lvl, pen=pg.mkPen(color, style=Qt.DashLine))

        # === MACD (gizli) ===
        self.graph.nextRow()
        self.macd_plot = self.graph.addPlot(title="📉 MACD")
        self.macd_plot.setLabel("left", "MACD")
        self.macd_line = self.macd_plot.plot(
            x, df["MACD"], pen=pg.mkPen("#2196F3", width=2)
        )
        self.macd_signal = self.macd_plot.plot(
            x, df["MACD_Signal"], pen=pg.mkPen("#FF5722", width=2)
        )
        hist_colors = np.where(df["MACD_Hist"] >= 0, "#2E7D32", "#C62828")
        self.macd_hist = pg.BarGraphItem(
            x=x, height=df["MACD_Hist"], width=0.6, brushes=hist_colors
        )
        self.macd_plot.addItem(self.macd_hist)
        self.macd_plot.addLine(y=0, pen=pg.mkPen("#9E9E9E"))

        # === STOCH (gizli) ===
        self.graph.nextRow()
        self.stoch_plot = self.graph.addPlot(title="⚡ Stochastic (14,3,3)")
        self.stoch_plot.setYRange(0, 100)
        self.stoch_plot.setLabel("left", "Stochastic")
        self.stoch_k = self.stoch_plot.plot(
            x, df["STOCH_K"], pen=pg.mkPen("#2196F3", width=2)
        )
        self.stoch_d = self.stoch_plot.plot(
            x, df["STOCH_D"], pen=pg.mkPen("#FF5722", width=2)
        )
        for lvl in (20, 50, 80):
            self.stoch_plot.addLine(y=lvl, pen=pg.mkPen("#9E9E9E", style=Qt.DashLine))

        # === ADX (gizli) ===
        self.graph.nextRow()
        self.adx_plot = self.graph.addPlot(title="💪 ADX (14)")
        self.adx_plot.setYRange(0, 100)
        self.adx_plot.setLabel("left", "ADX")
        self.adx_line = self.adx_plot.plot(
            x, df["ADX"], pen=pg.mkPen("#9C27B0", width=2)
        )
        self.adx_plot.addLine(y=25, pen=pg.mkPen("#FF9800", style=Qt.DashLine))

        # Link axes
        for p in [
            self.volume_plot,
            self.rsi_plot,
            self.macd_plot,
            self.stoch_plot,
            self.adx_plot,
        ]:
            p.setXLink(self.price_plot)

        # CRITICAL: Plot'ları gizle ama grafiği render et
        self.rsi_plot.setVisible(False)
        self.macd_plot.setVisible(False)
        self.stoch_plot.setVisible(False)
        self.adx_plot.setVisible(False)

        # Skor Kartı HUD
        self.score_card_hud = ScoreCardHUD(self.df, self)
        self.score_card_hud.setGeometry(self.width() - 250, 100, 230, 200)
        self.score_card_hud.show()

    def toggle_indicator(self, indicator: str, visible: bool):
        """Gösterge görünürlüğünü değiştir"""
        if indicator in ["EMA9", "EMA20", "EMA50", "SMA200"]:
            if indicator in self.ema_items:
                self.ema_items[indicator].setVisible(visible)
        elif indicator == "BB":
            for item in [self.bb_upper, self.bb_middle, self.bb_lower, self.bb_fill]:
                item.setVisible(visible)
        elif indicator == "BB_SQUEEZE":
            ohlc = self.df[["open", "high", "low", "close"]].values
            if visible:
                self.candles.setData(ohlc, self.df)
            else:
                temp_df = self.df.copy()
                temp_df["BB_Squeeze"] = False
                self.candles.setData(ohlc, temp_df)
        elif indicator == "VWAP" and self.vwap_line:
            self.vwap_line.setVisible(visible)
        elif indicator.startswith("PATTERN_"):
            pattern_name = indicator.replace("PATTERN_", "").lower()
            if pattern_name in self.pattern_items:
                self.pattern_items[pattern_name]["scatter"].setVisible(visible)

        # 🆕 SWING PATTERN TOGGLE
        elif indicator.startswith("SWING_"):
            if indicator in self.swing_pattern_items:
                self.swing_pattern_items[indicator].setVisible(visible)

        elif indicator == "DIVERGENCES":
            for item in self.divergence_items.values():
                item.setVisible(visible)
        elif indicator == "VOLUME_PROFILE":
            for item in self.volume_profile_items + [
                self.poc_line,
                self.vah_line,
                self.val_line,
            ]:
                item.setVisible(visible)
        elif indicator == "FIXED_VOLUME_PROFILE":
            for item in self.fixed_vp_items:
                item.setVisible(visible)
        elif indicator == "RSI":
            self.rsi_plot.setVisible(visible)
        elif indicator == "MACD":
            self.macd_plot.setVisible(visible)
        elif indicator == "STOCH":
            self.stoch_plot.setVisible(visible)
        elif indicator == "ADX":
            self.adx_plot.setVisible(visible)
        elif indicator == "SUPPORT":
            for line in self.support_lines:
                line.setVisible(visible)
        elif indicator == "RESISTANCE":
            for line in self.resistance_lines:
                line.setVisible(visible)
        elif indicator == "PIVOTS":
            for line in self.pivot_lines:
                line.setVisible(visible)

    def handle_drawing_tool(self, tool_id: str):
        """Çizim aracı handler'ı"""
        if tool_id == "measure":
            self.measure_tool.activate()
        elif tool_id == "rr_long":
            if not self.rr_tool:
                self.rr_tool = RiskRewardTool(self.price_plot, self)
            self.rr_tool.activate(mode="long")
        elif tool_id == "rr_short":
            if not self.rr_tool:
                self.rr_tool = RiskRewardTool(self.price_plot, self)
            self.rr_tool.activate(mode="short")
        elif tool_id == "trendline":
            self.trend_tool.activate()
        elif tool_id == "fib_retracement":
            self.fibonacci.activate(mode="retracement")
        elif tool_id == "fib_extension":
            self.fibonacci.activate(mode="extension")
        elif tool_id == "fib_auto":
            bars, ok = QInputDialog.getInt(
                self, "🔢 Otomatik Fibonacci", "Kaç bar için hesaplansın?", 100, 20, 500
            )
            if ok:
                recent_data = self.df.tail(bars)
                high, low = recent_data["high"].max(), recent_data["low"].min()
                self.fibonacci.set_mode("retracement")
                self.fibonacci.draw_retracement(low, high)
        elif tool_id == "hline":
            if not self.hline_tool:
                self.hline_tool = HorizontalLineTool(self.price_plot, self)
            self.hline_tool.activate()
        elif tool_id == "channel":
            if not self.channel_tool:
                self.channel_tool = ChannelTool(self.price_plot, self)
            self.channel_tool.activate()
        elif tool_id == "rectangle":
            if not self.rectangle_tool:
                self.rectangle_tool = RectangleTool(self.price_plot, self)
            self.rectangle_tool.activate()
        elif tool_id == "text":
            if not self.text_tool:
                self.text_tool = TextAnnotationTool(self.price_plot, self)
            self.text_tool.activate()
        elif tool_id == "clear_all":
            self.clear_all_drawings()

    def clear_all_drawings(self):
        """Tüm çizimleri temizle"""
        reply = QMessageBox.question(
            self,
            "🗑️ Tüm Çizimleri Sil",
            "Tüm çizimler silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if self.fibonacci and self.fibonacci.is_visible():
                self.fibonacci.clear()
            if self.trend_tool:
                self.trend_tool.clear_all()
            if self.measure_tool:
                self.measure_tool.clear()
            if self.rr_tool:
                self.rr_tool.clear()
            if self.hline_tool:
                self.hline_tool.clear_all()
            if self.channel_tool:
                self.channel_tool.clear_all()
            if self.rectangle_tool:
                self.rectangle_tool.clear_all()
            if self.text_tool:
                self.text_tool.clear_all()

    def show_swing_pattern_analysis(self):
        """🆕 Swing Pattern Analiz Dialogu"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"🚀 {self.symbol} - Swing Pattern Analizi")
        dialog.resize(900, 750)

        layout = QVBoxLayout(dialog)

        # Özet başlık
        total_patterns = sum(
            len(positions) for positions in self.swing_patterns.values()
        )

        header = QLabel(
            f"<h2>🚀 SWING TRADE PATTERN ANALİZİ</h2>"
            f"<p style='font-size: 14px;'>Toplam {total_patterns} adet swing pattern tespit edildi.</p>"
        )
        header.setStyleSheet("color: #FF6F00; padding: 10px; background: #FFF3E0;")
        layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()

        # Her pattern türü için tab
        pattern_groups = {
            "Reversal Patterns": ["bullish_reversal_combo", "bearish_reversal_combo"],
            "Continuation Patterns": ["bullish_flag", "bearish_flag"],
            "Exhaustion Patterns": ["buying_climax", "selling_climax"],
            "Key Reversals": ["key_reversal_up", "key_reversal_down"],
            "Breakouts": ["breakout_up", "breakdown"],
        }

        for group_name, pattern_keys in pattern_groups.items():
            widget = QWidget()
            widget_layout = QVBoxLayout(widget)

            for pattern_key in pattern_keys:
                positions = self.swing_patterns.get(pattern_key, [])
                if not positions:
                    continue

                config = SwingPatternRecognizer.SWING_PATTERNS[pattern_key]

                pattern_html = f"""
                <div style='border: 3px solid {config['color']}; border-radius: 8px; 
                     padding: 15px; margin: 10px; background: rgba(255,255,255,0.9);'>
                    <h3>{config['emoji']} {config['name']}</h3>
                    <p><i>{config['desc']}</i></p>
                    <p><b>Tespit Sayısı:</b> {len(positions)} adet</p>
                    <p><b>Son Tespit:</b> Bar {positions[-1][0]} - Fiyat {positions[-1][1]:.2f} - 
                       Güç {positions[-1][2]:.0f}%</p>
                </div>
                """

                label = QLabel(pattern_html)
                label.setWordWrap(True)
                widget_layout.addWidget(label)

            widget_layout.addStretch()
            tabs.addTab(widget, group_name)

        # Tüm pattern'lerin listesi tab
        all_widget = QWidget()
        all_layout = QVBoxLayout(all_widget)

        all_html = "<h3>📋 Tüm Pattern Tespitleri</h3>"
        for pattern_key, positions in self.swing_patterns.items():
            if not positions:
                continue

            config = SwingPatternRecognizer.SWING_PATTERNS[pattern_key]
            all_html += f"<p><b>{config['emoji']} {config['name']}:</b> {len(positions)} adet</p>"

        all_label = QLabel(all_html)
        all_label.setWordWrap(True)
        all_layout.addWidget(all_label)
        all_layout.addStretch()

        tabs.addTab(all_widget, "📋 Özet")

        layout.addWidget(tabs)

        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def update_live_price(self, price: float):
        """WebSocket'ten gelen canlı fiyatı grafikte yatay çizgi olarak günceller (Seçenek C)"""
        if not hasattr(self, "live_price_line") or price <= 0:
            return
        try:
            self._live_price = float(price)
            self.live_price_line.setPos(self._live_price)
        except Exception:
            pass

    def save_indicator_layout(self):
        """Açık/kapalı indikatör ayarlarını JSON şablon olarak kaydeder (Seçenek C)"""
        try:
            state = {"indicators": {}, "timeframe": getattr(self, "current_timeframe", "1d")}
            if hasattr(self, "indicator_panel") and hasattr(self.indicator_panel, "indicators"):
                for key, cb in self.indicator_panel.indicators.items():
                    if isinstance(cb, QCheckBox):
                        state["indicators"][key] = cb.isChecked()
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Şablon Kaydet",
                "",
                "JSON Şablon (*.json);;Tüm Dosyalar (*.*)",
            )
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Şablon Kaydedildi", f"Ayar şablonu kaydedildi:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Şablon kaydedilemedi: {e}")

    def load_indicator_layout(self):
        """Kaydedilmiş indikatör şablonunu yükler ve uygular (Seçenek C)"""
        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Şablon Yükle",
                "",
                "JSON Şablon (*.json);;Tüm Dosyalar (*.*)",
            )
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            if not isinstance(state, dict):
                return
            indicators = state.get("indicators", {})
            if hasattr(self, "indicator_panel") and hasattr(self.indicator_panel, "indicators"):
                for key, cb in self.indicator_panel.indicators.items():
                    if key in indicators and isinstance(cb, QCheckBox):
                        cb.setChecked(bool(indicators[key]))
                        self.toggle_indicator(key, bool(indicators[key]))
            if state.get("timeframe") and state["timeframe"] != getattr(self, "current_timeframe", ""):
                self.change_timeframe(state["timeframe"])
            QMessageBox.information(self, "Şablon Yüklendi", f"Ayar şablonu uygulandı:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Şablon yüklenemedi: {e}")

    def change_timeframe(self, timeframe: str):
        """Zaman dilimini değiştir"""
        self.current_timeframe = timeframe

        progress = QProgressDialog(
            f"{MultiTimeframeManager.get_timeframe_name(timeframe)} verileri yükleniyor...",
            None,
            0,
            100,
            self,
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(20)

        try:
            new_df = self.mtf_manager.get_data(
                self.symbol, timeframe, force_refresh=False
            )

            if new_df is None or len(new_df) < 200:
                QMessageBox.critical(self, "❌ Hata", "Yetersiz veri!")
                progress.close()
                return

            progress.setValue(40)

            self.df = new_df.copy().reset_index(drop=True)

            if "date" not in self.df.columns:
                self.df["date"] = pd.date_range(
                    end=datetime.now(), periods=len(self.df), freq="D"
                )

            IndicatorCalculator.validate_df(self.df)
            progress.setValue(60)

            # Cache'leri temizle
            IndicatorCalculator._cache.clear()
            VolumeProfile._cache.clear()

            # Hesaplamalar
            self.df = IndicatorCalculator.calculate(self.df)
            self.signals = IndicatorCalculator.detect_signals(self.df)
            self.patterns = PatternRecognizer.detect_patterns(self.df)

            # 🆕 SWING PATTERNS YENİDEN HESAPLA
            self.swing_patterns = SwingPatternRecognizer.detect_all_swing_patterns(
                self.df
            )

            # Divergence
            swing_analysis = SwingDivergenceAnalyzer.analyze_complete(
                self.df, mtf_data=None, min_quality=50
            )
            self.divergences = swing_analysis["divergences"]
            self.swing_structure = swing_analysis["swing_structure"]
            self.high_prob_setups = swing_analysis.get("high_probability_setups", [])

            self.divergence_summary = {
                "total_count": sum(
                    len(divs)
                    for types in self.divergences.values()
                    for divs in types.values()
                ),
                "by_indicator": {
                    ind: sum(len(divs) for divs in types.values())
                    for ind, types in self.divergences.items()
                },
                "strong_signals": self.high_prob_setups[:5],
            }

            self.volume_profile_data = VolumeProfile.calculate(self.df)
            progress.setValue(80)

            # Grafiği yeniden çiz
            self.graph.clear()
            self._build_plots()
            progress.setValue(100)

            QMessageBox.information(
                self,
                "✅ Başarılı",
                f"Grafik güncellendi.\n\n"
                f"📊 Toplam bar: {len(self.df)}\n"
                f"🚀 Swing Patterns: {sum(len(p) for p in self.swing_patterns.values())} adet",
            )

        except Exception as e:
            QMessageBox.critical(self, "❌ Hata", f"Hata: {str(e)}")
        finally:
            progress.close()

    def add_price_alert(self):
        """Fiyat alarmı ekle"""
        current_price = self.df["close"].iloc[-1]
        price, ok = QInputDialog.getDouble(
            self,
            "🔔 Fiyat Alarmı",
            f"Alarm fiyatı girin:\n(Mevcut: {current_price:.2f})",
            current_price,
            0,
            current_price * 10,
            2,
        )
        if ok:
            alert_type = "above" if price > current_price else "below"
            self.price_alerts.add_alert(
                price, alert_type, f"Fiyat {price:.2f} seviyesine ulaştı!"
            )
            QMessageBox.information(
                self, "✅ Alarm Eklendi", f"Fiyat {price:.2f} alarmı eklendi."
            )

    def toggle_theme(self):
        """Tema değiştir"""
        new_theme = "dark" if CURRENT_THEME == "light" else "light"
        set_theme(new_theme)

        # PyQtGraph ayarlarını güncelle
        theme = THEMES[new_theme]
        pg.setConfigOption("background", theme["background"])
        pg.setConfigOption("foreground", theme["foreground"])

        QMessageBox.information(
            self,
            "🌓 Tema Değiştirildi",
            f"{new_theme.upper()} tema aktif.\n\n"
            "Not: Yeni grafikler açıldığında tema uygulanacak.",
        )

    def reset_zoom(self):
        """Zoom'u sıfırla"""
        self.price_plot.autoRange()
        for plot in [self.volume_plot, self.rsi_plot, self.macd_plot]:
            if plot.isVisible():
                plot.autoRange()

    def toggle_fullscreen(self):
        """Tam ekran aç/kapat"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def export_chart(self):
        """Grafiği PNG olarak kaydet"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Grafiği Kaydet",
                f"{self.symbol}_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                "PNG Files (*.png)",
            )
            if filename:
                exporter = pg.exporters.ImageExporter(self.graph.scene())
                exporter.parameters()["width"] = 1920
                exporter.export(filename)
                QMessageBox.information(
                    self, "✅ Başarılı", f"Grafik kaydedildi:\n{filename}"
                )
        except Exception as e:
            QMessageBox.critical(self, "❌ Hata", f"Export hatası: {str(e)}")

    def show_statistics(self):
        """İstatistikler dialogu - Swing Patterns eklenmiş"""
        df = self.df
        current_price = df["close"].iloc[-1]

        # 🆕 SWING PATTERN İSTATİSTİKLERİ
        total_swing_patterns = sum(
            len(positions) for positions in self.swing_patterns.values()
        )

        stats_text = f"""
<h2>📈 Fiyat Bilgileri</h2>
<p><b>Mevcut Fiyat:</b> {current_price:.2f} ₺</p>

<h2>🚀 Swing Trade Patterns</h2>
<p><b>Toplam Pattern:</b> {total_swing_patterns} adet</p>
"""

        for pattern_key, positions in self.swing_patterns.items():
            if not positions:
                continue
            config = SwingPatternRecognizer.SWING_PATTERNS[pattern_key]
            stats_text += f"<p>{config['emoji']} <b>{config['name']}:</b> {len(positions)} adet</p>"

        stats_text += f"""
<h2>⚠️ Uyumsuzluklar</h2>
<p><b>Toplam:</b> {self.divergence_summary['total_count']} adet</p>
"""

        # Dialog oluştur
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📊 {self.symbol} - İstatistikler")
        dialog.resize(600, 700)

        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        label = QLabel(stats_text)
        label.setWordWrap(True)
        scroll.setWidget(label)
        layout.addWidget(scroll)

        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def show_mtf_analysis(self):
        """Çoklu zaman dilimi analizi dialogu"""
        progress = QProgressDialog("MTF analiz yapılıyor...", None, 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(20)

        try:
            # Analiz yap
            analysis = self.mtf_analyzer.analyze_multi_timeframe_trend(
                self.symbol, timeframes=["15m", "1h", "4h", "1d", "1w"]
            )

            progress.setValue(80)

            # Dialog oluştur
            dialog = QDialog(self)
            dialog.setWindowTitle(f"📊 {self.symbol} - Multi-Timeframe Analiz")
            dialog.resize(700, 600)

            layout = QVBoxLayout(dialog)

            # Genel trend
            overall_trend = analysis["overall_trend"]
            trend_strength = analysis["trend_strength"]

            trend_emoji = (
                "🟢"
                if overall_trend == "bullish"
                else "🔴" if overall_trend == "bearish" else "🟡"
            )
            trend_color = (
                "#4CAF50"
                if overall_trend == "bullish"
                else "#F44336" if overall_trend == "bearish" else "#FF9800"
            )

            header = QLabel(
                f"<h2>{trend_emoji} GENEL TREND: {overall_trend.upper()}</h2>"
                f"<p style='font-size: 14px;'>Trend Gücü: {trend_strength:.1f}% "
                f"({analysis['aligned_count']}/{analysis['total_timeframes']} timeframe hizalı)</p>"
            )
            header.setStyleSheet(f"color: {trend_color}; padding: 10px;")
            layout.addWidget(header)

            # Timeframe detayları
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)

            content = QWidget()
            content_layout = QVBoxLayout(content)

            for tf, data in analysis["timeframe_trends"].items():
                tf_trend = data["trend"]
                tf_aligned = data["ema_alignment"]

                tf_emoji = (
                    "🟢"
                    if tf_trend == "bullish"
                    else "🔴" if tf_trend == "bearish" else "🟡"
                )
                align_emoji = "✅" if tf_aligned else "❌"

                tf_text = f"""
                    <div style='border: 2px solid #ccc; border-radius: 5px; padding: 10px; margin: 5px;'>
                        <h3>{tf_emoji} {MultiTimeframeManager.get_timeframe_name(tf)} ({tf.upper()})</h3>
                        <p><b>Trend:</b> {tf_trend.upper()}</p>
                        <p><b>EMA Hizalı:</b> {align_emoji} {'Evet' if tf_aligned else 'Hayır'}</p>
                        <p><b>Fiyat:</b> {data['current_price']:.2f} ₺</p>
                        <p><b>EMA20:</b> {data['ema20']:.2f} ₺</p>
                        <p><b>EMA50:</b> {data['ema50']:.2f} ₺</p>
                    </div>
                    """

                label = QLabel(tf_text)
                label.setWordWrap(True)
                content_layout.addWidget(label)

            content_layout.addStretch()
            scroll.setWidget(content)
            layout.addWidget(scroll)

            # Tavsiye
            advice_text = ""
            if trend_strength >= 80:
                advice_text = "🔥 <b>ÇOK GÜÇLÜ TREND!</b> Tüm timeframe'ler hizalı. Trend yönünde işlem yapılabilir."
            elif trend_strength >= 60:
                advice_text = "✅ <b>GÜÇLÜ TREND</b> Çoğu timeframe hizalı. Trend yönünde işlem önerilir."
            elif trend_strength >= 40:
                advice_text = "⚠️ <b>ORTA TREND</b> Kısmi hizalanma var. Dikkatli olun."
            else:
                advice_text = (
                    "❌ <b>ZAYIF/KARARSİZ</b> Timeframe'ler hizalı değil. İşlem riskli."
                )

            advice_label = QLabel(
                f"<p style='padding: 10px; background: #FFF9C4;'>{advice_text}</p>"
            )
            advice_label.setWordWrap(True)
            layout.addWidget(advice_label)

            # Kapat butonu
            close_btn = QPushButton("Kapat")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            progress.setValue(100)
            progress.close()

            dialog.exec_()

        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "❌ Hata", f"MTF analiz hatası:\n{str(e)}")

    def show_divergence_analysis(self):
        """COMPLETE Swing Divergence analiz dialogu"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"⚠️ {self.symbol} - SWING DIVERGENCE Analizi")
        dialog.resize(800, 700)

        layout = QVBoxLayout(dialog)

        # Swing yapısı
        swing_struct = self.swing_structure
        total_divs = self.divergence_summary["total_count"]
        high_prob_count = len(self.high_prob_setups)

        header = QLabel(
            f"<h2>🎯 SWING TRADE ANALİZİ</h2>"
            f"<p><b>Swing Yapısı:</b> {swing_struct.get('structure', 'N/A').upper()}</p>"
            f"<p><b>Higher Highs:</b> {swing_struct.get('higher_highs', 0)} | "
            f"<b>Lower Lows:</b> {swing_struct.get('lower_lows', 0)}</p>"
            f"<p><b>Toplam Divergence:</b> {total_divs} | "
            f"<b>Yüksek Olasılıklı Setup:</b> {high_prob_count}</p>"
        )
        header.setStyleSheet("color: #2196F3; padding: 10px; background: #E3F2FD;")
        layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()

        # Tab 1: High Probability Setups
        if self.high_prob_setups:
            hp_widget = QWidget()
            hp_layout = QVBoxLayout(hp_widget)

            for i, setup in enumerate(self.high_prob_setups[:10], 1):  # Top 10
                score = setup["score"]
                score_color = (
                    "#4CAF50" if score >= 8 else "#FF9800" if score >= 6 else "#F44336"
                )

                setup_text = f"""
                <div style='border: 2px solid {score_color}; border-radius: 5px; padding: 10px; margin: 5px;'>
                    <h3>#{i} - Score: {score}/10 🔥</h3>
                    <p><b>Gösterge:</b> {setup['indicator'].upper()}</p>
                    <p><b>Tip:</b> {setup['type'].replace('_', ' ').title()}</p>
                    <p><b>Bar:</b> {setup['index']} | <b>Fiyat:</b> {setup['price']:.2f}</p>
                    <p><b>Kalite:</b> {setup['quality']:.0f}%</p>
                    <p><b>Nedenler:</b></p>
                    <ul>
                """

                for reason in setup["reasons"]:
                    setup_text += f"<li>{reason}</li>"

                setup_text += "</ul></div>"

                label = QLabel(setup_text)
                label.setWordWrap(True)
                hp_layout.addWidget(label)

            hp_layout.addStretch()
            tabs.addTab(hp_widget, "🔥 Yüksek Olasılıklı")

        # Tab 2: Tüm Divergences
        all_widget = QWidget()
        all_layout = QVBoxLayout(all_widget)

        for indicator, types in self.divergences.items():
            indicator_count = sum(len(divs) for divs in types.values())
            if indicator_count == 0:
                continue

            ind_text = f"<h3>📊 {indicator.upper()} ({indicator_count} adet)</h3>"

            for div_type, div_list in types.items():
                if not div_list:
                    continue

                ind_text += f"<p><b>{div_type.replace('_', ' ').title()}:</b> {len(div_list)} adet</p>"

            label = QLabel(ind_text)
            all_layout.addWidget(label)

        all_layout.addStretch()
        tabs.addTab(all_widget, "📋 Tümü")

        # Tab 3: Swing Yapısı
        swing_widget = QWidget()
        swing_layout = QVBoxLayout(swing_widget)

        swing_text = f"""
        <h3>📈 Swing Yapısı Analizi</h3>
        <p><b>Trend:</b> {swing_struct.get('structure', 'N/A').upper()}</p>
        <p><b>Swing High Sayısı:</b> {len(swing_struct.get('swing_highs', []))}</p>
        <p><b>Swing Low Sayısı:</b> {len(swing_struct.get('swing_lows', []))}</p>
        <p><b>Higher Highs:</b> {swing_struct.get('higher_highs', 0)}</p>
        <p><b>Lower Lows:</b> {swing_struct.get('lower_lows', 0)}</p>
        
        <h4>💡 Yorumlama:</h4>
        """

        if swing_struct.get("structure") == "uptrend":
            swing_text += "<p>✅ <b>Yükseliş trendi</b> - Higher Highs dominant. Dips'lerde alım fırsatı.</p>"
        elif swing_struct.get("structure") == "downtrend":
            swing_text += "<p>⚠️ <b>Düşüş trendi</b> - Lower Lows dominant. Rallies'de satış fırsatı.</p>"
        else:
            swing_text += "<p>⚡ <b>Yatay hareket</b> - Range trading. Destek/direnç stratejisi.</p>"

        swing_label = QLabel(swing_text)
        swing_label.setWordWrap(True)
        swing_layout.addWidget(swing_label)
        swing_layout.addStretch()

        tabs.addTab(swing_widget, "📊 Swing Yapısı")

        layout.addWidget(tabs)

        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec_()

    def resizeEvent(self, event):
        """Pencere boyutu değiştiğinde HUD'ı yeniden konumlandır"""
        super().resizeEvent(event)
        if self.score_card_hud:
            self.score_card_hud.setGeometry(self.width() - 250, 100, 230, 200)
        """Pencere boyutu değiştiğinde HUD'ı yeniden konumlandır"""
        super().resizeEvent(event)
        if self.score_card_hud:
            self.score_card_hud.setGeometry(self.width() - 250, 100, 230, 200)


    def toggle_heikin_ashi(self, checked):
        """Heikin Ashi modunu aç/kapat"""
        if not hasattr(self, 'price_plot') or not hasattr(self, 'candles'):
            return

        if checked:
            # Heikin Ashi hesapla
            df_ha = self._calculate_heikin_ashi(self.df)
            ohlc = df_ha[["open", "high", "low", "close"]].values
            self.candles.setData(ohlc, df_ha)
            
            # Başlığı güncelle
            self.price_plot.setTitle(f"🚀 {self.symbol} - {self.current_timeframe.upper()} (Heikin Ashi)")
            self.btn_ha.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        else:
            # Normal mumlara dön
            ohlc = self.df[["open", "high", "low", "close"]].values
            self.candles.setData(ohlc, self.df)
            
            self.price_plot.setTitle(f"🚀 {self.symbol} - {self.current_timeframe.upper()}")
            self.btn_ha.setStyleSheet("")

    def _calculate_heikin_ashi(self, df):
        """Heikin Ashi hesapla"""
        ha_df = df.copy()
        
        # HA_Close
        ha_df['close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        
        # HA_Open
        ha_open = [ (df['open'].iloc[0] + df['close'].iloc[0]) / 2 ]
        for i in range(1, len(df)):
            prev_open = ha_open[i-1]
            prev_close = ha_df['close'].iloc[i-1]
            current_open = (prev_open + prev_close) / 2
            ha_open.append(current_open)
            
        ha_df['open'] = ha_open
        
        # HA_High ve HA_Low
        ha_df['high'] = ha_df[['high', 'open', 'close']].max(axis=1)
        ha_df['low'] = ha_df[['low', 'open', 'close']].min(axis=1)
        
        return ha_df

# Test için
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=500, freq="D")
    base_price = 100
    prices = []
    for i in range(500):
        base_price += np.random.randn() * 2
        prices.append(base_price)

    test_df = pd.DataFrame(
        {
            "date": dates,
            "open": prices,
            "high": [p + abs(np.random.randn() * 2) for p in prices],
            "low": [p - abs(np.random.randn() * 2) for p in prices],
            "close": [p + np.random.randn() for p in prices],
            "volume": [np.random.randint(1000000, 10000000) for _ in range(500)],
        }
    )

    app = QApplication(sys.argv)
    chart = SwingTradeChart(test_df, "THYAO", {})
    chart.exec_()
    sys.exit(0)
