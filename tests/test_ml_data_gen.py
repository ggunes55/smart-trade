
# -*- coding: utf-8 -*-
"""
ML Veri Üretim Testi
Bu script, sanal bir backtest çalıştırarak 'data_cache/ml_training_data.csv' 
dosyasının oluşturulup oluşturulmadığını test eder.
"""
import pandas as pd
import numpy as np
import logging
import os
import sys

# Proje dizinini ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest.backtester import RealisticBacktester
from analysis.trade_collector import TradeCollector

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def create_synthetic_data(days=365):
    """Test için sanal veri oluştur"""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    # Random walk
    prices = 100 + np.cumsum(np.random.randn(days))
    
    df = pd.DataFrame({
        'open': prices + np.random.randn(days),
        'high': prices + 2,
        'low': prices - 2,
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, days)
    }, index=dates)
    
    # Fake indikatörler (Backtester bunları bekliyor olabilir)
    df['ATR14'] = df['close'] * 0.02
    return df

class MockHunter:
    """Backtester'ın ihtiyaç duyduğu minimal Hunter sınıfı"""
    def __init__(self):
        self.cfg = {
            'exchange': 'BIST',
            'min_volume_ratio': 0.5,
            'min_rsi': 30,
            'max_rsi': 70
        }
        
    def calculate_indicators(self, df):
        # Dataframe'e gerekli sütunları ekleyip geri döndür
        df = df.copy()
        # Rastgele değerler
        df['RSI'] = np.random.randint(30, 80, len(df))
        df['MACD'] = np.random.randn(len(df))
        df['ADX'] = np.random.randint(10, 50, len(df))
        df['Relative_Volume'] = np.random.uniform(0.5, 2.0, len(df))
        df['trend_score'] = 50
        return df

def main():
    print("🚀 ML Veri Üretim Testi Başlıyor...")
    
    # 1. Config
    config = {
        'initial_capital': 10000,
        'commission_pct': 0.1,
        'collect_ml_data': True,  # KRİTİK: Veri toplamayı aç
        'max_open_positions': 5,
        'max_risk_pct': 2.0,
        'atr_stop_multiplier': 2.0,
        'target1_multiplier': 1.5,
        'target2_multiplier': 2.5
    }
    
    # 2. Backtester Init
    backtester = RealisticBacktester(config)
    hunter = MockHunter()
    
    # 3. Veri Oluştur
    df = create_synthetic_data(1000)
    print(f"✔️ {len(df)} barlık sanal veri oluşturuldu.")
    
    # 4. Giriş Sinyalini Manipüle Et (Zorla işlem açtır)
    # Her 10. barda gir
    # backtester.check_entry_signal metodunu değil, OPTIMIZED olanı patch'lememiz lazım
    # çünkü backtester artık check_entry_signal_optimized kullanıyor.
    def mock_check_entry(df, idx, h):
        is_signal = idx % 10 == 0
        return is_signal
        
    backtester.check_entry_signal_optimized = mock_check_entry
    
    # 5. Çalıştır
    symbol = "TEST_ML"
    result = backtester.run_backtest(symbol, df, hunter)
    
    print(f"\n📊 Backtest Sonucu:")
    print(f"Top. İşlem: {result['metrics']['total_trades']}")
    print(f"Kazanç: {result['metrics']['total_profit']:.2f} TL")
    
    # 6. Dosya Kontrol
    csv_path = os.path.join("data_cache", "ml_training_data.csv")
    if os.path.exists(csv_path):
        df_csv = pd.read_csv(csv_path)
        print(f"\n✅ BAŞARILI: '{csv_path}' dosyası mevcut.")
        print(f"Toplam Veri Satırı: {len(df_csv)}")
        
        # Bu testin verilerini göster
        recent = df_csv[df_csv['symbol'] == symbol]
        print(f"Bu testten gelen kayıt sayısı: {len(recent)}")
        if len(recent) > 0:
            print("\nÖrnek veri:")
            print(recent.head(1).iloc[0])
    else:
        print(f"\n❌ BAŞARISIZ: '{csv_path}' dosyası oluşturulmadı!")

if __name__ == "__main__":
    main()
