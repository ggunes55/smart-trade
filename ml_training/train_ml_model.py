# -*- coding: utf-8 -*-
"""
ML Eğitim Betiği - FAZA 2: Backtest to ML Training Loop

Bu betik:
1. Backtest sonuçlarını toplar veya CSV'den okur
2. FAZA 2 ML Training Pipeline kullanarak modeli eğitir
3. Genetic Algorithm ile parameter optimization yapar
4. Optimized ağırlıkları config'e kaydeder
5. Portfolio optimizer ile position sizing yapar

Kullanım:
    python train_ml_model.py
    
FAZA 2 Task 2.3: Backtest to ML Training Loop
Tarih: 12 Şubat 2026
Versiyon: 2.0
"""
import logging
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Proje dizinini ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# FAZA 2 imports
from analysis.ml_signal_classifier import MLSignalClassifier
from analysis.trade_collector import TradeCollector
from analysis.ml_training_pipeline import MLTrainingPipeline
from analysis.parameter_optimizer import GeneticAlgorithmOptimizer, GeneticAlgorithmConfig
from risk.portfolio_optimizer import PortfolioOptimizer, PortfolioConfig

# Legacy import
try:
    from analysis.trade_collector import TradeCollector
except ImportError:
    TradeCollector = None

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_backtest_data() -> pd.DataFrame:
    """Backtest verisi yükleme (CSV veya TradeCollector'dan)"""
    
    # 1. CSV'den yüklemeyi dene
    csv_path = Path('data_cache/ml_training_data.csv')
    if csv_path.exists():
        logger.info(f"📁 Loading backtest data from {csv_path}")
        df = pd.read_csv(csv_path)
        logger.info(f"✅ Loaded {len(df)} trades from CSV")
        return df
    
    # 2. TradeCollector'dan topla
    if TradeCollector:
        try:
            logger.info("📊 Collecting trades from TradeCollector...")
            collector = TradeCollector()
            trades = collector.load_data()
            
            if trades:
                df = pd.DataFrame(trades)
                logger.info(f"✅ Collected {len(df)} trades")
                
                # CSV'ye kaydet
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(csv_path, index=False)
                logger.info(f"💾 Saved to {csv_path}")
                return df
        except Exception as e:
            logger.warning(f"TradeCollector error: {e}")
    
    # 3. Örnek veri oluştur (test için)
    logger.warning("⚠️  No backtest data found. Creating sample data for testing...")
    sample_trades = pd.DataFrame({
        'symbol': ['SUWEN', 'TRKCM', 'SASA'] * 30,
        'entry_date': pd.date_range('2025-01-01', periods=90),
        'entry_price': np.random.uniform(10, 100, 90),
        'exit_date': pd.date_range('2025-01-02', periods=90),
        'exit_price': np.random.uniform(10, 100, 90),
        'profit_pct': np.random.uniform(-5, 15, 90),
    })
    
    logger.info(f"📊 Created sample data with {len(sample_trades)} trades")
    return sample_trades


