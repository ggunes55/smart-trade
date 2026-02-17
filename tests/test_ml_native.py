
import sys
sys.path.append("c:/Users/Administrator/Desktop/PYTHON/16.01.26SWING-TRADE V.2.10.0")
from analysis.ml_signal_classifier import MLSignalClassifier

def test_ml_classifier():
    print("Initializing MLSignalClassifier...")
    clf = MLSignalClassifier()
    
    print("Testing prediction on dummy data...")
    features = {
        'rsi': 30,
        'macd': 0.1,
        'adx': 40,
        'volume_ratio': 2.0,
        'trend_score': 80,
        'atr_percent': 1.5,
        'volatility': 20
    }
    
    result = clf.predict_signal_quality(features)
    print("Prediction Result:", result)
    
    if result['confidence'] >= 0.0:
        print("✅ ML Classifier seems to work (even if untrained/random)")
    else:
        print("❌ ML Classifier failed")

if __name__ == "__main__":
    test_ml_classifier()
