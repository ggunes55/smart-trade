# -*- coding: utf-8 -*-
"""
Phase 2 Analytics Engine - Verification Test Suite
Tests: CorrelationAnalyzer, RiskManager, Database Integration
"""
import os
import sys
import logging
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from watchlist.database import (
    migrate_database, WatchlistEntry
)
from watchlist.watchlist_manager import WatchlistManager
from watchlist.risk_manager import RiskManager
from watchlist.correlation_analyzer import CorrelationAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import time
DB_PATH = f"watchlist_test_phase2_{int(time.time())}.db"
PASS = 0
FAIL = 0

def check(condition, msg):
    global PASS, FAIL
    if condition:
        PASS += 1
        logger.info(f"✅ {msg}")
    else:
        FAIL += 1
        logger.error(f"❌ {msg}")

def create_synthetic_data(n_days=100, trend=0.001, volatility=0.02, seed=42):
    """Create synthetic daily price data"""
    np.random.seed(seed)
    returns = np.random.normal(trend, volatility, n_days)
    price_start = 100.0
    prices = price_start * (1 + returns).cumprod()
    
    # Use fixed date range to ensure alignment across different calls
    end_date = datetime(2025, 1, 1)
    dates = pd.date_range(end=end_date, periods=n_days, freq='D')
    
    df = pd.DataFrame({
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, n_days)
    }, index=dates)
    return df

def test_risk_manager_basics():
    """Test VaR, CVaR and Risk Score calculations"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 1: RISK MANAGER BASICS ---")
    
    rm = RiskManager()
    
    # 1. Normal Volatility Stock
    df_normal = create_synthetic_data(volatility=0.015) # ~24% annual vol
    score_normal = rm.calculate_stock_risk_score(df_normal)
    
    check(0 <= score_normal['risk_score'] <= 100, f"Normal Risk Score: {score_normal['risk_score']}")
    check(score_normal['risk_label'] in ['LOW', 'MEDIUM'], f"Normal Risk Label: {score_normal['risk_label']}")
    check(score_normal['var_95'] < 0, f"VaR_95 is negative: {score_normal['var_95']}%")
    
    # 2. High Volatility Stock
    df_high = create_synthetic_data(volatility=0.05) # ~80% annual vol
    score_high = rm.calculate_stock_risk_score(df_high)
    
    check(score_high['risk_score'] > score_normal['risk_score'], 
          f"High Vol Score ({score_high['risk_score']}) > Normal ({score_normal['risk_score']})")
    check(score_high['risk_label'] in ['HIGH', 'CRITICAL'], f"High Vol Risk Label: {score_high['risk_label']}")
    check(score_high['components']['volatility_risk'] > 80, "Volatility component high")
    
    # 3. Crash Scenario (High Drawdown)
    df_crash = create_synthetic_data(n_days=100)
    # Introduce crash
    df_crash.iloc[-10:, 0] = df_crash.iloc[-10:, 0] * 0.7  # 30% drop
    score_crash = rm.calculate_stock_risk_score(df_crash)
    
    check(score_crash['components']['drawdown_risk'] > 60, 
          f"Drawdown risk captured: {score_crash['components']['drawdown_risk']}")

def test_correlation_analyzer():
    """Test Correlation Matrix and Diversification Score"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 2: CORRELATION ANALYZER ---")
    
    ca = CorrelationAnalyzer()
    
    # Create perfectly correlated assets (Corr = 1.0)
    df1 = create_synthetic_data(seed=1)
    df2 = df1.copy() 
    df2['close'] = df2['close'] * 1.5 + 5  # Linear transformation
    
    # Inverse correlated (Corr = -1.0)
    df3 = df1.copy()
    df3['close'] = 200 - df1['close']
    
    # Uncorrelated (Random)
    df4 = create_synthetic_data(seed=2)
    
    ca.set_price_data_bulk({
        'SYM1': df1['close'],
        'SYM2': df2['close'],
        'SYM3': df3['close'],
        'SYM4': df4['close']
    })
    
    matrix = ca.calculate_correlation_matrix()
    
    check(matrix is not None, "Matrix calculated")
    if matrix is not None:
        check(matrix.shape == (4, 4), "Matrix shape 4x4")
        
        # Check correlations
        check(abs(matrix.loc['SYM1', 'SYM2'] - 1.0) < 0.05, "SYM1-SYM2 corr ~ 1.0")
        check(abs(matrix.loc['SYM1', 'SYM3'] - (-1.0)) < 0.05, "SYM1-SYM3 corr ~ -1.0")
        
        # High correlation pairs
        pairs = ca.find_highly_correlated_pairs(threshold=0.9)
        check(any(p['pair'] == ('SYM1', 'SYM2') for p in pairs), "Found SYM1-SYM2 pair")
        
        # Summary
        summary = ca.get_correlation_summary()
        check(summary['diversification_score'] > 0, f"Diversification Score: {summary['diversification_score']}")

def test_portfolio_risk():
    """Test Portfolio Risk Calculation"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 3: PORTFOLIO RISK ---")
    
    rm = RiskManager()
    
    # Create 2 uncorrelated assets to show diversification benefit
    df1 = create_synthetic_data(seed=10)
    df2 = create_synthetic_data(seed=20)
    
    returns_dict = {
        'A': df1['close'].pct_change().dropna(),
        'B': df2['close'].pct_change().dropna()
    }
    
    port_risk = rm.calculate_portfolio_risk(returns_dict)
    
    check(port_risk['diversification_benefit_pct'] > 0, 
          f"Diversification benefit exists: {port_risk['diversification_benefit_pct']}%")
    check(len(port_risk['individual_vars']) == 2, "Individual VaRs calculated")

def test_database_integration():
    """Test risk_score column in database and WatchlistManager integration"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 4: DATABASE INTEGRATION ---")
    
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except:
            pass
            
    # Initialize Manager first to create tables
    wm = WatchlistManager(DB_PATH)
    
    # Run migration (should be idempotent / safe)
    migrate_database(DB_PATH)
    
    # Check if column exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(watchlist_entries)")
    cols = {row[1] for row in cursor.fetchall()}
    conn.close()
    
    check('risk_score' in cols, "Column 'risk_score' exists in watchlist_entries")
    
    # Add entry
    wm.add_to_watchlist("TEST", "BIST", {'current_price': 100, 'stop': 90, 'target1': 110})
    
    # Verify risk_score is writable
    session = wm._get_session()
    entry = session.query(WatchlistEntry).first()
    entry.risk_score = 45.5
    session.commit()
    
    entry_read = session.query(WatchlistEntry).first()
    check(entry_read.risk_score == 45.5, "risk_score column is writable/readable")
    
    wm.close()

if __name__ == "__main__":
    logger.info("🚀 PHASE 2 ANALYTICS ENGINE TEST")
    
    try:
        test_risk_manager_basics()
        test_correlation_analyzer()
        test_portfolio_risk()
        test_database_integration()
    except Exception as e:
        logger.error(f"⚠️ Critical Error: {e}")
        import traceback
        traceback.print_exc()
        FAIL += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"📋 RESULTS: ✅ {PASS} passed, ❌ {FAIL} failed")
    
    # Close sessions
    import gc
    gc.collect()
    
    # Cleanup
    import time
    time.sleep(0.5)
    for ext in ['', '-wal', '-shm']:
        path = DB_PATH + ext
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
            
    if FAIL == 0:
        logger.info("🎉 ALL TESTS PASSED!")
    else:
        logger.error(f"⚠️ {FAIL} test(s) FAILED")
