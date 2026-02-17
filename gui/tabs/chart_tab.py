# -*- coding: utf-8 -*-
"""
Chart Tab - Mevcut chart_widget.py ile entegre grafik sekmesi
"""
import logging
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from tvDatafeed import Interval

# Mevcut chart widget'ı kullan
from ..chart_widget import SwingTradeChart


class ChartTab(QWidget):
    """Grafik sekmesi - Mevcut chart_widget entegrasyonu"""

    chart_opened = pyqtSignal(object)  # Grafik penceresi açıldığında

    def __init__(self, tv_datafeed, cfg, parent=None):
        super().__init__(parent)
        self.tv = tv_datafeed
        self.cfg = cfg
        self.open_charts = []  # Açık grafik pencereleri
        self.init_ui()

    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)

        # Başlık
        self.chart_title = QLabel("📊 Hisse Grafiği")
        self.chart_title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; padding: 10px; "
            "background-color: #e3f2fd; border-radius: 4px;"
        )
        self.chart_title.setAlignment(Qt.AlignCenter)

        # Info label
        self.info_label = QLabel(
            "ℹ️ Grafikleri açmak için:\n\n"
            "• Sol panelden bir hisse seçin\n"
            "• Veya Sonuçlar sekmesinden bir satıra tıklayın\n\n"
            "Grafikler ayrı pencerede açılacaktır."
        )
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet(
            "font-size: 11pt; padding: 30px; "
            "background-color: #f5f5f5; border-radius: 8px; "
            "color: #666;"
        )

        layout.addWidget(self.chart_title)
        layout.addWidget(self.info_label, 1)

    def show_chart(self, symbol, trade_info=None):
        """
        Grafik göster - Mevcut SwingTradeChart kullanır

        Args:
            symbol: Hisse sembolü
            trade_info: Trade bilgileri (dict veya None)
        """
        try:
            # Veri çek - CRYPTO kontrolü
            exchange = self.cfg.get("exchange", "BIST")
            
            if exchange == "CRYPTO":
                try:
                    import yfinance as yf
                    logging.info(f"⚡ Grafikte kripto veri: {symbol} (yfinance)")
                    ticker = yf.Ticker(f"{symbol}-USD")
                    df = ticker.history(period="1y", interval="1d")
                    
                    if df is not None:
                        # Sütun isimlerini tvDatafeed uyumlu hale getir
                        df = df.rename(columns={
                            'Open': 'open',
                            'High': 'high',
                            'Low': 'low',
                            'Close': 'close',
                            'Volume': 'volume'
                        })
                        # Gerekli sütunları al
                        cols = ['open', 'high', 'low', 'close', 'volume']
                        df = df[[c for c in cols if c in df.columns]]
                        
                        # TA-Lib için veri tiplerini float'a zorla (ÖNEMLİ DÜZELTME)
                        for col in cols:
                            if col in df.columns:
                                df[col] = df[col].astype(float)
                        
                except Exception as e:
                    logging.error(f"Grafik yfinance hatası: {e}")
                    df = None
            else:
                # Normal veri çekme - tvDatafeed ile, timeout hatası durumunda yfinance fallback
                df = None
                try:
                    logging.debug(f"📡 tvDatafeed ile veri çekiliyor: {symbol}")
                    df = self.tv.get_hist(
                        symbol=symbol,
                        exchange=exchange,
                        interval=Interval.in_daily,
                        n_bars=self.cfg.get("lookback_bars", 250),
                    )
                except (TimeoutError, ConnectionError, Exception) as e:
                    logging.warning(f"⚠️ tvDatafeed hatası ({symbol}): {type(e).__name__} - Fallback: yfinance")
                    
                    # Fallback: yfinance kullan
                    try:
                        import yfinance as yf
                        
                        # Sembol formatını düzelt (BIST .IS suffix ekleme)
                        yf_symbol = symbol
                        if exchange == "BIST" and not symbol.endswith(".IS"):
                            yf_symbol = f"{symbol}.IS"
                        
                        logging.debug(f"🔄 yfinance ile deneniyor: {yf_symbol}")
                        ticker = yf.Ticker(yf_symbol)
                        df = ticker.history(period="1y", interval="1d")
                        
                        if df is not None and len(df) > 0:
                            # Sütun isimlerini tvDatafeed uyumlu hale getir
                            df = df.rename(columns={
                                'Open': 'open',
                                'High': 'high',
                                'Low': 'low',
                                'Close': 'close',
                                'Volume': 'volume'
                            })
                            # Gerekli sütunları al
                            cols = ['open', 'high', 'low', 'close', 'volume']
                            df = df[[c for c in cols if c in df.columns]]
                            
                            # Veri tiplerini kontrol et
                            for col in cols:
                                if col in df.columns:
                                    df[col] = pd.to_numeric(df[col], errors='coerce')
                            
                            logging.info(f"✅ yfinance fallback başarılı: {symbol} ({len(df)} gün)")
                        else:
                            df = None
                    except Exception as fallback_error:
                        logging.error(f"❌ yfinance fallback da başarısız ({symbol}): {fallback_error}")
                        df = None

            if df is None or len(df) < 30:
                self.chart_title.setText(f"❌ {symbol}: Yetersiz veri")
                QMessageBox.warning(
                    self,
                    "Uyarı",
                    f"{symbol} için yeterli veri bulunamadı.\n\n"
                    "En az 30 günlük veri gereklidir.",
                )
                return None

            # İndikatörleri hesapla
            from indicators.ta_manager import calculate_indicators

            df = calculate_indicators(df)

            # Trade info yoksa, varsayılan bilgileri topla
            if trade_info is None:
                trade_info = self._collect_default_trade_info(df)

            # MEVCUT chart_widget.py'yi kullan (exchange-aware)
            exchange = self.cfg.get("exchange", "BIST")
            chart_window = SwingTradeChart(df, symbol, trade_info, exchange=exchange)
            chart_window.show()

            # Referansı sakla (garbage collection'dan koru)
            self.open_charts.append(chart_window)

            # Başlığı güncelle
            self.chart_title.setText(f"✅ {symbol} grafiği açıldı")

            # Sinyal gönder
            self.chart_opened.emit(chart_window)

            logging.info(f"✅ {symbol} grafiği açıldı")
            return chart_window

        except TimeoutError as e:
            logging.error(f"⏱️ Grafik timeout hatası {symbol}: Bağlantı zaman aşımına uğradı")
            self.chart_title.setText(f"⏱️ {symbol}: Timeout")
            QMessageBox.warning(
                self, "Bağlantı Timeout", 
                f"{symbol} grafiği açılamadı.\n\n"
                "Sebep: TradingView bağlantısı zaman aşımına uğradı.\n\n"
                "Çözüm:\n"
                "• İnternet bağlantınızı kontrol edin\n"
                "• Birkaç saniye sonra tekrar deneyin\n"
                "• yfinance fallback otomatik olarak kullanılmıştır"
            )
            return None
        except ConnectionError as e:
            logging.error(f"🔌 Grafik bağlantı hatası {symbol}: {e}")
            self.chart_title.setText(f"🔌 {symbol}: Bağlantı Hatası")
            QMessageBox.warning(
                self, "Bağlantı Hatası", 
                f"{symbol} grafiği açılamadı.\n\n"
                "Sebep: İnternet bağlantısı kaybı veya sunucu hatası\n\n"
                "Çözüm:\n"
                "• İnternet bağlantınızı kontrol edin\n"
                "• Firewall/VPN ayarlarını kontrol edin\n"
                "• Tekrar deneyin"
            )
            return None
        except Exception as e:
            logging.error(f"❌ Grafik açma hatası {symbol}: {type(e).__name__}: {e}", exc_info=True)
            self.chart_title.setText(f"❌ {symbol}: Hata")
            
            # Hata türüne göre mesaj
            error_msg = str(e)
            if "SSL" in error_msg or "certificate" in error_msg.lower():
                detailed_msg = (
                    f"{symbol} grafiği açılamadı.\n\n"
                    "Sebep: SSL/Sertifika hatası\n\n"
                    "Çözüm:\n"
                    "• Windows sertifika deposu güncelleyin\n"
                    "• VPN kullanıyorsanız devre dışı bırakın\n"
                    "• Firewall ayarlarını kontrol edin"
                )
            else:
                detailed_msg = (
                    f"{symbol} grafiği açılamadı.\n\n"
                    f"Teknik hata: {type(e).__name__}\n\n"
                    "Çözüm: Birkaç saniye sonra tekrar deneyin"
                )
            
            QMessageBox.critical(self, "Grafik Hatası", detailed_msg)
            return None

    def _collect_default_trade_info(self, df):
        """Varsayılan trade bilgilerini topla"""
        trade_info = {}

        try:
            # Pattern analizi
            from patterns.price_action import PriceActionDetector

            pattern_detector = PriceActionDetector()
            patterns = pattern_detector.analyze_patterns(df)
            trade_info["patterns"] = patterns

            # Konsolidasyon
            from analysis.consolidation import detect_consolidation_pattern

            consolidation = detect_consolidation_pattern(df)
            trade_info["consolidation"] = consolidation.__dict__

            # Fibonacci
            from analysis.fibonacci import calculate_fibonacci_levels

            fib = calculate_fibonacci_levels(df)
            trade_info["fibonacci"] = fib

            # Support/Resistance
            from analysis.support_resistance import SupportResistanceFinder

            sr_finder = SupportResistanceFinder()
            sr_levels = sr_finder.find_levels(df)
            trade_info["sr_levels"] = sr_levels

            breakout_info = sr_finder.check_breakout(df, sr_levels)
            trade_info["breakout_info"] = breakout_info

            # Varsayılan trade seviyeleri
            latest = df.iloc[-1]
            trade_info["stop_loss"] = latest["close"] * 0.95
            trade_info["target1"] = latest["close"] * 1.10

        except Exception as e:
            logging.error(f"Trade info toplama hatası: {e}")
            # Minimal trade info
            latest = df.iloc[-1]
            trade_info = {
                "stop_loss": latest["close"] * 0.95,
                "target1": latest["close"] * 1.10,
            }

        return trade_info

    def show_chart_with_details(self, symbol, entry_price, stop_loss, target1):
        """
        Detaylı trade bilgileriyle grafik göster

        Args:
            symbol: Hisse sembolü
            entry_price: Giriş fiyatı
            stop_loss: Stop loss
            target1: Hedef 1
        """
        try:
            # Veri çek
            df = self.tv.get_hist(
                symbol=symbol,
                exchange=self.cfg.get("exchange", "BIST"),
                interval=Interval.in_daily,
                n_bars=self.cfg.get("lookback_bars", 250),
            )

            if df is None or len(df) < 30:
                return None

            # İndikatörleri hesapla
            from indicators.ta_manager import calculate_indicators

            df = calculate_indicators(df)

            # Trade bilgilerini topla ve entry/stop/target ekle
            trade_info = self._collect_default_trade_info(df)
            trade_info.update(
                {
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "target1": target1,
                    "target_price": target1,  # Alternatif isim
                }
            )

            # Grafik aç
            return self.show_chart(symbol, trade_info)

        except Exception as e:
            logging.error(f"Detaylı grafik hatası {symbol}: {e}")
            return None

    def update_live_price_for_symbol(self, symbol: str, price: float):
        """Açık grafiklerden sembole ait olanlarda canlı fiyat çizgisini günceller (Seçenek C)"""
        for w in self.open_charts:
            try:
                if w and getattr(w, "symbol", None) == symbol and getattr(w, "isVisible", lambda: False)():
                    if hasattr(w, "update_live_price"):
                        w.update_live_price(price)
                    break
            except Exception:
                pass

    def close_all_charts(self):
        """Tüm açık grafikleri kapat"""
        for chart_window in self.open_charts:
            try:
                if chart_window and hasattr(chart_window, "close"):
                    chart_window.close()
            except Exception:
                pass

        self.open_charts.clear()
        self.chart_title.setText("📊 Hisse Grafiği")
        logging.info("Tüm grafikler kapatıldı")

    def get_open_charts_count(self):
        """Açık grafik sayısı"""
        # Garbage collected pencereleri temizle
        self.open_charts = [
            w for w in self.open_charts if w and hasattr(w, "isVisible")
        ]
        return len(self.open_charts)
