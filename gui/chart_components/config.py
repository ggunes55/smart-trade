"""
Chart Configuration - Tema, sabitler, global ayarlar
"""

from PyQt5.QtCore import Qt

# Zorunlu kolonlar
REQUIRED_COLUMNS = {"open", "high", "low", "close", "volume"}

# Tema ayarları
THEMES = {
    "light": {
        "background": "w",
        "foreground": "k",
        "grid": "#E0E0E0",
        "candle_up": "#2E7D32",
        "candle_down": "#C62828",
    },
    "dark": {
        "background": "#1E1E1E",
        "foreground": "w",
        "grid": "#424242",
        "candle_up": "#4CAF50",
        "candle_down": "#F44336",
    },
}

# Global tema
CURRENT_THEME = "light"

# EMA Konfigürasyonu
EMA_CONFIG = {
    "EMA9": dict(period=9, color="#FF9800", width=1.3, style=Qt.DashLine),
    "EMA20": dict(period=20, color="#FF5722", width=1.6, style=Qt.DashLine),
    "EMA50": dict(period=50, color="#2196F3", width=2.0, style=Qt.SolidLine),
    "SMA200": dict(period=200, color="#9C27B0", width=2.4, style=Qt.SolidLine),
}

# Fibonacci seviyeleri
FIBONACCI_RETRACEMENT_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]
FIBONACCI_RETRACEMENT_COLORS = [
    "#F44336",
    "#FF9800",
    "#FFEB3B",
    "#4CAF50",
    "#2196F3",
    "#9C27B0",
    "#E91E63",
]
FIBONACCI_RETRACEMENT_NAMES = ["0%", "23.6%", "38.2%", "50%", "61.8%", "78.6%", "100%"]

FIBONACCI_EXTENSION_LEVELS = [0, 0.618, 1, 1.272, 1.618, 2, 2.618]
FIBONACCI_EXTENSION_COLORS = [
    "#F44336",
    "#FF9800",
    "#FFEB3B",
    "#4CAF50",
    "#2196F3",
    "#9C27B0",
    "#E91E63",
]
FIBONACCI_EXTENSION_NAMES = [
    "0%",
    "61.8%",
    "100%",
    "127.2%",
    "161.8%",
    "200%",
    "261.8%",
]

# Pattern sembolleri ve renkler
PATTERN_CONFIG = {
    "hammer": {"symbol": "t1", "color": "#4CAF50", "size": 12},
    "shooting_star": {"symbol": "t", "color": "#F44336", "size": 12},
    "engulfing_bullish": {"symbol": "t1", "color": "#2E7D32", "size": 14},
    "engulfing_bearish": {"symbol": "t", "color": "#C62828", "size": 14},
    "doji": {"symbol": "o", "color": "#FF9800", "size": 10},
    "morning_star": {"symbol": "star", "color": "#00BCD4", "size": 16},
    "evening_star": {"symbol": "star", "color": "#E91E63", "size": 16},
}

PATTERN_DESCRIPTIONS = {
    "hammer": "🔨 Çekiç\nGüçlü yükseliş sinyali",
    "shooting_star": "⭐ Düşen Yıldız\nGüçlü düşüş sinyali",
    "engulfing_bullish": "📈 Yutan Boğa\nGüçlü yükseliş",
    "engulfing_bearish": "📉 Yutan Ayı\nGüçlü düşüş",
    "doji": "🎯 Doji\nKararsızlık",
    "morning_star": "🌅 Sabah Yıldızı\nYükseliş dönüşü",
    "evening_star": "🌆 Akşam Yıldızı\nDüşüş dönüşü",
}


def get_theme():
    """Aktif temayı döndür"""
    return THEMES[CURRENT_THEME]


def set_theme(theme_name: str):
    """Temayı değiştir"""
    global CURRENT_THEME
    if theme_name in THEMES:
        CURRENT_THEME = theme_name
        return True
    return False
