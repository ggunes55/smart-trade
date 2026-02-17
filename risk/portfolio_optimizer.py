# -*- coding: utf-8 -*-
"""
Portfolio Optimizer - FAZA 2: Risk Parity & Position Sizing

Portföy seviyesinde optimizasyon:
- Position Sizing: Her işlem için optimum lot sayısı
- Risk Parity: Tüm pozisyonlar eşit risk taşısın
- Diversification: Kolerasyon tablosundan faydalanarak

Tarih: 12 Şubat 2026
Versiyon: 1.0 (FAZA 2)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PortfolioConfig:
    """Portföy optimizasyonu konfigürasyonu"""
    total_capital: float = 100000.0  # Toplam sermaye (TL)
    risk_per_trade: float = 0.01  # Her işlem başına risk (%1)
    max_drawdown: float = 0.20  # Maksimum çekilme (%20)
    position_size_method: str = "kelly"  # kelly, fixed_fractional, risk_parity
    max_positions: int = 10  # Aynı anda maksimum 10 pozisyon
    correlation_threshold: float = 0.7  # Yüksek kolerasyon eşiği
    rebalance_frequency: str = "weekly"  # weekly, monthly, quarterly


class PositionSizer:
    """Her işlem için optimum lot sayısı hesaplama"""
    
    def __init__(self, capital: float, risk_per_trade: float = 0.01):
        """
        Args:
            capital: Toplam sermaye
            risk_per_trade: Her işlem başına risk oranı (örn: 0.01 = %1)
        """
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.used_capital = 0
    
    def kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Kelly Criterion: f* = (p*b - q) / b
        
        f*: Optimal fraction of capital to bet
        p: Winning probability
        q: Losing probability (1-p)
        b: Ratio of win to loss
        
        Returns:
            Optimal fraction (0.0-1.0)
        """
        if avg_loss <= 0:
            return 0
        
        q = 1 - win_rate
        b = avg_win / avg_loss
        
        f_optimal = (win_rate * b - q) / b
        
        # Kelly fraction'ı conservative bırak (%50-75)
        f_safe = f_optimal * 0.5
        
        return max(0, min(1, f_safe))
    
    def calculate_position_size(self,
                               entry_price: float,
                               stop_loss: float,
                               win_rate: float = 0.55,
                               avg_win: float = 2.0,
                               avg_loss: float = 1.0,
                               method: str = "kelly") -> float:
        """
        Position size hesapla
        
        Args:
            entry_price: Giriş fiyatı
            stop_loss: Stop loss fiyatı
            win_rate: Tarihsel win rate
            avg_win: Ortalama kazanan işlem (%)
            avg_loss: Ortalama kayıp işlem (%)
            method: kelly, fixed_fractional, vb.
        
        Returns:
            Miktar (lot)
        """
        risk_amount = self.capital * self.risk_per_trade
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share <= 0:
            return 0
        
        # Base position size
        position_size = risk_amount / risk_per_share
        
        if method == "kelly":
            kelly_fraction = self.kelly_criterion(win_rate, avg_win, avg_loss)
            position_size = position_size * kelly_fraction
        
        # Available capital kontrol et
        cost = entry_price * position_size
        available = self.capital - self.used_capital
        
        if cost > available:
            position_size = available / entry_price if entry_price > 0 else 0
        
        return max(0, int(position_size))
    
    def update_used_capital(self, position_size: float, entry_price: float):
        """Kullanılan sermayeyi güncelle"""
        self.used_capital += position_size * entry_price


class RiskParity:
    """Risk parity: Tüm pozisyonlar eşit risk taşısın"""
    
    def __init__(self, positions: List[Dict]):
        """
        Args:
            positions: Position listesi
                Her position: {
                    'symbol': str,
                    'size': float (lot),
                    'entry_price': float,
                    'stop_loss': float,
                    'volatility': float
                }
        """
        self.positions = positions
        self.adjusted_sizes = []
    
    def calculate_risk_per_position(self, position: Dict) -> float:
        """Her pozisyon için risk hesapla (TL cinsinden)"""
        size = position['size']
        entry_price = position['entry_price']
        stop_loss = position['stop_loss']
        
        risk = abs(entry_price - stop_loss) * size
        return risk
    
    def adjust_for_risk_parity(self, target_risk_per_position: float) -> List[Dict]:
        """
        Pozisyon boyutlarını ayarla (risk parity)
        
        Args:
            target_risk_per_position: Her pozisyon için hedef risk
        
        Returns:
            Ayarlanmış pozisyon listesi
        """
        adjusted = []
        
        for position in self.positions:
            current_risk = self.calculate_risk_per_position(position)
            
            if current_risk > 0:
                # Gerekli adjustment
                adjustment_factor = target_risk_per_position / current_risk
                
                adjusted_position = position.copy()
                adjusted_position['size'] = adjusted_position['size'] * adjustment_factor
                adjusted_position['original_size'] = position['size']
                adjusted_position['adjustment_factor'] = adjustment_factor
                
                adjusted.append(adjusted_position)
        
        self.adjusted_sizes = adjusted
        return adjusted


