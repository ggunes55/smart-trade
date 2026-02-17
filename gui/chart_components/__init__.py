"""
Chart Components Package - Modüler grafik bileşenleri
"""

# Config
from .config import (
    REQUIRED_COLUMNS,
    THEMES,
    CURRENT_THEME,
    EMA_CONFIG,
    PATTERN_CONFIG,
    PATTERN_DESCRIPTIONS,
    get_theme,
    set_theme,
)

# Core Components
from .candles import CandlestickItem
from .indicators import IndicatorCalculator
from .patterns import PatternRecognizer
from .volume_profile import VolumeProfile, FixedRangeVolumeProfile
from .pivot_points import PivotPointsCalculator
from .price_alerts import PriceAlert
from .risk_reward import RiskRewardTool
from .score_card import ScoreCardHUD
from .fundamental_analysis import FundamentalAnalysis
from .fundamental_widget import FundamentalPanel, FundamentalDetailDialog
from .multi_timeframe import MultiTimeframeManager, MultiTimeframeAnalyzer
from .swing_divergence_analyzer import SwingDivergenceAnalyzer

# Reporting
from gui.reporting.report_generator import ReportGenerator

# Drawing Tools
from .drawing_tools import (
    BaseTool,
    MeasureTool,
    TrendLineTool,
    FibonacciTool,
    HorizontalLineTool,
    ChannelTool,
    RectangleTool,
    TextAnnotationTool,
    CrosshairCursor,
)

__all__ = [
    # Config
    "REQUIRED_COLUMNS",
    "THEMES",
    "CURRENT_THEME",
    "EMA_CONFIG",
    "PATTERN_CONFIG",
    "PATTERN_DESCRIPTIONS",
    "get_theme",
    "set_theme",
    # Core Components
    "CandlestickItem",
    "IndicatorCalculator",
    "PatternRecognizer",
    "VolumeProfile",
    "FixedRangeVolumeProfile",
    "PivotPointsCalculator",
    "PriceAlert",
    "RiskRewardTool",
    "ScoreCardHUD",
    "FundamentalAnalysis",
    "FundamentalPanel",
    "FundamentalDetailDialog",
    "MultiTimeframeManager",
    "MultiTimeframeAnalyzer",
    "SwingDivergenceAnalyzer",
    # Drawing Tools
    "BaseTool",
    "MeasureTool",
    "TrendLineTool",
    "FibonacciTool",
    "HorizontalLineTool",
    "ChannelTool",
    "RectangleTool",
    "TextAnnotationTool",
    "CrosshairCursor",
]

__version__ = "2.0.0"
__author__ = "Swing Analyzer Team"
