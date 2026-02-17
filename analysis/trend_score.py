# analysis/trend_score.py
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from core.types import FilterScore
from analysis.risk_metrics import calculate_risk_metrics
from analysis.swing_quality import calculate_swing_quality

def calculate_advanced_trend_score(
    df: pd.DataFrame, 
    symbol: str, 
    config: Dict[str, Any], 
    market_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Gelişmiş trend ve momentum skorunu hesaplar
    
    Args:
        df: OHLCV + indikatör verisi içeren DataFrame
        symbol: Hisse sembolü
        config: Konfigürasyon dictionary
        market_analysis: Piyasa analizi (opsiyonel)
    
    Returns:
        Skor bilgisi içeren dictionary
    """
    if df is None or len(df) < 20:
        return {
            "total_score": 0, 
            "components": [], 
            "recommendation": "Yetersiz veri",
            "passed": False
        }
    
    latest = df.iloc[-1]
    components = []

    # 1. EMA Alignment Skoru
    ema_score = _calculate_ema_alignment_score(latest, config)
    components.append(ema_score)

    # 2. RSI Momentum Skoru
    rsi_score = _calculate_rsi_momentum_score(latest, config)
    components.append(rsi_score)

    # 3. MACD Skoru
    macd_score = _calculate_macd_score(latest, config)
    components.append(macd_score)

    # 4. Volume Confirmation Skoru
    volume_score = _calculate_volume_score(latest, df, config)
    components.append(volume_score)

    # 5. ADX Trend Gücü Skoru
    adx_score = _calculate_adx_score(latest, config)
    components.append(adx_score)

    # 6. Price Action Skoru
    if market_analysis and isinstance(market_analysis, dict) and 'levels' in market_analysis:
        pa_score = _calculate_price_action_score(latest, market_analysis['levels'], config)
        components.append(pa_score)
    else:
        pa_score = FilterScore(
            category="Price Action (Destek Yakınlığı)",
            score=5,
            max_score=10,
            weight=config.get('pa_weight', 0.10),
            details={"status": "Destek verisi yok"},
            passed=True
        )
        components.append(pa_score)

    # 7. Market Regime Uyumu
    if market_analysis and isinstance(market_analysis, dict) and 'regime' in market_analysis:
        regime_score = _calculate_regime_alignment_score(market_analysis['regime'], config)
        components.append(regime_score)
    else:
        regime_score = FilterScore(
            category="Market Regime Uyumu",
            score=3,
            max_score=5,
            weight=config.get('regime_weight', 0.05),
            details={"status": "Piyasa analizi yok"},
            passed=True
        )
        components.append(regime_score)
        
    # --- YENİ BİLEŞENLER ---
    
    # 8. [YENI] Risk & Stability Score
    risk_data = calculate_risk_metrics(df)
    risk_points = 0
    risk_details = {}
    
    sharpe = risk_data.get('sharpe_ratio', 0)
    
    # Sharpe Points (Max 10)
    if sharpe > 2.0: risk_points += 10
    elif sharpe > 1.0: risk_points += 7
    elif sharpe > 0.0: risk_points += 4
    
    # Stability Points (Max 10)
    vol_annual = risk_data.get('volatility_annualized', 0)
    
    if 25 <= vol_annual <= 60:
        risk_points += 10 # İdeal swing aralığı
    elif 15 <= vol_annual < 25:
        risk_points += 6 # Biraz yavaş
    elif 60 < vol_annual <= 90:
        risk_points += 5 # Çok hareketli
    else:
        risk_points += 2 # Çok riskli veya ölü
        
    risk_details['sharpe'] = sharpe
    risk_details['annual_vol'] = vol_annual
    
    components.append(FilterScore(
        category="Risk Profili",
        score=risk_points,
        max_score=20,
        weight=0.15,
        details=risk_details,
        passed=True
    ))

    # 9. [YENI] Swing Quality (Efficiency)
    quality_data = calculate_swing_quality(df)
    efficiency = quality_data.get('efficiency_ratio', 0)
    
    qual_points = 0
    # Max Score = 15
    if efficiency > 0.5: qual_points += 15
    elif efficiency > 0.3: qual_points += 10
    elif efficiency > 0.1: qual_points += 5
    
    components.append(FilterScore(
        category="Swing Kalitesi",
        score=qual_points,
        max_score=15,
        weight=0.15,
        details={'efficiency': efficiency},
        passed=True
    ))


    # 10. [YENİ] Rolling Correlation (Endeks ile son 30 bar korelasyon)
    rolling_corr_score = 0
    rolling_corr = None
    benchmark_col = None
    if 'benchmark_close' in df.columns:
        benchmark_col = 'benchmark_close'
    elif 'index_close' in df.columns:
        benchmark_col = 'index_close'
    if benchmark_col:
        try:
            rolling_corr = df['close'].rolling(30).corr(df[benchmark_col]).iloc[-1]
            if pd.notnull(rolling_corr):
                # Korelasyon düşükse (0.5 altı) daha yüksek puan, çünkü bağımsızlık istenir
                if rolling_corr < 0.3:
                    rolling_corr_score = 10
                elif rolling_corr < 0.5:
                    rolling_corr_score = 7
                elif rolling_corr < 0.7:
                    rolling_corr_score = 4
                else:
                    rolling_corr_score = 1
        except Exception as e:
            rolling_corr = None
    components.append(FilterScore(
        category="Rolling Correlation (Endeks)",
        score=rolling_corr_score,
        max_score=10,
        weight=0.08,
        details={"rolling_corr": rolling_corr},
        passed=True
    ))

    # Gelişmiş composite score: risk, kalite, korelasyon, trend, momentum, hacim, volatilite, price action, regime, swing efficiency
    total_raw = sum(comp.score for comp in components)
    total_max = sum(comp.max_score for comp in components)
    if total_max > 0:
        total_score = round((total_raw / total_max * 100), 1)
    else:
        total_score = 0

    # DEBUG için
    debug_mode = config.get('debug_mode', False)
    if debug_mode:
        print(f"\\n📊 {symbol} - COMPOSITE SKOR ANALİZİ:")
        for comp in components:
            print(f"   {comp.category}: {comp.score}/{comp.max_score}")
        print(f"   Toplam Skor: {total_score}/100")
    
    min_score = config.get('min_total_score', 50)
    passed = total_score >= min_score
    
    # Öneri oluştur
    if passed:
        if total_score >= 80:
            recommendation = "🔥 GÜÇLÜ AL - YÜKSEK KALİTE"
        elif total_score >= 65:
            recommendation = "📈 AL - İYİ POTANSİYEL"
        else:
            recommendation = "✅ TAKİP ET"
    else:
        recommendation = "📉 ZAYIF GÖRÜNÜM"

    return {
        "total_score": total_score,
        "components": [comp.__dict__ for comp in components],
        "recommendation": recommendation,
        "passed": passed,
        "risk_metrics": risk_data,
        "quality_metrics": quality_data
    }

def _calculate_ema_alignment_score(latest, config):
    score = 0
    max_score = 25
    weight = config.get('ema_weight', 0.25)
    details = {}

    ema20 = latest.get('EMA20', 0)
    ema50 = latest.get('EMA50', 0)
    ema200 = latest.get('EMA200', 0)
    close = latest['close']

    # EMA200 varsa kontrol et, yoksa sadece EMA20 ve EMA50 ile çalış
    if ema200 > 0:
        if close > ema20 > ema50 > ema200:
            score = max_score
            details["align"] = "EMA20>50>200 + Fiyat Üstte"
        elif close > ema20 and ema20 > ema50 and ema50 < ema200:
            score = 18
            details["align"] = "Kısa vadeli yükseliş"
        elif close > ema20 > ema50:
            score = 20
            details["align"] = "EMA20>50 + Fiyat Üstte"
        elif close > ema20:
            score = 15  # 12'den 15'e yükseltildi
            details["align"] = "Fiyat EMA20 üstünde"
        elif close > ema50:
            score = 10  # Yeni eklendi
            details["align"] = "Fiyat EMA50 üstünde"
        else:
            score = 5   # 0'dan 5'e yükseltildi
            details["align"] = "Trend zayıf"
    else:
        # EMA200 yoksa sadece EMA20 ve EMA50 ile
        if close > ema20 > ema50:
            score = 20
            details["align"] = "EMA20>50 + Fiyat Üstte"
        elif close > ema20:
            score = 15
            details["align"] = "Fiyat EMA20 üstünde"
        elif close > ema50:
            score = 10
            details["align"] = "Fiyat EMA50 üstünde"
        else:
            score = 5
            details["align"] = "Trend zayıf"

    return FilterScore(
        category="EMA Alignment",
        score=score,
        max_score=max_score,
        weight=weight,
        details=details,
        passed=(score >= 10)  # 12'den 10'a düşürüldü
    )

def _calculate_rsi_momentum_score(latest, config):
    score = 0
    max_score = 20
    weight = config.get('rsi_weight', 0.20)
    rsi = latest.get('RSI', 50)
    details = {"rsi": rsi}

    # RSI skorlama - GEVŞETİLMİŞ
    if 45 <= rsi <= 70:  # Daha geniş aralık
        score = max_score  # Sağlıklı yükseliş
    elif 40 <= rsi < 45:
        score = 15
    elif 70 < rsi <= 75:
        score = 12  # 10'dan 12'ye yükseltildi
    elif 75 < rsi <= 80:
        score = 8   # 5'ten 8'e yükseltildi
    elif rsi > 80:
        score = 3   # 0'dan 3'e yükseltildi
    elif 35 <= rsi < 40:
        score = 12  # 10'dan 12'ye yükseltildi
    elif 30 <= rsi < 35:
        score = 10  # 8'den 10'a yükseltildi
    elif rsi < 30:
        score = 5   # 5'ten 5'e sabit

    return FilterScore(
        category="RSI Momentum",
        score=score,
        max_score=max_score,
        weight=weight,
        details=details,
        passed=(score >= 8)  # 10'dan 8'e düşürüldü
    )

def _calculate_macd_score(latest, config):
    score = 0
    max_score = 15
    weight = config.get('macd_weight', 0.15)
    macd = latest.get('MACD_Level', 0)
    signal = latest.get('MACD_Signal', 0)
    hist = latest.get('MACD_Hist', 0)
    details = {"macd": macd, "signal": signal, "hist": hist}

    if macd > signal and hist > 0:
        score = max_score
        details["status"] = "Güçlü pozitif momentum"
    elif macd > signal:
        score = 12  # 8'den 12'ye yükseltildi
        details["status"] = "MACD sinyal üstünde"
    elif macd < signal and hist < 0:
        score = 3   # 0'dan 3'e yükseltildi
        details["status"] = "Negatif momentum"
    else:
        score = 8   # 5'ten 8'e yükseltildi
        details["status"] = "Nötr"

    return FilterScore(
        category="MACD Momentum",
        score=score,
        max_score=max_score,
        weight=weight,
        details=details,
        passed=(score >= 8)
    )

def _calculate_volume_score(latest, df, config):
    score = 0
    max_score = 15
    weight = config.get('volume_weight', 0.15)
    rel_vol = latest.get('Relative_Volume', 1.0)
    obv = latest.get('OBV', 0)
    obv_ema = latest.get('OBV_EMA', 0)
    
    details = {
        "rel_vol": rel_vol, 
        "obv_ratio": obv / obv_ema if obv_ema != 0 else 1
    }

    # Volume skoru - GEVŞETİLMİŞ
    if rel_vol >= 1.5:
        vol_score = max_score * 0.6  # 9 puan
    elif rel_vol >= 1.2:
        vol_score = max_score * 0.5  # 7.5 puan
    elif rel_vol >= 0.8:
        vol_score = max_score * 0.4  # 6 puan
    elif rel_vol >= 0.6:
        vol_score = max_score * 0.3  # 4.5 puan
    elif rel_vol >= 0.4:
        vol_score = max_score * 0.2  # 3 puan
    else:
        vol_score = max_score * 0.1  # 1.5 puan

    # OBV skoru
    if obv_ema > 0:
        if obv > obv_ema:
            obv_score = max_score * 0.4  # 6 puan
        else:
            obv_score = max_score * 0.2  # 3 puan
    else:
        obv_score = max_score * 0.2  # 3 puan (varsayılan)

    score = vol_score + obv_score
    details["source"] = f"RelVol: {vol_score:.1f} + OBV: {obv_score:.1f}"
    
    return FilterScore(
        category="Volume Confirmation",
        score=round(score, 1),
        max_score=max_score,
        weight=weight,
        details=details,
        passed=(score >= 6)  # 8'den 6'ya düşürüldü
    )

def _calculate_adx_score(latest, config):
    score = 0
    max_score = 10
    weight = config.get('adx_weight', 0.10)
    adx = latest.get('ADX', 0)
    plus_di = latest.get('DI_Plus', 0)
    minus_di = latest.get('DI_Minus', 0)
    details = {"adx": adx, "plus_di": plus_di, "minus_di": minus_di}

    # ADX skorlama - GEVŞETİLMİŞ
    if adx >= 20 and plus_di > minus_di:
        score = max_score
        details["status"] = "Güçlü yükseliş trendi"
    elif adx >= 15 and plus_di > minus_di:
        score = 7
        details["status"] = "Orta yükseliş trendi"
    elif adx < 15:
        score = 4  # 3'ten 4'e yükseltildi
        details["status"] = "Zayıf trend"
    else:
        score = 2  # 1'den 2'ye yükseltildi
        details["status"] = "Trend belirsiz"

    return FilterScore(
        category="ADX Trend Gücü",
        score=score,
        max_score=max_score,
        weight=weight,
        details=details,
        passed=(score >= 4)  # 5'ten 4'e düşürüldü
    )

def _calculate_price_action_score(latest, levels, config):
    score = 0
    max_score = 10
    weight = config.get('pa_weight', 0.10)
    current = latest['close']
    
    # Nearest support kontrolü
    nearest_support = levels.get('nearest_support', 0)
    if nearest_support == 0:
        nearest_support = current * 0.9
    
    distance_to_support = (current - nearest_support) / current * 100
    details = {"distance_to_support_pct": round(distance_to_support, 2)}

    # Price action skoru - GEVŞETİLMİŞ
    if distance_to_support <= 3:  # 2'den 3'e çıkarıldı
        score = max_score
        details["status"] = "Destek çok yakın"
    elif distance_to_support <= 6:  # 4'ten 6'ya çıkarıldı
        score = 7
        details["status"] = "Destek yakında"
    elif distance_to_support <= 10:  # 7'den 10'a çıkarıldı
        score = 5
        details["status"] = "Orta mesafe"
    else:
        score = 3  # 1'den 3'e yükseltildi
        details["status"] = "Destek uzak"

    return FilterScore(
        category="Price Action (Destek Yakınlığı)",
        score=score,
        max_score=max_score,
        weight=weight,
        details=details,
        passed=(score >= 3)  # 4'ten 3'e düşürüldü
    )

def _calculate_regime_alignment_score(regime: str, config):
    score = 0
    max_score = 5
    weight = config.get('regime_weight', 0.05)
    details = {"regime": regime}

    # Regime skoru - GEVŞETİLMİŞ
    if regime in ["bullish", "sideways"]:  # sideways da eklenebilir
        score = max_score
        details["status"] = "Piyasa uyumlu"
    elif regime == "volatile":
        score = 4  # max_score'tan 4'e düşürüldü
        details["status"] = "Volatil piyasa - dikkatli"
    else:  # bearish
        score = 2  # 0'dan 2'ye yükseltildi
        details["status"] = "Piyasa satım baskılı"

    return FilterScore(
        category="Market Regime Uyumu",
        score=score,
        max_score=max_score,
        weight=weight,
        details=details,
        passed=(score > 1)  # 0'dan 1'e yükseltildi
    )

def calculate_simple_trend_score(df, config):
    """
    Basit trend skoru (hızlı kontrol için)
    """
    if df is None or len(df) < 10:
        return 0
    
    latest = df.iloc[-1]
    score = 0
    
    # EMA durumu
    if 'EMA20' in latest and 'EMA50' in latest:
        if latest['close'] > latest['EMA20'] > latest['EMA50']:
            score += 40
        elif latest['close'] > latest['EMA20']:
            score += 25
        elif latest['close'] > latest['EMA50']:
            score += 15
    
    # RSI durumu
    if 'RSI' in latest:
        rsi = latest['RSI']
        if 40 <= rsi <= 70:
            score += 30
        elif 30 <= rsi <= 80:
            score += 20
    
    # Volume durumu
    if 'Relative_Volume' in latest:
        rel_vol = latest['Relative_Volume']
        if rel_vol >= 0.8:
            score += 20
        elif rel_vol >= 0.6:
            score += 10
    
    return min(score, 100)