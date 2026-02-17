# analysis module

# v2.7.3: Signal Confirmation entegrasyonu
try:
    from analysis.signal_confirmation import SignalConfirmationFilter
except ImportError:
    pass  # Optional feature

# v2.8: Market Regime Adapter, Entry Timing, Kalman Filter
try:
    from analysis.market_regime_adapter import MarketRegimeAdapter, MarketRegime
    from analysis.entry_timing import EntryTimingOptimizer, SignalType
    from analysis.kalman_filter import KalmanPriceFilter, apply_kalman_smoothing
except ImportError:
    pass  # Optional v2.8 features
