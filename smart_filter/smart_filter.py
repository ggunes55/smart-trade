# smart_filter/smart_filter.py - EXCHANGE-SPECIFIC VERSION
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from core.types import FilterScore, MarketRegime

class SmartFilterSystem:
    """Akıllı filtre sistemi - Exchange-specific parametreler"""
    
    # 🆕 EXCHANGE-SPECIFIC CONFIGURATIONS
    EXCHANGE_CONFIGS = {
        'BIST': {
            'name': 'Borsa Istanbul',
            'currency': 'TRY',
            'min_rsi': 30,
            'max_rsi': 70,
            'min_relative_volume': 1.0,
            'min_trend_score': 50,
            'min_adx': 20,
            'min_risk_reward': 2.0,
            'max_daily_change': 10.0,
            'min_liquidity': 0.5,
            'volatility_multiplier': 1.0,
            'commission_rate': 0.2,  # %0.2 komisyon + KDV
            'description': 'Türkiye piyasası - yüksek volatilite, likidite odaklı'
        },
        'NASDAQ': {
            'name': 'NASDAQ',
            'currency': 'USD',
            'min_rsi': 35,
            'max_rsi': 65,
            'min_relative_volume': 1.2,
            'min_trend_score': 60,
            'min_adx': 25,
            'min_risk_reward': 2.5,
            'max_daily_change': 8.0,
            'min_liquidity': 1.0,
            'volatility_multiplier': 0.8,
            'commission_rate': 0.1,
            'description': 'NASDAQ - teknoloji ağırlıklı, momentum odaklı'
        },
        'NYSE': {
            'name': 'New York Stock Exchange',
            'currency': 'USD',
            'min_rsi': 35,
            'max_rsi': 65,
            'min_relative_volume': 1.1,
            'min_trend_score': 55,
            'min_adx': 22,
            'min_risk_reward': 2.3,
            'max_daily_change': 7.0,
            'min_liquidity': 0.8,
            'volatility_multiplier': 0.9,
            'commission_rate': 0.1,
            'description': 'NYSE - geleneksel hisseler, daha stabil'
        },
        'CRYPTO': {
            'name': 'Crypto Market',
            'currency': 'USD',
            'min_rsi': 30,
            'max_rsi': 80,
            'min_relative_volume': 1.0,
            'min_trend_score': 65,  # Daha yüksek trend onayı gerekli
            'min_adx': 25,
            'min_risk_reward': 3.0, # Daha yüksek R/R
            'max_daily_change': 20.0, # Yüksek volatilite toleransı
            'min_liquidity': 1.0,
            'volatility_multiplier': 1.5, # Geniş stoplar
            'commission_rate': 0.1,
            'description': 'Kripto Piyasası - Yüksek volatilite, yüksek risk/getiri'
        }
    }
    
    def __init__(self, config, exchange='BIST'):
        self.config = config
        self.exchange = exchange.upper()
        
        # Exchange-specific ayarları yükle
        self.exchange_config = self.EXCHANGE_CONFIGS.get(
            self.exchange, 
            self.EXCHANGE_CONFIGS['BIST']
        )
        
        # Ağırlıkları exchange'e göre ayarla
        self.weights = self._get_exchange_weights()
        
        # Minimum skorları exchange'e göre ayarla
        self.min_total_score = config.get('min_total_score', 60)
        self.min_category_scores = self._get_exchange_min_scores()
        
        print(f"✅ {self.exchange_config['name']} için filtreler yüklendi")
        print(f"📋 {self.exchange_config['description']}")
    
    def _get_exchange_weights(self) -> dict:
        """Exchange'e özel ağırlıklar"""
        if self.exchange == 'BIST':
            # BIST: Volatilite ve hacim daha önemli
            return {
                'trend': 25,
                'momentum': 25,
                'volume': 25,
                'volatility': 15,
                'risk': 10
            }
        elif self.exchange == 'NASDAQ':
            # NASDAQ: Momentum ve trend daha önemli
            return {
                'trend': 30,
                'momentum': 30,
                'volume': 20,
                'volatility': 10,
                'risk': 10
            }
        elif self.exchange == 'CRYPTO':
            # CRYPTO: Momentum ve Risk en önemli
            return {
                'trend': 30,
                'momentum': 25,
                'volume': 15,
                'volatility': 10,
                'risk': 20
            }
        else:  # NYSE
            # NYSE: Dengeli yaklaşım
            return {
                'trend': 30,
                'momentum': 25,
                'volume': 20,
                'volatility': 15,
                'risk': 10
            }
    
    def _get_exchange_min_scores(self) -> dict:
        """Exchange'e özel minimum skorlar"""
        if self.exchange == 'BIST':
            return {
                'trend': 12,
                'momentum': 10,
                'volume': 10,
            }
        elif self.exchange == 'NASDAQ':
            return {
                'trend': 18,
                'momentum': 15,
                'volume': 8,
            }
        elif self.exchange == 'CRYPTO':
            return {
                'trend': 20,
                'momentum': 15,
                'volume': 8,
            }
        else:  # NYSE
            return {
                'trend': 15,
                'momentum': 12,
                'volume': 8,
            }
    
    def get_exchange_info(self) -> str:
        """Exchange bilgisi döndür"""
        cfg = self.exchange_config
        return f"""
🌍 {cfg['name']} ({self.exchange})
💰 Para Birimi: {cfg['currency']}
📊 Min RSI: {cfg['min_rsi']} - Max RSI: {cfg['max_rsi']}
📈 Min Trend Skoru: {cfg['min_trend_score']}
💵 Komisyon: %{cfg['commission_rate']}
📋 {cfg['description']}
"""
    
    def detect_market_regime(self, market_data: pd.DataFrame) -> MarketRegime:
        """Piyasa rejimini tespit et (Exchange-aware)"""
        if market_data is None or len(market_data) < 50:
            return MarketRegime.SIDEWAYS
        
        close = market_data['close']
        ema20 = close.ewm(span=20).mean()
        ema50 = close.ewm(span=50).mean()
        current_price = close.iloc[-1]
        
        # 🆕 Exchange'e özel volatilite eşiği
        volatility_threshold = {
            'BIST': 0.4,
            'NASDAQ': 0.35,
            'NYSE': 0.3,
            'CRYPTO': 0.8  # Kripto için çok daha yüksek eşik
        }.get(self.exchange, 0.4)
        
        if current_price > ema20.iloc[-1] > ema50.iloc[-1]:
            slope_20 = (ema20.iloc[-1] - ema20.iloc[-20]) / ema20.iloc[-20] * 100
            if slope_20 > 5:
                return MarketRegime.BULL
            else:
                return MarketRegime.SIDEWAYS
        elif current_price < ema20.iloc[-1] < ema50.iloc[-1]:
            return MarketRegime.BEAR
        
        returns = close.pct_change()
        volatility = returns.std() * np.sqrt(252)
        if volatility > volatility_threshold:
            return MarketRegime.VOLATILE
        
        return MarketRegime.SIDEWAYS
    
    def calculate_trend_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        """Trend skoru - EXCHANGE-AWARE"""
        score = 0.0
        max_score = 30.0
        details = {}
        
        # 🆕 Exchange-specific minimum trend skoru
        min_trend = self.exchange_config['min_trend_score']
        
        # EMA alignment
        ema_score = 4 if latest['close'] > latest.get('EMA20', 0) else 0
        if ema_score > 0 and latest.get('EMA20', 0) > latest.get('EMA50', 0):
            ema_score += 6
        details['ema_alignment'] = ema_score
        score += ema_score
        
        # EMA slopes
        ema20_slope = df['EMA20'].pct_change(5).iloc[-1] * 100 if 'EMA20' in df.columns else 0
        ema50_slope = df['EMA50'].pct_change(5).iloc[-1] * 100 if 'EMA50' in df.columns else 0
        
        # 🆕 Exchange'e göre slope eşikleri
        slope_thresholds = {
            'BIST': (0.1, 0.05),  # Daha yüksek eşik (volatil piyasa)
            'NASDAQ': (0.05, 0.02),
            'NYSE': (0.04, 0.02),
            'CRYPTO': (0.15, 0.08) # Çok güçlü trend onayı
        }.get(self.exchange, (0.05, 0.02))
        
        slope_score = 0
        if ema20_slope > slope_thresholds[0]: 
            slope_score += 5
        elif ema20_slope > 0: 
            slope_score += 2
        if ema50_slope > slope_thresholds[1]: 
            slope_score += 5
        elif ema50_slope > 0: 
            slope_score += 2
        
        details['ema_slopes'] = {'ema20': ema20_slope, 'ema50': ema50_slope}
        score += slope_score
        
        # ADX - Exchange-specific eşikler
        adx = latest.get('ADX', 0)
        min_adx = self.exchange_config['min_adx']
        
        adx_score = 10 if adx > min_adx + 10 else (7 if adx > min_adx + 5 else (4 if adx > min_adx else 0))
        details['adx'] = adx
        details['min_adx_threshold'] = min_adx
        score += adx_score
        
        passed = score >= self.min_category_scores.get('trend', 15)
        return FilterScore('trend', score, max_score, self.weights['trend'], details, passed)
    
    def calculate_momentum_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        """Momentum skoru - EXCHANGE-AWARE"""
        score = 0.0
        max_score = 25.0
        details = {}
        
        # RSI - Exchange-specific aralıklar
        rsi = latest.get('RSI', 50)
        min_rsi = self.exchange_config['min_rsi']
        max_rsi = self.exchange_config['max_rsi']
        
        # RSI skorlama
        if min_rsi <= rsi <= max_rsi:
            rsi_score = 10
        elif min_rsi - 5 <= rsi <= max_rsi + 5:
            rsi_score = 7
        elif min_rsi - 10 <= rsi <= max_rsi + 10:
            rsi_score = 4
        else:
            rsi_score = 0
        
        details['rsi'] = rsi
        details['rsi_range'] = f"{min_rsi}-{max_rsi}"
        score += rsi_score
        
        # MACD
        macd_level = latest.get('MACD_Level', 0)
        macd_signal = latest.get('MACD_Signal', 0)
        macd_hist = latest.get('MACD_Hist', 0)
        
        macd_score = 0
        if macd_level > macd_signal:
            macd_score += 4
            if macd_hist > 0 and len(df) > 1:
                prev_hist = df['MACD_Hist'].iloc[-2]
                if macd_hist > prev_hist:
                    macd_score += 4
        
        details['macd'] = {'level': macd_level, 'signal': macd_signal}
        score += macd_score
        
        # Price momentum - Exchange-specific eşikler
        weekly_change = latest.get('Weekly_Change_Pct', 0)
        daily_change = latest.get('Daily_Change_Pct', 0)
        max_daily = self.exchange_config['max_daily_change']
        
        momentum_score = 0
        if 0 < weekly_change <= 15:
            momentum_score += 4
        if -3 < daily_change <= max_daily:
            momentum_score += 3
        
        details['price_momentum'] = {
            'weekly': weekly_change, 
            'daily': daily_change,
            'max_daily_threshold': max_daily
        }
        score += momentum_score
        
        passed = score >= self.min_category_scores.get('momentum', 10)
        return FilterScore('momentum', score, max_score, self.weights['momentum'], details, passed)
    
    def calculate_volume_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        """Hacim skoru - EXCHANGE-AWARE"""
        score = 0.0
        max_score = 20.0
        details = {}
        
        # Relative volume - Exchange-specific minimum
        rel_volume = latest.get('Relative_Volume', 1.0)
        min_vol = self.exchange_config['min_relative_volume']
        
        if rel_volume >= min_vol + 0.5:
            vol_score = 12
        elif rel_volume >= min_vol + 0.2:
            vol_score = 9
        elif rel_volume >= min_vol:
            vol_score = 6
        else:
            vol_score = 0
        
        details['relative_volume'] = rel_volume
        details['min_volume_threshold'] = min_vol
        score += vol_score
        
        # Volume trend
        volume_trend_score = 0
        if 'volume' in df.columns and len(df) >= 20:
            vol_ma10 = df['volume'].rolling(10).mean()
            vol_ma20 = df['volume'].rolling(20).mean()
            current_vol = latest.get('volume', 0)
            
            if current_vol > vol_ma10.iloc[-1]:
                volume_trend_score += 4
            if vol_ma10.iloc[-1] > vol_ma20.iloc[-1]:
                volume_trend_score += 4
        
        details['volume_trend'] = volume_trend_score > 0
        score += volume_trend_score
        
        passed = score >= self.min_category_scores.get('volume', 8)
        return FilterScore('volume', score, max_score, self.weights['volume'], details, passed)
    
    def calculate_volatility_score(self, df: pd.DataFrame, latest: pd.Series) -> FilterScore:
        """Volatilite skoru - EXCHANGE-AWARE"""
        score = 0.0
        max_score = 15.0
        details = {}
        
        # ATR - Exchange-specific çarpan
        atr_pct = (latest.get('ATR14', 0) / latest['close'] * 100) if latest['close'] > 0 else 0
        vol_multiplier = self.exchange_config['volatility_multiplier']
        
        # Ayarlanmış eşikler
        if 1 * vol_multiplier <= atr_pct <= 4 * vol_multiplier:
            atr_score = 7
        elif 4 * vol_multiplier < atr_pct <= 6 * vol_multiplier:
            atr_score = 4
        else:
            atr_score = 0
        
        details['atr_pct'] = atr_pct
        details['volatility_multiplier'] = vol_multiplier
        score += atr_score
        
        # BB Width
        bb_width = latest.get('BB_Width_Pct', 0)
        bb_score = 8 if 5 <= bb_width <= 20 else (5 if 20 < bb_width <= 30 else 2)
        details['bb_width'] = bb_width
        score += bb_score
        
        passed = score >= 5
        return FilterScore('volatility', score, max_score, self.weights['volatility'], details, passed)
    
    def calculate_risk_score(self, df: pd.DataFrame, latest: pd.Series, risk_reward: Dict) -> FilterScore:
        """Risk skoru - EXCHANGE-AWARE"""
        score = 0.0
        max_score = 10.0
        details = {}
        
        # R/R ratio - Exchange-specific minimum
        rr_ratio = risk_reward.get('rr_ratio', 0)
        min_rr = self.exchange_config['min_risk_reward']
        
        if rr_ratio >= min_rr + 0.5:
            rr_score = 6
        elif rr_ratio >= min_rr:
            rr_score = 5
        elif rr_ratio >= min_rr - 0.5:
            rr_score = 4
        else:
            rr_score = 0
        
        details['rr_ratio'] = rr_ratio
        details['min_rr_threshold'] = min_rr
        score += rr_score
        
        # Risk percentage
        risk_pct = risk_reward.get('risk_pct', 100)
        risk_score = 4 if risk_pct <= 3 else (3 if risk_pct <= 5 else (1 if risk_pct <= 8 else 0))
        details['risk_pct'] = risk_pct
        score += risk_score
        
        passed = score >= 4
        return FilterScore('risk', score, max_score, self.weights['risk'], details, passed)
    
    def evaluate_stock(self, df: pd.DataFrame, latest: pd.Series, risk_reward: Dict, symbol: str) -> Tuple[bool, float, Dict]:
        """Hisse değerlendirmesi - EXCHANGE-AWARE"""
        trend_score = self.calculate_trend_score(df, latest)
        momentum_score = self.calculate_momentum_score(df, latest)
        volume_score = self.calculate_volume_score(df, latest)
        volatility_score = self.calculate_volatility_score(df, latest)
        risk_score = self.calculate_risk_score(df, latest, risk_reward)
        
        total_weighted_score = (
            (trend_score.score / trend_score.max_score) * trend_score.weight +
            (momentum_score.score / momentum_score.max_score) * momentum_score.weight +
            (volume_score.score / volume_score.max_score) * volume_score.weight +
            (volatility_score.score / volatility_score.max_score) * volatility_score.weight +
            (risk_score.score / risk_score.max_score) * risk_score.weight
        )
        
        critical_checks = {
            'trend': trend_score.passed,
            'momentum': momentum_score.passed,
            'volume': volume_score.passed
        }
        
        passed = total_weighted_score >= self.min_total_score and all(critical_checks.values())
        
        report = {
            'symbol': symbol,
            'exchange': self.exchange,
            'total_score': round(total_weighted_score, 2),
            'passed': passed,
            'categories': {
                'trend': trend_score,
                'momentum': momentum_score,
                'volume': volume_score,
                'volatility': volatility_score,
                'risk': risk_score
            },
            'critical_checks': critical_checks,
            'signal_quality': self._determine_signal_quality(total_weighted_score),
            'exchange_config': self.exchange_config
        }
        
        return passed, total_weighted_score, report
    
    def _determine_signal_quality(self, score: float) -> str:
        """Sinyal kalitesi"""
        if score >= 85: return "🔥🔥🔥 Mükemmel"
        elif score >= 75: return "🔥🔥 Çok Güçlü"
        elif score >= 65: return "🔥 Güçlü"
        elif score >= 60: return "⚡ Orta"
        else: return "⚠️ Zayıf"
    
    def adjust_filters_for_regime(self, regime: MarketRegime) -> dict:
        """Piyasa rejimine göre filtreleri ayarla - EXCHANGE-AWARE"""
        base_adjustments = {}
        
        if regime == MarketRegime.BULL:
            base_adjustments = {
                'min_rsi': self.exchange_config['min_rsi'] + 5,
                'max_rsi': self.exchange_config['max_rsi'] + 5,
                'min_trend_score': self.exchange_config['min_trend_score'] + 5,
                'min_relative_volume': self.exchange_config['min_relative_volume'] - 0.1
            }
        elif regime == MarketRegime.BEAR:
            base_adjustments = {
                'min_rsi': self.exchange_config['min_rsi'] + 10,
                'max_rsi': self.exchange_config['max_rsi'] - 5,
                'min_trend_score': self.exchange_config['min_trend_score'] + 20,
                'min_relative_volume': self.exchange_config['min_relative_volume'] + 0.3,
                'check_adx': True,
                'min_adx': self.exchange_config['min_adx'] + 5
            }
        elif regime == MarketRegime.VOLATILE:
            base_adjustments = {
                'max_atr14_pct': 5.0 * self.exchange_config['volatility_multiplier'],
                'max_daily_change_pct': self.exchange_config['max_daily_change'] - 1.0,
                'min_trend_score': self.exchange_config['min_trend_score'] + 15,
                'use_atr_stop': True
            }
        else:  # SIDEWAYS
            base_adjustments = {
                'check_consolidation': True,
                'max_consolidation_range': 8.0,
                'check_breakout_potential': True
            }
        
        return base_adjustments
