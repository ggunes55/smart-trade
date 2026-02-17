"""
SWING TRADE PATTERNS - Gelişmiş mum pattern'leri
Klasik pattern'lere ek swing trade için özel formasyonlar
"""

import numpy as np
import pandas as pd

try:
    import talib

    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False


class SwingPatternRecognizer:
    """
    Swing Trade için özel pattern'ler
    - Multiple candlestick patterns
    - Consolidation breakouts
    - Key reversal patterns
    - Exhaustion patterns
    """

    # Pattern tanımları
    SWING_PATTERNS = {
        # Reversal Patterns
        "bullish_reversal_combo": {
            "name": "🔄 Bullish Reversal Combo",
            "desc": "Hammer + Volume + Trend exhaustion",
            "emoji": "🔄",
            "color": "#4CAF50",
        },
        "bearish_reversal_combo": {
            "name": "🔄 Bearish Reversal Combo",
            "desc": "Shooting Star + Volume + Trend exhaustion",
            "emoji": "🔄",
            "color": "#F44336",
        },
        # Continuation Patterns
        "bullish_flag": {
            "name": "🚩 Bull Flag",
            "desc": "Uptrend + consolidation + breakout",
            "emoji": "🚩",
            "color": "#2E7D32",
        },
        "bearish_flag": {
            "name": "🚩 Bear Flag",
            "desc": "Downtrend + consolidation + breakdown",
            "emoji": "🚩",
            "color": "#C62828",
        },
        # Exhaustion Patterns
        "buying_climax": {
            "name": "💥 Buying Climax",
            "desc": "Extreme volume + long candle at top",
            "emoji": "💥",
            "color": "#FF9800",
        },
        "selling_climax": {
            "name": "💥 Selling Climax",
            "desc": "Extreme volume + long candle at bottom",
            "emoji": "💥",
            "color": "#FF5722",
        },
        # Key Reversals
        "key_reversal_up": {
            "name": "🔑 Key Reversal Up",
            "desc": "New low then closes near high",
            "emoji": "🔑",
            "color": "#00BCD4",
        },
        "key_reversal_down": {
            "name": "🔑 Key Reversal Down",
            "desc": "New high then closes near low",
            "emoji": "🔑",
            "color": "#E91E63",
        },
        # Consolidation Breakouts
        "breakout_up": {
            "name": "💪 Breakout Up",
            "desc": "Consolidation + volume breakout",
            "emoji": "💪",
            "color": "#8BC34A",
        },
        "breakdown": {
            "name": "📉 Breakdown",
            "desc": "Consolidation + volume breakdown",
            "emoji": "📉",
            "color": "#D32F2F",
        },
    }

    @staticmethod
    def detect_all_swing_patterns(df: pd.DataFrame) -> dict:
        """
        Tüm swing pattern'leri tespit et

        Returns:
            {
                'pattern_name': [(index, price, strength, context), ...],
                ...
            }
        """
        if not TALIB_AVAILABLE or len(df) < 50:
            return {}

        patterns = {}

        # Reversal Combos
        patterns["bullish_reversal_combo"] = (
            SwingPatternRecognizer._detect_bullish_reversal_combo(df)
        )
        patterns["bearish_reversal_combo"] = (
            SwingPatternRecognizer._detect_bearish_reversal_combo(df)
        )

        # Flags
        patterns["bullish_flag"] = SwingPatternRecognizer._detect_bull_flag(df)
        patterns["bearish_flag"] = SwingPatternRecognizer._detect_bear_flag(df)

        # Exhaustion
        patterns["buying_climax"] = SwingPatternRecognizer._detect_buying_climax(df)
        patterns["selling_climax"] = SwingPatternRecognizer._detect_selling_climax(df)

        # Key Reversals
        patterns["key_reversal_up"] = SwingPatternRecognizer._detect_key_reversal_up(df)
        patterns["key_reversal_down"] = (
            SwingPatternRecognizer._detect_key_reversal_down(df)
        )

        # Breakouts
        patterns["breakout_up"] = SwingPatternRecognizer._detect_breakout_up(df)
        patterns["breakdown"] = SwingPatternRecognizer._detect_breakdown(df)

        return patterns

    @staticmethod
    def _detect_bullish_reversal_combo(df: pd.DataFrame) -> list:
        """Bullish Reversal Combo: Hammer + High Volume + Downtrend"""
        patterns = []

        o = df["open"].values
        h = df["high"].values
        low = df["low"].values
        c = df["close"].values
        v = df["volume"].values

        # Hammer pattern
        hammers = talib.CDLHAMMER(o, h, low, c)

        # Volume MA
        vol_ma = talib.SMA(v, timeperiod=20)

        # EMA20
        ema20 = talib.EMA(c, timeperiod=20)

        for i in range(30, len(df) - 5):
            # Hammer var mı?
            if hammers[i] == 0:
                continue

            # Downtrend içinde mi?
            if c[i] > ema20[i]:
                continue

            # Volume yüksek mi?
            if v[i] < vol_ma[i] * 1.5:
                continue

            # Trend exhaustion (5 barlık düşüş)
            recent_trend = c[i] - c[i - 5]
            if recent_trend > 0:
                continue

            # Strength hesapla
            vol_ratio = v[i] / vol_ma[i]
            body = abs(c[i] - o[i])
            range_val = h[i] - low[i]
            wick_ratio = (range_val - body) / range_val if range_val > 0 else 0

            strength = min(100, (vol_ratio * 30) + (wick_ratio * 50))

            patterns.append((i, c[i], strength, "downtrend_reversal"))

        return patterns

    @staticmethod
    def _detect_bearish_reversal_combo(df: pd.DataFrame) -> list:
        """Bearish Reversal Combo"""
        patterns = []

        o = df["open"].values
        h = df["high"].values
        low = df["low"].values
        c = df["close"].values
        v = df["volume"].values

        shooting_stars = talib.CDLSHOOTINGSTAR(o, h, low, c)
        vol_ma = talib.SMA(v, timeperiod=20)
        ema20 = talib.EMA(c, timeperiod=20)

        for i in range(30, len(df) - 5):
            if shooting_stars[i] == 0:
                continue

            if c[i] < ema20[i]:
                continue

            if v[i] < vol_ma[i] * 1.5:
                continue

            recent_trend = c[i] - c[i - 5]
            if recent_trend < 0:
                continue

            vol_ratio = v[i] / vol_ma[i]
            strength = min(100, vol_ratio * 50)

            patterns.append((i, c[i], strength, "uptrend_reversal"))

        return patterns

    @staticmethod
    def _detect_bull_flag(df: pd.DataFrame) -> list:
        """Bull Flag: Strong up move + consolidation + breakout"""
        patterns = []

        c = df["close"].values
        h = df["high"].values
        v = df["volume"].values

        for i in range(20, len(df) - 5):
            # 1. Strong up move (son 10 bar)
            move = (c[i - 1] - c[i - 10]) / c[i - 10]
            if move < 0.05:  # En az %5 yükseliş
                continue

            # 2. Consolidation (son 5 bar dar range)
            consol_range = h[i - 5 : i].max() - h[i - 5 : i].min()
            if consol_range / c[i - 5] > 0.03:  # Max %3 range
                continue

            # 3. Breakout (current bar)
            if c[i] <= h[i - 5 : i].max():
                continue

            # Volume confirmation
            vol_ma = np.mean(v[i - 20 : i])
            if v[i] < vol_ma * 1.2:
                continue

            strength = min(100, move * 1000 + (v[i] / vol_ma) * 20)
            patterns.append((i, c[i], strength, "continuation"))

        return patterns

    @staticmethod
    def _detect_bear_flag(df: pd.DataFrame) -> list:
        """Bear Flag: Strong down move + consolidation + breakdown"""
        patterns = []

        c = df["close"].values
        low = df["low"].values
        v = df["volume"].values

        for i in range(20, len(df) - 5):
            move = (c[i - 1] - c[i - 10]) / c[i - 10]
            if move > -0.05:
                continue

            consol_range = low[i - 5 : i].max() - low[i - 5 : i].min()
            if consol_range / c[i - 5] > 0.03:
                continue

            if c[i] >= low[i - 5 : i].min():
                continue

            vol_ma = np.mean(v[i - 20 : i])
            if v[i] < vol_ma * 1.2:
                continue

            strength = min(100, abs(move) * 1000 + (v[i] / vol_ma) * 20)
            patterns.append((i, c[i], strength, "continuation"))

        return patterns

    @staticmethod
    def _detect_buying_climax(df: pd.DataFrame) -> list:
        """Buying Climax: Extreme volume + long candle at trend end"""
        patterns = []

        o = df["open"].values
        c = df["close"].values
        h = df["high"].values
        low = df["low"].values
        v = df["volume"].values

        for i in range(50, len(df)):
            # Extreme volume (3x average)
            vol_ma = np.mean(v[i - 20 : i])
            if v[i] < vol_ma * 2.5:
                continue

            # Long bullish candle
            body = c[i] - o[i]
            range_val = h[i] - low[i]
            if body < 0 or body / range_val < 0.7:
                continue

            # At trend top (EMA50 üstünde)
            ema50 = talib.EMA(c[: i + 1], timeperiod=50)[-1]
            if c[i] < ema50 * 1.02:
                continue

            strength = min(100, (v[i] / vol_ma) * 25)
            patterns.append((i, c[i], strength, "exhaustion"))

        return patterns

    @staticmethod
    def _detect_selling_climax(df: pd.DataFrame) -> list:
        """Selling Climax"""
        patterns = []

        o = df["open"].values
        c = df["close"].values
        h = df["high"].values
        low = df["low"].values
        v = df["volume"].values

        for i in range(50, len(df)):
            vol_ma = np.mean(v[i - 20 : i])
            if v[i] < vol_ma * 2.5:
                continue

            body = o[i] - c[i]
            range_val = h[i] - low[i]
            if body < 0 or body / range_val < 0.7:
                continue

            ema50 = talib.EMA(c[: i + 1], timeperiod=50)[-1]
            if c[i] > ema50 * 0.98:
                continue

            strength = min(100, (v[i] / vol_ma) * 25)
            patterns.append((i, c[i], strength, "exhaustion"))

        return patterns

    @staticmethod
    def _detect_key_reversal_up(df: pd.DataFrame) -> list:
        """Key Reversal Up: New low then closes near high"""
        patterns = []

        h = df["high"].values
        low = df["low"].values
        c = df["close"].values

        for i in range(10, len(df)):
            # New low (10 bar içinde)
            if low[i] > low[i - 10 : i].min():
                continue

            # Closes in top 25% of range
            range_val = h[i] - low[i]
            close_position = (c[i] - low[i]) / range_val if range_val > 0 else 0

            if close_position < 0.75:
                continue

            strength = close_position * 100
            patterns.append((i, c[i], strength, "key_reversal"))

        return patterns

    @staticmethod
    def _detect_key_reversal_down(df: pd.DataFrame) -> list:
        """Key Reversal Down"""
        patterns = []

        h = df["high"].values
        low = df["low"].values
        c = df["close"].values

        for i in range(10, len(df)):
            if h[i] < h[i - 10 : i].max():
                continue

            range_val = h[i] - low[i]
            close_position = (h[i] - c[i]) / range_val if range_val > 0 else 0

            if close_position < 0.75:
                continue

            strength = close_position * 100
            patterns.append((i, c[i], strength, "key_reversal"))

        return patterns

    @staticmethod
    def _detect_breakout_up(df: pd.DataFrame) -> list:
        """Breakout Up: Consolidation + volume breakout"""
        patterns = []

        h = df["high"].values
        c = df["close"].values
        v = df["volume"].values

        for i in range(20, len(df)):
            # Consolidation (10 bar dar range)
            consol_high = h[i - 10 : i].max()
            consol_low = h[i - 10 : i].min()
            range_pct = (consol_high - consol_low) / consol_low

            if range_pct > 0.05:  # Max %5 range
                continue

            # Breakout
            if c[i] <= consol_high:
                continue

            # Volume
            vol_ma = np.mean(v[i - 20 : i])
            if v[i] < vol_ma * 1.5:
                continue

            breakout_pct = ((c[i] - consol_high) / consol_high) * 100
            strength = min(100, breakout_pct * 20 + (v[i] / vol_ma) * 20)

            patterns.append((i, c[i], strength, "breakout"))

        return patterns

    @staticmethod
    def _detect_breakdown(df: pd.DataFrame) -> list:
        """Breakdown"""
        patterns = []

        low = df["low"].values
        c = df["close"].values
        v = df["volume"].values

        for i in range(20, len(df)):
            consol_high = low[i - 10 : i].max()
            consol_low = low[i - 10 : i].min()
            range_pct = (consol_high - consol_low) / consol_low

            if range_pct > 0.05:
                continue

            if c[i] >= consol_low:
                continue

            vol_ma = np.mean(v[i - 20 : i])
            if v[i] < vol_ma * 1.5:
                continue

            breakdown_pct = ((consol_low - c[i]) / consol_low) * 100
            strength = min(100, breakdown_pct * 20 + (v[i] / vol_ma) * 20)

            patterns.append((i, c[i], strength, "breakdown"))

        return patterns
