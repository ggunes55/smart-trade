import sys
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from PyQt5.QtWidgets import QApplication

# Adjust path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
# Configure logging
logging.basicConfig(level=logging.DEBUG)

from watchlist.watchlist_manager import WatchlistManager
from watchlist.database import init_db, WatchlistEntry
from gui.workers.watchlist_worker import WatchlistUpdateWorker
from gui.widgets.risk_analysis_dialog import RiskAnalysisDialog
import scanner.data_handler # Ensure imported for patching

# Dummy DataHandler
class MockDataHandler:
    def __init__(self, config=None):
        pass
        
    def get_daily_data(self, symbol, exchange, n_bars=120):
        print(f"MockDataHandler.get_daily_data called for {symbol}")
        # Create dummy dataframe
        dates = pd.date_range(end=datetime.now(), periods=n_bars)
        data = {
            'Open': np.random.randn(n_bars) + 100,
            'High': np.random.randn(n_bars) + 102,
            'Low': np.random.randn(n_bars) + 98,
            'Close': np.random.randn(n_bars) + 100,
            'Volume': np.random.randint(1000, 10000, n_bars)
        }
        df = pd.DataFrame(data, index=dates)
        return df

class TestPhase3Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create simple DB
        cls.db_path = f"test_phase3_{int(datetime.now().timestamp())}.db"
        init_db(cls.db_path)
        cls.manager = WatchlistManager(cls.db_path)
        
        # Add a dummy entry
        session = cls.manager._get_session()
        # Delete if exists
        session.query(WatchlistEntry).delete()
        entry = WatchlistEntry(symbol="TEST", exchange="BIST", is_active=True)
        session.add(entry)
        session.commit()
        cls.entry_id = entry.id
        
        # Init Qt App
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_risk_analysis_fetching(self):
        """Test WatchlistManager.get_risk_analysis"""
        print("\n--- Testing get_risk_analysis ---")
        # Patch the CLASS in the MODULE
        with patch('scanner.data_handler.DataHandler', side_effect=MockDataHandler):
            risk_data = self.manager.get_risk_analysis("TEST", "BIST")
            print(f"Risk Data Result: {risk_data}")
            
            if not risk_data:
                # Debug why
                session = self.manager._get_session()
                entry = session.query(WatchlistEntry).filter_by(symbol="TEST").first()
                print(f"Entry found: {entry.symbol if entry else 'None'}, Active: {entry.is_active if entry else 'N/A'}")
            
            self.assertIsInstance(risk_data, dict)
            self.assertIn('risk_score', risk_data)
            self.assertIn('components', risk_data)
            self.assertTrue(0 <= risk_data['risk_score'] <= 100)

    def test_worker_integration(self):
        """Test WatchlistUpdateWorker integrates RiskManager"""
        print("\n--- Testing WatchlistUpdateWorker ---")
        
        # Patch DataHandler imported in watchlist_worker module
        with patch('gui.workers.watchlist_worker.DataHandler', side_effect=MockDataHandler):
            worker = WatchlistUpdateWorker()
            
            # Mock Scanner and Analyzer
            mock_scanner = MagicMock()
            mock_scanner.symbol_analyzer.analyze_symbol.return_value = {
                'current_price': 100,
                'symbol': 'TEST',
                'entry': 90,
                'stop': 85,
                # Add basic fields required by _convert_result_to_snapshot
                'target1': 110,
                'main_trend': 'UP'
            }
            # cfg for setup
            mock_scanner.cfg = {}
            
            # Setup worker
            # MockDataHandler will be used via patch
            worker.setup([{'symbol': 'TEST', 'exchange': 'BIST'}], mock_scanner, self.manager)
            
            # Reset MockDataHandler instance if needed, but side_effect creates new one each time.
            # worker._data_handler is now MockDataHandler instance.
            
            # Run worker (synchronously logic check)
            with patch.object(self.manager, 'create_snapshot') as mock_create:
                worker.run()
                
                # Check if called
                if not mock_create.called:
                    print("create_snapshot NOT called. Worker might have hit exception.")
                    
                self.assertTrue(mock_create.called)
                
                # Check result
                args, _ = mock_create.call_args
                symbol, exchange, result = args
                
                print(f"Worker Snapshot Result keys: {list(result.keys())}")
                if 'risk_score' in result:
                    print(f"Risk Score: {result['risk_score']}")
                
                self.assertEqual(symbol, 'TEST')
                self.assertIn('risk_score', result)
                self.assertIn('risk_analysis', result)

    def test_dialog_init(self):
        """Test RiskAnalysisDialog initialization"""
        risk_data = {
            'risk_score': 65.5,
            'risk_label': 'HIGH',
            'components': {'volatility_risk': 70, 'drawdown_risk': 60},
            'var_95': 2.5,
            'max_drawdown_pct': 15.0
        }
        try:
            dialog = RiskAnalysisDialog("TEST", risk_data)
            self.assertEqual(dialog.symbol, "TEST")
            print("Dialog initialized successfully")
        except Exception as e:
            self.fail(f"Dialog init failed: {e}")

    @classmethod
    def tearDownClass(cls):
        import os
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

if __name__ == '__main__':
    unittest.main()
