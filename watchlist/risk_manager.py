# -*- coding: utf-8 -*-
"""
Risk Manager (V3.0) - Portföy Seviyesinde Risk Değerlendirmesi
VaR, CVaR, Bileşik Risk Skoru ve Portföy Risk Analizi
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Kurumsal düzeyde risk yönetimi motoru.
    
    Kullanım:
        rm = RiskManager()
        risk_score = rm.calculate_stock_risk_score(df)
        var = rm.calculate_var(returns, confidence=0.95)
        portfolio = rm.calculate_portfolio_risk(returns_dict)
    """
    
    # Bileşik risk skoru ağırlıkları
    WEIGHT_VOLATILITY = 0.30      # Volatilite
    WEIGHT_DRAWDOWN = 0.25        # Maximum Drawdown
    WEIGHT_TAIL_RISK = 0.15       # Kuyruk riski (VaR)
    WEIGHT_LIQUIDITY = 0.15       # Likidite riski  
    WEIGHT_MOMENTUM = 0.15        # Negatif momentum
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
    
    # =========================================================================
    # VALUE AT RISK (VaR)
    # =========================================================================
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence: float = 0.95,
        method: str = 'historical'
    ) -> float:
        """
        Value at Risk (VaR) hesapla
        
        Args:
            returns: Günlük getiri serisi
            confidence: Güven düzeyi (0.90, 0.95, 0.99)
            method: 'historical' veya 'parametric'
        
        Returns:
            VaR değeri (negatif float, ör: -0.032 = %3.2 kayıp riski)
        """
        if returns is None or len(returns) < 20:
            return 0.0
        
        try:
            clean = returns.dropna()
            
            if method == 'parametric':
                # Normal dağılım varsayımı ile
                from scipy import stats
                z_score = stats.norm.ppf(1 - confidence)
                var = clean.mean() + z_score * clean.std()
            else:
                # Historical - gerçek dağılımdan
                var = float(np.percentile(clean, (1 - confidence) * 100))
            
            return round(var, 6)
            
        except Exception as e:
            logger.error(f"❌ VaR hesaplama hatası: {e}")
            return 0.0
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence: float = 0.95
    ) -> float:
        """
        Conditional VaR (Expected Shortfall) hesapla
        VaR'ı aşan kayıpların ortalaması
        
        Args:
            returns: Günlük getiri serisi
            confidence: Güven düzeyi
        
        Returns:
            CVaR değeri (negatif float, VaR'dan daha kötü)
        """
        if returns is None or len(returns) < 20:
            return 0.0
        
        try:
            clean = returns.dropna()
            var = self.calculate_var(clean, confidence)
            
            # VaR'ın altındaki getiriler
            tail_losses = clean[clean <= var]
            
            if len(tail_losses) == 0:
                return var
            
            return round(float(tail_losses.mean()), 6)
            
        except Exception as e:
            logger.error(f"❌ CVaR hesaplama hatası: {e}")
            return 0.0
    
    # =========================================================================
    # BİLEŞİK RİSK SKORU (0-100)
    # =========================================================================
    
    def calculate_stock_risk_score(
        self,
        df: pd.DataFrame,
        avg_volume: float = None,
        market_avg_volume: float = None
    ) -> Dict:
        """
        Hisse bazlı bileşik risk skoru hesapla (0=düşük risk, 100=yüksek risk)
        
        Args:
            df: OHLCV DataFrame ('close', 'volume' sütunları gerekli)
            avg_volume: Hissenin ortalama günlük hacmi
            market_avg_volume: Piyasa ortalama günlük hacmi (likidite karşılaştırması)
        
        Returns:
            {
                'risk_score': float (0-100),
                'components': {
                    'volatility_risk': float,
                    'drawdown_risk': float,
                    'tail_risk': float,
                    'liquidity_risk': float,
                    'momentum_risk': float
                },
                'var_95': float,
                'cvar_95': float,
                'risk_label': str ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
            }
        """
        result = {
            'risk_score': 50.0,
            'components': {},
            'var_95': 0.0,
            'cvar_95': 0.0,
            'risk_label': 'MEDIUM'
        }
        
        if df is None or len(df) < 30:
            return result
        
        try:
            prices = df['close']
            returns = prices.pct_change().dropna()
            
            # 1. Volatilite Riski (0-100)
            annual_vol = returns.std() * np.sqrt(252)
            # BIST'te normal vol ~25-40%, yüksek >60%
            vol_risk = min(100.0, (annual_vol / 0.80) * 100)
            
            # 2. Drawdown Riski (0-100)
            peak = prices.expanding().max()
            drawdown = (prices - peak) / peak
            max_dd = abs(drawdown.min())
            # %30+ MDD = yüksek risk
            dd_risk = min(100.0, (max_dd / 0.50) * 100)
            
            # 3. Kuyruk Riski - VaR (0-100) 
            var_95 = self.calculate_var(returns, 0.95)
            cvar_95 = self.calculate_cvar(returns, 0.95)
            # Günlük %3+ VaR = yüksek kuyruk riski
            tail_risk = min(100.0, (abs(var_95) / 0.05) * 100)
            
            # 4. Likidite Riski (0-100)
            if 'volume' in df.columns and avg_volume and market_avg_volume:
                vol_ratio = avg_volume / market_avg_volume if market_avg_volume > 0 else 1.0
                # Düşük hacim = yüksek likidite riski
                liq_risk = max(0.0, min(100.0, (1.0 - min(1.0, vol_ratio)) * 100))
            elif 'volume' in df.columns:
                avg_vol = df['volume'].mean()
                recent_vol = df['volume'].tail(20).mean()
                if avg_vol > 0:
                    vol_ratio = recent_vol / avg_vol
                    liq_risk = max(0.0, min(100.0, (1.0 - min(1.0, vol_ratio * 0.5)) * 50))
                else:
                    liq_risk = 50.0
            else:
                liq_risk = 50.0  # Veri yoksa orta
            
            # 5. Negatif Momentum Riski (0-100)
            if len(returns) >= 20:
                recent_20 = returns.tail(20).mean() * 252  # Yıllıklandırılmış
                sma_50 = prices.tail(50).mean() if len(prices) >= 50 else prices.mean()
                current = prices.iloc[-1]
                
                # Fiyat SMA50 altında + negatif momentum = max risk
                below_sma = 1.0 if current < sma_50 else 0.0
                neg_momentum = max(0.0, -recent_20)  # Sadece negatif kısım
                
                mom_risk = min(100.0, (neg_momentum / 0.50) * 50 + below_sma * 50)
            else:
                mom_risk = 50.0
            
            # Bileşik skor
            risk_score = (
                vol_risk * self.WEIGHT_VOLATILITY +
                dd_risk * self.WEIGHT_DRAWDOWN +
                tail_risk * self.WEIGHT_TAIL_RISK +
                liq_risk * self.WEIGHT_LIQUIDITY +
                mom_risk * self.WEIGHT_MOMENTUM
            )
            
            risk_score = round(max(0.0, min(100.0, risk_score)), 1)
            
            # Risk etiketi
            if risk_score >= 75:
                label = "CRITICAL"
            elif risk_score >= 50:
                label = "HIGH"
            elif risk_score >= 25:
                label = "MEDIUM"
            else:
                label = "LOW"
            
            result = {
                'risk_score': risk_score,
                'components': {
                    'volatility_risk': round(vol_risk, 1),
                    'drawdown_risk': round(dd_risk, 1),
                    'tail_risk': round(tail_risk, 1),
                    'liquidity_risk': round(liq_risk, 1),
                    'momentum_risk': round(mom_risk, 1)
                },
                'var_95': round(var_95 * 100, 2),  # Yüzde olarak
                'cvar_95': round(cvar_95 * 100, 2),
                'max_drawdown_pct': round(max_dd * 100, 2),
                'annual_volatility_pct': round(annual_vol * 100, 2),
                'risk_label': label
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Risk skoru hesaplama hatası: {e}")
            return result
    
    # =========================================================================
    # PORTFÖY RİSK ANALİZİ
    # =========================================================================
    
    def calculate_portfolio_risk(
        self,
        returns_dict: Dict[str, pd.Series],
        weights: Dict[str, float] = None
    ) -> Dict:
        """
        Portföy seviyesinde risk analizi
        
        Args:
            returns_dict: {'GARAN': pd.Series, 'THYAO': pd.Series, ...}
            weights: {'GARAN': 0.3, 'THYAO': 0.7, ...} (None = eşit ağırlık)
        
        Returns:
            {
                'portfolio_var': float,
                'portfolio_cvar': float,
                'portfolio_volatility': float,
                'individual_risks': {symbol: risk_score, ...},
                'diversification_benefit': float,
                'weighted_risk_score': float
            }
        """
        if not returns_dict or len(returns_dict) < 1:
            return {'error': 'Yeterli veri yok'}
        
        try:
            symbols = list(returns_dict.keys())
            n = len(symbols)
            
            # Eşit ağırlık
            if weights is None:
                weights = {s: 1.0/n for s in symbols}
            
            # Returns DataFrame
            returns_df = pd.DataFrame(returns_dict).dropna()
            
            if len(returns_df) < 20:
                return {'error': 'Yeterli ortak veri yok'}
            
            # Ağırlık vektörü
            w = np.array([weights.get(s, 1.0/n) for s in returns_df.columns])
            w = w / w.sum()  # Normalize
            
            # Portföy getirisi
            portfolio_returns = returns_df.dot(w)
            
            # Portföy VaR & CVaR
            port_var = self.calculate_var(portfolio_returns, 0.95)
            port_cvar = self.calculate_cvar(portfolio_returns, 0.95)
            
            # Portföy volatilite
            cov_matrix = returns_df.cov() * 252
            port_vol = float(np.sqrt(w.T @ cov_matrix.values @ w))
            
            # Bireysel VaR'lar toplamı vs Portföy VaR (çeşitlendirme faydası)
            individual_vars = {}
            sum_individual_var = 0.0
            for sym in symbols:
                i_var = self.calculate_var(returns_dict[sym], 0.95)
                w_sym = weights.get(sym, 1.0/n)
                individual_vars[sym] = round(i_var * 100, 2)
                sum_individual_var += abs(i_var) * w_sym
            
            # Çeşitlendirme faydası (%)
            if sum_individual_var > 0:
                div_benefit = (1 - abs(port_var) / sum_individual_var) * 100
            else:
                div_benefit = 0.0
            
            # Bireysel risk skorları
            individual_risks = {}
            for sym in symbols:
                if sym in returns_dict:
                    r = returns_dict[sym]
                    fake_df = pd.DataFrame({'close': (1 + r).cumprod() * 100})
                    score_data = self.calculate_stock_risk_score(fake_df)
                    individual_risks[sym] = score_data['risk_score']
            
            # Ağırlıklı bileşik risk
            weighted_risk = sum(
                individual_risks.get(s, 50.0) * weights.get(s, 1.0/n)
                for s in symbols
            )
            
            return {
                'portfolio_var_95': round(port_var * 100, 2),
                'portfolio_cvar_95': round(port_cvar * 100, 2),
                'portfolio_volatility_annual': round(port_vol * 100, 2),
                'individual_vars': individual_vars,
                'individual_risks': individual_risks,
                'diversification_benefit_pct': round(max(0, div_benefit), 1),
                'weighted_risk_score': round(weighted_risk, 1),
                'symbols': symbols,
                'weights': {s: round(w, 4) for s, w in zip(symbols, w)}
            }
            
        except Exception as e:
            logger.error(f"❌ Portföy risk hesaplama hatası: {e}")
            return {'error': str(e)}
