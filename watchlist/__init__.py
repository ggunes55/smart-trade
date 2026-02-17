"""
Watchlist Module (V2.0) - Professional Swing Trade Tracking
Portfolio tracking, alert system, and performance analysis
"""
from .database import (
    WatchlistEntry, 
    WatchlistSnapshot, 
    WatchlistAlert,
    init_db,
    migrate_database,
    StatusLabel,
    SetupStatus,
    TrendDirection,
    AlertType
)
from .watchlist_manager import WatchlistManager
from .performance_analyzer import PerformanceAnalyzer
from .correlation_analyzer import CorrelationAnalyzer
from .risk_manager import RiskManager

__all__ = [
    # Models
    'WatchlistEntry',
    'WatchlistSnapshot',
    'WatchlistAlert',
    
    # Manager
    'WatchlistManager',
    'PerformanceAnalyzer',
    'CorrelationAnalyzer',
    'RiskManager',
    
    # Functions
    'init_db',
    'migrate_database',
    
    # Enums
    'StatusLabel',
    'SetupStatus', 
    'TrendDirection',
    'AlertType',
]
