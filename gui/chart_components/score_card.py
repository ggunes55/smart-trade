"""
Score Card HUD - Swing Trade skor kartı
"""

import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class ScoreCardHUD(QWidget):
    """
    Swing Trade Skor Kartı - Sağ üst köşe HUD
    - Trend skoru
    - Momentum skoru
    - Volatilite skoru
    - Toplam puan
    """

    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.df = df
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self):
        """UI oluştur"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Ana container
        container = QWidget()
        container.setStyleSheet(
            """
            QWidget {
                background-color: rgba(255, 255, 255, 220);
                border: 2px solid #2196F3;
                border-radius: 10px;
            }
        """
        )

        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(8)

        # Başlık
        title = QLabel("📊 SWING SKOR KARTI")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #1976D2;")
        title.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title)

        # Skorları hesapla
        scores = self._calculate_scores()

        # Trend
        trend_label = self._create_score_label(
            "Trend:", scores["trend"]["emoji"], scores["trend"]["text"]
        )
        container_layout.addWidget(trend_label)

        # Momentum
        momentum_label = self._create_score_label(
            "Momentum:", scores["momentum"]["emoji"], scores["momentum"]["text"]
        )
        container_layout.addWidget(momentum_label)

        # Volatilite
        volatility_label = self._create_score_label(
            "Volatilite:", scores["volatility"]["emoji"], scores["volatility"]["text"]
        )
        container_layout.addWidget(volatility_label)


        # Genel Puan
        container_layout.addSpacing(5)
        total_score = scores["total_score"]
        score_color = (
            "#4CAF50"
            if total_score >= 7
            else "#FF9800" if total_score >= 5 else "#F44336"
        )

        total_label = QLabel(f"⭐ Genel Puan: {total_score}/10")
        total_label.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {score_color};"
        )
        total_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(total_label)

        # --- Gelişmiş metrikler özeti ---
        if hasattr(self.df, 'trend_score_result') and self.df.trend_score_result:
            result = self.df.trend_score_result
            # Rolling correlation
            for comp in result.get('components', []):
                if comp.get('category', '').startswith('Rolling Correlation'):
                    rc = comp['details'].get('rolling_corr', None)
                    if rc is not None:
                        rc_label = QLabel(f"🔄 Endeks Korelasyonu (30g): {rc:.2f}")
                        rc_label.setStyleSheet("font-size: 11px; color: #607D8B;")
                        rc_label.setAlignment(Qt.AlignCenter)
                        container_layout.addWidget(rc_label)
            # Composite score
            comp_label = QLabel(f"🧮 Composite Score: {result.get('total_score', 0)}/100")
            comp_label.setStyleSheet("font-size: 11px; color: #607D8B;")
            comp_label.setAlignment(Qt.AlignCenter)
            container_layout.addWidget(comp_label)

        layout.addWidget(container)

    def _create_score_label(self, title: str, emoji: str, text: str) -> QLabel:
        """Skor etiketi oluştur"""
        label = QLabel(f"{title} {emoji} {text}")
        label.setStyleSheet("font-size: 11px; padding: 3px;")
        return label

    def _calculate_scores(self) -> dict:
        """Skorları hesapla"""
        if len(self.df) < 50:
            return self._default_scores()

        last_bar = self.df.iloc[-1]

        # Trend Skoru (EMA20 vs EMA50)
        ema20 = last_bar.get("EMA20", 0)
        ema50 = last_bar.get("EMA50", 0)

        if ema20 > ema50:
            trend = {"emoji": "🟢", "text": "Yükseliş", "score": 3}
        elif ema20 < ema50:
            trend = {"emoji": "🔴", "text": "Düşüş", "score": 1}
        else:
            trend = {"emoji": "🟡", "text": "Yatay", "score": 2}

        # Momentum Skoru (RSI)
        rsi = last_bar.get("RSI", 50)

        if rsi > 70:
            momentum = {"emoji": "🔥", "text": "AŞIRI Alım", "score": 1}
        elif rsi > 55:
            momentum = {"emoji": "🟢", "text": "Güçlü", "score": 3}
        elif rsi > 45:
            momentum = {"emoji": "🟡", "text": "Nötr", "score": 2}
        elif rsi > 30:
            momentum = {"emoji": "🔵", "text": "Zayıf", "score": 2}
        else:
            momentum = {"emoji": "❄️", "text": "AŞIRI Satım", "score": 3}

        # Volatilite Skoru (BB Squeeze)
        bb_squeeze = last_bar.get("BB_Squeeze", False)

        if bb_squeeze:
            volatility = {"emoji": "🟡", "text": "Sıkışma!", "score": 4}
        else:
            bb_width = last_bar.get("BB_Width", 0)
            if bb_width > 0.05:
                volatility = {"emoji": "📈", "text": "Yüksek", "score": 2}
            else:
                volatility = {"emoji": "📊", "text": "Normal", "score": 3}

        total_score = trend["score"] + momentum["score"] + volatility["score"]

        return {
            "trend": trend,
            "momentum": momentum,
            "volatility": volatility,
            "total_score": total_score,
        }

    def _default_scores(self) -> dict:
        """Varsayılan skorlar"""
        return {
            "trend": {"emoji": "⚪", "text": "Belirsiz", "score": 0},
            "momentum": {"emoji": "⚪", "text": "Belirsiz", "score": 0},
            "volatility": {"emoji": "⚪", "text": "Belirsiz", "score": 0},
            "total_score": 0,
        }
