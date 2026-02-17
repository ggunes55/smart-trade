# -*- coding: utf-8 -*-
"""
Institutional Watchlist V3.0 - Comprehensive Test Suite
Tests: Migration, Audit Logging, Trade Execution, Journal, Sector Performance, Portfolio Summary
"""
import os
import sys
import logging
import sqlite3
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from watchlist.database import (
    migrate_database, get_session, WatchlistEntry, WatchlistAuditLog,
    TradeExecution, TradeJournal, SectorPerformanceHistory
)
from watchlist.watchlist_manager import WatchlistManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "watchlist_test_v3.db"
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


def test_migration():
    """Test database migration creates all V3.0 tables and columns"""
    logger.info("\n{'='*60}")
    logger.info("--- TEST 1: DATABASE MIGRATION ---")
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    # Create minimal old-version DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE watchlist_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, exchange TEXT, is_active INTEGER,
            added_date DATETIME, notes TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE watchlist_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            watchlist_entry_id INTEGER, snapshot_date DATETIME, price REAL
        )
    """)
    conn.commit()
    conn.close()
    
    success = migrate_database(DB_PATH)
    check(success, "Migration completed successfully")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = [
        'watchlist_audit_logs', 'trade_executions',
        'trade_journals', 'sector_performance_history'
    ]
    for t in required_tables:
        check(t in tables, f"Table '{t}' exists")
    
    # Check new columns on entries
    cursor.execute("PRAGMA table_info(watchlist_entries)")
    entry_cols = {row[1] for row in cursor.fetchall()}
    for col in ['sector', 'status_label', 'psychological_risk', 'total_trades']:
        check(col in entry_cols, f"Column 'watchlist_entries.{col}' exists")
    
    conn.close()
    return success


def test_audit_logging():
    """Test audit trail for CRUD operations"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 2: AUDIT LOGGING ---")
    
    manager = WatchlistManager(DB_PATH)
    
    # 1. Add entry -> CREATE audit
    scan = {'current_price': 100.0, 'stop': 90.0, 'target1': 115.0}
    manager.add_to_watchlist("GARAN", "BIST", scan, notes="Test")
    
    audits = manager.get_audit_history("GARAN", "BIST", days=0)
    check(len(audits) > 0, "Audit log created on add_to_watchlist")
    check(any(a['action_type'] == 'CREATE' for a in audits), "CREATE action recorded")
    
    # 2. Status change -> STATUS_CHANGE audit
    manager.update_status_label("GARAN", "BIST", "WAIT")
    audits = manager.get_audit_history("GARAN", "BIST", days=0)
    status_audits = [a for a in audits if a['action_type'] == 'STATUS_CHANGE']
    check(len(status_audits) > 0, "STATUS_CHANGE audit recorded")
    if status_audits:
        check(status_audits[0]['new_value'] == 'WAIT', "STATUS_CHANGE new_value = WAIT")
    
    # 3. Setup update -> SETUP_UPDATE audit
    manager.update_setup_status("GARAN", "BIST", "READY", 3)
    audits = manager.get_audit_history("GARAN", "BIST", days=0)
    check(any(a['action_type'] == 'SETUP_UPDATE' for a in audits), "SETUP_UPDATE audit recorded")
    
    # 4. Psych flags -> PSYCH_FLAG_UPDATE audit
    manager.update_psychological_flags("GARAN", "BIST", {'high_volatility_risk': True})
    audits = manager.get_audit_history("GARAN", "BIST", days=0)
    check(any(a['action_type'] == 'PSYCH_FLAG_UPDATE' for a in audits), "PSYCH_FLAG_UPDATE audit recorded")
    
    # 5. Filter audit by action type
    create_only = manager.get_audit_history("GARAN", "BIST", days=0, action_filter="CREATE")
    check(len(create_only) == 1 and create_only[0]['action_type'] == 'CREATE', "Audit filter by action_type works")
    
    # 6. Archive -> ARCHIVE audit
    manager.remove_from_watchlist("GARAN", "BIST", "Test complete")
    audits = manager.get_audit_history("GARAN", "BIST", days=0)
    check(any(a['action_type'] == 'ARCHIVE' for a in audits), "ARCHIVE audit recorded")


