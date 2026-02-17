# -*- coding: utf-8 -*-
"""
Multi-Level Exit Strategy - 3 seviyeli kademeli çıkış stratejisi
Tek hedeften çıkarak, 3 seviyeli kademeli çıkış ile kar potansiyelini maksimize et
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MultiLevelExitStrategy:
    """
    3 seviyede kâr al (Partial Exit):
    1. Target 1 (+1.5R): Pozisyonun 1/3'ünü kapat → Stop'u breakeven'e çek
    2. Target 2 (+2.5R): Pozisyonun 1/3'ünü kapat → Stop'u +1R'ye çek
    3. Target 3 (+4R): Kalan 1/3'ü trailing stop ile kapat
    """
    
    def __init__(self, config: dict):
        """
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.target1_multiplier = config.get('multilevel_target1_multiplier', 1.5)
        self.target2_multiplier = config.get('multilevel_target2_multiplier', 2.5)
        self.target3_multiplier = config.get('multilevel_target3_multiplier', 4.0)
    
    def calculate_multi_level_targets(
        self,
        entry_price: float,
        stop_loss: float,
        atr: Optional[float] = None
    ) -> Dict:
        """
        ATR bazlı çoklu hedefler hesapla
        
        Args:
            entry_price: Giriş fiyatı
            stop_loss: Stop-loss seviyesi
            atr: Average True Range (opsiyonel, kullanılmıyorsa risk'ten hesapla)
        
        Returns:
            Dictionary with targets and risk/reward info
        """
        # Risk (Entry - Stop arası mesafe)
        risk = abs(entry_price - stop_loss)
        
        if risk <= 0:
            logger.error("Invalid risk calculation: entry=stop")
            return {}
        
        # Hedefler (Risk * Multiplier)
        target_1 = entry_price + (risk * self.target1_multiplier)   # 1.5R
        target_2 = entry_price + (risk * self.target2_multiplier)   # 2.5R
        target_3 = entry_price + (risk * self.target3_multiplier)   # 4.0R
        
        # Risk/Reward oranları
        rr1 = self.target1_multiplier
        rr2 = self.target2_multiplier
        rr3 = self.target3_multiplier
        
        return {
            'entry': entry_price,
            'stop_loss': stop_loss,
            'risk': risk,
            'risk_percent': (risk / entry_price) * 100,
            
            # 3 Hedef
            'target_1': round(target_1, 2),
            'target_2': round(target_2, 2),
            'target_3': round(target_3, 2),
            
            # Risk/Reward
            'rr_target1': rr1,
            'rr_target2': rr2,
            'rr_target3': rr3,
            
            # Exit plan
            'exit_plan': {
                'target1_reached': {'action': 'Close 1/3, move stop to breakeven (entry price)', 'new_stop': entry_price},
                'target2_reached': {'action': 'Close another 1/3, move stop to +1R', 'new_stop': entry_price + risk},
                'target3_reached': {'action': 'Close remaining 1/3 with trailing stop', 'new_stop': 'Trailing'},
            }
        }
    
    def execute_partial_exit(
        self,
        current_price: float,
        position: Dict
    ) -> Dict:
        """
        Hedeflere ulaştığında kısmi çıkış önerisi
        
        Args:
            current_price: Güncel fiyat
            position: Position dictionary (entry, stop, targets)
        
        Returns:
            Exit recommendation dictionary
        """
        exits = []
        new_stop = position.get('stop_loss')
        remaining_position = 100  # %
        
        # Target 1 kontrolü
        if current_price >= position.get('target_1', float('inf')):
            exits.append({
                'level': 1,
                'target_price': position.get('target_1'),
                'current_price': current_price,
                'percent_to_close': 33,
                'action': 'CLOSE_1/3',
                'stop_action': 'MOVE_TO_BREAKEVEN',
                'reason': f"Target 1 reached (+{position.get('rr_target1', 1.5)}R)"
            })
            
            # Stop-Loss'u maliyet fiyatına çek (Breakeven)
            new_stop = position.get('entry')
            remaining_position -= 33
        
        # Target 2 kontrolü
        if current_price >= position.get('target_2', float('inf')):
            exits.append({
                'level': 2,
                'target_price': position.get('target_2'),
                'current_price': current_price,
                'percent_to_close': 33,
                'action': 'CLOSE_1/3',
                'stop_action': 'MOVE_TO_+1R',
                'reason': f"Target 2 reached (+{position.get('rr_target2', 2.5)}R)"
            })
            
            # Stop-Loss'u +1R'ye çek
            new_stop = position.get('entry') + position.get('risk', 0)
            remaining_position -= 33
        
        # Target 3 kontrolü
        if current_price >= position.get('target_3', float('inf')):
            exits.append({
                'level': 3,
                'target_price': position.get('target_3'),
                'current_price': current_price,
                'percent_to_close': 34,  # Kalan
                'action': 'CLOSE_REMAINING',
                'stop_action': 'TRAILING_STOP',
                'reason': f"Target 3 reached (+{position.get('rr_target3', 4.0)}R) - Use trailing stop"
            })
            
            # Trailing stop aktif
            remaining_position = 0
        
        return {
            'exits': exits,
            'new_stop': new_stop,
            'remaining_position_pct': remaining_position,
            'recommendation': self._generate_position_recommendation(exits, remaining_position)
        }
    
    def smart_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        risk: float,
        atr: Optional[float] = None
    ) -> Dict:
        """
        Trailing stop hesapla (Kârdaki stop'u sürmek)
        
        Args:
            entry_price: Giriş fiyatı
            current_price: Güncel fiyat
            risk: İlk risk miktarı
            atr: Average True Range (opsiyonel)
        
        Returns:
            Trailing stop dictionary
        """
        profit = current_price - entry_price
        profit_percent = (profit / entry_price) * 100
        
        if profit_percent < 2:
            # Henüz trailing stop için erken
            return {
                'action': 'WAIT',
                'message': 'Profit too small for trailing stop (< 2%)',
                'trailing_stop': None
            }
        
        # Trailing stop seviyesi: En yüksek fiyattan 1.5 ATR veya 2R aşağıda
        if atr and atr > 0:
            trailing_distance = atr * 1.5
        else:
            trailing_distance = risk * 2
        
        trailing_stop = current_price - trailing_distance
        
        # Trailing stop, en azından +1R'de olmalı
        min_trailing_stop = entry_price + risk
        trailing_stop = max(trailing_stop, min_trailing_stop)
        
        return {
            'action': 'TRAILING',
            'trailing_stop': round(trailing_stop, 2),
            'trailing_distance': round(trailing_distance, 2),
            'protection_level': round(((trailing_stop - entry_price) / risk, 2)),
            'message': f'Profit protected at {round(((trailing_stop - entry_price) / risk, 1))}R'
        }
    
    def _generate_position_recommendation(
        self,
        exits: list,
        remaining_position_pct: int
    ) -> str:
        """Pozisyon önerisi oluştur"""
        
        if not exits:
            return 'HOLD'  # Henüz hedeflereulaşılmadı
        
        if remaining_position_pct == 0:
            return 'FULLY_EXITED'  # Tüm pozisyon kapatıldı
        
        if len(exits) == 1:
            return 'PARTIAL_EXIT_1/3'  # İlk hedef, 1/3 çıkıldı
        
        if len(exits) == 2:
            return 'PARTIAL_EXIT_2/3'  # İkinci hedef, 2/3 çıkıldı
        
        if len(exits) == 3:
            return 'USE_TRAILING_STOP'  # Üçüncü hedef, trailing stop kullan
        
        return 'HOLD'
    
    @staticmethod
    def apply_to_trade_plan(trade_plan: Dict, config: dict) -> Dict:
        """
        Mevcut trade plan'a multi-level exit ekle
        
        Args:
            trade_plan: Trade plan dictionary (entry, stop, target1)
            config: Configuration
        
        Returns:
            Enhanced trade plan with 3 targets
        """
        strategy = MultiLevelExitStrategy(config)
        
        entry = trade_plan.get('entry', 0)
        stop = trade_plan.get('stop', 0)
        
        if entry == 0 or stop == 0:
            logger.warning("Invalid trade plan (missing entry or stop)")
            return trade_plan
        
        # Multi-level targets hesapla
        ml_targets = strategy.calculate_multi_level_targets(entry, stop)
        
        # Mevcut trade plan'a ekle
        enhanced_plan = trade_plan.copy()
        enhanced_plan.update({
            'target1': ml_targets.get('target_1'),
            'target2': ml_targets.get('target_2'),
            'target3': ml_targets.get('target_3'),
            'rr_target1': ml_targets.get('rr_target1'),
            'rr_target2': ml_targets.get('rr_target2'),
            'rr_target3': ml_targets.get('rr_target3'),
            'exit_strategy': 'MULTI_LEVEL',
            'exit_plan': ml_targets.get('exit_plan'),
        })
        
        logger.info(f"✅ Multi-level targets: T1={ml_targets.get('target_1')}, T2={ml_targets.get('target_2')}, T3={ml_targets.get('target_3')}")
        
        return enhanced_plan
