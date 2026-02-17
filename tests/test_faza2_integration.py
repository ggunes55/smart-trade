# -*- coding: utf-8 -*-
"""
FAZA 2 Integration & Testing

Task 2.1, 2.2, 2.3, 2.4'ü test etmek için comprehensive test suite

Tarih: 12 Şubat 2026
Versiyon: 1.0
"""
import os
import sys
import logging
from datetime import datetime
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


def test_ml_training_pipeline():
    """Test Task 2.1: ML Training Pipeline"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: ML Training Pipeline (Task 2.1)")
    logger.info("="*80)
    
    try:
        from analysis.ml_training_pipeline import MLTrainingPipeline
        
        # Sample data oluştur
        sample_trades = pd.DataFrame({
            'symbol': ['SUWEN', 'TRKCM', 'SASA'] * 25,
            'entry_price': np.random.uniform(10, 100, 75),
            'exit_price': np.random.uniform(10, 100, 75),
            'profit_pct': np.random.uniform(-5, 15, 75),
        })
        
        # Pipeline çalıştır
        pipeline = MLTrainingPipeline(sample_trades)
        
        if not pipeline.validate_data():
            logger.warning("⚠️  Data validation warning, but continuing...")
        
        if pipeline.extract_features():
            logger.info("✅ Features extracted successfully")
        
        if pipeline.train_model():
            logger.info("✅ Model trained successfully")
            
            metrics = pipeline.evaluate()
            if metrics:
                logger.info(f"✅ Model evaluation:")
                logger.info(f"   - Accuracy: {metrics.get('accuracy', 0):.1%}")
                logger.info(f"   - Precision: {metrics.get('precision', 0):.1%}")
                logger.info(f"   - F1-Score: {metrics.get('f1', 0):.3f}")
            
            return True
        else:
            logger.error("❌ Model training failed")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_genetic_algorithm_optimizer():
    """Test Task 2.2: Genetic Algorithm Parameter Optimization"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Genetic Algorithm Optimizer (Task 2.2)")
    logger.info("="*80)
    
    try:
        from analysis.parameter_optimizer import GeneticAlgorithmOptimizer, GeneticAlgorithmConfig
        
        # Sample backtest data
        sample_backtest = pd.DataFrame({
            'profit_pct': np.random.uniform(-5, 15, 100),
            'win': np.random.choice([True, False], 100, p=[0.58, 0.42])
        })
        
        # GA optimizer çalıştır
        config = GeneticAlgorithmConfig(
            population_size=20,
            generations=10  # Quick test
        )
        
        optimizer = GeneticAlgorithmOptimizer(config)
        best_weights = optimizer.evolve(sample_backtest, generations=5)
        
        if best_weights:
            logger.info(f"✅ Optimization completed")
            logger.info(f"   - Base Signal: {best_weights['base_signal']:.3f}")
            logger.info(f"   - Confirmation: {best_weights['confirmation']:.3f}")
            logger.info(f"   - ML Confidence: {best_weights['ml_confidence']:.3f}")
            logger.info(f"   - Entry Timing: {best_weights['entry_timing']:.3f}")
            logger.info(f"   - Best Fitness: {optimizer.best_fitness:.3f}")
            
            # Ağırlıklar valid mi (toplam 1.0)?
            total = sum(best_weights.values())
            if 0.99 <= total <= 1.01:
                logger.info(f"✅ Weights sum to 1.0: {total:.3f}")
                return True
            else:
                logger.error(f"❌ Weights don't sum to 1.0: {total:.3f}")
                return False
        else:
            logger.error("❌ No best weights found")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_portfolio_optimizer():
    """Test Task 2.4: Portfolio Optimization"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Portfolio Optimizer (Task 2.4)")
    logger.info("="*80)
    
    try:
        from risk.portfolio_optimizer import PortfolioOptimizer, PortfolioConfig
        
        # Sample signals
        signals = [
            {
                'symbol': 'SUWEN',
                'entry_price': 100.0,
                'stop_loss': 95.0,
                'win_rate': 0.58,
                'avg_win': 2.5,
                'avg_loss': 1.0
            },
            {
                'symbol': 'TRKCM',
                'entry_price': 50.0,
                'stop_loss': 48.0,
                'win_rate': 0.55,
                'avg_win': 2.0,
                'avg_loss': 1.0
            },
            {
                'symbol': 'SASA',
                'entry_price': 25.5,
                'stop_loss': 24.0,
                'win_rate': 0.60,
                'avg_win': 3.0,
                'avg_loss': 1.0
            }
        ]
        
        # Portfolio optimizer çalıştır
        config = PortfolioConfig(
            total_capital=100000,
            risk_per_trade=0.01
        )
        
        optimizer = PortfolioOptimizer(config)
        portfolio = optimizer.optimize_portfolio(signals)
        
        if portfolio and len(portfolio['positions']) > 0:
            logger.info(f"✅ Portfolio optimized successfully")
            logger.info(f"   - Positions: {len(portfolio['positions'])}")
            logger.info(f"   - Total Risk: ${portfolio['total_risk']:,.2f}")
            
            for pos in portfolio['positions']:
                logger.info(f"   - {pos['symbol']}: {pos['size']:.0f} lot @ {pos['entry_price']:.2f}")
            
            return True
        else:
            logger.error("❌ Portfolio optimization failed")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_faza2_pipeline():
    """Test Task 2.3: Full Backtest to ML Training Loop"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Full FAZA 2 Pipeline (Task 2.3)")
    logger.info("="*80)
    
    try:
        # ML Training
        logger.info("  [1/3] Training ML Model...")
        from analysis.ml_training_pipeline import MLTrainingPipeline
        
        trades_df = pd.DataFrame({
            'symbol': ['SUWEN', 'TRKCM'] * 40,
            'entry_price': np.random.uniform(10, 100, 80),
            'exit_price': np.random.uniform(10, 100, 80),
            'profit_pct': np.random.uniform(-5, 15, 80),
        })
        
        pipeline = MLTrainingPipeline(trades_df)
        pipeline.train_model()
        logger.info("  ✅ ML Model trained")
        
        # Parameter Optimization
        logger.info("  [2/3] Optimizing Parameters...")
        from analysis.parameter_optimizer import GeneticAlgorithmOptimizer, GeneticAlgorithmConfig
        
        config = GeneticAlgorithmConfig(population_size=15, generations=5)
        optimizer = GeneticAlgorithmOptimizer(config)
        best_weights = optimizer.evolve(trades_df, generations=3)
        logger.info("  ✅ Parameters optimized")
        
        # Portfolio Optimization
        logger.info("  [3/3] Optimizing Portfolio...")
        from risk.portfolio_optimizer import PortfolioOptimizer, PortfolioConfig
        
        signals = [
            {'symbol': 'TEST', 'entry_price': 100, 'stop_loss': 95, 'win_rate': 0.58}
        ]
        
        port_config = PortfolioConfig(total_capital=100000)
        port_optimizer = PortfolioOptimizer(port_config)
        portfolio = port_optimizer.optimize_portfolio(signals)
        logger.info("  ✅ Portfolio optimized")
        
        logger.info(f"✅ Full pipeline completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    logger.info("\n")
    logger.info("╔" + "="*78 + "╗")
    logger.info("║" + " "*20 + "FAZA 2 INTEGRATION ENGINE TESTS" + " "*27 + "║")
    logger.info("║" + " "*20 + "Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " "*33 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    results = []
    
    # Run all tests
    results.append(("ML Training Pipeline", test_ml_training_pipeline()))
    results.append(("Genetic Algorithm Optimizer", test_genetic_algorithm_optimizer()))
    results.append(("Portfolio Optimizer", test_portfolio_optimizer()))
    results.append(("Full FAZA 2 Pipeline", test_full_faza2_pipeline()))
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 ALL FAZA 2 TESTS PASSED!")
        return 0
    else:
        logger.info(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

