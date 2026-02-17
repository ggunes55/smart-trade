# -*- coding: utf-8 -*-
"""
Watchlist Update Worker - Asenkron Watchlist Güncelleme
UI'ı dondurmadan arka planda veri güncelleme yapar
"""
import logging
from typing import Dict, List, Optional, Any

from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from watchlist.risk_manager import RiskManager
from scanner.data_handler import DataHandler

logger = logging.getLogger(__name__)


class WatchlistUpdateWorker(QThread):
    # Signals - UI güncellemesi için
    symbol_updated = pyqtSignal(str, str, dict)  # symbol, exchange, data
    progress_updated = pyqtSignal(int, int, str)
    all_finished = pyqtSignal(int, int)
    error_occurred = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._symbols: List[Dict] = []
        self._scanner = None
        self._manager = None
        self._is_cancelled = False
        self._mutex = QMutex()
        self._risk_manager = RiskManager()
        self._data_handler = None
    
    def setup(self, symbols: List[Dict], scanner: Any, manager: Any):
        """
        Worker'ı yapılandır
        
        Args:
            symbols: Güncellenecek sembol listesi [{'symbol': 'X', 'exchange': 'Y'}, ...]
            scanner: Scanner instance (symbol_analyzer erişimi için)
            manager: WatchlistManager instance
        """
        self._symbols = symbols
        self._scanner = scanner
        self._manager = manager
        self._is_cancelled = False
        
        # DataHandler'ı yapılandır
        cfg = scanner.cfg if scanner and hasattr(scanner, 'cfg') else {}
        self._data_handler = DataHandler(cfg)
    
    def cancel(self):
        """İşlemi iptal et"""
        with QMutexLocker(self._mutex):
            self._is_cancelled = True
    
    def is_cancelled(self) -> bool:
        """İptal durumunu kontrol et"""
        with QMutexLocker(self._mutex):
            return self._is_cancelled
    
    def run(self):
        """Ana çalışma döngüsü"""
        if not self._symbols:
            logger.warning("⚠️ Güncellenecek sembol yok")
            self.all_finished.emit(0, 0)
            return
        
        if not self._scanner or not hasattr(self._scanner, 'symbol_analyzer'):
            logger.error("❌ Scanner veya symbol_analyzer bulunamadı")
            self.all_finished.emit(0, len(self._symbols))
            return
        
        total = len(self._symbols)
        success_count = 0
        fail_count = 0
        
        logger.info(f"🔄 Watchlist güncelleme başladı: {total} sembol")
        
        for idx, entry in enumerate(self._symbols):
            if self.is_cancelled():
                logger.info(f"⏹️ Güncelleme {idx}/{total}'da iptal edildi")
                break
            
            symbol = entry.get('symbol', '')
            exchange = entry.get('exchange', '')
            
            if not symbol:
                continue
            
            self.progress_updated.emit(idx + 1, total, symbol)
            
            try:
                # 1. Teknik Analiz
                result = self._scanner.symbol_analyzer.analyze_symbol(symbol, skip_filters=True)
                
                if result:
                    # 2. Risk Analizi (V3.0)
                    try:
                        df = self._data_handler.get_daily_data(symbol, exchange, n_bars=120)
                        if df is not None and len(df) > 30:
                            risk_data = self._risk_manager.calculate_stock_risk_score(df)
                            result['risk_score'] = risk_data.get('risk_score')
                            result['risk_analysis'] = risk_data # Detaylı veriler
                    except Exception as e:
                        logger.warning(f"⚠️ Risk calculation failed for {symbol}: {e}")
                    
                    # 3. Snapshot Dönüşüm
                    scan_result = self._convert_result_to_snapshot(result)
                    
                    # 4. Kaydet ve Bildir
                    if self._manager.create_snapshot(symbol, exchange, scan_result):
                        success_count += 1
                        self.symbol_updated.emit(symbol, exchange, scan_result)
                        logger.debug(f"✅ {symbol} güncellendi")
                    else:
                        fail_count += 1
                        self.error_occurred.emit(symbol, "Snapshot oluşturulamadı")
                else:
                    fail_count += 1
                    self.error_occurred.emit(symbol, "Analiz sonucu boş")
                    
            except Exception as e:
                fail_count += 1
                error_msg = str(e)
                logger.error(f"❌ {symbol} güncelleme hatası: {error_msg}")
                self.error_occurred.emit(symbol, error_msg)
        
        logger.info(f"✅ Watchlist güncelleme tamamlandı: {success_count} başarılı, {fail_count} başarısız")
        self.all_finished.emit(success_count, fail_count)
    
    def _convert_result_to_snapshot(self, result: Dict) -> Dict:
        """Snapshot formatına dönüştür"""
        snapshot = {
            'current_price': result.get('current_price', 0),
            # ... (mevcut alanlar)
            'entry': result.get('entry'),
            'stop': result.get('stop'),
            'target1': result.get('target1'),
            'target2': result.get('target2'),
            'target3': result.get('target3'),
            'trigger_price': result.get('trigger_price'),
            
            'main_trend': result.get('main_trend'),
            'trend_strength': result.get('trend_strength'),
            'ma_alignment': result.get('ma_alignment'),
            'setup_type': result.get('setup_type') or result.get('signal_type'),
            'structure_type': result.get('structure_type'),
            
            'rsi': result.get('rsi') or result.get('RSI'),
            'rsi_trend': result.get('rsi_trend'),
            'macd': result.get('macd') or result.get('MACD'),
            'macd_signal': result.get('macd_signal'),
            'macd_histogram': result.get('macd_histogram'),
            'adx': result.get('adx') or result.get('ADX'),
            'plus_di': result.get('plus_di'),
            'minus_di': result.get('minus_di'),
            
            'volume': result.get('volume'),
            'volume_avg': result.get('volume_avg'),
            'volume_ratio': result.get('volume_ratio'),
            'rvol': result.get('rvol') or result.get('RVOL'),
            'volume_confirms_price': result.get('volume_confirms_price'),
            
            'atr': result.get('atr'),
            'volatility_status': result.get('volatility_status'),
            
            'rs_rating': result.get('rs_rating'),
            'trend_score': result.get('trend_score'),
            'swing_efficiency': result.get('swing_efficiency'),
            'market_regime': result.get('market_regime'),
            
            'signal_type': result.get('signal_type'),
            'signal_strength': result.get('signal_strength'),
            'confidence': result.get('confidence'),
            'confirmations': result.get('confirmations', 0),
            
            'divergence_desc': result.get('divergence_desc'),
            'tv_signal': result.get('tv_signal'),
            'tv_signal_details': result.get('tv_signal_details'),
            'ml_prediction': result.get('ml_prediction'),
            'squeeze_data': result.get('squeeze_data'),
            'risk_metrics': result.get('risk_metrics'),
            'quality_metrics': result.get('quality_metrics'),
            'rs_data': result.get('rs_data'),
            'confirmation_data': result.get('confirmation_data'),
            'entry_recommendation': result.get('entry_recommendation'),
            'daily_change_pct': result.get('daily_change_pct'),
            
            # YENİ - Risk Analizi
            'risk_score': result.get('risk_score'),
            'risk_analysis': result.get('risk_analysis'),
        }
        return snapshot


