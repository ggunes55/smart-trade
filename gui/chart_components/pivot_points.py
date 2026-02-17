"""
Pivot Points Calculator - Otomatik pivot noktaları
"""

import pandas as pd


class PivotPointsCalculator:
    """
    Pivot Points hesaplayıcı
    - Standard Pivots (P, R1, R2, S1, S2)
    - Fibonacci Pivots
    """

    @staticmethod
    def calculate_standard_pivots(df: pd.DataFrame) -> dict:
        """
        Standard Pivot Points (P, R1, R2, S1, S2)

        Args:
            df: OHLCV DataFrame

        Returns:
            {
                'P': Pivot,
                'R1': Resistance 1,
                'R2': Resistance 2,
                'S1': Support 1,
                'S2': Support 2
            }
        """
        if len(df) < 2:
            return {}

        # Dün kapanmış bar
        last_bar = df.iloc[-2]
        H = last_bar["high"]
        L = last_bar["low"]
        C = last_bar["close"]

        # Pivot formülleri
        P = (H + L + C) / 3
        R1 = (2 * P) - L
        S1 = (2 * P) - H
        R2 = P + (H - L)
        S2 = P - (H - L)

        return {"P": P, "R1": R1, "R2": R2, "S1": S1, "S2": S2}

    @staticmethod
    def calculate_fibonacci_pivots(df: pd.DataFrame) -> dict:
        """
        Fibonacci Pivot Points

        Args:
            df: OHLCV DataFrame

        Returns:
            {
                'P': Pivot,
                'R1': Fib 38.2% direnç,
                'R2': Fib 61.8% direnç,
                'R3': Fib 100% direnç,
                'S1': Fib 38.2% destek,
                'S2': Fib 61.8% destek,
                'S3': Fib 100% destek
            }
        """
        if len(df) < 2:
            return {}

        last_bar = df.iloc[-2]
        H = last_bar["high"]
        L = last_bar["low"]
        C = last_bar["close"]

        P = (H + L + C) / 3
        R1 = P + 0.382 * (H - L)
        R2 = P + 0.618 * (H - L)
        R3 = P + (H - L)
        S1 = P - 0.382 * (H - L)
        S2 = P - 0.618 * (H - L)
        S3 = P - (H - L)

        return {"P": P, "R1": R1, "R2": R2, "R3": R3, "S1": S1, "S2": S2, "S3": S3}

    @staticmethod
    def calculate_camarilla_pivots(df: pd.DataFrame) -> dict:
        """
        Camarilla Pivot Points (daha hassas)

        Args:
            df: OHLCV DataFrame

        Returns:
            {
                'P': Pivot,
                'R1': Resistance 1,
                'R2': Resistance 2,
                'R3': Resistance 3,
                'R4': Resistance 4,
                'S1': Support 1,
                'S2': Support 2,
                'S3': Support 3,
                'S4': Support 4
            }
        """
        if len(df) < 2:
            return {}

        last_bar = df.iloc[-2]
        H = last_bar["high"]
        L = last_bar["low"]
        C = last_bar["close"]

        P = (H + L + C) / 3
        R1 = C + 1.1 * (H - L) / 12
        R2 = C + 1.1 * (H - L) / 6
        R3 = C + 1.1 * (H - L) / 4
        R4 = C + 1.1 * (H - L) / 2

        S1 = C - 1.1 * (H - L) / 12
        S2 = C - 1.1 * (H - L) / 6
        S3 = C - 1.1 * (H - L) / 4
        S4 = C - 1.1 * (H - L) / 2

        return {
            "P": P,
            "R1": R1,
            "R2": R2,
            "R3": R3,
            "R4": R4,
            "S1": S1,
            "S2": S2,
            "S3": S3,
            "S4": S4,
        }
