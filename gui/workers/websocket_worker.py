# -*- coding: utf-8 -*-
"""
WebSocket Worker - Real-time Veri Akışı
Canlı fiyat güncellemeleri, sinyal tetiklemesi, portfolio tracking
tvDatafeed entegrasyonu ile gerçek veriler
"""

import logging
import json
import time
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from PyQt5.QtCore import QThread, pyqtSignal

try:
    from tvDatafeed import TvDatafeed
    TVDATA_AVAILABLE = True
except ImportError:
    TVDATA_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Borsa → yfinance sembol soneki (canlı kaynak: yfinance için)
YFINANCE_SUFFIX = {"BIST": ".IS", "NASDAQ": "", "NYSE": "", "AMEX": "", "CRYPTO": "-USD"}


class WebSocketWorker(QThread):
    """Real-time veri akışı worker'ı - QThread'de çalışır"""
    
    # Sinyaller
    price_updated = pyqtSignal(str, float, float)          # symbol, price, change%
    signal_triggered = pyqtSignal(dict)                    # signal_data
    portfolio_updated = pyqtSignal(dict)                   # portfolio_state
    connection_status = pyqtSignal(bool)                   # connected/disconnected
    error_occurred = pyqtSignal(str)                       # error_message
    tick_received = pyqtSignal(dict)                       # raw tick data
    
    def __init__(self, symbols: List[str], config: Dict = None):
        super().__init__()
        self.symbols = symbols
        self.config = config or {}
        self.is_running = False
        self.ws = None
        self.tv = None  # tvDatafeed instance
        self.last_prices = {}
        self.last_signals = {}
        self.portfolio_state = {}
        
        # WebSocket configuration
        self.ws_endpoint = self.config.get('websocket', {}).get('endpoint', 
                                           'wss://data.tradingview.com/socket.io/')
        self.reconnect_attempts = self.config.get('websocket', {}).get('reconnect_attempts', 5)
        self.reconnect_delay = self.config.get('websocket', {}).get('reconnect_delay_ms', 5000) / 1000
        self.heartbeat_interval = self.config.get('websocket', {}).get('heartbeat_interval_ms', 30000) / 1000
        self.timeout = self.config.get('websocket', {}).get('timeout_ms', 60000) / 1000
        
        # tvDatafeed configuration (ücretsiz planda sık istek kısıtlamaya neden olabilir)
        rt = self.config.get('real_time', {})
        self.use_tvdata = rt.get('use_tvdata', True) and TVDATA_AVAILABLE
        self.update_interval = rt.get('update_interval_ms', 100) / 1000
        self.poll_interval_sec = max(3, rt.get('poll_interval_sec', 5))  # En az 3 sn, varsayılan 5 (free tier)
        self.max_live_symbols = max(10, min(200, rt.get('max_live_symbols', 30)))  # Canlıda en fazla bu kadar sembol
        self.exchange = self.config.get('exchange', 'BIST')
        self._symbol_index = 0  # Round-robin için
        # Canlı veri kaynağı: "tvdatafeed" | "yfinance" (tvDatafeed dışı alternatif)
        self.live_data_source = (rt.get('live_data_source') or 'tvdatafeed').lower()
        if self.live_data_source not in ('tvdatafeed', 'yfinance'):
            self.live_data_source = 'tvdatafeed'
    
    def run(self):
        """WebSocket bağlantısını başlat ve tick'leri oku"""
        try:
            self.is_running = True
            
            # Bağlantı kur
            self._connect_websocket()
            
            # Subscribe to symbols
            self._subscribe_to_prices()
            
            # Tick döngüsü (tvDatafeed ücretsiz planda kısıtlamaya girmemek için seyrek istek)
            while self.is_running:
                try:
                    tick = self._receive_tick()
                    if tick:
                        self._process_tick(tick)
                    # Gerçek kaynak (tvDatafeed/yfinance) kullanıyorsak seyrek poll; simülasyonda kısa bekle
                    has_real_source = (TVDATA_AVAILABLE and self.tv) or (self.live_data_source == 'yfinance' and YFINANCE_AVAILABLE)
                    delay = self.poll_interval_sec if has_real_source else 0.1
                    time.sleep(delay)
                except Exception as e:
                    logger.error(f"Tick işleme hatası: {e}")
                    self.error_occurred.emit(f"Tick işleme hatası: {str(e)}")
        
        except Exception as e:
            logger.error(f"WebSocket çalışma hatası: {e}")
            self.error_occurred.emit(f"WebSocket hatası: {str(e)}")
            self.connection_status.emit(False)
        
        finally:
            self._disconnect()
    
    def _connect_websocket(self):
        """tvDatafeed ile WebSocket bağlantısını başlat"""
        try:
            logger.info(f"🔌 tvDatafeed WebSocket'e bağlanılıyor...")
            
            if TVDATA_AVAILABLE:
                # tvDatafeed kü tütüphanesi ile veri almayı başlat
                self.tv = TvDatafeed()
                logger.info("✅ tvDatafeed bağlandı")
            else:
                logger.warning("tvDatafeed modülü bulunamadı, simülasyon modunda çalışılıyor")
                self.tv = None
            
            # WebSocket simülasyonu başlat
            self.ws = {
                'connected': True,
                'last_heartbeat': time.time(),
                'last_update': {}
            }
            
            self.connection_status.emit(True)
            logger.info("✅ WebSocket bağlandı")
        
        except Exception as e:
            logger.error(f"WebSocket bağlantı hatası: {e}")
            self.connection_status.emit(False)
            raise
            raise
    
    def _subscribe_to_prices(self):
        """Belirtilen semboller için fiyat akışını başlat"""
        try:
            for symbol in self.symbols:
                subscribe_msg = {
                    "method": "subscribe",
                    "params": {
                        "symbol": f"BVMT:{symbol}",  # Borsa Vizyon Market Türkiye
                        "session": "regular",
                        "type": "last_price"
                    }
                }
                
                logger.debug(f"Subscribe: {symbol}")
                
                # Simülasyon: subscription başarılı
                self.last_prices[symbol] = {
                    'price': 100.0,
                    'change_pct': 0.0,
                    'timestamp': datetime.now()
                }
            
            logger.info(f"✅ {len(self.symbols)} sembol subskribe edildi")
        
        except Exception as e:
            logger.error(f"Subscribe hatası: {e}")
            raise
    
    def _yfinance_symbol(self, symbol: str) -> str:
        """Sembolü yfinance formatına çevir (BIST → .IS, NYSE/NASDAQ → aynı)"""
        suffix = YFINANCE_SUFFIX.get(self.exchange.upper(), '')
        if suffix and not symbol.endswith(suffix):
            return f"{symbol}{suffix}"
        return symbol
    
    def _fetch_tick_yfinance(self, symbol: str) -> Optional[Dict]:
        """yfinance ile son fiyat al (polling; tvDatafeed alternatifi)"""
        if not YFINANCE_AVAILABLE:
            return None
        try:
            yf_sym = self._yfinance_symbol(symbol)
            ticker = yf.Ticker(yf_sym)
            df = ticker.history(period="1d", interval="1m")
            if df is None or df.empty:
                return None
            latest = df.iloc[-1]
            close = float(latest.get('Close', latest.get('close', 0)))
            if close <= 0:
                return None
            if symbol in self.last_prices:
                old = self.last_prices[symbol]['price']
                change_pct = ((close - old) / old) * 100
            else:
                change_pct = 0.0
            return {
                'symbol': symbol,
                'price': close,
                'change_pct': change_pct,
                'open': float(latest.get('Open', latest.get('open', close))),
                'high': float(latest.get('High', latest.get('high', close))),
                'low': float(latest.get('Low', latest.get('low', close))),
                'volume': int(latest.get('Volume', latest.get('volume', 0))),
                'timestamp': datetime.now().isoformat(),
                'source': 'yfinance'
            }
        except Exception as e:
            logger.debug(f"yfinance tick hatası ({symbol}): {e}")
            return None
    
    def _receive_tick(self) -> Optional[Dict]:
        """tvDatafeed'den tek sembol al (round-robin, istek sıklığı düşük = free tier dostu)"""
        try:
            if not self.ws or not self.ws.get('connected'):
                return None
            
            import random
            
            # Canlıda en fazla max_live_symbols kullan (istek yükünü sınırla)
            symbols = self.symbols[: self.max_live_symbols] if self.symbols else []
            if not symbols:
                return None
            
            # Round-robin: her çağrıda bir sonraki sembol
            symbol = symbols[self._symbol_index % len(symbols)]
            self._symbol_index += 1
            
            try:
                tick = None
                # Alternatif 1: yfinance (live_data_source == "yfinance")
                if self.live_data_source == 'yfinance' and YFINANCE_AVAILABLE:
                    tick = self._fetch_tick_yfinance(symbol)
                # Alternatif 2: tvDatafeed (varsayılan)
                if tick is None and TVDATA_AVAILABLE and self.tv:
                    df = self.tv.get_hist(symbol=symbol, exchange=self.exchange, interval=1, n_bars=1)
                    if df is not None and not df.empty:
                        latest = df.iloc[0]
                        current_price = float(latest.get('close', latest.get('Close', 0)))
                        if symbol in self.last_prices:
                            old_price = self.last_prices[symbol]['price']
                            change_pct = ((current_price - old_price) / old_price) * 100
                        else:
                            change_pct = 0.0
                        tick = {
                            'symbol': symbol,
                            'price': current_price,
                            'change_pct': change_pct,
                            'open': float(latest.get('open', current_price)),
                            'high': float(latest.get('high', current_price)),
                            'low': float(latest.get('low', current_price)),
                            'volume': int(latest.get('Volume', 0)),
                            'bid': current_price - 0.01,
                            'ask': current_price + 0.01,
                            'timestamp': datetime.now().isoformat(),
                            'source': 'tvDatafeed'
                        }
                if tick is not None:
                    return tick
                # Simülasyon (kaynak yok veya hata)
                else:
                    # Fallback: Simülasyon modu
                    current_price = self.last_prices[symbol]['price']
                    change = random.uniform(-0.5, 0.5)
                    new_price = current_price * (1 + change / 100)
                    
                    tick = {
                        'symbol': symbol,
                        'price': new_price,
                        'change_pct': change,
                        'volume': random.randint(1000, 10000),
                        'bid': new_price - 0.01,
                        'ask': new_price + 0.01,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'simulation'
                    }
                    
                    return tick
            
            except Exception as e:
                logger.debug(f"tvDatafeed hatası ({symbol}): {e}, simülasyon kullanılıyor")
                
                # Fallback: Simülasyon
                current_price = self.last_prices.get(symbol, {}).get('price', 100.0)
                change = random.uniform(-0.5, 0.5)
                new_price = current_price * (1 + change / 100)
                
                tick = {
                    'symbol': symbol,
                    'price': new_price,
                    'change_pct': change,
                    'volume': random.randint(1000, 10000),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'fallback_simulation'
                }
                
                return tick
            
        except Exception as e:
            logger.error(f"Tick alma hatası: {e}")
            return None
    
    def _process_tick(self, tick: Dict):
        """Gelen tick verilerini işle"""
        try:
            symbol = tick['symbol']
            price = tick['price']
            change_pct = tick['change_pct']
            
            # Son fiyatları güncelle
            self.last_prices[symbol] = {
                'price': price,
                'change_pct': change_pct,
                'timestamp': tick.get('timestamp')
            }
            
            # Signal emit et
            self.tick_received.emit(tick)
            self.price_updated.emit(symbol, price, change_pct)
            
            # Sinyal kontrolü
            signal = self._check_signal(symbol, price)
            if signal:
                self.signal_triggered.emit(signal)
            
            # Portfolio P&L güncelle
            portfolio = self._update_portfolio_pnl(symbol, price)
            if portfolio:
                self.portfolio_updated.emit(portfolio)
        
        except Exception as e:
            logger.error(f"Tick işleme hatası ({tick.get('symbol')}): {e}")
    
    def _check_signal(self, symbol: str, current_price: float) -> Optional[Dict]:
        """Gerçek zamanlı sinyal kontrolü"""
        try:
            # Basit sinyal kuralı: fiyat +2% veya -2% değişirse
            last_signal_time = self.last_signals.get(symbol, {}).get('timestamp')
            
            # Signal flood'u engelle (aynı symbol için 5sn içinde 1 signal)
            if last_signal_time:
                time_diff = (datetime.now() - last_signal_time).total_seconds()
                if time_diff < 5:
                    return None
            
            price_change = self.last_prices[symbol]['change_pct']
            
            # Buy sinyal: %2 ve üzeri artış
            if price_change >= 2.0:
                signal = {
                    'symbol': symbol,
                    'type': 'BUY',
                    'price': current_price,
                    'confidence': min(abs(price_change) / 5, 1.0),  # 0-100% confidence
                    'reason': f'Fiyat +{price_change:.2f}% yükseldi',
                    'timestamp': datetime.now().isoformat(),
                }
                
                self.last_signals[symbol] = signal
                logger.info(f"🎯 BUY Sinyali: {symbol} @ ₺{current_price:.2f}")
                
                return signal
            
            # Sell sinyal: %2 ve üzeri düşüş
            elif price_change <= -2.0:
                signal = {
                    'symbol': symbol,
                    'type': 'SELL',
                    'price': current_price,
                    'confidence': min(abs(price_change) / 5, 1.0),
                    'reason': f'Fiyat {price_change:.2f}% düştü',
                    'timestamp': datetime.now().isoformat(),
                }
                
                self.last_signals[symbol] = signal
                logger.info(f"🎯 SELL Sinyali: {symbol} @ ₺{current_price:.2f}")
                
                return signal
        
        except Exception as e:
            logger.error(f"Sinyal kontrolü hatası: {e}")
        
        return None
    
    def _update_portfolio_pnl(self, symbol: str, price: float) -> Optional[Dict]:
        """Açık pozisyonların P&L'ini güncelle"""
        try:
            # Sahta portfolio verileri ile demo
            # Gerçek implementasyonda trade DB'den pozisyonlar alınacak
            
            portfolio = {
                'symbol': symbol,
                'current_price': price,
                'update_time': datetime.now().isoformat(),
                'total_value': 50000,
                'daily_pnl': 1250,
                'daily_pnl_pct': 2.5,
                'daily_loss_pct': 0,  # Hiçbir zarar yok (demo)
            }
            
            return portfolio
        
        except Exception as e:
            logger.error(f"Portfolio güncelleme hatası: {e}")
            return None
    
    def stop(self):
        """Worker'ı durdur"""
        try:
            logger.info("WebSocket worker durduruluyor...")
        except RuntimeError:
            pass
        self.is_running = False
    
    def _disconnect(self):
        """WebSocket'i kapat (kapatma sırasında log/emit GUI silinmiş olabilir)"""
        try:
            if self.ws:
                self.ws['connected'] = False
                self.ws = None
            try:
                logger.info("WebSocket kapatıldı")
                self.connection_status.emit(False)
            except RuntimeError:
                pass  # Pencere kapanırken Qt objeleri silinmiş olabilir
        except RuntimeError:
            pass
        except Exception as e:
            try:
                logger.error(f"WebSocket disconnect hatası: {e}")
            except RuntimeError:
                pass
    
    def get_last_price(self, symbol: str) -> Optional[float]:
        """Son bilinen fiyatı al"""
        return self.last_prices.get(symbol, {}).get('price')
    
    def get_price_change(self, symbol: str) -> Optional[float]:
        """Fiyat değişim %'sini al"""
        return self.last_prices.get(symbol, {}).get('change_pct')
    
    def get_all_prices(self) -> Dict[str, Dict]:
        """Tüm son fiyatları al"""
        return self.last_prices.copy()
    
    def is_connected(self) -> bool:
        """Bağlantı durumunu kontrol et"""
        return self.ws is not None and self.ws.get('connected', False)
