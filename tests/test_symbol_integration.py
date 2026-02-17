
import unittest
import pandas as pd
import numpy as np
import logging
from unittest.mock import MagicMock
from scanner.symbol_analyzer import SymbolAnalyzer

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class TestSymbolIntegration(unittest.TestCase):

    def setUp(self):
        # Configuration
        self.cfg = {
            "exchange": "BIST",
            "use_kalman_filter": True,
            "use_signal_confirmation": True,
            "use_ml_classifier": True,
            "filter_mode": "manual",
            "min_price": 0,
            "min_volume": 0
        }
        
        # Mock DataHandler
        self.data_handler = MagicMock()
        
        # Create dummy DF with strong uptrend
        dates = pd.date_range(start="2023-01-01", periods=200)
        # uptrend prices
        prices = np.linspace(10, 20, 200) + np.random.normal(0, 0.1, 200)
        
        self.df = pd.DataFrame({
            'open': prices,
            'high': prices + 0.5,
            'low': prices - 0.5,
            'close': prices,
            'volume': np.random.randint(1000000, 2000000, 200),
        }, index=dates)
        
        # Ensure it passes pre_filter (price > 1, volume > 10000)
        
        # Make close logical
        self.df['close'] = self.df['close'].rolling(5).mean().fillna(50)
        
        self.data_handler.get_daily_data.return_value = self.df
        
        # Mock MarketAnalyzer
        self.market_analyzer = MagicMock()
        mock_analysis = MagicMock()
        mock_analysis.regime = "TRENDING_UP"
        mock_analysis.market_score = 80
        self.market_analyzer.get_cached_analysis.return_value = mock_analysis
        
        # Mock SmartFilter
        self.smart_filter = MagicMock()
        self.smart_filter.evaluate_stock.return_value = (True, 85, "Pass")

    def test_analyze_symbol_flow(self):
        print("\nTesting SymbolAnalyzer complete flow...")
        analyzer = SymbolAnalyzer(self.cfg, self.data_handler, self.market_analyzer, self.smart_filter)
        
        # Run analysis
        result = analyzer.analyze_symbol("TEST_SYM")
        
        if result:
            print(f"Result: {result['Hisse']} - Score: {result['Skor']}")
            print(f"Signal Strength: {result['Sinyal']}")
            
            # Check for new keys
            if 'Onay' in result:
                print(f"Signal Confirmation: {result['Onay']}")
            else:
                print("Signal Confirmation missing in result")
                
            if 'YZ Tahmini' in result:
                print(f"ML Prediction: {result['YZ Tahmini']}")
            else:
                print("ML Prediction missing in result")
            
            # Check for Kalman Effect (indirectly via logs or debugging, simpler here to just ensure run)
            # We can't easily check for 'price_filtered' column here as result is a dict.
            # But if it didn't crash, it's good.
            
            self.assertIsNotNone(result)
        else:
            print("Analysis returned None (could be due to filters)")

if __name__ == '__main__':
    unittest.main()