def main():
    logger.info("=" * 80)
    logger.info("🚀 FAZA 2: ML Training & Optimization Pipeline Started")
    logger.info("=" * 80)
    
    # ========================================================================
    # STEP 1: Load Backtest Data
    # ========================================================================
    logger.info("\n[STEP 1/4] Loading Backtest Data...")
    trades_df = load_backtest_data()
    
    if trades_df is None or len(trades_df) == 0:
        logger.error("❌ No backtest data available!")
        return False
    
    logger.info(f"✅ Loaded {len(trades_df)} trades")
    logger.info(f"   - Profit range: {trades_df['profit_pct'].min():.2f}% to {trades_df['profit_pct'].max():.2f}%")
    logger.info(f"   - Win rate: {(trades_df['profit_pct'] > 0).sum() / len(trades_df):.1%}")
    
    # ========================================================================
    # STEP 2: Train ML Model (Task 2.1)
    # ========================================================================
    logger.info("\n[STEP 2/4] Training ML Model (Task 2.1)...")
    
    try:
        ml_pipeline = MLTrainingPipeline(trades_df)
        
        if not ml_pipeline.validate_data():
            logger.warning("⚠️  Data validation failed, but continuing...")
        
        if ml_pipeline.train_model():
            metrics = ml_pipeline.evaluate()
            
            # Model'i kaydet
            model_path = 'models/signal_predictor_faza2.pkl'
            if ml_pipeline.save_model(model_path):
                logger.info(f"✅ ML Model trained and saved")
                logger.info(f"   - Accuracy: {metrics.get('accuracy', 0):.1%}")
                logger.info(f"   - F1-Score: {metrics.get('f1', 0):.3f}")
                logger.info(f"   - AUC-ROC: {metrics.get('auc_roc', 0):.3f}")
            else:
                logger.error("❌ Model save failed")
                return False
        else:
            logger.error("❌ Model training failed")
            return False
    
    except Exception as e:
        logger.error(f"❌ ML Training error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================================================
    # STEP 3: Optimize Parameters (Task 2.2)
    # ========================================================================
    logger.info("\n[STEP 3/4] Optimizing Integration Engine Parameters (Task 2.2)...")
    
    try:
        ga_config = GeneticAlgorithmConfig(
            population_size=30,
            generations=50,  # Düşük test için
            mutation_rate=0.15
        )
        
        optimizer = GeneticAlgorithmOptimizer(ga_config)
        best_weights = optimizer.evolve(trades_df, generations=10)  # Quick test: 10 gen
        
        # Optimized ağırlıkları kaydet
        results_path = 'analysis/optimized_weights_faza2.json'
        if optimizer.save_results(results_path):
            logger.info(f"✅ Parameters optimized and saved")
            logger.info(f"   - Base Signal: {best_weights['base_signal']:.3f}")
            logger.info(f"   - Confirmation: {best_weights['confirmation']:.3f}")
            logger.info(f"   - ML Confidence: {best_weights['ml_confidence']:.3f}")
            logger.info(f"   - Entry Timing: {best_weights['entry_timing']:.3f}")
            logger.info(f"   - Best Fitness: {optimizer.best_fitness:.3f}")
        else:
            logger.error("❌ Results save failed")
            return False
    
    except Exception as e:
        logger.error(f"❌ Parameter optimization error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================================================
    # STEP 4: Portfolio Optimization (Task 2.4)
    # ========================================================================
    logger.info("\n[STEP 4/4] Optimizing Portfolio (Task 2.4)...")
    
    try:
        # Örnek sinyaller (backtest'ten en iyi işlemler)
        top_trades = trades_df.nlargest(5, 'profit_pct')
        signals = []
        
        for idx, trade in top_trades.iterrows():
            signal = {
                'symbol': trade.get('symbol', f'SYM_{idx}'),
                'entry_price': float(trade.get('entry_price', 100)),
                'stop_loss': float(trade.get('entry_price', 100) * 0.95),  # %5 stop loss
                'win_rate': (trades_df['profit_pct'] > 0).sum() / len(trades_df),
                'avg_win': trades_df[trades_df['profit_pct'] > 0]['profit_pct'].mean(),
                'avg_loss': abs(trades_df[trades_df['profit_pct'] <= 0]['profit_pct'].mean())
            }
            signals.append(signal)
        
        portfolio_config = PortfolioConfig(
            total_capital=100000,
            risk_per_trade=0.01,
            position_size_method='kelly'
        )
        
        portfolio_optimizer = PortfolioOptimizer(portfolio_config)
        portfolio = portfolio_optimizer.optimize_portfolio(signals)
        
        portfolio_path = 'analysis/optimized_portfolio_faza2.json'
        if portfolio_optimizer.save_portfolio(portfolio, portfolio_path):
            logger.info(f"✅ Portfolio optimized and saved")
            logger.info(f"   - Positions: {len(portfolio['positions'])}")
            logger.info(f"   - Total Risk: ${portfolio['total_risk']:,.2f}")
        else:
            logger.error("❌ Portfolio save failed")
            return False
    
    except Exception as e:
        logger.error(f"❌ Portfolio optimization error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================================================
    # Legacy: FAZA 1 ML Classifier (Backwards compatibility)
    # ========================================================================
    logger.info("\n[LEGACY] Updating FAZA 1 ML Classifier...")
    
    try:
        classifier = MLSignalClassifier()
        
        if not classifier.is_trained:
            logger.info("Training legacy ML classifier...")
            # Legacy training (if supported)
            if hasattr(classifier, 'train'):
                classifier.train(trades_df.to_dict('records'))
        
        logger.info(f"✅ Legacy classifier status: {'Trained' if classifier.is_trained else 'Not trained'}")
    
    except Exception as e:
        logger.warning(f"Legacy classifier update skipped: {e}")
    
    # ========================================================================
    # Summary
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("✅ FAZA 2 TRAINING PIPELINE COMPLETED SUCCESSFULLY!")
    logger.info("=" * 80)
    logger.info("\nGenerated Files:")
    logger.info(f"  1. models/signal_predictor_faza2.pkl (ML Model)")
    logger.info(f"  2. analysis/optimized_weights_faza2.json (Optimized Weights)")
    logger.info(f"  3. analysis/optimized_portfolio_faza2.json (Portfolio Config)")
    logger.info("\nNext Steps:")
    logger.info("  - Use optimized weights in swing_config.json")
    logger.info("  - Run live trading with portfolio config")
    logger.info("  - Monitor performance metrics")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
