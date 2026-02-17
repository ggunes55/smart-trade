# -*- coding: utf-8 -*-
"""
Main Window - Chart Widget Entegrasyonlu Ana Pencere
"""
import sys
import json
import logging
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTabWidget,
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QThread
from tvDatafeed import TvDatafeed

# Workers
from ..workers import ScanWorker, BacktestWorker, MarketAnalysisWorker, WebSocketWorker

# Tabs
from ..tabs.symbols_tab import SymbolsTab
from ..tabs.criteria_tab import CriteriaTab
from ..tabs.results_tab import ResultsTab
from ..tabs.market_tab import MarketTab
from ..tabs.chart_tab import ChartTab  # 🆕 Yeni chart tab
from ..tabs.readme_tab import ReadmeTab  # 🆕 Hakkında sekmesi
from ..tabs.watchlist_tab import WatchlistTab  # Phase 1: Watchlist
from ..tabs.analysis_tab import AnalysisTab  # 🆕 Detaylı Analiz Sekmesi
from ..tabs.portfolio_tab import PortfolioTab  # 🆕 Portfolio Yönetimi
from ..tabs.settings_tab import SettingsTab  # 🆕 Ayarlar
from ..tabs.backtest_results_tab import BacktestResultsTab, BacktestVisualizer  # 🆕 Backtest Görselleştirme
from ..tabs.ml_management_tab import MLManagementTab, MLModelRegistry  # 🆕 ML Yönetimi

# Widgets
from ..widgets.control_panel import ControlPanel
from ..widgets.log_widget import QTextEditLogger
from ..widgets.price_ticker import LivePriceTicker

# Utils
from ..utils.styles import MAIN_STYLESHEET, TITLE_STYLE, LOG_WIDGET, STOP_BUTTON, SUCCESS_BUTTON
from ..utils.helpers import safe_float_conversion, format_trade_plan
from ..utils.themes import ThemeManager, apply_theme
from ..data.state_manager import GUIStateManager
from ..reporting.exporter import ExportManager
from ..notifications.notification_manager import NotificationManager

# Core imports
try:
    from scanner.swing_hunter import SwingHunterUltimate
    from smart_filter.smart_filter import SmartFilterSystem
except ImportError:
    import os

    sys.path.append(os.path.dirname(__file__))
    from scanner.swing_hunter import SwingHunterUltimate
    from smart_filter.smart_filter import SmartFilterSystem


