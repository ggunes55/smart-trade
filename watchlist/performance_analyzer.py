# -*- coding: utf-8 -*-
"""
Performance Analyzer - Watchlist performance karşılaştırma ve analiz
Geçmiş vs güncel değerleri karşılaştır, performans metriklerini hesapla
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

from .watchlist_manager import WatchlistManager

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Watchlist performans analiz motor
    """
    
    def __init__(self, watchlist_manager: WatchlistManager):
        """
        Args:
            watchlist_manager: WatchlistManager instance
        """
        self.manager = watchlist_manager
    
    def compare_with_initial(self, symbol: str, exchange: str) -> Dict:
        """
        İlk snapshot ile son snapshot'ı karşılaştır
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
        
        Returns:
            Comparison dictionary
        """
        history = self.manager.get_watchlist_history(symbol, exchange, days=0)
        
        if len(history) < 2:
            logger.warning(f"⚠️ {symbol} için yetersiz veri (en az 2 snapshot gerekli)")
            return {}
        
        initial = history[0]
        current = history[-1]
        
        # Temel hesaplamalar
        days_elapsed = (current['date'] - initial['date']).days
        price_change = current['price'] - initial['price']
        price_change_pct = (price_change / initial['price']) * 100 if initial['price'] > 0 else 0
        
        # Trade plan analizi
        entry_hit = False
        target1_hit = False
        target2_hit = False
        target3_hit = False
        stop_hit = False
        
        if initial['entry_price']:
            entry_hit = current['price'] >= initial['entry_price']
        
        if initial['target1']:
            target1_hit = current['price'] >= initial['target1']
        
        if initial['target2']:
            target2_hit = current['price'] >= initial ['target2']
        
        if initial['target3']:
            target3_hit = current['price'] >= initial['target3']
        
        if initial['stop_loss']:
            stop_hit = current['price'] <= initial['stop_loss']
        
        # Mesafe hesaplamaları (negatif = hedefi geçti)
        distance_to_target1 = None
        if initial['target1'] and current['price'] > 0:
            distance_to_target1 = ((initial['target1'] - current['price']) / current['price']) * 100
        
        distance_to_target2 = None
        if initial['target2'] and current['price'] > 0:
            distance_to_target2 = ((initial['target2'] - current['price']) / current['price']) * 100
        
        distance_to_stop = None
        if initial['stop_loss'] and current['price'] > 0:
            distance_to_stop = ((current['price'] - initial['stop_loss']) / current['price']) * 100
        
        # Trend tahmini doğrulama
        actual_vs_predicted_trend = self._compare_trends(initial, current)
        
        # RSI değişimi
        rsi_change = None
        if initial['rsi'] and current['rsi']:
            rsi_change = current['rsi'] - initial['rsi']
        
        # Trend score değişimi
        trend_score_change = None
        if initial['trend_score'] and current['trend_score']:
            trend_score_change = current['trend_score'] - initial['trend_score']
        
        # Sinyal doğruluğu (basit)
        signal_accuracy = None
        if initial['confidence']:
            if target1_hit and not stop_hit:
                signal_accuracy = initial['confidence']  # Tahmin doğru çıktı
            elif stop_hit:
                signal_accuracy = 1 - initial['confidence']  # Tahmin yanlış
            else:
                signal_accuracy = 0.5  # Henüz belirsiz
        
        # Mevcut öneri
        recommendation = self._generate_recommendation(
            price_change_pct, target1_hit, target2_hit, stop_hit, distance_to_stop
        )
        
        return {
            'symbol': symbol,
            'exchange': exchange,
            'initial_date': initial['date'],
            'current_date': current['date'],
            'days_elapsed': days_elapsed,
            
            # Price
            'initial_price': initial['price'],
            'current_price': current['price'],
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            
            # Trade Plan
            'entry_hit': entry_hit,
            'target1_hit': target1_hit,
            'target2_hit': target2_hit,
            'target3_hit': target3_hit,
            'stop_hit': stop_hit,
            
            # Distances
            'distance_to_target1': distance_to_target1,
            'distance_to_target2': distance_to_target2,
            'distance_to_stop': distance_to_stop,
            
            # Analysis
            'actual_vs_predicted_trend': actual_vs_predicted_trend,
            'rsi_change': rsi_change,
            'trend_score_change': trend_score_change,
            'signal_accuracy': signal_accuracy,
            'recommendation': recommendation,
        }
    
    def _compare_trends(self, initial: Dict, current: Dict) -> str:
        """
        Trend tahminini gerçekle şenle karşılaştır
        """
        initial_trend = initial.get('market_regime') or 'UNKNOWN'
        
        # Sıfıra bölme hatasını önle
        if not initial.get('price') or initial['price'] <= 0:
            return 'UNKNOWN'
        
        price_change_pct = ((current['price'] - initial['price']) / initial['price']) * 100
        
        if 'UP' in initial_trend.upper() and price_change_pct > 0:
            return 'MATCHED'  # Tahmin doğru: Yükseliş
        elif 'DOWN' in initial_trend.upper() and price_change_pct < 0:
            return 'MATCHED'  # Tahmin doğru: Düşüş
        elif 'CONSOLIDATION' in initial_trend.upper() and abs(price_change_pct) < 2:
            return 'MATCHED'  # Tahmin doğru: Yatay
        else:
            return 'MISMATCHED'  # Tahmin yanlış
    
    def _generate_recommendation(
        self,
        price_change_pct: float,
        target1_hit: bool,
        target2_hit: bool,
        stop_hit: bool,
        distance_to_stop: Optional[float]
    ) -> str:
        """Mevcut öneri oluştur"""
        
        if stop_hit:
            return 'EXIT_LOSS'  # Stop'a takıldı, çık
        
        if target2_hit:
            return 'TAKE_PROFIT'  # Target 2'ye ulaştı, kar al
        
        if target1_hit:
            return 'HOLD_PARTIAL'  # Target 1'de, 1/3 sat geri kalanı tut
        
        if price_change_pct > 3:
            return 'HOLD'  # Kârda, bekle
        
        if distance_to_stop and distance_to_stop < 2:
            return 'WATCH_CLOSELY'  # Stop'a yakın, dikkatli ol
        
        if abs(price_change_pct) < 1:
            return 'WAIT'  # Henüz hareket yok
        
        if price_change_pct < -3:
            return 'CONSIDER_EXIT'  # Zarar büyüyor
        
        return 'HOLD'  # Varsayılan
    
    def calculate_win_rate(self) -> Dict:
        """
        Tüm watchlist için kazanç oranını hesapla
        
        Returns:
            Win rate statistics
        """
        watchlist = self.manager.get_active_watchlist()
        
        total = 0
        winners = 0
        losers = 0
        target1_count = 0
        target2_count = 0
        stop_count = 0
        
        for entry in watchlist:
            if entry['snapshots_count'] < 2:
                continue  # Yetersiz veri
            
            comparison = self.compare_with_initial(entry['symbol'], entry['exchange'])
            
            if not comparison:
                continue
            
            total += 1
            
            if comparison['target1_hit']:
                target1_count += 1
                winners += 1
            
            if comparison['target2_hit']:
                target2_count += 1
            
            if comparison['stop_hit']:
                stop_count += 1
                losers += 1
            
            # Henüz target/stop'a ulaşmayanları neutral say
        
        win_rate = (winners / total * 100) if total > 0 else 0
        target1_hit_rate = (target1_count / total * 100) if total > 0 else 0
        target2_hit_rate = (target2_count / total * 100) if total > 0 else 0
        stop_hit_rate = (stop_count / total * 100) if total > 0 else 0
        
        return {
            'total_items': total,
            'winners': winners,
            'losers': losers,
            'win_rate': win_rate,
            'target1_hit_rate': target1_hit_rate,
            'target2_hit_rate': target2_hit_rate,
            'stop_hit_rate': stop_hit_rate,
        }
    
    def get_best_performers(self, days: int = 7, top_n: int = 5) -> List[Dict]:
        """
        En iyi performans gösteren hisseleri listele
        
        Args:
            days: Son N gün
            top_n: Kaç tane
        
        Returns:
            List of top performers
        """
        watchlist = self.manager.get_active_watchlist()
        
        performers = []
        for entry in watchlist:
            comparison = self.compare_with_initial(entry['symbol'], entry['exchange'])
            
            if comparison and comparison.get('days_elapsed', 0) <= days:
                performers.append({
                    'symbol': entry['symbol'],
                    'exchange': entry['exchange'],
                    'price_change_pct': comparison['price_change_pct'],
                    'days_elapsed': comparison['days_elapsed'],
                })
        
        # Sort by price change (descending)
        performers.sort(key=lambda x: x['price_change_pct'], reverse=True)
        
        return performers[:top_n]
    
    def get_worst_performers(self, days: int = 7, top_n: int = 5) -> List[Dict]:
        """
        En kötü performans gösterenleri listele
        
        Args:
            days: Son N gün
            top_n: Kaç tane
        
        Returns:
            List of worst performers
        """
        watchlist = self.manager.get_active_watchlist()
        
        performers = []
        for entry in watchlist:
            comparison = self.compare_with_initial(entry['symbol'], entry['exchange'])
            
            if comparison and comparison.get('days_elapsed', 0) <= days:
                performers.append({
                    'symbol': entry['symbol'],
                    'exchange': entry['exchange'],
                    'price_change_pct': comparison['price_change_pct'],
                    'days_elapsed': comparison['days_elapsed'],
                })
        
        # Sort by price change (ascending)
        performers.sort(key=lambda x: x['price_change_pct'])
        
        return performers[:top_n]