class CorrelationAnalyzer:
    """Semboller arasındaki kolerasyon analizi"""
    
    @staticmethod
    def calculate_correlation_matrix(price_data: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Semboller arasındaki correlation matrix hesapla
        
        Args:
            price_data: {'SYMBOL': price_series, ...}
        
        Returns:
            Correlation DataFrame
        """
        df = pd.DataFrame(price_data)
        correlation = df.corr()
        return correlation
    
    @staticmethod
    def find_correlated_pairs(correlation: pd.DataFrame, 
                             threshold: float = 0.7) -> List[Tuple[str, str]]:
        """Yüksek kolerasyon gösteren çiftleri bul"""
        pairs = []
        symbols = correlation.columns
        
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                corr_value = correlation.loc[sym1, sym2]
                if abs(corr_value) >= threshold:
                    pairs.append((sym1, sym2, corr_value))
        
        return sorted(pairs, key=lambda x: abs(x[2]), reverse=True)


class PortfolioOptimizer:
    """Portföy seviyesinde optimizasyon orchestrator"""
    
    def __init__(self, cfg: Optional[PortfolioConfig] = None):
        self.cfg = cfg or PortfolioConfig()
        self.position_sizer = PositionSizer(
            self.cfg.total_capital,
            self.cfg.risk_per_trade
        )
        self.correlation_analyzer = CorrelationAnalyzer()
        logger.info(f"✅ PortfolioOptimizer initialized (FAZA 2)")
        logger.info(f"   - Capital: ${self.cfg.total_capital:,.0f}")
        logger.info(f"   - Risk per trade: {self.cfg.risk_per_trade:.1%}")
    
    def optimize_portfolio(self,
                          signals: List[Dict],
                          price_data: Optional[Dict] = None) -> Dict:
        """
        Portföy optimizasyonu full pipeline
        
        Args:
            signals: Sembol sinyalleri listesi
                    Her signal: {'symbol', 'entry_price', 'stop_loss', 'win_rate', ...}
            price_data: Optional kolerasyon analizi için fiyat verileri
        
        Returns:
            Optimized portfolio configuration
        """
        
        # 1. Position sizing hesapla
        portfolio = {
            'positions': [],
            'total_risk': 0,
            'diversification': None,
            'correlation_issues': []
        }
        
        for signal in signals[:self.cfg.max_positions]:
            size = self.position_sizer.calculate_position_size(
                entry_price=signal.get('entry_price'),
                stop_loss=signal.get('stop_loss'),
                win_rate=signal.get('win_rate', 0.55),
                method=self.cfg.position_size_method
            )
            
            if size > 0:
                position = {
                    'symbol': signal['symbol'],
                    'size': size,
                    'entry_price': signal['entry_price'],
                    'stop_loss': signal['stop_loss'],
                    'risk': abs(signal['entry_price'] - signal['stop_loss']) * size
                }
                portfolio['positions'].append(position)
                portfolio['total_risk'] += position['risk']
        
        # 2. Risk parity adjustment
        if len(portfolio['positions']) > 1:
            target_risk = portfolio['total_risk'] / len(portfolio['positions'])
            risk_parity = RiskParity(portfolio['positions'])
            adjusted = risk_parity.adjust_for_risk_parity(target_risk)
            portfolio['positions'] = adjusted
            logger.info(f"✅ Risk parity applied to {len(adjusted)} positions")
        
        # 3. Kolerasyon analizi
        if price_data and len(portfolio['positions']) > 1:
            try:
                symbols = [p['symbol'] for p in portfolio['positions']]
                price_subset = {s: price_data[s] for s in symbols if s in price_data}
                
                if len(price_subset) > 1:
                    corr_matrix = self.correlation_analyzer.calculate_correlation_matrix(price_subset)
                    correlated_pairs = self.correlation_analyzer.find_correlated_pairs(
                        corr_matrix,
                        self.cfg.correlation_threshold
                    )
                    
                    if correlated_pairs:
                        logger.warning(f"⚠️  High correlation detected:")
                        for sym1, sym2, corr in correlated_pairs:
                            logger.warning(f"   - {sym1} ↔ {sym2}: {corr:.2f}")
                            portfolio['correlation_issues'].append({
                                'symbols': (sym1, sym2),
                                'correlation': corr
                            })
            except Exception as e:
                logger.warning(f"Correlation analysis error: {e}")
        
        logger.info(f"✅ Portfolio optimized: {len(portfolio['positions'])} positions, Risk: ${portfolio['total_risk']:,.0f}")
        return portfolio
    
    def save_portfolio(self, portfolio: Dict, filepath: str) -> bool:
        """Optimized portfolio'yu dosyaya kaydet"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize for JSON
            portfolio_json = {
                'positions': [
                    {
                        'symbol': p['symbol'],
                        'size': float(p['size']),
                        'entry_price': float(p['entry_price']),
                        'stop_loss': float(p['stop_loss']),
                        'risk': float(p.get('risk', 0))
                    }
                    for p in portfolio['positions']
                ],
                'total_risk': float(portfolio['total_risk']),
                'correlation_issues': portfolio['correlation_issues'],
                'config': {
                    'total_capital': self.cfg.total_capital,
                    'risk_per_trade': self.cfg.risk_per_trade,
                    'position_size_method': self.cfg.position_size_method
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(portfolio_json, f, indent=2)
            
            logger.info(f"✅ Portfolio saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")
            return False


# ============================================================================
# ÖRNEK KULLANIM
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Örnek: Trading sinyalleri
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
        }
    ]
    
    # Portfolio optimizer çalıştır
    optimizer = PortfolioOptimizer(
        PortfolioConfig(
            total_capital=100000,
            risk_per_trade=0.01
        )
    )
    
    portfolio = optimizer.optimize_portfolio(signals)
    
    print("\n" + "="*60)
    print("FAZA 2: Portfolio Optimization")
    print("="*60)
    print(f"\nOptimized Positions:")
    for pos in portfolio['positions']:
        print(f"  {pos['symbol']}: {pos['size']:.0f} lot @ {pos['entry_price']:.2f}")

