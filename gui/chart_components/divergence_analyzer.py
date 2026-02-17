"""
Advanced Divergence Analyzer - Gelişmiş uyumsuzluk analizi
"""

import numpy as np
import pandas as pd

try:
    import talib

    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False


class DivergenceType:
    """Divergence tipleri"""

    REGULAR_BULLISH = "regular_bullish"  # Regular Bullish (düşüş trendinde)
    REGULAR_BEARISH = "regular_bearish"  # Regular Bearish (yükseliş trendinde)
    HIDDEN_BULLISH = "hidden_bullish"  # Hidden Bullish (yükseliş trendinde)
    HIDDEN_BEARISH = "hidden_bearish"  # Hidden Bearish (düşüş trendinde)


class AdvancedDivergenceAnalyzer:
    """
    Gelişmiş divergence analizi
    - Regular Divergence (trend dönüşü)
    - Hidden Divergence (trend devamı)
    - Multi-indicator (RSI, MACD, Stochastic)
    - Kalite skorlaması
    - Güç analizi
    """

    @staticmethod
    def detect_all_divergences(
        df: pd.DataFrame,
        indicators: list = None,
        min_quality: int = 50,
        lookback: int = 20,
    ) -> dict:
        """
        Tüm divergence'leri tespit et

        Args:
            df: OHLCV + göstergeler DataFrame
            indicators: Analiz edilecek göstergeler ['RSI', 'MACD', 'STOCH']
            min_quality: Minimum kalite skoru (0-100)
            lookback: Geriye bakış penceresi

        Returns:
            {
                'rsi': {
                    'regular_bullish': [...],
                    'regular_bearish': [...],
                    'hidden_bullish': [...],
                    'hidden_bearish': [...]
                },
                'macd': {...},
                'stoch': {...}
            }
        """
        if not TALIB_AVAILABLE:
            return {}

        if indicators is None:
            indicators = ["RSI", "MACD", "STOCH"]

        results = {}

        # RSI Divergences
        if "RSI" in indicators and "RSI" in df.columns:
            results["rsi"] = AdvancedDivergenceAnalyzer._detect_rsi_divergences(
                df, min_quality, lookback
            )

        # MACD Divergences
        if "MACD" in indicators and "MACD" in df.columns:
            results["macd"] = AdvancedDivergenceAnalyzer._detect_macd_divergences(
                df, min_quality, lookback
            )

        # Stochastic Divergences
        if "STOCH" in indicators and "STOCH_K" in df.columns:
            results["stoch"] = AdvancedDivergenceAnalyzer._detect_stoch_divergences(
                df, min_quality, lookback
            )

        return results

    @staticmethod
    def _detect_rsi_divergences(
        df: pd.DataFrame, min_quality: int, lookback: int
    ) -> dict:
        """RSI divergence'leri tespit et"""
        close = df["close"].values
        rsi = df["RSI"].values

        divergences = {
            "regular_bullish": [],  # Fiyat düşüyor, RSI yükseliyor
            "regular_bearish": [],  # Fiyat yükseliyor, RSI düşüyor
            "hidden_bullish": [],  # Fiyat yükseliyor, RSI düşüyor (trend devamı)
            "hidden_bearish": [],  # Fiyat düşüyor, RSI yükseliyor (trend devamı)
        }

        for i in range(lookback * 2, len(df) - lookback):
            prev_idx = i - lookback

            # Pivot noktaları bul
            if not AdvancedDivergenceAnalyzer._is_pivot(close, i, lookback):
                continue
            if not AdvancedDivergenceAnalyzer._is_pivot(close, prev_idx, lookback):
                continue

            price_diff = close[i] - close[prev_idx]
            rsi_diff = rsi[i] - rsi[prev_idx]

            # Regular Bullish (fiyat düşüyor, RSI yükseliyor)
            if price_diff < 0 and rsi_diff > 0:
                quality = AdvancedDivergenceAnalyzer._calculate_quality(
                    close[prev_idx : i + 1], rsi[prev_idx : i + 1]
                )
                if quality >= min_quality:
                    divergences["regular_bullish"].append(
                        {
                            "index": i,
                            "price": close[i],
                            "indicator_value": rsi[i],
                            "quality": quality,
                            "prev_index": prev_idx,
                            "strength": AdvancedDivergenceAnalyzer._calculate_strength(
                                abs(price_diff), abs(rsi_diff)
                            ),
                        }
                    )

            # Regular Bearish (fiyat yükseliyor, RSI düşüyor)
            elif price_diff > 0 and rsi_diff < 0:
                quality = AdvancedDivergenceAnalyzer._calculate_quality(
                    close[prev_idx : i + 1], rsi[prev_idx : i + 1]
                )
                if quality >= min_quality:
                    divergences["regular_bearish"].append(
                        {
                            "index": i,
                            "price": close[i],
                            "indicator_value": rsi[i],
                            "quality": quality,
                            "prev_index": prev_idx,
                            "strength": AdvancedDivergenceAnalyzer._calculate_strength(
                                abs(price_diff), abs(rsi_diff)
                            ),
                        }
                    )

            # Hidden Bullish (fiyat yükseliyor, RSI düşüyor - trend devamı)
            elif price_diff > 0 and rsi_diff < 0 and close[i] > close[prev_idx]:
                quality = AdvancedDivergenceAnalyzer._calculate_quality(
                    close[prev_idx : i + 1], rsi[prev_idx : i + 1]
                )
                if quality >= min_quality * 0.8:  # Hidden için threshold düşük
                    divergences["hidden_bullish"].append(
                        {
                            "index": i,
                            "price": close[i],
                            "indicator_value": rsi[i],
                            "quality": quality,
                            "prev_index": prev_idx,
                            "strength": AdvancedDivergenceAnalyzer._calculate_strength(
                                abs(price_diff), abs(rsi_diff)
                            ),
                        }
                    )

        return divergences

    @staticmethod
    def _detect_macd_divergences(
        df: pd.DataFrame, min_quality: int, lookback: int
    ) -> dict:
        """MACD divergence'leri tespit et"""
        close = df["close"].values
        macd = df["MACD"].values

        divergences = {
            "regular_bullish": [],
            "regular_bearish": [],
            "hidden_bullish": [],
            "hidden_bearish": [],
        }

        for i in range(lookback * 2, len(df) - lookback):
            prev_idx = i - lookback

            if not AdvancedDivergenceAnalyzer._is_pivot(close, i, lookback):
                continue

            price_diff = close[i] - close[prev_idx]
            macd_diff = macd[i] - macd[prev_idx]

            # Regular Bullish
            if price_diff < 0 and macd_diff > 0:
                quality = AdvancedDivergenceAnalyzer._calculate_quality(
                    close[prev_idx : i + 1], macd[prev_idx : i + 1]
                )
                if quality >= min_quality:
                    divergences["regular_bullish"].append(
                        {
                            "index": i,
                            "price": close[i],
                            "indicator_value": macd[i],
                            "quality": quality,
                            "prev_index": prev_idx,
                            "strength": AdvancedDivergenceAnalyzer._calculate_strength(
                                abs(price_diff), abs(macd_diff) * 10
                            ),
                        }
                    )

            # Regular Bearish
            elif price_diff > 0 and macd_diff < 0:
                quality = AdvancedDivergenceAnalyzer._calculate_quality(
                    close[prev_idx : i + 1], macd[prev_idx : i + 1]
                )
                if quality >= min_quality:
                    divergences["regular_bearish"].append(
                        {
                            "index": i,
                            "price": close[i],
                            "indicator_value": macd[i],
                            "quality": quality,
                            "prev_index": prev_idx,
                            "strength": AdvancedDivergenceAnalyzer._calculate_strength(
                                abs(price_diff), abs(macd_diff) * 10
                            ),
                        }
                    )

        return divergences

    @staticmethod
    def _detect_stoch_divergences(
        df: pd.DataFrame, min_quality: int, lookback: int
    ) -> dict:
        """Stochastic divergence'leri tespit et"""
        close = df["close"].values
        stoch = df["STOCH_K"].values

        divergences = {
            "regular_bullish": [],
            "regular_bearish": [],
            "hidden_bullish": [],
            "hidden_bearish": [],
        }

        for i in range(lookback * 2, len(df) - lookback):
            prev_idx = i - lookback

            if not AdvancedDivergenceAnalyzer._is_pivot(close, i, lookback):
                continue

            price_diff = close[i] - close[prev_idx]
            stoch_diff = stoch[i] - stoch[prev_idx]

            # Regular Bullish
            if price_diff < 0 and stoch_diff > 0:
                quality = AdvancedDivergenceAnalyzer._calculate_quality(
                    close[prev_idx : i + 1], stoch[prev_idx : i + 1]
                )
                if quality >= min_quality:
                    divergences["regular_bullish"].append(
                        {
                            "index": i,
                            "price": close[i],
                            "indicator_value": stoch[i],
                            "quality": quality,
                            "prev_index": prev_idx,
                            "strength": AdvancedDivergenceAnalyzer._calculate_strength(
                                abs(price_diff), abs(stoch_diff)
                            ),
                        }
                    )

            # Regular Bearish
            elif price_diff > 0 and stoch_diff < 0:
                quality = AdvancedDivergenceAnalyzer._calculate_quality(
                    close[prev_idx : i + 1], stoch[prev_idx : i + 1]
                )
                if quality >= min_quality:
                    divergences["regular_bearish"].append(
                        {
                            "index": i,
                            "price": close[i],
                            "indicator_value": stoch[i],
                            "quality": quality,
                            "prev_index": prev_idx,
                            "strength": AdvancedDivergenceAnalyzer._calculate_strength(
                                abs(price_diff), abs(stoch_diff)
                            ),
                        }
                    )

        return divergences

    @staticmethod
    def _is_pivot(data: np.ndarray, index: int, window: int) -> bool:
        """Pivot nokta mı kontrol et"""
        if index < window or index >= len(data) - window:
            return False

        left = data[index - window : index]
        right = data[index : index + window]
        current = data[index]

        # Pivot high veya pivot low
        is_high = all(current >= x for x in left) and all(current >= x for x in right)
        is_low = all(current <= x for x in left) and all(current <= x for x in right)

        return is_high or is_low

    @staticmethod
    def _calculate_quality(price_data: np.ndarray, indicator_data: np.ndarray) -> float:
        """Divergence kalite skoru hesapla (0-100)"""
        try:
            if not TALIB_AVAILABLE or len(price_data) < 5:
                return 0

            # Eğim farkı
            price_slope = talib.LINEARREG_SLOPE(price_data, timeperiod=len(price_data))[
                -1
            ]
            indicator_slope = talib.LINEARREG_SLOPE(
                indicator_data, timeperiod=len(indicator_data)
            )[-1]

            slope_diff = abs(price_slope - indicator_slope)
            quality = min(100, slope_diff * 50)

            return quality
        except Exception:
            return 0

    @staticmethod
    def _calculate_strength(price_change: float, indicator_change: float) -> str:
        """Divergence gücü (Weak/Medium/Strong)"""
        total_change = price_change + indicator_change

        if total_change > 10:
            return "Strong"
        elif total_change > 5:
            return "Medium"
        else:
            return "Weak"

    @staticmethod
    def get_divergence_summary(divergences: dict) -> dict:
        """Divergence özeti"""
        summary = {
            "total_count": 0,
            "by_type": {},
            "by_indicator": {},
            "avg_quality": 0,
            "strong_signals": [],
        }

        all_qualities = []

        for indicator, types in divergences.items():
            indicator_count = 0

            for div_type, divs in types.items():
                count = len(divs)
                indicator_count += count
                summary["total_count"] += count

                if div_type not in summary["by_type"]:
                    summary["by_type"][div_type] = 0
                summary["by_type"][div_type] += count

                # Kalite skorlarını topla
                for div in divs:
                    all_qualities.append(div["quality"])

                    # Güçlü sinyaller (quality > 70 ve strength = Strong)
                    if div["quality"] > 70 and div.get("strength") == "Strong":
                        summary["strong_signals"].append(
                            {
                                "indicator": indicator,
                                "type": div_type,
                                "index": div["index"],
                                "quality": div["quality"],
                            }
                        )

            summary["by_indicator"][indicator] = indicator_count

        # Ortalama kalite
        if all_qualities:
            summary["avg_quality"] = sum(all_qualities) / len(all_qualities)

        return summary
