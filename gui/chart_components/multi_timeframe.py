"""
Multi-Timeframe Manager - Gelişmiş çoklu zaman dilimi yönetimi
"""

import pandas as pd
from typing import Optional

# Optional imports
try:
    from tvDatafeed import TvDatafeed, Interval

    TVDATAFEED_AVAILABLE = True
except ImportError:
    TVDATAFEED_AVAILABLE = False
    print("⚠️ tvDatafeed kurulu değil.")

try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ yfinance kurulu değil.")


class MultiTimeframeManager:
    """
    Çoklu zaman dilimi veri yöneticisi
    - tvDatafeed (öncelik 1)
    - yfinance (fallback)
    - Cache mekanizması
    - Otomatik resampling
    """

    _cache = {}  # {symbol: {timeframe: df}}

    # Zaman dilimi konfigürasyonu
    TIMEFRAME_CONFIG = {
        "1m": {"name": "1 Dakika", "bars": 500, "yf_interval": "1m", "yf_period": "5d"},
        "5m": {
            "name": "5 Dakika",
            "bars": 500,
            "yf_interval": "5m",
            "yf_period": "30d",
        },
        "15m": {
            "name": "15 Dakika",
            "bars": 500,
            "yf_interval": "15m",
            "yf_period": "60d",
        },
        "30m": {
            "name": "30 Dakika",
            "bars": 500,
            "yf_interval": "30m",
            "yf_period": "60d",
        },
        "1h": {"name": "1 Saat", "bars": 500, "yf_interval": "1h", "yf_period": "90d"},
        "4h": {"name": "4 Saat", "bars": 500, "yf_interval": "1h", "yf_period": "180d"},
        "1d": {"name": "1 Gün", "bars": 500, "yf_interval": "1d", "yf_period": "2y"},
        "1w": {"name": "1 Hafta", "bars": 300, "yf_interval": "1wk", "yf_period": "5y"},
        "1M": {"name": "1 Ay", "bars": 200, "yf_interval": "1mo", "yf_period": "10y"},
    }

    @staticmethod
    def get_data(
        symbol: str, timeframe: str, force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Belirtilen sembol ve timeframe için veri çek

        Args:
            symbol: Hisse sembolü (örn: "THYAO", "THYAO.IS")
            timeframe: Zaman dilimi ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M')
            force_refresh: Cache'i bypass et

        Returns:
            DataFrame veya None
        """
        # Cache kontrolü
        if not force_refresh:
            if symbol in MultiTimeframeManager._cache:
                if timeframe in MultiTimeframeManager._cache[symbol]:
                    cached_df = MultiTimeframeManager._cache[symbol][timeframe]
                    print(f"✅ Cache'den yüklendi: {symbol} - {timeframe}")
                    return cached_df.copy()

        # Timeframe config
        if timeframe not in MultiTimeframeManager.TIMEFRAME_CONFIG:
            print(f"❌ Geçersiz timeframe: {timeframe}")
            return None

        config = MultiTimeframeManager.TIMEFRAME_CONFIG[timeframe]

        # 1. tvDatafeed ile dene
        df = MultiTimeframeManager._fetch_from_tvdatafeed(symbol, timeframe, config)

        # 2. Başarısızsa yfinance dene
        if df is None:
            df = MultiTimeframeManager._fetch_from_yfinance(symbol, timeframe, config)

        # 3. Başarılıysa cache'e kaydet
        if df is not None and len(df) > 0:
            if symbol not in MultiTimeframeManager._cache:
                MultiTimeframeManager._cache[symbol] = {}
            MultiTimeframeManager._cache[symbol][timeframe] = df.copy()
            print(f"✅ Veri yüklendi: {symbol} - {timeframe} ({len(df)} bar)")
            return df

        print(f"❌ Veri alınamadı: {symbol} - {timeframe}")
        return None

    @staticmethod
    def _fetch_from_tvdatafeed(
        symbol: str, timeframe: str, config: dict
    ) -> Optional[pd.DataFrame]:
        """tvDatafeed ile veri çek"""
        if not TVDATAFEED_AVAILABLE:
            return None

        try:

            # Interval mapping
            interval_map = {
                "1m": Interval.in_1_minute,
                "5m": Interval.in_5_minute,
                "15m": Interval.in_15_minute,
                "30m": Interval.in_30_minute,
                "1h": Interval.in_1_hour,
                "4h": Interval.in_4_hour,
                "1d": Interval.in_daily,
                "1w": Interval.in_weekly,
                "1M": Interval.in_monthly,
            }

            if timeframe not in interval_map:
                return None

            tv = TvDatafeed()
            interval = interval_map[timeframe]
            n_bars = config["bars"]

            # BIST hisseleri
            symbol_clean = symbol.replace(".IS", "")

            hist = tv.get_hist(
                symbol=symbol_clean, exchange="BIST", interval=interval, n_bars=n_bars
            )

            if hist is None or hist.empty:
                return None

            # DataFrame formatı
            df = pd.DataFrame(
                {
                    "date": hist.index,
                    "open": hist["open"].values,
                    "high": hist["high"].values,
                    "low": hist["low"].values,
                    "close": hist["close"].values,
                    "volume": hist["volume"].values,
                }
            ).reset_index(drop=True)

            print(f"✅ tvDatafeed: {symbol} - {timeframe}")
            return df

        except Exception as e:
            print(f"⚠️ tvDatafeed hatası: {e}")
            return None

    @staticmethod
    def _fetch_from_yfinance(
        symbol: str, timeframe: str, config: dict
    ) -> Optional[pd.DataFrame]:
        """yfinance ile veri çek"""
        if not YFINANCE_AVAILABLE:
            print("❌ yfinance kurulu değil. 'pip install yfinance' ile yükleyin.")
            return None

        try:

            # Symbol formatı (.IS ekle)
            symbol_yahoo = symbol if symbol.endswith(".IS") else f"{symbol}.IS"

            interval = config["yf_interval"]
            period = config["yf_period"]

            ticker = yf.Ticker(symbol_yahoo)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return None

            # DataFrame formatı
            df = pd.DataFrame(
                {
                    "date": hist.index,
                    "open": hist["Open"].values,
                    "high": hist["High"].values,
                    "low": hist["Low"].values,
                    "close": hist["Close"].values,
                    "volume": hist["Volume"].values,
                }
            ).reset_index(drop=True)

            # 4h için resample (yfinance 4h desteklemiyor)
            if timeframe == "4h" and interval == "1h":
                df = MultiTimeframeManager._resample_to_4h(df)

            print(f"✅ yfinance: {symbol} - {timeframe}")
            return df

        except Exception as e:
            print(f"⚠️ yfinance hatası: {e}")
            return None

    @staticmethod
    def _resample_to_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
        """1 saatlik veriyi 4 saatlik barlara dönüştür"""
        try:
            df_1h["date"] = pd.to_datetime(df_1h["date"])
            df_1h.set_index("date", inplace=True)

            # 4 saatlik resampling
            resampled = pd.DataFrame(
                {
                    "open": df_1h["open"].resample("4h").first(),
                    "high": df_1h["high"].resample("4h").max(),
                    "low": df_1h["low"].resample("4h").min(),
                    "close": df_1h["close"].resample("4h").last(),
                    "volume": df_1h["volume"].resample("4h").sum(),
                }
            ).dropna()

            resampled.reset_index(inplace=True)
            return resampled

        except Exception as e:
            print(f"4h resampling hatası: {e}")
            return df_1h

    @staticmethod
    def get_available_timeframes() -> list:
        """Kullanılabilir zaman dilimlerini döndür"""
        return list(MultiTimeframeManager.TIMEFRAME_CONFIG.keys())

    @staticmethod
    def get_timeframe_name(timeframe: str) -> str:
        """Zaman dilimi adını döndür"""
        if timeframe in MultiTimeframeManager.TIMEFRAME_CONFIG:
            return MultiTimeframeManager.TIMEFRAME_CONFIG[timeframe]["name"]
        return timeframe

    @staticmethod
    def clear_cache(symbol: str = None, timeframe: str = None):
        """Cache'i temizle"""
        if symbol is None:
            # Tüm cache'i temizle
            MultiTimeframeManager._cache.clear()
            print("✅ Tüm cache temizlendi")
        elif timeframe is None:
            # Belirli symbol'ün tüm timeframe'lerini temizle
            if symbol in MultiTimeframeManager._cache:
                del MultiTimeframeManager._cache[symbol]
                print(f"✅ {symbol} cache temizlendi")
        else:
            # Belirli symbol ve timeframe'i temizle
            if symbol in MultiTimeframeManager._cache:
                if timeframe in MultiTimeframeManager._cache[symbol]:
                    del MultiTimeframeManager._cache[symbol][timeframe]
                    print(f"✅ {symbol} - {timeframe} cache temizlendi")

    @staticmethod
    def get_cache_info() -> dict:
        """Cache bilgilerini döndür"""
        info = {}
        for symbol, timeframes in MultiTimeframeManager._cache.items():
            info[symbol] = {
                "timeframes": list(timeframes.keys()),
                "total_bars": sum(len(df) for df in timeframes.values()),
            }
        return info


class MultiTimeframeAnalyzer:
    """
    Çoklu zaman dilimi analizi
    - Trend uyumu
    - Güç analizi
    - Sinyal validasyonu
    """

    @staticmethod
    def analyze_multi_timeframe_trend(symbol: str, timeframes: list = None) -> dict:
        """
        Çoklu timeframe trend analizi

        Args:
            symbol: Hisse sembolü
            timeframes: Analiz edilecek timeframe'ler (None = hepsi)

        Returns:
            {
                'overall_trend': 'bullish' | 'bearish' | 'neutral',
                'trend_strength': 0-100,
                'timeframe_trends': {timeframe: {'trend': str, 'ema_alignment': bool}},
                'aligned_count': int
            }
        """
        if timeframes is None:
            timeframes = ["15m", "1h", "4h", "1d", "1w"]

        trends = {}
        aligned_count = 0
        bullish_count = 0
        bearish_count = 0

        for tf in timeframes:
            df = MultiTimeframeManager.get_data(symbol, tf)
            if df is None or len(df) < 50:
                continue

            # EMA analizi (basit)
            close = df["close"].values
            ema20 = pd.Series(close).ewm(span=20).mean().values[-1]
            ema50 = pd.Series(close).ewm(span=50).mean().values[-1]
            current_price = close[-1]

            # Trend belirleme
            if current_price > ema20 and ema20 > ema50:
                trend = "bullish"
                bullish_count += 1
            elif current_price < ema20 and ema20 < ema50:
                trend = "bearish"
                bearish_count += 1
            else:
                trend = "neutral"

            ema_aligned = (current_price > ema20 and ema20 > ema50) or (
                current_price < ema20 and ema20 < ema50
            )

            if ema_aligned:
                aligned_count += 1

            trends[tf] = {
                "trend": trend,
                "ema_alignment": ema_aligned,
                "current_price": current_price,
                "ema20": ema20,
                "ema50": ema50,
            }

        # Genel trend
        if bullish_count > bearish_count:
            overall_trend = "bullish"
        elif bearish_count > bullish_count:
            overall_trend = "bearish"
        else:
            overall_trend = "neutral"

        # Trend gücü (hizalanma oranı)
        trend_strength = (aligned_count / len(timeframes)) * 100 if timeframes else 0

        return {
            "overall_trend": overall_trend,
            "trend_strength": trend_strength,
            "timeframe_trends": trends,
            "aligned_count": aligned_count,
            "total_timeframes": len(timeframes),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
        }
