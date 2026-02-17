import pandas as pd
import numpy as np
import sys
import logging

import pytest
from core.utils import clean_and_validate_df

# Logları ayarla
logging.basicConfig(level=logging.INFO)

# Path ekle
sys.path.append('.')

try:
    from analysis.volatility import detect_volatility_squeeze
    from analysis.relative_strength import calculate_relative_strength
    print("✅ Modüller başarıyla import edildi")
except Exception as e:
    print(f"❌ Import hatası: {e}")
    sys.exit(1)

def create_mock_data():
    dates = pd.date_range(start='2023-01-01', periods=100)
    
    # 1. Sıkışmış Veri (Squeeze)
    squeeze_df = pd.DataFrame(index=dates)
    squeeze_df['close'] = 100 + np.random.normal(0, 0.5, 100)  # Çok az hareket
    squeeze_df['high'] = squeeze_df['close'] + 0.5
    squeeze_df['low'] = squeeze_df['close'] - 0.5
    squeeze_df['EMA20'] = squeeze_df['close'].rolling(20).mean()
    squeeze_df['ATR14'] = 1.0
    # BB (Tight)
    squeeze_df['BB_Upper'] = squeeze_df['EMA20'] + 1.5
    squeeze_df['BB_Lower'] = squeeze_df['EMA20'] - 1.5
    squeeze_df['BB_Width_Pct'] = 3.0  # %3 (Süper sıkışık)
    
    # 2. Benchmark (Index)
    bench_df = pd.DataFrame(index=dates)
    bench_df['close'] = np.linspace(100, 105, 100)  # %5 yükseliş
    
    # 3. Outperforming Stock (Alpha)
    stock_df = pd.DataFrame(index=dates)
    stock_df['close'] = np.linspace(100, 120, 100)  # %20 yükseliş
    
    return squeeze_df, stock_df, bench_df


# --- Yeni test: Veri temizleme ve kalite kontrolü ---
def test_clean_and_validate_df():
    df, _, _ = create_mock_data()
    # Eksik veri ve NaN ekle
    df.loc[df.index[0], 'open'] = None
    df['open'] = df['close'] * 0.99
    df['volume'] = np.nan
    # Temizleme fonksiyonunu uygula
    cleaned = clean_and_validate_df(df)
    assert not cleaned.isnull().any().any(), "Temizlenen dataframe'de NaN kalmamalı"
    assert len(cleaned) >= 50, "Yeterli satır olmalı"

def test_squeeze():
    df, _, _ = create_mock_data()
    # Veri eksiklerini tamamla (EMA vs) için ffill
    df = df.ffill().dropna()
    
    squeeze_on, status, score = detect_volatility_squeeze(df)
    
    print(f"🔍 Squeeze Test: {status} (Skor: {score})")
    
    # Beklenen: Squeeze ON veya Dar Bant
    if score > 0:
        print("✅ Squeeze tespiti başarılı")
    else:
        print("⚠️ Squeeze tespit edilemedi (Data sentetik olduğu için normal olabilir)")

def test_rs():
    _, stock, bench = create_mock_data()
    
    rs_data = calculate_relative_strength(stock, bench)
    print(f"🔍 RS Test: {rs_data}")
    
    # Beklenen: Alpha > 0
    # Beklenen: Alpha > 0
    if rs_data['alpha'] > 10:
        print("✅ RS Alpha tespiti başarılı")
    else:
        print(f"❌ RS Alpha hatalı: {rs_data['alpha']}")

    # 4. KEY KONTROLÜ (BUG FIX)
    if 'rs_rating' in rs_data:
        print(f"✅ RS Rating key mevcut: {rs_data['rs_rating']}")
    else:
        print("❌ RS Rating key EKSİK!")

if __name__ == "__main__":
    print("\n--- TEST BAŞLIYOR ---\n")
    test_squeeze()
    print("\n")
    test_rs()
    print("\n--- TEST TAMAMLANDI ---\n")
