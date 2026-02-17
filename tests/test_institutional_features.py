
import unittest
import pandas as pd
import numpy as np
import logging
from analysis.signal_confirmation import SignalConfirmationFilter
from analysis.ml_signal_classifier import MLSignalClassifier

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class TestInstitutionalFeatures(unittest.TestCase):

    def setUp(self):
        # Create dummy data for testing
        dates = pd.date_range(start="2024-01-01", periods=100)
        self.df = pd.DataFrame({
            'open': np.random.rand(100) * 100,
            'high': np.random.rand(100) * 100,
            'low': np.random.rand(100) * 100,
            'close': np.random.rand(100) * 100,
            'volume': np.random.rand(100) * 1000000,
            'rsi': np.random.rand(100) * 100,
            'macd': np.random.randn(100),
            'macd_signal': np.random.randn(100),
            'macd_hist': np.random.randn(100),
            'adx': np.random.rand(100) * 50,
            'atr': np.random.rand(100) * 2
        }, index=dates)
        
        # Ensure some logical consistency for checks
        self.df['close'] = self.df['close'].rolling(5).mean().fillna(50)
        self.df['volume'] = self.df['volume'].rolling(5).mean().fillna(100000)

        self.config = {
            'use_signal_confirmation': True,
            'strict_confirmation_mode': False
        }

    def test_signal_confirmation(self):
        print("\nTesting SignalConfirmationFilter...")
        confirmer = SignalConfirmationFilter(self.df, self.config)
        is_valid, details = confirmer.multi_source_confirmation()
        
        print(f"Confirmation Result: {is_valid}")
        print(f"Details: {details}")
        
        self.assertIn('is_valid', details)
        self.assertIn('confidence', details)
        self.assertIsInstance(is_valid, bool)

    def test_ml_classifier(self):
        print("\nTesting MLSignalClassifier...")
        classifier = MLSignalClassifier()
        
        # Test prediction without training
        features = {
            'rsi': 50,
            'macd': 0.5,
            'adx': 25,
            'volume_ratio': 1.2,
            'trend_score': 70,
            'atr_percent': 2.0,
            'volatility': 20
        }
        
        prediction = classifier.predict_signal_quality(features)
        print(f"Prediction (Untrained): {prediction}")
        self.assertIn('prediction', prediction)
        
        # If sklearn is available, try a mini training session
        try:
            import sklearn
            print("sklearn found, attempting training...")
            
            # Create dummy historical trades
            trades = []
            for _ in range(60):
                trades.append({
                    'features': features,
                    'profit_pct': np.random.uniform(-5, 10)
                })
            
            classifier.train(trades)
            print("Training completed.")
            
            prediction_trained = classifier.predict_signal_quality(features)
            print(f"Prediction (Trained): {prediction_trained}")
            self.assertNotEqual(prediction_trained['prediction'], 'UNKNOWN')
            
        except ImportError:
            print("sklearn not found, skipping training test.")

if __name__ == '__main__':
    unittest.main()
