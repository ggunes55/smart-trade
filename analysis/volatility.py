# analysis/volatility.py
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple

def detect_volatility_squeeze(df: pd.DataFrame) -> Tuple[bool, str, float]:
    """
    Volatility Squeeze (TTM Squeeze benzeri) ve Bandwidth analizi yapar.
    
    Logic: Bollinger Bantları, Keltner Kanallarının içine girdiğinde 'Squeeze' oluşur.
    Bu, enerjinin biriktiğini ve patlamanın yakın olduğunu gösterir.
    
    Returns:
        (squeeze_on, status_message, squeeze_score)
    """
    if df is None or len(df) < 20:
        return False, "Yetersiz Veri", 0
        
    try:
        # Gerekli verilerin varlığını kontrol et
        needed = ['close', 'EMA20', 'BB_Upper', 'BB_Lower', 'ATR14']
        if not all(col in df.columns for col in needed):
            # Eksikse hesapla (basitçe)
            return False, "Eksik İndikatör", 0
            
        current = df.iloc[-1]
        
        # 1. Keltner Channels (KC) Hesapla
        # Genelde EMA20 +/- 1.5 * ATR kullanılır
        kc_upper = current['EMA20'] + (1.5 * current['ATR14'])
        kc_lower = current['EMA20'] - (1.5 * current['ATR14'])
        
        # 2. Squeeze Kontrolü (BB, KC'nin içinde mi?)
        bb_upper = current['BB_Upper']
        bb_lower = current['BB_Lower']
        
        squeeze_on = (bb_upper <= kc_upper) and (bb_lower >= kc_lower)
        
        # 3. Bandwidth Analizi (Alternatif Sıkışma)
        bandwidth = current.get('BB_Width_Pct', 100)
        is_tight = bandwidth < 10.0  # %10'dan dar bant
        
        score = 0
        status = "Normal"
        
        if squeeze_on:
            score += 25
            status = "🔥 SQUEEZE (Patlama Hazırlığı)"
            if is_tight:
                score += 10
                status += " + DAR BANT"
        elif is_tight:
            score += 15
            status = "Daralma (Watchlist)"
            
        # 4. Momentum Kontrolü (Patlama yönü tahmini)
        # MACD Hist veya Close > EMA20
        if squeeze_on:
            if current['close'] > current['EMA20']:
                status += " [YUKARI YÖNLÜ]"
                score += 5
            else:
                status += " [AŞAĞI YÖNLÜ]"
                
        return squeeze_on, status, score
        
    except Exception as e:
        return False, f"Hata: {str(e)}", 0
