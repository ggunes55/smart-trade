# -*- coding: utf-8 -*-
"""
Detailed Analysis Report - Kapsamlı Hisse Analiz Raporu

Tek bir hisse için projenin tüm analiz özelliklerini kullanarak
detaylı trade uygunluk raporu oluşturur.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Çeviri modülü
try:
    from gui.utils.translations import translate, translate_checklist, format_trend_turkish, format_strength_turkish
except ImportError:
    # Fallback dummy functions if import fails
    def translate(text): return text
    def translate_checklist(cl): return cl
    def format_trend_turkish(t): return t
    def format_strength_turkish(s): return s


class DetailedAnalysisReport:
    """
    Tek hisse için projenin tüm özelliklerini kullanarak
    detaylı analiz raporu oluşturur.
    """
    
    def __init__(self, config: dict, data_handler=None, symbol_analyzer=None):
        """
        Args:
            config: Ana konfigürasyon
            data_handler: Veri çekme handler'ı
            symbol_analyzer: Sembol analiz sınıfı
        """
        self.config = config
        self.data_handler = data_handler
        self.symbol_analyzer = symbol_analyzer
        
        # Entry timing için import
        try:
            from analysis.entry_timing import EntryTimingOptimizer
            self.entry_optimizer = EntryTimingOptimizer(config)
        except ImportError:
            self.entry_optimizer = None
            
        # Trade calculator için import
        try:
            from scanner.trade_calculator import TradeCalculator
            self.trade_calculator = TradeCalculator(config)
        except ImportError:
            self.trade_calculator = None
    
    def analyze_symbol(self, symbol: str, df: pd.DataFrame = None, exchange: str = 'BIST') -> Dict[str, Any]:
        """
        Tüm analiz modüllerini kullanarak tam analiz yapar.
        
        Args:
            symbol: Hisse sembolü
            df: OHLCV verisi (None ise data_handler'dan çekilir)
            exchange: Borsa bilgisi (BIST, NASDAQ, vb.)
            
        Returns:
            Kapsamlı analiz dictionary'si
        """
        result = {
            'symbol': symbol,
            'analysis_date': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'status': 'error',
            'error': None
        }
        
        try:
            # Veri çek
            if df is None and self.data_handler:
                try:
                    df = self.data_handler.get_daily_data(symbol, exchange=exchange)
                except AttributeError:
                    if hasattr(self.data_handler, 'get_data'):
                        df = self.data_handler.get_data(symbol)
                    else:
                        raise AttributeError("DataHandler metodları bulunamadı")
            
            if df is None or len(df) < 50:
                result['error'] = 'Yetersiz veri'
                return result
            
            # ✅ DÜZELTME: İndikatörleri hesapla (ham OHLCV verisi değil)
            try:
                from scanner.swing_hunter import SwingHunter
                hunter = SwingHunter(self.config)
                df = hunter.calculate_indicators(df)
                if df is None or df.empty:
                    result['error'] = 'İndikatör hesaplama hatası'
                    return result
            except Exception as e:
                logger.warning(f"SwingHunter indikatör hesaplama hatası: {e}")
                # Manuel indikatör hesaplama
                df = self._calculate_basic_indicators(df)
            
            latest = df.iloc[-1]
            current_price = latest['close']
            
            # 1. Fiyat bilgileri
            result['price_info'] = self._get_price_info(df, latest)
            
            # 2. Teknik göstergeler
            result['indicators'] = self._get_indicators(df, latest)
            
            # 3. Trend analizi
            result['trend'] = self._get_trend_analysis(df, latest)
            
            # 4. Destek/Direnç seviyeleri
            result['levels'] = self._get_support_resistance(df, latest)
            
            # 5. Hacim analizi
            result['volume'] = self._get_volume_analysis(df, latest)
            
            # 6. Risk metrikleri
            result['risk'] = self._get_risk_metrics(df)
            
            # 7. Entry timing
            result['entry'] = self._get_entry_timing(df, symbol)
            
            # 8. Trade planı
            result['trade_plan'] = self._get_trade_plan(symbol, df, latest)
            
            # 9. Trade uygunluk değerlendirmesi
            result['suitability'] = self._evaluate_trade_suitability(result)
            
            result['status'] = 'success'
            
        except Exception as e:
            logger.error(f"Analiz hatası {symbol}: {e}")
            result['error'] = str(e)
            
        return result
    
    def _get_price_info(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Fiyat bilgilerini al"""
        current = latest['close']
        prev_close = df.iloc[-2]['close'] if len(df) > 1 else current
        
        # Değişim hesapla
        daily_change = ((current - prev_close) / prev_close) * 100 if prev_close > 0 else 0
        
        # Haftalık değişim
        weekly_change = 0
        if len(df) >= 5:
            week_ago = df.iloc[-5]['close']
            weekly_change = ((current - week_ago) / week_ago) * 100 if week_ago > 0 else 0
        
        # Aylık değişim
        monthly_change = 0
        if len(df) >= 20:
            month_ago = df.iloc[-20]['close']
            monthly_change = ((current - month_ago) / month_ago) * 100 if month_ago > 0 else 0
        
        # 52 hafta high/low
        high_52w = df['high'].max()
        low_52w = df['low'].min()
        from_high = ((current - high_52w) / high_52w) * 100 if high_52w > 0 else 0
        from_low = ((current - low_52w) / low_52w) * 100 if low_52w > 0 else 0
        
        return {
            'current': round(current, 2),
            'open': round(latest['open'], 2),
            'high': round(latest['high'], 2),
            'low': round(latest['low'], 2),
            'prev_close': round(prev_close, 2),
            'daily_change': round(daily_change, 2),
            'weekly_change': round(weekly_change, 2),
            'monthly_change': round(monthly_change, 2),
            'high_52w': round(high_52w, 2),
            'low_52w': round(low_52w, 2),
            'from_high_pct': round(from_high, 2),
            'from_low_pct': round(from_low, 2)
        }
    
    def _get_indicators(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Teknik göstergeleri al"""
        indicators = {}
        
        # RSI
        rsi = latest.get('rsi', latest.get('RSI14', None))
        if rsi is not None:
            if rsi < 30:
                rsi_status = 'Aşırı Satım ⚠️'
            elif rsi > 70:
                rsi_status = 'Aşırı Alım ⚠️'
            elif 40 <= rsi <= 60:
                rsi_status = 'Nötr ✅'
            else:
                rsi_status = 'Normal ✅'
            indicators['rsi'] = {'value': round(rsi, 1), 'status': rsi_status}
        
        # MACD
        macd = latest.get('macd', latest.get('MACD', None))
        macd_signal = latest.get('macd_signal', latest.get('MACD_Signal', None))
        if macd is not None and macd_signal is not None:
            macd_hist = macd - macd_signal
            if macd > macd_signal:
                macd_status = 'Pozitif ✅'
            else:
                macd_status = 'Negatif ❌'
            indicators['macd'] = {
                'value': round(macd, 4),
                'signal': round(macd_signal, 4),
                'histogram': round(macd_hist, 4),
                'status': macd_status
            }
        
        # ADX
        adx = latest.get('adx', latest.get('ADX14', None))
        if adx is not None:
            if adx < 20:
                adx_status = 'Trend Yok ⚠️'
            elif adx < 25:
                adx_status = 'Zayıf Trend'
            elif adx < 40:
                adx_status = 'Güçlü Trend ✅'
            else:
                adx_status = 'Çok Güçlü Trend 🔥'
            indicators['adx'] = {'value': round(adx, 1), 'status': adx_status}
        
        # Stochastic
        stoch_k = latest.get('stoch_k', latest.get('STOCH_K', None))
        stoch_d = latest.get('stoch_d', latest.get('STOCH_D', None))
        if stoch_k is not None and stoch_d is not None:
            if stoch_k < 20:
                stoch_status = 'Aşırı Satım ⚠️'
            elif stoch_k > 80:
                stoch_status = 'Aşırı Alım ⚠️'
            else:
                stoch_status = 'Normal ✅'
            indicators['stochastic'] = {
                'k': round(stoch_k, 1),
                'd': round(stoch_d, 1),
                'status': stoch_status
            }
        
        # Bollinger Bands
        bb_upper = latest.get('bb_upper', latest.get('BB_Upper', None))
        bb_lower = latest.get('bb_lower', latest.get('BB_Lower', None))
        bb_middle = latest.get('bb_middle', latest.get('BB_Middle', None))
        if bb_upper and bb_lower and bb_middle:
            price = latest['close']
            bb_width = ((bb_upper - bb_lower) / bb_middle) * 100 if bb_middle > 0 else 0
            
            if price > bb_upper:
                bb_status = 'Üst Bant Üstü ⚠️'
            elif price < bb_lower:
                bb_status = 'Alt Bant Altı ⚠️'
            elif price > bb_middle:
                bb_status = 'Üst Yarı'
            else:
                bb_status = 'Alt Yarı'
            
            indicators['bollinger'] = {
                'upper': round(bb_upper, 2),
                'middle': round(bb_middle, 2),
                'lower': round(bb_lower, 2),
                'width': round(bb_width, 2),
                'status': bb_status
            }
        
        # ATR
        atr = latest.get('ATR14', latest.get('atr', None))
        if atr is not None:
            atr_pct = (atr / latest['close']) * 100 if latest['close'] > 0 else 0
            indicators['atr'] = {
                'value': round(atr, 2),
                'pct': round(atr_pct, 2)
            }
        
        # OBV trend
        if 'obv' in df.columns or 'OBV' in df.columns:
            obv = df.get('obv', df.get('OBV'))
            if len(obv) >= 20:
                obv_sma = obv.rolling(20).mean().iloc[-1]
                obv_current = obv.iloc[-1]
                if obv_current > obv_sma:
                    obv_status = 'Birikiyor ✅'
                else:
                    obv_status = 'Dağılıyor ⚠️'
                indicators['obv'] = {'status': obv_status}
        
        return indicators
    
    def _calculate_basic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Temel indikatörleri manuel hesapla (fallback)"""
        try:
            import talib
            
            close = df['close'].values.astype(float)
            high = df['high'].values.astype(float)
            low = df['low'].values.astype(float)
            volume = df['volume'].values.astype(float)
            
            # RSI
            df['rsi'] = talib.RSI(close, timeperiod=14)
            
            # MACD
            df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(close)
            
            # ADX
            df['adx'] = talib.ADX(high, low, close, timeperiod=14)
            
            # Stochastic
            df['stoch_k'], df['stoch_d'] = talib.STOCH(high, low, close)
            
            # Bollinger Bands
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(close)
            
            # ATR
            df['ATR14'] = talib.ATR(high, low, close, timeperiod=14)
            
            # OBV
            df['obv'] = talib.OBV(close, volume)
            
        except Exception as e:
            logger.warning(f"TA-Lib manuel hesaplama hatası: {e}")
            # En basit hesaplamalar
            df['rsi'] = 50  # Varsayılan
            df['macd'] = 0
            df['adx'] = 25
            
        return df
    
    def _get_trend_analysis(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Trend analizini al"""
        trend = {}
        
        # EMA'ları hesapla
        close = df['close']
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1] if len(df) >= 200 else None
        
        current_price = latest['close']
        
        # EMA alignment
        if ema200:
            if current_price > ema20 > ema50 > ema200:
                alignment = 'Mükemmel Yükseliş ✅'
                alignment_score = 100
            elif current_price > ema20 > ema50:
                alignment = 'Güçlü Yükseliş ✅'
                alignment_score = 80
            elif current_price > ema50:
                alignment = 'Yükseliş'
                alignment_score = 60
            elif current_price < ema20 < ema50 < ema200:
                alignment = 'Mükemmel Düşüş ❌'
                alignment_score = 0
            elif current_price < ema20 < ema50:
                alignment = 'Güçlü Düşüş ❌'
                alignment_score = 20
            else:
                alignment = 'Karışık ⚠️'
                alignment_score = 40
        else:
            if current_price > ema20 > ema50:
                alignment = 'Yükseliş ✅'
                alignment_score = 75
            elif current_price < ema20 < ema50:
                alignment = 'Düşüş ❌'
                alignment_score = 25
            else:
                alignment = 'Nötr'
                alignment_score = 50
        
        trend['ema20'] = round(ema20, 2)
        trend['ema50'] = round(ema50, 2)
        trend['ema200'] = round(ema200, 2) if ema200 else None
        trend['alignment'] = alignment
        trend['alignment_score'] = alignment_score
        
        # Trend yönü
        if len(df) >= 20:
            price_20_ago = df.iloc[-20]['close']
            trend_pct = ((current_price - price_20_ago) / price_20_ago) * 100
            
            if trend_pct > 5:
                direction = 'Güçlü Yükseliş ▲'
            elif trend_pct > 0:
                direction = 'Yükseliş ▲'
            elif trend_pct > -5:
                direction = 'Düşüş ▼'
            else:
                direction = 'Güçlü Düşüş ▼'
            
            trend['direction'] = direction
            trend['trend_pct'] = round(trend_pct, 2)
        
        # Momentum
        macd = latest.get('macd', latest.get('MACD', 0))
        macd_signal = latest.get('macd_signal', latest.get('MACD_Signal', 0))
        rsi = latest.get('rsi', latest.get('RSI14', 50))
        
        momentum_score = 50
        if macd > macd_signal:
            momentum_score += 20
        if rsi > 50:
            momentum_score += 15
        if current_price > ema20:
            momentum_score += 15
        
        trend['momentum_score'] = min(100, momentum_score)
        
        if momentum_score >= 80:
            trend['momentum'] = 'Çok Güçlü ✅'
        elif momentum_score >= 60:
            trend['momentum'] = 'Güçlü'
        elif momentum_score >= 40:
            trend['momentum'] = 'Nötr'
        else:
            trend['momentum'] = 'Zayıf ⚠️'
        
        return trend
    
    def _get_support_resistance(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Destek ve direnç seviyelerini al"""
        current = latest['close']
        
        # Basit S/R hesaplama
        high_20 = df['high'].rolling(20).max().iloc[-1]
        low_20 = df['low'].rolling(20).min().iloc[-1]
        
        # Pivot points
        prev = df.iloc[-2] if len(df) > 1 else latest
        pivot = (prev['high'] + prev['low'] + prev['close']) / 3
        r1 = 2 * pivot - prev['low']
        s1 = 2 * pivot - prev['high']
        r2 = pivot + (prev['high'] - prev['low'])
        s2 = pivot - (prev['high'] - prev['low'])
        
        levels = {
            'current_price': round(current, 2),
            'resistance1': round(r1, 2),
            'resistance1_pct': round(((r1 - current) / current) * 100, 2),
            'resistance2': round(r2, 2),
            'resistance2_pct': round(((r2 - current) / current) * 100, 2),
            'support1': round(s1, 2),
            'support1_pct': round(((s1 - current) / current) * 100, 2),
            'support2': round(s2, 2),
            'support2_pct': round(((s2 - current) / current) * 100, 2),
            'pivot': round(pivot, 2),
            'high_20': round(high_20, 2),
            'low_20': round(low_20, 2)
        }
        
        # Fibonacci seviyeleri
        fib_high = df['high'].max()
        fib_low = df['low'].min()
        fib_range = fib_high - fib_low
        
        levels['fibonacci'] = {
            '0.0': round(fib_low, 2),
            '0.236': round(fib_low + fib_range * 0.236, 2),
            '0.382': round(fib_low + fib_range * 0.382, 2),
            '0.5': round(fib_low + fib_range * 0.5, 2),
            '0.618': round(fib_low + fib_range * 0.618, 2),
            '0.786': round(fib_low + fib_range * 0.786, 2),
            '1.0': round(fib_high, 2)
        }
        
        return levels
    
    def _get_volume_analysis(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Hacim analizini al"""
        current_volume = latest['volume']
        
        # Volume ortalamaları
        vol_sma20 = df['volume'].rolling(20).mean().iloc[-1]
        vol_sma50 = df['volume'].rolling(50).mean().iloc[-1] if len(df) >= 50 else vol_sma20
        
        rvol = (current_volume / vol_sma20) if vol_sma20 > 0 else 1
        
        if rvol > 2:
            vol_status = 'Çok Yüksek 🔥'
        elif rvol > 1.5:
            vol_status = 'Yüksek ✅'
        elif rvol > 0.8:
            vol_status = 'Normal'
        else:
            vol_status = 'Düşük ⚠️'
        
        volume = {
            'current': int(current_volume),
            'avg_20': int(vol_sma20),
            'avg_50': int(vol_sma50),
            'rvol': round(rvol, 2),
            'status': vol_status
        }
        
        # Son 5 günlük hacim trendi
        if len(df) >= 5:
            vol_5d = df['volume'].tail(5)
            vol_trend = 'Artan' if vol_5d.iloc[-1] > vol_5d.iloc[0] else 'Azalan'
            volume['trend'] = vol_trend
        
        return volume
    
    def _get_risk_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Risk metriklerini hesapla"""
        risk = {}
        
        if len(df) < 20:
            return risk
        
        returns = df['close'].pct_change().dropna()
        
        # Volatilite (yıllık)
        volatility = returns.std() * np.sqrt(252) * 100
        
        if volatility < 20:
            vol_status = 'Düşük ✅'
        elif volatility < 40:
            vol_status = 'Normal'
        elif volatility < 60:
            vol_status = 'Yüksek ⚠️'
        else:
            vol_status = 'Çok Yüksek ⚠️'
        
        risk['volatility'] = round(volatility, 2)
        risk['volatility_status'] = vol_status
        
        # Sharpe Ratio (basitleştirilmiş, rf=0)
        mean_return = returns.mean() * 252
        sharpe = mean_return / (volatility / 100) if volatility > 0 else 0
        risk['sharpe'] = round(sharpe, 2)
        
        if sharpe > 2:
            risk['sharpe_status'] = 'Mükemmel ✅'
        elif sharpe > 1:
            risk['sharpe_status'] = 'İyi ✅'
        elif sharpe > 0:
            risk['sharpe_status'] = 'Pozitif'
        else:
            risk['sharpe_status'] = 'Negatif ⚠️'
        
        # Maximum Drawdown
        cummax = df['close'].cummax()
        drawdown = ((df['close'] - cummax) / cummax) * 100
        max_dd = drawdown.min()
        risk['max_drawdown'] = round(max_dd, 2)
        
        # ATR bazlı risk
        if 'ATR14' in df.columns or 'atr' in df.columns:
            atr = df.get('ATR14', df.get('atr')).iloc[-1]
            atr_pct = (atr / df['close'].iloc[-1]) * 100
            risk['atr_pct'] = round(atr_pct, 2)
        
        return risk
    
    def _get_entry_timing(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Entry timing değerlendirmesi"""
        entry = {
            'recommendation': 'BEKLE',
            'confidence': 0,
            'checklist': {},
            'failed_checks': []
        }
        
        if self.entry_optimizer:
            try:
                result = self.entry_optimizer.get_entry_recommendation(df, symbol)
                entry['recommendation'] = result.get('recommendation', 'BEKLE')
                entry['confidence'] = result.get('overall_confidence', 0)
                entry['checklist'] = result.get('checklist', {})
                entry['failed_checks'] = result.get('failed_checks', [])
                entry['action'] = result.get('action', '')
                
                if result.get('entry_info'):
                    entry['signal_type'] = result['entry_info'].get('signal_type', '')
                    entry['reason'] = result['entry_info'].get('reason', '')
            except Exception as e:
                logger.error(f"Entry timing hatası: {e}")
        else:
            # Manuel kontrol
            latest = df.iloc[-1]
            checklist = {}
            failed = []
            
            # Volume
            vol_sma = df['volume'].rolling(20).mean().iloc[-1]
            checklist['volume_above_average'] = latest['volume'] > vol_sma
            if not checklist['volume_above_average']:
                failed.append('Hacim ortalamanın altında')
            
            # RSI
            rsi = latest.get('rsi', latest.get('RSI14', 50))
            checklist['rsi_not_extreme'] = 25 < rsi < 75
            if not checklist['rsi_not_extreme']:
                failed.append(f'RSI extreme ({rsi:.1f})')
            
            # Trend
            ema20 = df['close'].ewm(span=20).mean().iloc[-1]
            ema50 = df['close'].ewm(span=50).mean().iloc[-1]
            checklist['trend_aligned'] = latest['close'] > ema20 and ema20 > ema50
            if not checklist['trend_aligned']:
                failed.append('Trend uyumsuz')
            
            # Momentum
            macd = latest.get('macd', latest.get('MACD', 0))
            macd_signal = latest.get('macd_signal', latest.get('MACD_Signal', 0))
            checklist['momentum_positive'] = macd > macd_signal
            if not checklist['momentum_positive']:
                failed.append('Momentum negatif')
            
            passed = sum(checklist.values())
            total = len(checklist)
            
            entry['checklist'] = checklist
            entry['failed_checks'] = failed
            entry['confidence'] = passed / total if total > 0 else 0
            
            if passed == total:
                entry['recommendation'] = 'GÜÇLÜ AL'
            elif passed >= total * 0.75:
                entry['recommendation'] = 'AL'
            else:
                entry['recommendation'] = 'BEKLE'
        
        return entry
    
    def _get_trade_plan(self, symbol: str, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Trade planını hesapla"""
        current = latest['close']
        
        # ATR bazlı stop ve target
        atr = latest.get('ATR14', latest.get('atr', None))
        if atr is None:
            # Manuel ATR hesapla
            tr = pd.concat([
                df['high'] - df['low'],
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
        
        # Stop loss
        stop_loss = current - (atr * 2)
        stop_loss_pct = ((stop_loss - current) / current) * 100
        
        # Targets
        target1 = current + (atr * 3)
        target1_pct = ((target1 - current) / current) * 100
        
        target2 = current + (atr * 5)
        target2_pct = ((target2 - current) / current) * 100
        
        # R/R oranları
        risk = current - stop_loss
        reward1 = target1 - current
        reward2 = target2 - current
        
        rr1 = reward1 / risk if risk > 0 else 0
        rr2 = reward2 / risk if risk > 0 else 0
        
        # Pozisyon büyüklüğü hesabı
        capital = self.config.get('default_capital', 100000)
        risk_pct = self.config.get('risk_per_trade', 2) / 100
        risk_amount = capital * risk_pct
        
        shares = int(risk_amount / (current - stop_loss)) if (current - stop_loss) > 0 else 0
        position_value = shares * current
        
        trade_plan = {
            'entry': round(current, 2),
            'stop_loss': round(stop_loss, 2),
            'stop_loss_pct': round(stop_loss_pct, 2),
            'target1': round(target1, 2),
            'target1_pct': round(target1_pct, 2),
            'target2': round(target2, 2),
            'target2_pct': round(target2_pct, 2),
            'rr1': round(rr1, 2),
            'rr2': round(rr2, 2),
            'capital': capital,
            'risk_pct': self.config.get('risk_per_trade', 2),
            'risk_amount': round(risk_amount, 2),
            'shares': shares,
            'position_value': round(position_value, 2)
        }
        
        # R/R değerlendirmesi
        if rr1 >= 2:
            trade_plan['rr_status'] = 'Mükemmel ✅'
        elif rr1 >= 1.5:
            trade_plan['rr_status'] = 'İyi ✅'
        elif rr1 >= 1:
            trade_plan['rr_status'] = 'Kabul Edilebilir'
        else:
            trade_plan['rr_status'] = 'Düşük ⚠️'
        
        return trade_plan
    
    def _evaluate_trade_suitability(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trade uygunluğunu kapsamlı olarak değerlendir.
        
        Returns:
            suitability: UYGUN, BEKLE, UYGUN_DEGIL
            score: 0-100
            reasons: neden uygun/uygun değil
            wait_for: ne beklenmeli (uygun değilse)
        """
        score = 0
        max_score = 100
        positives = []
        negatives = []
        wait_for = []
        
        # 1. Trend değerlendirmesi (25 puan)
        trend = analysis.get('trend', {})
        alignment_score = trend.get('alignment_score', 50)
        trend_score = (alignment_score / 100) * 25
        score += trend_score
        
        if alignment_score >= 75:
            positives.append(f"Trend güçlü ve yukarı yönlü ({trend.get('alignment', '')})")
        elif alignment_score < 40:
            negatives.append("Trend zayıf veya aşağı yönlü")
            wait_for.append("EMA'ların yukarı yönlü hizalanmasını bekleyin")
        
        # 2. Entry timing (25 puan)
        entry = analysis.get('entry', {})
        entry_confidence = entry.get('confidence', 0)
        entry_score = entry_confidence * 25
        score += entry_score
        
        checklist = entry.get('checklist', {})
        passed = sum(1 for v in checklist.values() if v)
        total = len(checklist)
        
        if passed == total and total > 0:
            positives.append(f"Tüm giriş kriterleri sağlanıyor ({passed}/{total})")
        elif passed < total:
            failed = entry.get('failed_checks', [])
            for fail in failed[:3]:
                negatives.append(fail)
                wait_for.append(f"{fail} düzelmesini bekleyin")
        
        # 3. R/R oranı (20 puan)
        trade_plan = analysis.get('trade_plan', {})
        rr1 = trade_plan.get('rr1', 0)
        
        if rr1 >= 2:
            score += 20
            positives.append(f"R/R oranı mükemmel ({rr1}:1)")
        elif rr1 >= 1.5:
            score += 15
            positives.append(f"R/R oranı iyi ({rr1}:1)")
        elif rr1 >= 1:
            score += 10
        else:
            negatives.append(f"R/R oranı düşük ({rr1}:1)")
            wait_for.append("Daha iyi giriş noktası için fiyatın düzeltme yapmasını bekleyin")
        
        # 4. Hacim (15 puan)
        volume = analysis.get('volume', {})
        rvol = volume.get('rvol', 1)
        
        if rvol >= 1.5:
            score += 15
            positives.append(f"Hacim desteği var (RVOL: {rvol}x)")
        elif rvol >= 1:
            score += 10
        else:
            negatives.append("Hacim desteği zayıf")
            wait_for.append("Hacmin ortalamanın üzerine çıkmasını bekleyin")
        
        # 5. Risk metrikleri (15 puan)
        risk = analysis.get('risk', {})
        volatility = risk.get('volatility', 30)
        sharpe = risk.get('sharpe', 0)
        
        if volatility < 40 and sharpe > 0:
            score += 15
            positives.append("Risk parametreleri kabul edilebilir")
        elif volatility < 60:
            score += 10
        else:
            negatives.append(f"Volatilite çok yüksek ({volatility}%)")
            wait_for.append("Volatilitenin düşmesini bekleyin")
        
        # Sonuç belirleme
        if score >= 75:
            suitability = 'UYGUN'
            verdict = '✅ TRADE İÇİN UYGUN'
        elif score >= 50:
            suitability = 'BEKLE'
            verdict = '⚠️ BEKLE - Daha iyi fırsat bekleyin'
        else:
            suitability = 'UYGUN_DEGIL'
            verdict = '❌ TRADE İÇİN UYGUN DEĞİL'
        
        return {
            'verdict': verdict,
            'suitability': suitability,
            'score': round(score, 1),
            'max_score': max_score,
            'positives': positives,
            'negatives': negatives,
            'wait_for': wait_for
        }
    
    def generate_report_html(self, analysis: Dict[str, Any]) -> str:
        """HTML formatında detaylı rapor üret"""
        
        symbol = analysis.get('symbol', 'UNKNOWN')
        date = analysis.get('analysis_date', '')
        
        if analysis.get('status') != 'success':
            return f"""
            <html>
            <body style="font-family: Arial; padding: 20px;">
                <h1>❌ Analiz Hatası</h1>
                <p>{symbol} için analiz yapılamadı.</p>
                <p>Hata: {analysis.get('error', 'Bilinmeyen hata')}</p>
            </body>
            </html>
            """
        
        suitability = analysis.get('suitability', {})
        price_info = analysis.get('price_info', {})
        indicators = analysis.get('indicators', {})
        trend = analysis.get('trend', {})
        levels = analysis.get('levels', {})
        volume = analysis.get('volume', {})
        risk = analysis.get('risk', {})
        entry = analysis.get('entry', {})
        trade_plan = analysis.get('trade_plan', {})
        
        trade_plan = analysis.get('trade_plan', {})
        
        # Checklist çevirisi - Merkezi çeviri modülünden
        if entry.get('checklist'):
             entry['checklist'] = translate_checklist(entry['checklist'])
             
        # Diğer metinleri çevir
        symbol = analysis.get('symbol', 'UNKNOWN')
        verdict = translate(suitability.get('verdict', 'BEKLE'))
        recommendation = translate(entry.get('recommendation', 'BEKLE'))
        
        # Suitability textlerini çevir
        positives = [translate(p) for p in suitability.get('positives', [])]
        negatives = [translate(n) for n in suitability.get('negatives', [])]
        wait_for = [translate(w) for w in suitability.get('wait_for', [])]
        
        # Verdict color
        verdict_color = '#27ae60' if suitability.get('suitability') == 'UYGUN' else '#f39c12' if suitability.get('suitability') == 'BEKLE' else '#e74c3c'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
        .verdict-box {{ background: {verdict_color}; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }}
        .verdict-box h2 {{ margin: 0; font-size: 24px; }}
        .verdict-box p {{ margin: 5px 0 0 0; }}
        .section {{ background: #16213e; border-radius: 10px; padding: 15px; margin-bottom: 15px; }}
        .section h3 {{ margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 1px solid #333; color: #667eea; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
        .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
        .item {{ background: #0f3460; padding: 10px; border-radius: 5px; }}
        .item .label {{ font-size: 12px; color: #888; }}
        .item .value {{ font-size: 18px; font-weight: bold; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .neutral {{ color: #f39c12; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ color: #667eea; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 DETAYLI ANALİZ RAPORU</h1>
            <p>{symbol} - {date}</p>
        </div>
        
        <div class="verdict-box">
            <h2>{suitability.get('verdict', 'BEKLE')}</h2>
            <p>Skor: {suitability.get('score', 0)}/{suitability.get('max_score', 100)}</p>
        </div>
        
        <div class="section" style="text-align: center; padding: 10px;">
            <button onclick="window.dispatchEvent(new CustomEvent('showChart', {{detail: {{symbol: '{symbol}'}}}}))" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; margin: 5px;">📈 Grafiği Göster</button>
            <button onclick="window.print()" style="background: #27ae60; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; margin: 5px;">🖨️ Yazdır</button>
        </div>
        
        <div class="section">
            <h3>💰 FİYAT BİLGİLERİ</h3>
            <div class="grid">
                <div class="item">
                    <div class="label">Güncel Fiyat</div>
                    <div class="value">{price_info.get('current', 0)} TL</div>
                </div>
                <div class="item">
                    <div class="label">Günlük Değişim</div>
                    <div class="value {'positive' if price_info.get('daily_change', 0) >= 0 else 'negative'}">{price_info.get('daily_change', 0):+.2f}%</div>
                </div>
                <div class="item">
                    <div class="label">Haftalık Değişim</div>
                    <div class="value {'positive' if price_info.get('weekly_change', 0) >= 0 else 'negative'}">{price_info.get('weekly_change', 0):+.2f}%</div>
                </div>
                <div class="item">
                    <div class="label">Aylık Değişim</div>
                    <div class="value {'positive' if price_info.get('monthly_change', 0) >= 0 else 'negative'}">{price_info.get('monthly_change', 0):+.2f}%</div>
                </div>
                <div class="item">
                    <div class="label">52H Yüksek</div>
                    <div class="value">{price_info.get('high_52w', 0)} TL ({price_info.get('from_high_pct', 0):.1f}%)</div>
                </div>
                <div class="item">
                    <div class="label">52H Düşük</div>
                    <div class="value">{price_info.get('low_52w', 0)} TL (+{price_info.get('from_low_pct', 0):.1f}%)</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>📈 TREND ANALİZİ</h3>
            <div class="grid">
                <div class="item">
                    <div class="label">Trend Yönü</div>
                    <div class="value">{trend.get('direction', '-')}</div>
                </div>
                <div class="item">
                    <div class="label">EMA Alignment</div>
                    <div class="value">{trend.get('alignment', '-')}</div>
                </div>
                <div class="item">
                    <div class="label">Momentum</div>
                    <div class="value">{trend.get('momentum', '-')}</div>
                </div>
                <div class="item">
                    <div class="label">Trend Skoru</div>
                    <div class="value">{trend.get('alignment_score', 0)}/100</div>
                </div>
            </div>
            <table style="margin-top: 15px;">
                <tr><th>EMA</th><th>Değer</th></tr>
                <tr><td>EMA 20</td><td>{trend.get('ema20', '-')} TL</td></tr>
                <tr><td>EMA 50</td><td>{trend.get('ema50', '-')} TL</td></tr>
                <tr><td>EMA 200</td><td>{trend.get('ema200', '-') or '-'} TL</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h3>📊 TEKNİK GÖSTERGELER</h3>
            <table>
                <tr><th>Gösterge</th><th>Değer</th><th>Durum</th></tr>
                <tr><td>RSI (14)</td><td>{indicators.get('rsi', {}).get('value', '-')}</td><td>{indicators.get('rsi', {}).get('status', '-')}</td></tr>
                <tr><td>MACD</td><td>{indicators.get('macd', {}).get('value', '-')}</td><td>{indicators.get('macd', {}).get('status', '-')}</td></tr>
                <tr><td>ADX</td><td>{indicators.get('adx', {}).get('value', '-')}</td><td>{indicators.get('adx', {}).get('status', '-')}</td></tr>
                <tr><td>Stokastik</td><td>{indicators.get('stochastic', {}).get('k', '-')}/{indicators.get('stochastic', {}).get('d', '-')}</td><td>{indicators.get('stochastic', {}).get('status', '-')}</td></tr>
                <tr><td>Bollinger</td><td>{indicators.get('bollinger', {}).get('width', '-')}%</td><td>{indicators.get('bollinger', {}).get('status', '-')}</td></tr>
                <tr><td>ATR</td><td>{indicators.get('atr', {}).get('value', '-')}</td><td>{indicators.get('atr', {}).get('pct', '-')}%</td></tr>
                <tr><td>OBV</td><td>-</td><td>{indicators.get('obv', {}).get('status', '-')}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h3>📍 DESTEK / DİRENÇ SEVİYELERİ</h3>
            <table>
                <tr><th>Seviye</th><th>Fiyat</th><th>Mesafe</th></tr>
                <tr><td>Direnç 2</td><td>{levels.get('resistance2', '-')} TL</td><td class="positive">+{levels.get('resistance2_pct', 0):.1f}%</td></tr>
                <tr><td>Direnç 1</td><td>{levels.get('resistance1', '-')} TL</td><td class="positive">+{levels.get('resistance1_pct', 0):.1f}%</td></tr>
                <tr style="background: #667eea22;"><td><strong>Güncel Fiyat</strong></td><td><strong>{levels.get('current_price', '-')} TL</strong></td><td>-</td></tr>
                <tr><td>Destek 1</td><td>{levels.get('support1', '-')} TL</td><td class="negative">{levels.get('support1_pct', 0):.1f}%</td></tr>
                <tr><td>Destek 2</td><td>{levels.get('support2', '-')} TL</td><td class="negative">{levels.get('support2_pct', 0):.1f}%</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h3>📊 HACİM ANALİZİ</h3>
            <div class="grid">
                <div class="item">
                    <div class="label">Güncel Hacim</div>
                    <div class="value">{volume.get('current', 0):,}</div>
                </div>
                <div class="item">
                    <div class="label">RVOL</div>
                    <div class="value {'positive' if volume.get('rvol', 1) >= 1.5 else 'neutral' if volume.get('rvol', 1) >= 1 else 'negative'}">{volume.get('rvol', 1)}x</div>
                </div>
                <div class="item">
                    <div class="label">Ortalama (20)</div>
                    <div class="value">{volume.get('avg_20', 0):,}</div>
                </div>
                <div class="item">
                    <div class="label">Durum</div>
                    <div class="value">{volume.get('status', '-')}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>⚠️ RİSK METRİKLERİ</h3>
            <div class="grid">
                <div class="item">
                    <div class="label">Volatilite (Yıllık)</div>
                    <div class="value">{risk.get('volatility', 0)}% {risk.get('volatility_status', '')}</div>
                </div>
                <div class="item">
                    <div class="label">Sharpe Ratio</div>
                    <div class="value">{risk.get('sharpe', 0)} {risk.get('sharpe_status', '')}</div>
                </div>
                <div class="item">
                    <div class="label">Max Drawdown</div>
                    <div class="value negative">{risk.get('max_drawdown', 0)}%</div>
                </div>
                <div class="item">
                    <div class="label">ATR %</div>
                    <div class="value">{risk.get('atr_pct', 0)}%</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>✅ GİRİŞ DOĞRULAMA</h3>
            <p><strong>Öneri:</strong> {entry.get('recommendation', 'BEKLE')} (Güven: {entry.get('confidence', 0) * 100:.0f}%)</p>
            <div class="grid">
            <div class="grid">
                {''.join([f'<div class="item"><div class="value {"positive" if v else "negative"}">{"✅" if v else "❌"} {k}</div></div>' for k, v in entry.get('checklist', {}).items()])}
            </div>
            </div>
            {f'<p style="margin-top:10px; color: #e74c3c;"><strong>Eksikler:</strong> {", ".join(entry.get("failed_checks", []))}</p>' if entry.get('failed_checks') else ''}
        </div>
        
        <div class="section">
            <h3>💰 TRADE PLANI</h3>
            <div class="grid">
                <div class="item">
                    <div class="label">Giriş Fiyatı</div>
                    <div class="value">{trade_plan.get('entry', 0)} TL</div>
                </div>
                <div class="item">
                    <div class="label">Stop-Loss</div>
                    <div class="value negative">{trade_plan.get('stop_loss', 0)} TL ({trade_plan.get('stop_loss_pct', 0):.1f}%)</div>
                </div>
                <div class="item">
                    <div class="label">Hedef 1</div>
                    <div class="value positive">{trade_plan.get('target1', 0)} TL (+{trade_plan.get('target1_pct', 0):.1f}%)</div>
                </div>
                <div class="item">
                    <div class="label">Hedef 2</div>
                    <div class="value positive">{trade_plan.get('target2', 0)} TL (+{trade_plan.get('target2_pct', 0):.1f}%)</div>
                </div>
                <div class="item">
                    <div class="label">R/R Oranı (H1)</div>
                    <div class="value">{trade_plan.get('rr1', 0)}:1 {trade_plan.get('rr_status', '')}</div>
                </div>
                <div class="item">
                    <div class="label">R/R Oranı (H2)</div>
                    <div class="value">{trade_plan.get('rr2', 0)}:1</div>
                </div>
            </div>
            <table style="margin-top: 15px;">
                <tr><th>Parametre</th><th>Değer</th></tr>
                <tr><td>Sermaye</td><td>{trade_plan.get('capital', 0):,} TL</td></tr>
                <tr><td>Risk Oranı</td><td>{trade_plan.get('risk_pct', 0)}%</td></tr>
                <tr><td>Risk Tutarı</td><td>{trade_plan.get('risk_amount', 0):,} TL</td></tr>
                <tr><td>Alınacak Adet</td><td>{trade_plan.get('shares', 0):,} adet</td></tr>
                <tr><td>Pozisyon Değeri</td><td>{trade_plan.get('position_value', 0):,} TL</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h3>📝 SONUÇ VE ÖNERİ</h3>
            <div class="verdict-box" style="background: {verdict_color};">
                <h2>{suitability.get('verdict', 'BEKLE')}</h2>
            </div>
            
            {f'''<h4 class="positive">Neden Uygun:</h4>
            <ul>{''.join([f"<li>{p}</li>" for p in suitability.get('positives', [])])}</ul>''' if suitability.get('positives') else ''}
            
            {f'''<h4 class="negative">Dikkat Edilmesi Gerekenler:</h4>
            <ul>{''.join([f"<li>{n}</li>" for n in suitability.get('negatives', [])])}</ul>''' if suitability.get('negatives') else ''}
            
            {f'''<h4 class="neutral">Ne Beklenmeli:</h4>
            <ul>{''.join([f"<li>{w}</li>" for w in suitability.get('wait_for', [])])}</ul>''' if suitability.get('wait_for') else ''}
        </div>
        
        <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
            <p>Bu rapor Swing Trade Scanner v3.1.0 tarafından oluşturulmuştur.</p>
            <p>⚠️ Bu rapor yatırım tavsiyesi değildir. Yatırım kararlarınızda kendi araştırmanızı yapın.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def generate_report_text(self, analysis: Dict[str, Any]) -> str:
        """Text formatında rapor üret (konsol/log için)"""
        
        symbol = analysis.get('symbol', 'UNKNOWN')
        date = analysis.get('analysis_date', '')
        
        if analysis.get('status') != 'success':
            return f"❌ {symbol} analizi yapılamadı: {analysis.get('error', 'Bilinmeyen hata')}"
        
        suitability = analysis.get('suitability', {})
        price_info = analysis.get('price_info', {})
        trend = analysis.get('trend', {})
        entry = analysis.get('entry', {})
        trade_plan = analysis.get('trade_plan', {})
        
        lines = [
            "═" * 60,
            f"              📊 DETAYLI ANALİZ RAPORU",
            f"                   {symbol} - {date}",
            "═" * 60,
            "",
            f"🎯 SONUÇ: {suitability.get('verdict', 'BEKLE')}",
            f"   Skor: {suitability.get('score', 0)}/{suitability.get('max_score', 100)}",
            "",
            "━" * 60,
            "📈 TREND ANALİZİ",
            "━" * 60,
            f"• Trend Yönü: {trend.get('direction', '-')}",
            f"• EMA Alignment: {trend.get('alignment', '-')}",
            f"• Momentum: {trend.get('momentum', '-')}",
            "",
            "━" * 60,
            "💰 TRADE PLANI",
            "━" * 60,
            f"Entry:     {trade_plan.get('entry', 0)} TL",
            f"Stop-Loss: {trade_plan.get('stop_loss', 0)} TL ({trade_plan.get('stop_loss_pct', 0):.1f}%)",
            f"Target 1:  {trade_plan.get('target1', 0)} TL (+{trade_plan.get('target1_pct', 0):.1f}%) [R/R: {trade_plan.get('rr1', 0)}:1]",
            f"Target 2:  {trade_plan.get('target2', 0)} TL (+{trade_plan.get('target2_pct', 0):.1f}%) [R/R: {trade_plan.get('rr2', 0)}:1]",
            "",
            f"Pozisyon: {trade_plan.get('capital', 0):,} TL sermaye için: {trade_plan.get('shares', 0)} adet",
            f"Risk: {trade_plan.get('risk_pct', 0)}% = {trade_plan.get('risk_amount', 0):,} TL",
            "",
            "━" * 60,
            "✅ GİRİŞ DOĞRULAMA",
            "━" * 60,
            f"Öneri: {entry.get('recommendation', 'BEKLE')}",
        ]
        
        for k, v in entry.get('checklist', {}).items():
            status = "✅" if v else "❌"
            lines.append(f"{status} {k.replace('_', ' ').title()}")
        
        if suitability.get('wait_for'):
            lines.append("")
            lines.append("⚠️ Ne Beklenmeli:")
            for w in suitability.get('wait_for', []):
                lines.append(f"  • {w}")
        
        lines.append("")
        lines.append("═" * 60)
        
        return "\n".join(lines)
    
    def export_to_pdf(self, html_content: str, filename: str) -> bool:
        """HTML raporu PDF olarak kaydet"""
        try:
            # weasyprint veya pdfkit kullanarak PDF oluştur
            try:
                from weasyprint import HTML
                HTML(string=html_content).write_pdf(filename)
                return True
            except ImportError:
                pass
            
            # Alternatif: pdfkit
            try:
                import pdfkit
                pdfkit.from_string(html_content, filename)
                return True
            except ImportError:
                pass
            
            # Fallback: HTML olarak kaydet
            html_filename = filename.replace('.pdf', '.html')
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.warning(f"PDF kütüphanesi bulunamadı, HTML olarak kaydedildi: {html_filename}")
            return True
            
        except Exception as e:
            logger.error(f"PDF export hatası: {e}")
            return False
    
    def export_to_excel(self, analysis: Dict[str, Any], filename: str) -> bool:
        """Analiz sonuçlarını Excel'e kaydet"""
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Özet
                summary_data = {
                    'Parametre': ['Sembol', 'Analiz Tarihi', 'Sonuç', 'Skor'],
                    'Değer': [
                        analysis.get('symbol', ''),
                        analysis.get('analysis_date', ''),
                        analysis.get('suitability', {}).get('verdict', ''),
                        f"{analysis.get('suitability', {}).get('score', 0)}/{analysis.get('suitability', {}).get('max_score', 100)}"
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Özet', index=False)
                
                # Fiyat bilgileri
                price_info = analysis.get('price_info', {})
                pd.DataFrame([price_info]).T.reset_index().rename(
                    columns={'index': 'Parametre', 0: 'Değer'}
                ).to_excel(writer, sheet_name='Fiyat', index=False)
                
                # Trend
                trend = analysis.get('trend', {})
                pd.DataFrame([trend]).T.reset_index().rename(
                    columns={'index': 'Parametre', 0: 'Değer'}
                ).to_excel(writer, sheet_name='Trend', index=False)
                
                # Trade planı
                trade_plan = analysis.get('trade_plan', {})
                pd.DataFrame([trade_plan]).T.reset_index().rename(
                    columns={'index': 'Parametre', 0: 'Değer'}
                ).to_excel(writer, sheet_name='Trade Planı', index=False)
                
                # Risk
                risk = analysis.get('risk', {})
                pd.DataFrame([risk]).T.reset_index().rename(
                    columns={'index': 'Parametre', 0: 'Değer'}
                ).to_excel(writer, sheet_name='Risk', index=False)
                
            return True
            
        except Exception as e:
            logger.error(f"Excel export hatası: {e}")
            return False