def test_trade_execution():
    """Test trade execution recording and querying"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 3: TRADE EXECUTION ---")
    
    manager = WatchlistManager(DB_PATH)
    
    scan = {'current_price': 50.0, 'stop': 45.0, 'target1': 60.0}
    manager.add_to_watchlist("THYAO", "BIST", scan)
    
    # Add BUY trade
    result = manager.add_trade_execution("THYAO", "BIST", "BUY", 100, 50.5, 2.5, "LIMIT", "Test buy")
    check(result, "Trade execution BUY added")
    
    # Add SELL trade
    result = manager.add_trade_execution("THYAO", "BIST", "SELL", 50, 55.0, 1.25, "MARKET", "Partial exit")
    check(result, "Trade execution SELL added")
    
    # Query trades
    trades = manager.get_trade_executions("THYAO", "BIST")
    check(len(trades) == 2, f"get_trade_executions returns 2 trades (got {len(trades)})")
    
    if trades:
        # Most recent first
        check(trades[0]['side'] == 'SELL', "Trades ordered by date desc (SELL first)")
        check(trades[0]['total_cost'] == 50 * 55.0 + 1.25, "total_cost calculated correctly")
    
    # Check audit for TRADE_EXEC
    audits = manager.get_audit_history("THYAO", "BIST", days=0, action_filter="TRADE_EXEC")
    check(len(audits) == 2, "TRADE_EXEC audit entries created for both trades")


def test_trade_journal():
    """Test trade journal CRUD"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 4: TRADE JOURNAL ---")
    
    manager = WatchlistManager(DB_PATH)
    
    # Initial journal - should be None
    journal = manager.get_trade_journal("THYAO", "BIST")
    check(journal is None, "No journal before creation")
    
    # Create journal
    journal_data = {
        'entry_reason': 'Breakout above resistance with volume',
        'setup_quality': 8,
        'emotion_entry': 'CONFIDENT'
    }
    result = manager.update_trade_journal("THYAO", "BIST", journal_data)
    check(result, "Trade journal created successfully")
    
    # Read journal
    journal = manager.get_trade_journal("THYAO", "BIST")
    check(journal is not None, "get_trade_journal returns data")
    if journal:
        check(journal['entry_reason'] == 'Breakout above resistance with volume', "Journal entry_reason correct")
        check(journal['setup_quality'] == 8, "Journal setup_quality correct")
        check(journal['emotion_entry'] == 'CONFIDENT', "Journal emotion_entry correct")
    
    # Update journal with exit data
    result = manager.update_trade_journal("THYAO", "BIST", {
        'exit_reason': 'Target 1 hit',
        'emotion_exit': 'SATISFIED',
        'lessons_learned': 'Patience with breakout setups pays off'
    })
    check(result, "Trade journal updated with exit data")
    
    journal = manager.get_trade_journal("THYAO", "BIST")
    if journal:
        check(journal['exit_reason'] == 'Target 1 hit', "Journal exit data updated correctly")


