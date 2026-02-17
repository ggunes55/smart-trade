"""
Pattern Recognition
NOT: Divergence analizi artık swing_divergence_analyzer.py'de
"""

import numpy as np
import pandas as pd

try:
    import talib

    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False


class PatternRecognizer:
    """
    Mum çubuğu pattern tespiti
    - Hammer, Shooting Star
    - Engulfing (Bullish/Bearish)
    - Doji
    - Morning/Evening Star
    """

    @staticmethod
    def detect_patterns(df: pd.DataFrame) -> dict:
        """
        Pattern'leri tespit et
        Returns: {pattern_name: [(index, price), ...]}
        """
        if not TALIB_AVAILABLE:
            return {
                "hammer": [],
                "shooting_star": [],
                "engulfing_bullish": [],
                "engulfing_bearish": [],
                "doji": [],
                "morning_star": [],
                "evening_star": [],
            }

        patterns = {
            "hammer": [],
            "shooting_star": [],
            "engulfing_bullish": [],
            "engulfing_bearish": [],
            "doji": [],
            "morning_star": [],
            "evening_star": [],
        }

        o = df["open"].values
        h = df["high"].values
        low = df["low"].values
        c = df["close"].values

        # TA-Lib pattern fonksiyonları
        patterns["hammer"] = [
            (i, c[i]) for i in np.where(talib.CDLHAMMER(o, h, low, c) != 0)[0]
        ]
        patterns["shooting_star"] = [
            (i, c[i]) for i in np.where(talib.CDLSHOOTINGSTAR(o, h, low, c) != 0)[0]
        ]
        patterns["engulfing_bullish"] = [
            (i, c[i]) for i in np.where(talib.CDLENGULFING(o, h, low, c) > 0)[0]
        ]
        patterns["engulfing_bearish"] = [
            (i, c[i]) for i in np.where(talib.CDLENGULFING(o, h, low, c) < 0)[0]
        ]
        patterns["doji"] = [
            (i, c[i]) for i in np.where(talib.CDLDOJI(o, h, low, c) != 0)[0]
        ]
        patterns["morning_star"] = [
            (i, c[i]) for i in np.where(talib.CDLMORNINGSTAR(o, h, low, c) != 0)[0]
        ]
        patterns["evening_star"] = [
            (i, c[i]) for i in np.where(talib.CDLEVENINGSTAR(o, h, low, c) != 0)[0]
        ]

        return patterns


class DivergenceDetector:
    """
    RSI-Price ve MACD-Price divergence tespiti
    - Kalite puanlama sistemi (0-100)
    - Bullish/Bearish divergence
    """

    @staticmethod
    def quality_score(
        close: np.ndarray, indicator: np.ndarray, lookback: int = 20
    ) -> float:
        """
        Divergence kalite puanı hesapla (0-100)
        Yüksek puan = güçlü divergence
        """
        try:
            if not TALIB_AVAILABLE:
                return 0

            price_trend = talib.LINEARREG_SLOPE(close, timeperiod=lookback)[-1]
            indicator_trend = talib.LINEARREG_SLOPE(indicator, timeperiod=lookback)[-1]

            # Eğim farkı ne kadar büyükse divergence o kadar güçlü
            slope_diff = abs(price_trend - indicator_trend)
            score = min(100, slope_diff * 10)

            return score
        except Exception:
            return 0

    @staticmethod
    def detect_divergences(df: pd.DataFrame, min_quality: int = 50) -> dict:
        """
        Uyumsuzlukları tespit et (kaliteli olanları)

        Args:
            df: OHLCV + göstergeler içeren DataFrame
            min_quality: Minimum kalite puanı (0-100), varsayılan 50

        Returns:
            {
                'bullish_rsi': [(index, price, rsi, quality), ...],
                'bearish_rsi': [...],
                'bullish_macd': [...],
                'bearish_macd': [...]
            }
        """
        divergences = {
            "bullish_rsi": [],
            "bearish_rsi": [],
            "bullish_macd": [],
            "bearish_macd": [],
        }

        if len(df) < 50 or not TALIB_AVAILABLE:
            return divergences

        close = df["close"].values
        rsi = df["RSI"].values
        macd = df["MACD"].values

        window = 20

        # RSI Divergences
        for i in range(window, len(df) - window):
            if i > window * 2:
                prev_low_idx = i - window

                # Bullish Divergence: Fiyat düşük yapıyor ama RSI yükseliyor
                if close[i] < close[prev_low_idx]:
                    if rsi[i] > rsi[prev_low_idx]:
                        quality = DivergenceDetector.quality_score(
                            close[prev_low_idx : i + 1],
                            rsi[prev_low_idx : i + 1],
                            lookback=window,
                        )

                        if quality >= min_quality:
                            divergences["bullish_rsi"].append(
                                (i, close[i], rsi[i], quality)
                            )

                # Bearish Divergence: Fiyat yüksek yapıyor ama RSI düşüyor
                if close[i] > close[prev_low_idx]:
                    if rsi[i] < rsi[prev_low_idx]:
                        quality = DivergenceDetector.quality_score(
                            close[prev_low_idx : i + 1],
                            rsi[prev_low_idx : i + 1],
                            lookback=window,
                        )

                        if quality >= min_quality:
                            divergences["bearish_rsi"].append(
                                (i, close[i], rsi[i], quality)
                            )

        # MACD Divergences
        for i in range(window, len(df) - window):
            if i > window * 2:
                prev_idx = i - window

                # Bullish: Fiyat düşük, MACD yüksek
                if close[i] < close[prev_idx] and macd[i] > macd[prev_idx]:
                    quality = DivergenceDetector.quality_score(
                        close[prev_idx : i + 1], macd[prev_idx : i + 1], lookback=window
                    )

                    if quality >= min_quality:
                        divergences["bullish_macd"].append(
                            (i, close[i], macd[i], quality)
                        )

                # Bearish: Fiyat yüksek, MACD düşük
                if close[i] > close[prev_idx] and macd[i] < macd[prev_idx]:
                    quality = DivergenceDetector.quality_score(
                        close[prev_idx : i + 1], macd[prev_idx : i + 1], lookback=window
                    )

                    if quality >= min_quality:
                        divergences["bearish_macd"].append(
                            (i, close[i], macd[i], quality)
                        )

        return divergences