class SwingGUIAdvancedPlus(QWidget):
    """Ana GUI sınıfı - Chart Widget Entegrasyonlu"""

    def __init__(self):
        super().__init__()

        # State Manager (merkezi veri yönetimi)
        self.state_manager = GUIStateManager()
        
        # Export Manager
        self.export_manager = ExportManager('./exports')
        
        # Theme Manager
        self.theme_manager = ThemeManager('light')

        # Core bileşenler
        self.hunter = SwingHunterUltimate()
        self.cfg = self.hunter.cfg
        
        # Notification Manager (cfg'den sonra)
        self.notification_manager = NotificationManager(self.cfg)
        
        # TvDatafeed timeout ayarı - WebSocket timeout sorununu çöz
        import socket
        socket.setdefaulttimeout(30)  # Global timeout 30 saniye
        
        self.tv = TvDatafeed()
        
        # SSL context ayarlaması (Windows sertifika sorunu)
        try:
            import ssl
            import certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        except Exception:
            pass  # SSL ayarı zorunlu değil

        # Veri depolama
        self.backtest_results = None
        self.market_analysis = None

        # Worker referansları
        self.scan_worker = None
        self.scan_thread = None
        self.backtest_worker = None
        self.backtest_thread = None
        self.market_worker = None
        self.market_thread = None
        
        # WebSocket Worker
        self.ws_worker = None
        self.ws_thread = None
        self.price_ticker = None

        # UI başlat
        self.init_ui()
        self.setup_logging()
        self.load_settings()
        self.connect_signals()

        # Otomatik piyasa analizi
        self.start_market_analysis()

    def init_ui(self):
        """UI başlangıcı"""
        self.setWindowTitle(
            "🎯 Swing Hunter Advanced Plus - Profesyonel Tarama Sistemi"
        )
        self.setGeometry(50, 50, 1800, 1000)
        self.setStyleSheet(MAIN_STYLESHEET)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_widget = self._create_left_panel()
        right_widget = self._create_right_panel()
        left_widget.setMinimumWidth(280)
        left_widget.setMaximumWidth(520)
        right_widget.setMinimumWidth(350)

        main_layout.addWidget(left_widget, 0)
        main_layout.addWidget(right_widget, 1)

    def _create_left_panel(self):
        """Sol panel - Ayarlar ve Kontroller"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Başlık
        title = QLabel("🚀 Ultimate Scanner Plus")
        title.setStyleSheet(TITLE_STYLE)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Tab widget
        tabs = QTabWidget()

        # Hisseler sekmesi
        self.symbols_tab = SymbolsTab(self.cfg)
        tabs.addTab(self.symbols_tab, "🎯 Hisseler")

        # Kriterler sekmesi
        self.criteria_tab = CriteriaTab(self.cfg)
        tabs.addTab(self.criteria_tab, "📊 Kriterler")

        # Canlı Fiyatlar sekmesi (ayrı tab, geniş alan)
        self.price_ticker = LivePriceTicker()
        live_prices_tab = QWidget()
        live_prices_layout = QVBoxLayout(live_prices_tab)
        live_prices_layout.setContentsMargins(8, 8, 8, 8)
        live_prices_layout.addWidget(QLabel("📈 Canlı fiyatlar — Bağlantıyı açıp tarama beklemeden veri alabilirsiniz. Bağlantı durumu üstte gösterilir."))
        # WebSocket Aç / Kes butonları
        ws_btn_layout = QHBoxLayout()
        self.ws_connect_btn = QPushButton("🔌 WebSocket'i Aç")
        self.ws_connect_btn.setToolTip("Canlı fiyat akışını başlatır (seçili semboller)")
        self.ws_connect_btn.setStyleSheet(SUCCESS_BUTTON)
        self.ws_connect_btn.clicked.connect(self.start_websocket)
        self.ws_disconnect_btn = QPushButton("WebSocket Bağlantısını Kes")
        self.ws_disconnect_btn.setToolTip("Canlı fiyat akışını durdurur")
        self.ws_disconnect_btn.setStyleSheet(STOP_BUTTON)
        self.ws_disconnect_btn.clicked.connect(self.stop_websocket)
        ws_btn_layout.addWidget(self.ws_connect_btn)
        ws_btn_layout.addWidget(self.ws_disconnect_btn)
        ws_btn_layout.addStretch()
        live_prices_layout.addLayout(ws_btn_layout)
        live_prices_layout.addWidget(self.price_ticker, 1)
        tabs.addTab(live_prices_tab, "📈 Canlı Fiyatlar")

        layout.addWidget(tabs)

        # Kontrol paneli
        self.control_panel = ControlPanel()
        layout.addWidget(self.control_panel)

        # Log widget
        log_group = QGroupBox("📋 İşlem Günlüğü")
        log_layout = QVBoxLayout()
        self.log_widget = QTextEdit()
        self.log_widget.setMaximumHeight(120)
        self.log_widget.setStyleSheet(LOG_WIDGET)
        log_layout.addWidget(self.log_widget)
        log_group.setLayout(log_layout)

        layout.addWidget(log_group)

        return widget

    def _create_right_panel(self):
        """Sağ panel - Sonuçlar ve Grafik"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        tabs = QTabWidget()

        # 🆕 Chart sekmesi (Mevcut chart_widget.py kullanır)
        self.chart_tab = ChartTab(self.tv, self.cfg)
        tabs.addTab(self.chart_tab, "📊 Grafik")

        # Sonuçlar sekmesi
        self.results_tab = ResultsTab()
        tabs.addTab(self.results_tab, "📋 Sonuçlar")
        
        # Phase 1: Watchlist sekmesi
        self.watchlist_tab = WatchlistTab(scanner=self.hunter)
        tabs.addTab(self.watchlist_tab, "📋 Watchlist")
        
        # 🆕 Detaylı Analiz sekmesi
        self.analysis_tab = AnalysisTab(
            parent=self,
            config=self.cfg,
            data_handler=self.hunter.data_handler if hasattr(self.hunter, 'data_handler') else None,
            symbol_analyzer=self.hunter.symbol_analyzer if hasattr(self.hunter, 'symbol_analyzer') else None
        )
        tabs.addTab(self.analysis_tab, "🔍 Detaylı Analiz")

        # 🆕 Portfolio sekmesi
        self.portfolio_tab = PortfolioTab(state_manager=self.state_manager)
        self.portfolio_tab.positions_updated.connect(lambda pos: self.state_manager.set('portfolio_positions', pos))
        tabs.addTab(self.portfolio_tab, "💼 Portfolio")

        # Piyasa & Backtest sekmesi
        self.market_tab = MarketTab()
        tabs.addTab(self.market_tab, "📈 Piyasa & Backtest")
        
        # 🆕 Backtest Sonuçları sekmesi
        self.backtest_results_tab = BacktestResultsTab(state_manager=self.state_manager)
        tabs.addTab(self.backtest_results_tab, "📊 Backtest Grafikleri")
        
        # 🆕 ML Management sekmesi
        self.ml_management_tab = MLManagementTab(state_manager=self.state_manager)
        tabs.addTab(self.ml_management_tab, "🤖 ML Yönetimi")
        
        # 🆕 Settings sekmesi
        self.settings_tab = SettingsTab(config=self.cfg, state_manager=self.state_manager)
        self.settings_tab.settings_changed.connect(self.on_settings_changed)
        tabs.addTab(self.settings_tab, "⚙️ Ayarlar")

        # 🆕 Hakkında sekmesi
        self.readme_tab = ReadmeTab()
        tabs.addTab(self.readme_tab, "📖 Hakkında")

        layout.addWidget(tabs)

        return widget

    def setup_logging(self):
        """Log sistemi kurulumu"""
        log_handler = QTextEditLogger(self.log_widget)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(message)s", datefmt="%H:%M:%S")
        )
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def connect_signals(self):
        """Sinyalleri bağla"""
        # Kontrol paneli
        self.control_panel.run_btn.clicked.connect(self.start_scan)
        self.control_panel.stop_btn.clicked.connect(self.stop_scan)

        # Semboller sekmesi
        self.symbols_tab.symbol_selected.connect(self.on_symbol_selected)
        self.symbols_tab.exchange_changed.connect(self.on_exchange_changed)

        # Sonuçlar sekmesi
        self.results_tab.row_selected.connect(self.on_result_row_selected)

        # Piyasa sekmesi
        self.market_tab.refresh_market.connect(self.start_market_analysis)
        self.market_tab.start_backtest.connect(self.start_backtest)

        # 🆕 Chart sekmesi
        self.chart_tab.chart_opened.connect(self.on_chart_opened)
        
        # 🆕 Settings sekmesi
        self.settings_tab.settings_changed.connect(self.on_settings_changed)
        
        # 🆕 Notification manager callback
        self.notification_manager.register_callback(self.show_toast_notification)
    
    def on_settings_changed(self, settings: dict):
        """Ayarlar değiştiğinde"""
        try:
            # Theme değişirse uygula
            theme_name = settings.get('ui', {}).get('theme', 'light')
            if theme_name != self.theme_manager.current_theme:
                self.theme_manager.set_theme(theme_name)
                self.setStyleSheet(self.theme_manager.get_stylesheet())
            
            # State manager'a kaydet
            self.state_manager.set('settings', settings)
            
            # Config güncelle
            self.cfg.update(settings)
            
            logging.info("✓ Ayarlar uygulandı")
        except Exception as e:
            logging.error(f"Ayarlar uygulanması hatası: {e}")

    # ========================================================================
    # Grafik İşlemleri (MEVCUT CHART_WIDGET İLE ENTEGRE)
    # ========================================================================

    def on_symbol_selected(self, item):
        """Hisse seçildiğinde - Chart Tab kullan"""
        if not item:
            return
        symbol = item.text()
        self.chart_tab.show_chart(symbol)

    def on_result_row_selected(self, row_data):
        """Sonuç tablosunda satır seçildiğinde"""
        try:
            symbol = row_data.get("Hisse", "")

            # Fiyat verilerini güvenli şekilde al
            current_text = row_data.get("Fiyat", "")  # Güncel fiyat
            entry_text = row_data.get("Optimal Giriş", "")
            stop_text = row_data.get("Stop Loss", "")
            target_text = row_data.get("Hedef 1", "")

            current_price = safe_float_conversion(current_text)
            entry_price = safe_float_conversion(entry_text)
            stop_loss = safe_float_conversion(stop_text)
            target1 = safe_float_conversion(target_text)
            
            # TV Detaylarını al (gizli veriden)
            tv_details = row_data.get("tv_signal_details")

            if None not in [entry_price, stop_loss, target1]:
                # Trade detaylarını göster (current_price ile birlikte)
                self.show_trade_details(symbol, entry_price, stop_loss, target1, current_price, tv_details)

                # Grafiği detaylı göster
                self.chart_tab.show_chart_with_details(
                    symbol, entry_price, stop_loss, target1
                )
            else:
                # Sadece grafik göster
                self.chart_tab.show_chart(symbol)

        except Exception as e:
            logging.error(f"Satır seçim hatası: {e}")

    def on_chart_opened(self, chart_window):
        """Grafik penceresi açıldığında"""
        count = self.chart_tab.get_open_charts_count()
        logging.info(f"Açık grafik sayısı: {count}")

    def show_trade_details(self, symbol, entry_price, stop_loss, target1, current_price=None, tv_details=None):
        """Trade detaylarını göster"""
        try:
            capital = self.cfg.get("initial_capital", 10000)
            trade_plan = self.hunter.calculate_trade_plan(
                symbol, entry_price, stop_loss, target1, capital
            )
            
            # Güncel fiyatı trade_plan'e ekle (giriş stratejisi açıklaması için)
            if current_price:
                trade_plan['current_price'] = current_price
            else:
                trade_plan['current_price'] = entry_price

            validation = self.hunter.validate_trade_parameters(
                entry_price, stop_loss, target1, symbol
            )

            details = format_trade_plan(trade_plan, validation, tv_details)
            self.results_tab.set_trade_details(details)

        except Exception as e:
            logging.error(f"Trade detay gösterim hatası: {e}")
            self.results_tab.set_trade_details(f"Hata: {str(e)}")

    # ========================================================================
    # Tarama İşlemleri (Önceki metodlar aynı)
    # ========================================================================

    def start_scan(self):
        """Taramayı başlat"""
        symbols = self.symbols_tab.get_symbols()

        if not symbols:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir hisse ekleyin!")
            return

        # Önceki taramayı durdur
        if self.scan_worker:
            try:
                self.scan_worker.stop()
            except Exception:
                pass

        self.save_settings()

        self.control_panel.set_scanning(True)
        self.control_panel.update_progress(0, "🚀 Tarama hazırlanıyor...")
        self.results_tab.clear_results()

        # Scanner'ı resetle
        self.hunter.reset()

        # Hemen progress göster
        self.control_panel.update_progress(1, f"📋 {len(symbols)} sembol hazırlanıyor...")

        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(self.hunter, symbols)
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)

        self.scan_worker.progress.connect(self.control_panel.update_progress)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)

        self.scan_thread.start()

        logging.info(f"🚀 Tarama başlatıldı: {len(symbols)} sembol")

    def stop_scan(self):
        """Taramayı durdur"""
        if self.scan_worker:
            self.scan_worker.stop()
            self.control_panel.update_progress(0, "⏸️ Tarama durduruluyor...")
            logging.info("⏸️ Tarama durdurma sinyali gönderildi")
        self.stop_websocket()

    def scan_finished(self, output):
        """Tarama tamamlandı"""
        self.control_panel.set_scanning(False)
        self.control_panel.update_progress(100, "✅ Tarama tamamlandı!")

        results_list = output.get("results", {}).get("Swing Uygun", [])
        market_analysis = output.get("market_analysis")

        if results_list:
            self.results_tab.populate_table(results_list)

            # İlk hissenin grafiğini göster
            if results_list:
                first_symbol = results_list[0]["Hisse"]
                self.chart_tab.show_chart(first_symbol)

            msg = f"🎉 {len(results_list)} adet uygun hisse bulundu!"
            if market_analysis:
                msg += f"\n📈 Piyasa Durumu: {market_analysis.regime.title()}"
            if output.get("excel_file"):
                msg += f"\n📊 Excel Raporu: {output['excel_file']}"

            QMessageBox.information(self, "Başarılı", msg)
        else:
            QMessageBox.warning(
                self,
                "Sonuç Yok",
                "Kriterlere uyan hisse bulunamadı.\n\n"
                "💡 İpucu: Filtreleri gevşetmeyi deneyin.",
            )

        self.scan_worker = None

        # Tarama bittikten sonra canlı fiyat akışını başlat (aynı anda çalışma = kilitlenme riski yok)
        self.start_websocket()

    def scan_error(self, error_message):
        """Tarama hatası"""
        self.control_panel.set_scanning(False)
        self.control_panel.update_progress(0, "❌ Hata oluştu!")

        logging.error(f"Tarama hatası: {error_message}")
        QMessageBox.critical(self, "Hata", f"Tarama sırasında hata:\n\n{error_message}")

        self.scan_worker = None

    # ========================================================================
    # Piyasa Analizi (Önceki metodlar aynı)
    # ========================================================================

    def start_market_analysis(self):
        """Piyasa analizini başlat"""
        self.market_tab.market_status_label.setText("🔄 Piyasa analizi yapılıyor...")

        self.market_thread = QThread()
        self.market_worker = MarketAnalysisWorker(self.hunter)
        self.market_worker.moveToThread(self.market_thread)

        self.market_thread.started.connect(self.market_worker.run)
        self.market_worker.finished.connect(self.market_thread.quit)
        self.market_worker.finished.connect(self.market_worker.deleteLater)
        self.market_thread.finished.connect(self.market_thread.deleteLater)

        self.market_worker.finished.connect(self.market_analysis_finished)
        self.market_worker.error.connect(self.market_analysis_error)

        self.market_thread.start()

    def market_analysis_finished(self, analysis):
        """Piyasa analizi tamamlandı"""
        self.market_analysis = analysis
        self.market_tab.update_market_analysis(analysis)

    def market_analysis_error(self, error_message):
        """Piyasa analizi hatası"""
        self.market_tab.update_market_error(error_message)

    # ========================================================================
    # Backtest İşlemleri (Önceki metodlar aynı)
    # ========================================================================

    def start_backtest(self, config):
        """Backtest başlat"""
        symbols = self.symbols_tab.get_symbols()

        if not symbols:
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir hisse ekleyin!")
            return

        self.market_tab.set_backtest_running(True)

        self.backtest_thread = QThread()
        self.backtest_worker = BacktestWorker(self.hunter, symbols, config)
        self.backtest_worker.moveToThread(self.backtest_thread)

        self.backtest_thread.started.connect(self.backtest_worker.run)
        self.backtest_worker.finished.connect(self.backtest_thread.quit)
        self.backtest_worker.finished.connect(self.backtest_worker.deleteLater)
        self.backtest_thread.finished.connect(self.backtest_thread.deleteLater)

        self.backtest_worker.progress.connect(self.control_panel.update_progress)
        self.backtest_worker.finished.connect(self.backtest_finished)
        self.backtest_worker.error.connect(self.backtest_error)

        self.backtest_thread.start()

        logging.info(f"🎯 Backtest başlatıldı: {len(symbols)} sembol")

    def _backtest_results_for_graphs(self, results):
        """Hunter backtest sonucunu Backtest Grafikleri sekmesi formatına çevirir."""
        trades_for_tab = []
        raw = results.get("raw_results") or []
        for r in raw:
            symbol = r.get("symbol", "")
            for t in r.get("trades") or []:
                if hasattr(t, "profit"):
                    trades_for_tab.append({
                        "profit": t.profit,
                        "exit_date": getattr(t, "exit_date", None),
                        "profit_pct": getattr(t, "profit_pct", 0.0),
                        "result": "WIN" if t.profit > 0 else "LOSS",
                        "duration": getattr(t, "days_held", 0),
                        "symbol": symbol,
                    })
                elif isinstance(t, dict):
                    trades_for_tab.append({
                        "profit": t.get("profit", 0),
                        "exit_date": t.get("exit_date"),
                        "profit_pct": t.get("profit_pct", 0),
                        "result": "WIN" if t.get("profit", 0) > 0 else "LOSS",
                        "duration": t.get("days_held", t.get("duration", 0)),
                        "symbol": t.get("symbol", symbol),
                    })
        summary = results.get("summary") or {}
        return {
            "trades": trades_for_tab,
            "metrics": summary,
        }

    def backtest_finished(self, results):
        """Backtest tamamlandı"""
        self.backtest_results = results
        self.market_tab.set_backtest_running(False)
        self.market_tab.update_backtest_results(results)

        # Backtest Grafikleri sekmesine veri gönder (state üzerinden)
        graph_payload = self._backtest_results_for_graphs(results)
        self.state_manager.set("backtest_results", graph_payload)

        if "summary" in results:
            summary = results["summary"]
            QMessageBox.information(
                self,
                "Backtest Tamamlandı",
                f"Backtest sonuçları hazır!\n\n"
                f"Test edilen hisse: {summary['total_symbols']}\n"
                f"Toplam işlem: {summary['total_trades']}\n"
                f"Başarı oranı: {summary['win_rate']:.1f}%\n"
                f"Toplam kâr: {summary['total_profit']:,.0f} TL",
            )

        self.backtest_worker = None

    def backtest_error(self, error_message):
        """Backtest hatası"""
        self.market_tab.set_backtest_running(False)

        logging.error(f"Backtest hatası: {error_message}")
        QMessageBox.critical(
            self,
            "Backtest Hatası",
            f"Backtest sırasında hata oluştu:\n\n{error_message}",
        )

        self.backtest_worker = None

    # ========================================================================
    # Ayar Yönetimi (Önceki metodlar aynı)
    # ========================================================================

    def load_settings(self):
        """Ayarları yükle"""
        try:
            self.symbols_tab.load_settings(self.cfg)
            self.criteria_tab.load_settings(self.cfg)
            logging.info("✅ Ayarlar yüklendi")
        except Exception as e:
            logging.error(f"Ayar yükleme hatası: {e}")

    def save_settings(self):
        """Ayarları kaydet"""
        try:
            self.cfg["symbols"] = self.symbols_tab.get_symbols()
            self.cfg["exchange"] = self.symbols_tab.exchange_combo.currentText()
            self.cfg["lookback_bars"] = self.symbols_tab.lookback_spin.value()

            criteria_settings = self.criteria_tab.get_settings()
            self.cfg.update(criteria_settings)

            with open("swing_config.json", "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=2, ensure_ascii=False)

            logging.info("💾 Ayarlar kaydedildi")

        except Exception as e:
            logging.error(f"Ayar kaydetme hatası: {e}")

    def on_exchange_changed(self, exchange):
        """Exchange değiştiğinde"""
        try:
            # cfg güncelle
            self.cfg["exchange"] = exchange
            
            # SmartFilter'ı güncelle
            self.hunter.smart_filter = SmartFilterSystem(self.cfg, exchange=exchange)

            info = self.hunter.smart_filter.get_exchange_info()

            logging.info(f"📊 Exchange değiştirildi: {exchange}")
            logging.info(info)
            
            # MarketAnalyzer cache'ini temizle ve yeniden analiz başlat
            if hasattr(self.hunter, 'market_analyzer') and self.hunter.market_analyzer:
                self.hunter.market_analyzer.clear_cache()
                logging.info(f"🔄 Piyasa analizi cache'i temizlendi ({exchange})")
            
            # Piyasa analizini yeniden başlat
            self.start_market_analysis()

            QMessageBox.information(
                self,
                f"Exchange: {exchange}",
                f"Tarama kriterleri {exchange} için güncellendi:\n\n{info}",
            )

        except Exception as e:
            logging.error(f"Exchange değişim hatası: {e}")
            QMessageBox.warning(self, "Uyarı", f"Exchange ayarları güncellenemedi: {e}")

    # ========================================================================
    # Cleanup
    # ========================================================================

    def closeEvent(self, event):
        """Pencere kapatıldığında"""
        try:
            logging.info("🔄 Pencere kapatılıyor, işlemler durduruluyor...")
            
            # Worker'ları durdur
            if self.scan_worker:
                try:
                    logging.debug("Scan worker durduruluyor...")
                    self.scan_worker.stop()
                except Exception as e:
                    logging.warning(f"Scan worker durdurma hatası: {e}")

            # Thread'leri güvenli şekilde kapat (QThread zaten silinmiş olabilir)
            def safe_thread_stop(thread_obj, name="Thread"):
                if thread_obj is None:
                    return
                try:
                    if hasattr(thread_obj, "isRunning") and thread_obj.isRunning():
                        thread_obj.quit()
                        if not thread_obj.wait(1000):
                            thread_obj.terminate()
                            thread_obj.wait(500)
                except RuntimeError:
                    pass  # QThread zaten silinmiş (deleteLater vb.)
                except Exception:
                    pass

            safe_thread_stop(self.scan_thread, "ScanThread")
            safe_thread_stop(self.backtest_thread, "BacktestThread")
            safe_thread_stop(self.market_thread, "MarketThread")
            
            # WebSocket'i durdur
            try:
                self.stop_websocket()
            except Exception as e:
                logging.warning(f"WebSocket kapatma hatası: {e}")

            # Açık grafikleri kapat
            try:
                self.chart_tab.close_all_charts()
            except Exception as e:
                logging.warning(f"Grafik kapatma hatası: {e}")

            # Ayarları kaydet
            try:
                self.save_settings()
            except Exception as e:
                logging.warning(f"Ayar kaydetme hatası: {e}")

            logging.info("👋 Swing Hunter Advanced kapatılıyor...")
            event.accept()

        except Exception as e:
            logging.error(f"Kapatma hatası: {e}", exc_info=True)
            event.accept()

    # ========================================================================
    # WEBSOCKET VE REAL-TIME VERI IŞLEMLERI (FAZA 3)
    # ========================================================================

    def start_websocket(self):
        """Real-time veri akışını başlat"""
        try:
            symbols = self.symbols_tab.get_symbols()
            
            if not symbols:
                logging.warning("WebSocket için sembol seçilmedi")
                self.notification_manager.send_error_notification(
                    "Lütfen en az bir sembol seçin",
                    context="WebSocket başlatılmadı"
                )
                return
            
            # Önceki worker'ı durdur
            if self.ws_worker:
                self.stop_websocket()
            
            logging.info(f"🔌 WebSocket başlatılıyor: {len(symbols)} sembol...")
            
            # Worker oluştur
            self.ws_worker = WebSocketWorker(symbols, self.cfg)
            self.ws_thread = QThread()
            self.ws_worker.moveToThread(self.ws_thread)
            
            # Sinyalleri bağla
            self.ws_worker.price_updated.connect(self.on_ws_price_updated)
            self.ws_worker.signal_triggered.connect(self.on_ws_signal_triggered)
            self.ws_worker.portfolio_updated.connect(self.on_ws_portfolio_updated)
            self.ws_worker.error_occurred.connect(self.on_ws_error)
            self.ws_worker.connection_status.connect(self.on_ws_connection_status)
            
            # Thread'i başlat
            self.ws_thread.started.connect(self.ws_worker.run)
            self.ws_worker.finished.connect(self.ws_thread.quit)
            
            self.ws_thread.start()
            
            logging.info("✅ WebSocket başlatıldı")
        
        except Exception as e:
            logging.error(f"WebSocket başlatma hatası: {e}")
            self.notification_manager.send_error_notification(
                f"WebSocket başlatılamadı: {str(e)}"
            )

    def stop_websocket(self):
        """Real-time veri akışını durdur"""
        try:
            if not self.ws_worker:
                return
            try:
                logging.info("🛑 WebSocket durduruluyor...")
            except RuntimeError:
                pass
            self.ws_worker.stop()
            if self.ws_thread:
                try:
                    self.ws_thread.quit()
                    self.ws_thread.wait(2000)  # PyQt5: wait(msecs) pozisyonel argüman
                except RuntimeError:
                    pass
            try:
                logging.info("✅ WebSocket durduruldu")
            except RuntimeError:
                pass
        except RuntimeError:
            pass  # Pencere kapanırken Qt objeleri silinmiş olabilir
        except Exception as e:
            try:
                logging.error(f"WebSocket durdurma hatası: {e}")
            except RuntimeError:
                pass

    def on_ws_price_updated(self, symbol: str, price: float, change_pct: float):
        """Canlı fiyat güncellemesi (ticker + açık grafikte canlı fiyat çizgisi)"""
        try:
            if self.price_ticker:
                self.price_ticker.update_price(symbol, price, change_pct)
            if self.chart_tab:
                self.chart_tab.update_live_price_for_symbol(symbol, price)
        except Exception as e:
            logging.error(f"Fiyat güncelleme hatası: {e}")

    def on_ws_signal_triggered(self, signal_data: dict):
        """Real-time sinyal tetiklendiğinde"""
        try:
            symbol = signal_data['symbol']
            action = signal_data['type']
            confidence = signal_data['confidence']
            price = signal_data['price']
            
            self.notification_manager.send_signal_notification(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price
            )
            
            self.state_manager.append_to_list('real_time_signals', signal_data)
            logging.info(f"🎯 {action}: {symbol} @ ₺{price:.2f}")
        
        except Exception as e:
            logging.error(f"Sinyal işleme hatası: {e}")

    def on_ws_portfolio_updated(self, portfolio_state: dict):
        """Portfolio P&L güncelleme"""
        try:
            self.state_manager.set('portfolio_live_pnl', portfolio_state)
            daily_loss_pct = portfolio_state.get('daily_loss_pct', 0)
            
            if daily_loss_pct < -5:
                self.notification_manager.send_risk_alert(
                    f"Portfolio {daily_loss_pct:.2f}% zarar yaptı!"
                )
        
        except Exception as e:
            logging.error(f"Portfolio güncellemesi hatası: {e}")

    def on_ws_connection_status(self, connected: bool):
        """Bağlantı durumu"""
        try:
            if self.price_ticker:
                self.price_ticker.set_connection_status(connected)
            
            self.notification_manager.send_connection_alert(connected)
        
        except Exception as e:
            logging.error(f"Bağlantı durumu hatası: {e}")

    def on_ws_error(self, error_msg: str):
        """WebSocket hatası"""
        try:
            logging.error(f"WebSocket hatası: {error_msg}")
            self.notification_manager.send_error_notification(error_msg)
        
        except Exception as e:
            logging.error(f"Hata işleme hatası: {e}")

    def show_toast_notification(self, notification_data: dict):
        """Bildirimi göster"""
        try:
            title = notification_data.get('title', 'Bildirim')
            message = notification_data.get('message', '')
            level = notification_data.get('level', 'info')
            
            emoji = {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌'
            }.get(level, '📢')
            
            logging.info(f"{emoji} {title}: {message}")
        
        except Exception as e:
            logging.error(f"Toast hatası: {e}")
