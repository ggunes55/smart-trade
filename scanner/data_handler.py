# -*- coding: utf-8 -*-
"""
Data Handler - Veri çekme ve cache yönetimi
YENİ: yfinance fallback desteği eklendi
"""
import logging
import time
import random
import threading
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd

# Primary provider
from tvDatafeed import TvDatafeed, Interval

# Fallback provider
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
    logging.info("✅ yfinance fallback provider yüklü")
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("⚠️ yfinance yüklü değil. Fallback devre dışı. 'pip install yfinance' ile yükleyin.")

from cache.data_cache import DataCache


from core.types import IDataProvider

class DataHandler(IDataProvider):
    """Veri çekme ve cache yönetimi - yfinance fallback destekli"""
    def fetch_data(self, symbol: str, start: str, end: str):
        """IDataProvider interface'i için veri çekme metodu"""
        # start ve end parametreleri ile uyumlu veri çekme
        # Günlük veri çekimi örneği
        n_bars = self.cfg.get("lookback_bars", 250)
        interval = Interval.in_daily
        # start ve end parametreleri ile n_bars hesaplanabilir
        # Basit örnek: sadece n_bars kullanılıyor
        return self.safe_api_call(symbol, self.cfg.get("exchange", "BIST"), interval, n_bars)

    # Exchange'e göre yfinance symbol suffix mapping
    YFINANCE_SUFFIX = {
        'BIST': '.IS',      # BIST hisseleri için Istanbul suffix
        'NASDAQ': '',       # US hisseleri için suffix yok
        'NYSE': '',         # US hisseleri için suffix yok
        'AMEX': '',         # US hisseleri için suffix yok
        'CRYPTO': '-USD',   # Kripto sembolleri için USD suffix (örn: BTC-USD)
    }

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.tv = TvDatafeed()
        self.data_cache = DataCache(
            cache_dir=cfg.get("cache_dir", "data_cache"),
            ttl_hours=cfg.get("cache_ttl_hours", 1),
        )
        self.use_fallback = cfg.get("use_yfinance_fallback", True)
        self.tvdata_fail_count = 0  # Ardışık başarısızlık sayacı

    def _convert_to_yfinance_symbol(self, symbol: str, exchange: str) -> str:
        """Sembolü yfinance formatına çevir"""
        suffix = self.YFINANCE_SUFFIX.get(exchange.upper(), '')
        
        # Eğer symbol zaten suffix ile bitiyorsa tekrar ekleme (örn: BTC-USD-USD olmasın)
        if suffix and symbol.endswith(suffix):
            return symbol
            
        return f"{symbol}{suffix}"

    def _yfinance_fallback(
        self, symbol: str, exchange: str, interval: str, n_bars: int
    ) -> Optional[pd.DataFrame]:
        """
        yfinance ile veri çekme - fallback provider
        
        Args:
            symbol: Hisse sembolü
            exchange: Borsa
            interval: 'daily' veya 'weekly'
            n_bars: İstenen bar sayısı
        
        Returns:
            DataFrame veya None
        """
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            yf_symbol = self._convert_to_yfinance_symbol(symbol, exchange)
            
            # Interval'a göre period ve interval belirleme
            if interval == 'weekly':
                period = f"{max(n_bars * 7, 365)}d"
                yf_interval = "1wk"
            else:  # daily
                period = f"{max(n_bars, 365)}d"
                yf_interval = "1d"
            
            logging.debug(f"yfinance fallback: {yf_symbol} ({yf_interval}, period={period})")
            
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=yf_interval)
            
            if df is None or df.empty:
                logging.debug(f"yfinance boş veri: {yf_symbol}")
                return None
            
            # Sütun isimlerini tvDatafeed formatına çevir
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Sadece gerekli sütunları al
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in required_cols if col in df.columns]]
            
            # Son n_bars kadar veri al
            if len(df) > n_bars:
                df = df.tail(n_bars)
            
            logging.info(f"✅ yfinance başarılı: {yf_symbol} ({len(df)} bar)")
            return df
            
        except Exception as e:
            logging.debug(f"yfinance hatası {symbol}: {type(e).__name__}: {e}")
            return None

    def safe_api_call(
        self, symbol: str, exchange: str, interval: Interval, n_bars: int, timeout: int = 10
    ) -> Optional[pd.DataFrame]:
        """
        Güvenli API çağrısı - cache, retry ve yfinance fallback destekli

        Args:
            symbol: Hisse sembolü
            exchange: Borsa
            interval: Zaman dilimi (Interval enum)
            n_bars: Bar sayısı
            timeout: Timeout süresi (saniye)

        Returns:
            DataFrame veya None
        """
        # Cache kontrolü
        cache_key = self._get_cache_key(interval)
        cached = self.data_cache.get(symbol, cache_key, n_bars)
        if cached is not None:
            logging.debug(f"Cache hit: {symbol}")
            return cached

        # 1. tvDatafeed ile dene (CRYPTO hariç)
        # Kripto için direkt yfinance kullan çünkü tvdatafeed kripto verilerinde yavaş kalabiliyor
        if exchange != 'CRYPTO':
            data = self._try_tvdatafeed(symbol, exchange, interval, n_bars, timeout)
            
            if data is not None:
                self.tvdata_fail_count = 0  # Başarılıysa sayacı sıfırla
                self.data_cache.set(symbol, cache_key, n_bars, data)
                return data
        else:
             logging.info(f"⚡ {symbol}: Kripto varlık, doğrudan yfinance kullanılıyor...")
        
        # 2. tvDatafeed başarısız - yfinance fallback
        self.tvdata_fail_count += 1
        
        if self.use_fallback and YFINANCE_AVAILABLE:
            interval_str = 'weekly' if interval == Interval.in_weekly else 'daily'
            logging.info(f"🔄 {symbol}: tvDatafeed başarısız, yfinance deneniyor...")
            
            data = self._yfinance_fallback(symbol, exchange, interval_str, n_bars)
            
            if data is not None:
                self.data_cache.set(symbol, cache_key, n_bars, data)
                return data
            
            logging.warning(f"❌ {symbol}: Her iki provider da başarısız")
        else:
            if not YFINANCE_AVAILABLE:
                logging.warning(f"⚠️ {symbol}: tvDatafeed başarısız, yfinance yüklü değil")
        
        return None

    def _try_tvdatafeed(
        self, symbol: str, exchange: str, interval: Interval, n_bars: int, timeout: int
    ) -> Optional[pd.DataFrame]:
        """tvDatafeed ile veri çekmeyi dene"""
        start_time = time.time()
        
        for attempt in range(2):  # 2 deneme
            try:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    return None

                if attempt == 0:
                    time.sleep(random.uniform(0.1, 0.2))

                result_container = {"data": None, "error": None, "done": False}
                
                def api_call():
                    try:
                        result_container["data"] = self.tv.get_hist(
                            symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars
                        )
                    except Exception as e:
                        result_container["error"] = e
                    finally:
                        result_container["done"] = True
                
                api_thread = threading.Thread(target=api_call, daemon=True)
                api_thread.start()
                api_thread.join(timeout=timeout - elapsed)
                
                if not result_container["done"]:
                    continue
                
                if result_container["error"]:
                    raise result_container["error"]
                
                data = result_container["data"]
                
                if data is not None and not data.empty:
                    logging.debug(f"tvDatafeed başarılı: {symbol} ({len(data)} bar)")
                    return data

            except Exception as e:
                if attempt == 1:
                    logging.debug(f"tvDatafeed hatası {symbol}: {type(e).__name__}")
                else:
                    time.sleep(0.3)

        return None

    def get_daily_data(
        self, symbol: str, exchange: str, n_bars: int = None, timeout: int = 10
    ) -> Optional[pd.DataFrame]:
        """Günlük veri çek"""
        if n_bars is None:
            n_bars = self.cfg.get("lookback_bars", 250)

        return self.safe_api_call(symbol, exchange, Interval.in_daily, n_bars, timeout=timeout)

    def get_weekly_data(
        self, symbol: str, exchange: str, n_bars: int = 52
    ) -> Optional[pd.DataFrame]:
        """Haftalık veri çek"""
        return self.safe_api_call(symbol, exchange, Interval.in_weekly, n_bars)

    def get_multi_timeframe_data(
        self, symbol: str, exchange: str
    ) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Çoklu zaman dilimi verisi çek

        Returns:
            (daily_df, weekly_df) tuple
        """
        daily = self.get_daily_data(symbol, exchange)
        weekly = self.get_weekly_data(symbol, exchange)

        return daily, weekly

    def _get_cache_key(self, interval: Interval) -> str:
        """Interval'dan cache key oluştur"""
        if isinstance(interval, str):
            return interval
        return str(interval)

    def clear_cache(self):
        """Cache'i temizle"""
        try:
            self.data_cache.clear_cache()
            logging.info("✅ Cache temizlendi")
        except Exception as e:
            logging.error(f"Cache temizleme hatası: {e}")

    def get_cache_stats(self) -> dict:
        """Cache istatistikleri"""
        return {
            "cache_dir": self.data_cache.cache_dir,
            "ttl_hours": self.cfg.get("cache_ttl_hours", 1),
            "yfinance_available": YFINANCE_AVAILABLE,
            "use_fallback": self.use_fallback,
            "tvdata_fail_count": self.tvdata_fail_count,
        }
    
    def test_providers(self, symbol: str = "GARAN", exchange: str = "BIST") -> dict:
        """Provider'ları test et - Debug için"""
        results = {"tvdatafeed": False, "yfinance": False}
        
        # tvDatafeed test
        try:
            data = self.tv.get_hist(symbol=symbol, exchange=exchange, interval=Interval.in_daily, n_bars=10)
            results["tvdatafeed"] = data is not None and not data.empty
        except Exception as e:
            results["tvdatafeed_error"] = str(e)
        
        # yfinance test
        if YFINANCE_AVAILABLE:
            data = self._yfinance_fallback(symbol, exchange, "daily", 10)
            results["yfinance"] = data is not None and not data.empty
        else:
            results["yfinance_error"] = "yfinance not installed"
        
        return results

