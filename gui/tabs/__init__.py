# -*- coding: utf-8 -*-
"""
Tabs modülü
"""
from .symbols_tab import SymbolsTab
from .criteria_tab import CriteriaTab
from .results_tab import ResultsTab
from .market_tab import MarketTab
from .chart_tab import ChartTab  # 🆕 Yeni
from .watchlist_tab import WatchlistTab  # Phase 1
from .analysis_tab import AnalysisTab  # 🆕 Detaylı Analiz Sekmesi
from .portfolio_tab import PortfolioTab  # 🆕 Portfolio Yönetimi
from .settings_tab import SettingsTab  # 🆕 Ayarlar
from .readme_tab import ReadmeTab  # 🆕 Hakkında
from .backtest_results_tab import BacktestResultsTab, BacktestVisualizer  # 🆕 Backtest Görselleştirme
from .ml_management_tab import MLManagementTab, MLModelRegistry, MLModelVersion  # 🆕 ML Yönetimi

__all__ = [
    "SymbolsTab", 
    "CriteriaTab", 
    "ResultsTab", 
    "MarketTab", 
    "ChartTab", 
    "WatchlistTab", 
    "AnalysisTab",
    "PortfolioTab",
    "SettingsTab",
    "ReadmeTab",
    "BacktestResultsTab",
    "BacktestVisualizer",
    "MLManagementTab",
    "MLModelRegistry",
    "MLModelVersion",
]