def test_auto_cleanup_audit():
    """Test that auto_cleanup creates audit logs"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 5: AUTO CLEANUP AUDIT ---")
    
    manager = WatchlistManager(DB_PATH)
    
    # Add a stock that will be cleaned up (stop hit scenario)
    scan = {'current_price': 100.0, 'stop': 95.0, 'target1': 110.0}
    manager.add_to_watchlist("STOPTEST", "BIST", scan)
    
    # Cleanup with price below stop
    current_data = {'STOPTEST': {'price': 93.0}}
    result = manager.auto_cleanup(current_data)
    check(result['cleaned'] >= 1, f"Auto cleanup cleaned {result['cleaned']} entries")
    
    # Check for AUTO_CLEANUP audit
    audits = manager.get_audit_history("STOPTEST", "BIST", days=0, action_filter="AUTO_CLEANUP")
    check(len(audits) > 0, "AUTO_CLEANUP audit log created")
    if audits:
        check(audits[0]['user_context'] == 'Auto-Cleanup', "Audit context = 'Auto-Cleanup'")


def test_sector_performance():
    """Test sector performance recording and rotation history"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 6: SECTOR PERFORMANCE ---")
    
    manager = WatchlistManager(DB_PATH)
    
    sector_data = [
        {
            'sector': 'Bankacılık',
            'avg_change_pct': 2.1,
            'top_gainer': 'GARAN', 'top_gainer_pct': 4.5,
            'top_loser': 'VAKBN', 'top_loser_pct': -0.3,
            'stock_count': 12, 'bullish_count': 9, 'bearish_count': 2, 'neutral_count': 1,
            'sector_volume': 850000000, 'momentum_score': 72.5
        },
        {
            'sector': 'Holding',
            'avg_change_pct': -0.5,
            'top_gainer': 'SAHOL', 'top_gainer_pct': 1.2,
            'top_loser': 'KCHOL', 'top_loser_pct': -2.1,
            'stock_count': 8, 'bullish_count': 3, 'bearish_count': 4, 'neutral_count': 1,
            'sector_volume': 320000000, 'momentum_score': -15.0
        },
        {
            'sector': 'Teknoloji',
            'avg_change_pct': 3.8,
            'top_gainer': 'LOGO', 'top_gainer_pct': 6.2,
            'top_loser': 'ARDYZ', 'top_loser_pct': 0.1,
            'stock_count': 5, 'bullish_count': 5, 'bearish_count': 0, 'neutral_count': 0,
            'sector_volume': 120000000, 'momentum_score': 88.0
        }
    ]
    
    result = manager.record_sector_performance(sector_data)
    check(result, "Sector performance recorded successfully")
    
    # Query all sectors
    history = manager.get_sector_rotation_history(days=7)
    check(len(history) == 3, f"get_sector_rotation_history returns 3 records (got {len(history)})")
    
    # Query specific sector
    bank_history = manager.get_sector_rotation_history(days=7, sector='Bankacılık')
    check(len(bank_history) == 1, "Sector filter works correctly")
    if bank_history:
        check(bank_history[0]['avg_change_pct'] == 2.1, "Sector avg_change_pct correct")
        check(bank_history[0]['top_gainer'] == 'GARAN', "Sector top_gainer correct")
        check(bank_history[0]['momentum_score'] == 72.5, "Sector momentum_score correct")


def test_portfolio_summary():
    """Test portfolio summary aggregation"""
    logger.info("\n" + "="*60)
    logger.info("--- TEST 7: PORTFOLIO SUMMARY ---")
    
    manager = WatchlistManager(DB_PATH)
    
    summary = manager.get_portfolio_summary()
    check(isinstance(summary, dict), "get_portfolio_summary returns dict")
    check('total_active' in summary, "Summary has total_active")
    check('total_archived' in summary, "Summary has total_archived")
    check('status_distribution' in summary, "Summary has status_distribution")
    check('sector_distribution' in summary, "Summary has sector_distribution")
    check('trade_stats' in summary, "Summary has trade_stats")
    check('risk_flags' in summary, "Summary has risk_flags")
    
    logger.info(f"  📊 Active: {summary.get('total_active')}, Archived: {summary.get('total_archived')}")
    logger.info(f"  📊 Status: {summary.get('status_distribution')}")
    logger.info(f"  📊 Trades: {summary.get('trade_stats')}")
    logger.info(f"  📊 Risk: {summary.get('risk_flags')}")


if __name__ == "__main__":
    logger.info("🚀 INSTITUTIONAL WATCHLIST V3.0 - COMPREHENSIVE TEST SUITE")
    logger.info("=" * 60)
    
    if test_migration():
        test_audit_logging()
        test_trade_execution()
        test_trade_journal()
        test_auto_cleanup_audit()
        test_sector_performance()
        test_portfolio_summary()
    
    logger.info("\n" + "=" * 60)
    logger.info(f"📋 RESULTS: ✅ {PASS} passed, ❌ {FAIL} failed")
    logger.info("=" * 60)
    
    # Close all sessions before cleanup
    import gc
    gc.collect()
    
    # Cleanup test database files
    import time
    time.sleep(0.5)
    for ext in ['', '-wal', '-shm']:
        path = DB_PATH + ext
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass  # OK if cleanup fails
    
    if FAIL == 0:
        logger.info("🎉 ALL TESTS PASSED!")
    else:
        logger.error(f"⚠️ {FAIL} test(s) FAILED - review above")
