"""
Indicator Calculator - Tüm teknik göstergeleri hesapla
"""

import numpy as np
import pandas as pd
import talib
from .config import REQUIRED_COLUMNS, EMA_CONFIG


class IndicatorCalculator:
    """
    Teknik göstergeler hesaplayıcı
    - Cache mekanizması
    - EMA, SMA, BB, RSI, MACD, Stochastic, ADX
    - VWAP, ATR
    - Sinyal tespiti
    """

    _cache = {}

    @staticmethod
    def validate_df(df: pd.DataFrame):
        """DataFrame'i doğrula"""
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Eksik kolonlar: {missing}")

        if df[list(REQUIRED_COLUMNS)].isnull().any().any():
            raise ValueError("Veri setinde NaN değerler var!")

        if np.isinf(df[list(REQUIRED_COLUMNS)].values).any():
            raise ValueError("Veri setinde Inf değerler var!")

        if len(df) < 200:
            raise ValueError("EMA200 için en az 200 bar veri gerekli!")

    @staticmethod
    def calculate(df: pd.DataFrame) -> pd.DataFrame:
        """
        Tüm göstergeleri hesapla
        Returns: Göstergeler eklenmiş DataFrame
        """
        # Gelişmiş cache anahtarı
        last_index = df.index[-1] if hasattr(df.index[-1], "__hash__") else len(df) - 1
        cache_key = f"{len(df)}_{df['close'].iloc[-1]}_{last_index}"

        # Cache kontrolü
        if cache_key in IndicatorCalculator._cache:
            cached_df = IndicatorCalculator._cache[cache_key]
            if (
                len(cached_df) == len(df)
                and cached_df["close"].iloc[-1] == df["close"].iloc[-1]
            ):
                return cached_df.copy()

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        # EMA ve SMA
        for name, cfg in EMA_CONFIG.items():
            if name == "SMA200":
                df[name] = talib.SMA(close, timeperiod=cfg["period"])
            else:
                df[name] = talib.EMA(close, timeperiod=cfg["period"])

        # Bollinger Bands
        df["BB_Upper"], df["BB_Middle"], df["BB_Lower"] = talib.BBANDS(
            close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )

        # Bollinger Squeeze Detection
        df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / df["BB_Middle"]
        df["BB_Width_MA"] = df["BB_Width"].rolling(20).mean()
        df["BB_Squeeze"] = df["BB_Width"] < (df["BB_Width_MA"] * 0.5)
        df["BB_Squeeze"] = df["BB_Squeeze"].fillna(False)

        # VWAP
        df["VWAP"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()

        # RSI
        df["RSI"] = talib.RSI(close, timeperiod=14)
        df["RSI_MA"] = talib.EMA(df["RSI"], timeperiod=9)

        # MACD
        macd, signal, hist = talib.MACD(close, 12, 26, 9)
        df["MACD"] = macd
        df["MACD_Signal"] = signal
        df["MACD_Hist"] = hist

        # Volume Moving Averages
        df["VMA20"] = talib.SMA(volume, timeperiod=20)
        df["VMA50"] = talib.SMA(volume, timeperiod=50)

        # ATR
        df["ATR"] = talib.ATR(high, low, close, timeperiod=14)

        # Stochastic
        df["STOCH_K"], df["STOCH_D"] = talib.STOCH(
            high, low, close, fastk_period=14, slowk_period=3, slowd_period=3
        )

        # ADX
        df["ADX"] = talib.ADX(high, low, close, timeperiod=14)

        # Cache'e kaydet
        IndicatorCalculator._cache[cache_key] = df.copy()

        # Cache boyutunu sınırla (son 10 hesaplama)
        if len(IndicatorCalculator._cache) > 10:
            oldest_key = next(iter(IndicatorCalculator._cache))
            del IndicatorCalculator._cache[oldest_key]

        return df

    @staticmethod
    def detect_signals(df: pd.DataFrame) -> dict:
        """
        Alım/satım sinyalleri ve destek/direnç seviyeleri tespit et
        Returns: {buy, sell, support, resistance}
        """
        signals = {"buy": [], "sell": [], "support": [], "resistance": []}

        close = df["close"].values
        rsi = df["RSI"].values
        macd = df["MACD"].values
        macd_signal = df["MACD_Signal"].values

        # Alım sinyalleri (RSI < 35 + MACD kesişimi)
        for i in range(50, len(df)):
            if (
                rsi[i] < 35
                and rsi[i - 1] >= 35
                and macd[i] > macd_signal[i]
                and macd[i - 1] <= macd_signal[i - 1]
            ):
                signals["buy"].append((i, close[i]))

            # Satım sinyalleri (RSI > 65 + MACD kesişimi)
            if (
                rsi[i] > 65
                and rsi[i - 1] <= 65
                and macd[i] < macd_signal[i]
                and macd[i - 1] >= macd_signal[i - 1]
            ):
                signals["sell"].append((i, close[i]))

        # Destek/Direnç seviyeleri
        signals["support"] = IndicatorCalculator._find_support_resistance(df, "support")
        signals["resistance"] = IndicatorCalculator._find_support_resistance(
            df, "resistance"
        )

        return signals

    @staticmethod
    def _find_support_resistance(df: pd.DataFrame, sr_type: str) -> list:
        """Destek/direnç seviyelerini tespit et"""
        close = df["close"].values
        levels = []
        window = 20

        for i in range(window, len(close) - window):
            if sr_type == "support":
                if close[i] == min(close[i - window : i + window]):
                    levels.append(close[i])
            else:
                if close[i] == max(close[i - window : i + window]):
                    levels.append(close[i])

        if levels:
            levels = sorted(set(levels))
            # Birbirine yakın seviyeleri birleştir (%2 threshold)
            merged = [levels[0]]
            for level in levels[1:]:
                if abs(level - merged[-1]) / merged[-1] > 0.02:
                    merged.append(level)
            return merged
        return []