class BatchUpdateWorker(QThread):
    """
    Toplu güncelleme worker'ı - daha büyük işlemler için
    Sembolleri batch'ler halinde işler
    """
    
    batch_completed = pyqtSignal(int, int)  # batch_number, total_batches
    all_completed = pyqtSignal(dict)  # summary statistics
    
    def __init__(self, batch_size: int = 10, parent=None):
        super().__init__(parent)
        self._batch_size = batch_size
        self._symbols: List[Dict] = []
        self._scanner = None
        self._manager = None
        self._is_cancelled = False
        self._mutex = QMutex()
    
    def setup(self, symbols: List[Dict], scanner: Any, manager: Any):
        """Worker'ı yapılandır"""
        self._symbols = symbols
        self._scanner = scanner
        self._manager = manager
        self._is_cancelled = False
    
    def cancel(self):
        """İşlemi iptal et"""
        with QMutexLocker(self._mutex):
            self._is_cancelled = True
    
    def is_cancelled(self) -> bool:
        """İptal durumunu kontrol et"""
        with QMutexLocker(self._mutex):
            return self._is_cancelled
    
    def run(self):
        """Batch işleme döngüsü"""
        if not self._symbols:
            self.all_completed.emit({'total': 0, 'success': 0, 'failed': 0})
            return
        
        # Batch'lere böl
        batches = [
            self._symbols[i:i + self._batch_size] 
            for i in range(0, len(self._symbols), self._batch_size)
        ]
        
        total_batches = len(batches)
        total_success = 0
        total_failed = 0
        
        for batch_num, batch in enumerate(batches):
            if self.is_cancelled():
                break
            
            for entry in batch:
                if self.is_cancelled():
                    break
                
                symbol = entry.get('symbol', '')
                exchange = entry.get('exchange', '')
                
                try:
                    if hasattr(self._scanner, 'symbol_analyzer'):
                        result = self._scanner.symbol_analyzer.analyze_symbol(symbol, skip_filters=True)
                        if result and self._manager.create_snapshot(symbol, exchange, result):
                            total_success += 1
                        else:
                            total_failed += 1
                    else:
                        total_failed += 1
                except Exception as e:
                    logger.error(f"Batch update error for {symbol}: {e}")
                    total_failed += 1
            
            self.batch_completed.emit(batch_num + 1, total_batches)
        
        self.all_completed.emit({
            'total': len(self._symbols),
            'success': total_success,
            'failed': total_failed,
            'cancelled': self.is_cancelled()
        })
