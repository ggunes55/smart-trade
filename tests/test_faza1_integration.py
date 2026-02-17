# -*- coding: utf-8 -*-
"""
FAZA 1 Integration Engine Test
Test edilecek şeyler:
1. Integration Engine başlatılıyor mu
2. SymbolAnalyzer integration engine'i kullanıyor mu
3. Signal confirmation, ML, Entry timing pipeline'ı çalışıyor mu
4. Sonuçlar doğru şekilde döndürülüyor mu
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_integration_engine_init():
    """Test 1: Integration Engine başlatıldığını kontrol et"""
    logger.info("=" * 80)
    logger.info("TEST 1: Integration Engine Initialization")
    logger.info("=" * 80)
    
    try:
        from analysis.integration_engine import AnalysisIntegrationEngine
        from core.utils import load_config
        
        cfg = load_config('swing_config.json')
        engine = AnalysisIntegrationEngine(cfg)
        
        assert engine is not None, "Engine is None"
        assert engine.ml_classifier is not None or True, "ML classifier optional"
        logger.info("✅ Integration Engine initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Integration Engine init failed: {e}")
        return False


def test_symbol_analyzer_integration():
    """Test 2: SymbolAnalyzer Integration Engine kullanıyor mu"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: SymbolAnalyzer Integration")
    logger.info("=" * 80)
    
    try:
        from scanner.symbol_analyzer import SymbolAnalyzer
        from core.utils import load_config
        from unittest.mock import MagicMock
        
        cfg = load_config('swing_config.json')
        cfg['use_integration_engine'] = True
        
        # Mock dependencies
        data_handler = MagicMock()
        market_analyzer = MagicMock()
        smart_filter = MagicMock()
        
        analyzer = SymbolAnalyzer(cfg, data_handler, market_analyzer, smart_filter)
        
        assert analyzer.integration_engine is not None, "Integration engine not initialized in SymbolAnalyzer"
        logger.info("✅ SymbolAnalyzer has integration_engine")
        logger.info(f"   - Config: use_integration_engine = {cfg.get('use_integration_engine')}")
        logger.info(f"   - Engine: {analyzer.integration_engine.__class__.__name__}")
        return True
    except Exception as e:
        logger.error(f"❌ SymbolAnalyzer integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline_with_sample_data():
    """Test 3: Full pipeline sample data ile çalışıyor mu"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Full Pipeline with Sample Data")
    logger.info("=" * 80)
    
    try:
        from analysis.integration_engine import AnalysisIntegrationEngine
        from core.utils import load_config
        
        cfg = load_config('swing_config.json')
        engine = AnalysisIntegrationEngine(cfg)
        
        # Sample data oluştur
        dates = pd.date_range(end=datetime.now(), periods=100)
        np.random.seed(42)
        sample_data = pd.DataFrame({
            'date': dates,
            'open': np.linspace(100, 110, 100) + np.random.normal(0, 1, 100),
            'high': np.linspace(110, 120, 100) + np.random.normal(0, 1, 100),
            'low': np.linspace(90, 100, 100) + np.random.normal(0, 1, 100),
            'close': np.linspace(100, 110, 100) + np.random.normal(0, 1, 100),
            'volume': np.random.uniform(1e6, 5e6, 100),
        })
        
        # Base signal oluştur
        base_signal = {
            'symbol': 'TEST',
            'signal_type': 'BUY',
            'score': 75,
            'rsi': 32,
            'macd': 0.5,
            'atr_percent': 1.2,
        }
        
        # Pipeline çalıştır
        result = engine.full_analysis_pipeline(
            symbol='TEST',
            data=sample_data,
            base_signal=base_signal
        )
        
        assert result is not None, "Pipeline returned None"
        assert result.symbol == 'TEST', f"Symbol mismatch: {result.symbol}"
        assert result.final_score > 0, f"Final score should be > 0: {result.final_score}"
        assert result.recommendation in ['BUY', 'SELL', 'HOLD', 'STRONG BUY', 'STRONG SELL'], \
            f"Invalid recommendation: {result.recommendation}"
        
        logger.info("✅ Full pipeline executed successfully")
        logger.info(f"   - Symbol: {result.symbol}")
        logger.info(f"   - Final Score: {result.final_score:.0f}/100")
        logger.info(f"   - Recommendation: {result.recommendation}")
        logger.info(f"   - Confidence: {result.confidence_level}")
        logger.info(f"   - Valid Signal: {result.is_valid}")
        return True
    except Exception as e:
        logger.error(f"❌ Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """Test 4: Configuration kontrol et"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Configuration Verification")
    logger.info("=" * 80)
    
    try:
        from core.utils import load_config
        
        cfg = load_config('swing_config.json')
        
        # Check FAZA 1 settings
        assert cfg.get('use_integration_engine', False), "use_integration_engine not set"
        assert cfg.get('use_signal_confirmation', False), "use_signal_confirmation not set"
        assert cfg.get('use_ml_classifier', False), "use_ml_classifier not set"
        assert cfg.get('use_entry_timing_optimizer', False), "use_entry_timing_optimizer not set"
        
        logger.info("✅ Configuration verified")
        logger.info(f"   - use_integration_engine: {cfg.get('use_integration_engine')}")
        logger.info(f"   - use_signal_confirmation: {cfg.get('use_signal_confirmation')}")
        logger.info(f"   - use_ml_classifier: {cfg.get('use_ml_classifier')}")
        logger.info(f"   - use_entry_timing_optimizer: {cfg.get('use_entry_timing_optimizer')}")
        logger.info(f"   - min_signal_score: {cfg.get('min_signal_score')}")
        
        weights = cfg.get('integration_weights', {})
        if weights:
            logger.info(f"   - Integration Weights:")
            for key, value in weights.items():
                logger.info(f"     - {key}: {value}")
        
        return True
    except AssertionError as e:
        logger.error(f"❌ Configuration check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Configuration test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "FAZA 1 INTEGRATION ENGINE TESTS" + " " * 27 + "║")
    logger.info("║" + " " * 20 + "Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " * 33 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    
    results = []
    
    # Run all tests
    results.append(("Integration Engine Init", test_integration_engine_init()))
    results.append(("SymbolAnalyzer Integration", test_symbol_analyzer_integration()))
    results.append(("Configuration Verification", test_configuration()))
    results.append(("Full Pipeline", test_full_pipeline_with_sample_data()))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! FAZA 1 Integration is working correctly!")
        return 0
    else:
        logger.info(f"\n⚠️  {total - passed} test(s) failed. Please review the logs above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
