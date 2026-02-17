# indicators/ta_manager.py
import pandas as pd
import numpy as np
import warnings

# TA_LIBRARY kontrolü
TA_AVAILABLE = True
try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, ADXIndicator, EMAIndicator
    from ta.volatility import BollingerBands, AverageTrueRange
    from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator, MFIIndicator
    print("✅ TA-Lib kütüphanesi yüklü")
except ImportError:
    TA_AVAILABLE = False
    print("⚠️ TA-Lib kütüphanesi yüklenmedi, fallback metodlar kullanılacak")

# ADX warning'lerini gizle
warnings.filterwarnings('ignore', category=RuntimeWarning)

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    # 1. EMA'lar (her zaman hesaplanabilir)
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # 2. Diğer indikatörler (TA_AVAILABLE kontrolü)
    if TA_AVAILABLE:
        try:
            # RSI
            df['RSI'] = RSIIndicator(df['close'], window=14).rsi()
            
            # MACD
            macd = MACD(df['close'])
            df['MACD_Level'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            df['MACD_Hist'] = macd.macd_diff()
            
            # Bollinger Bands
            bb = BollingerBands(df['close'], window=20)
            df['BB_Upper'] = bb.bollinger_hband()
            df['BB_Lower'] = bb.bollinger_lband()
            df['BB_Middle'] = bb.bollinger_mavg()
            df['BB_Width_Pct'] = ((df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100).fillna(0)
            
            # ATR
            df['ATR14'] = AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
            
            # ADX (warning olabilir)
            adx = ADXIndicator(df['high'], df['low'], df['close'])
            df['ADX'] = adx.adx()
            df['DI_Plus'] = adx.adx_pos()
            df['DI_Minus'] = adx.adx_neg()
            
            # Volume indikatörleri
            df['OBV'] = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
            df['OBV_EMA'] = df['OBV'].ewm(span=20, adjust=False).mean()
            df['CMF'] = ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'], df['volume']).chaikin_money_flow()
            df['MFI'] = MFIIndicator(df['high'], df['low'], df['close'], df['volume']).money_flow_index()
            
        except Exception as e:
            print(f"⚠️ TA-Lib indikatör hatası: {e}. Fallback kullanılıyor...")
            _calculate_fallback_indicators(df)
    else:
        print("ℹ️ TA-Lib yok, fallback indikatörler kullanılıyor")
        _calculate_fallback_indicators(df)
    
    # 3. Hacim hesaplamaları (her zaman)
    _calculate_volume_indicators(df)
    
    # 4. Temizlik
    _cleanup_indicators(df)
    
    return df

def _calculate_fallback_indicators(df: pd.DataFrame) -> None:
    """TA-Lib yoksa fallback hesaplamalar - GELİŞTİRİLMİŞ ADX DAHİL"""
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / loss.replace(0, 0.00001)
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'].fillna(50, inplace=True)
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD_Level'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD_Level'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD_Level'] - df['MACD_Signal']
    
    # Bollinger Bands
    df['BB_Middle'] = df['close'].rolling(window=20, min_periods=1).mean()
    bb_std = df['close'].rolling(window=20, min_periods=1).std()
    df['BB_Upper'] = df['BB_Middle'] + bb_std * 2
    df['BB_Lower'] = df['BB_Middle'] - bb_std * 2
    df['BB_Width_Pct'] = ((df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100).fillna(0)
    
    # ATR
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    df['ATR14'] = tr.rolling(window=14, min_periods=1).mean()
    
    # ✅ GELİŞTİRİLMİŞ ADX HESAPLAMASI (Wilder's Smoothing)
    _calculate_adx_fallback(df)
    
    # Volume İndikatörleri
    df['OBV'] = (df['volume'] * np.sign(df['close'].diff())).cumsum()
    df['OBV_EMA'] = df['OBV'].ewm(span=20, adjust=False).mean()
    df['CMF'] = _calculate_cmf_fallback(df)
    df['MFI'] = _calculate_mfi_fallback(df)


def _calculate_adx_fallback(df: pd.DataFrame, period: int = 14) -> None:
    """
    ADX (Average Directional Index) hesaplama - Wilder's Smoothing
    Trend gücünü ölçer: >25 güçlü trend, <20 zayıf/yatay trend
    """
    # True Range
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    
    # +DM ve -DM (Directional Movement)
    high_diff = df['high'].diff()
    low_diff = df['low'].diff() * -1  # Negatif olarak hesapla
    
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
    
    # Wilder's Smoothing (EMA with alpha = 1/period)
    alpha = 1 / period
    
    # Smoothed TR, +DM, -DM
    atr = pd.Series(tr).ewm(alpha=alpha, adjust=False).mean()
    smoothed_plus_dm = pd.Series(plus_dm).ewm(alpha=alpha, adjust=False).mean()
    smoothed_minus_dm = pd.Series(minus_dm).ewm(alpha=alpha, adjust=False).mean()
    
    # +DI ve -DI
    df['DI_Plus'] = (smoothed_plus_dm / atr * 100).fillna(0).clip(0, 100)
    df['DI_Minus'] = (smoothed_minus_dm / atr * 100).fillna(0).clip(0, 100)
    
    # DX (Directional Index)
    di_sum = df['DI_Plus'] + df['DI_Minus']
    di_diff = abs(df['DI_Plus'] - df['DI_Minus'])
    dx = (di_diff / di_sum.replace(0, 1) * 100).fillna(0)
    
    # ADX = Smoothed DX
    df['ADX'] = dx.ewm(alpha=alpha, adjust=False).mean().fillna(20).clip(0, 100)


def _calculate_cmf_fallback(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Chaikin Money Flow hesaplama"""
    high_low = df['high'] - df['low']
    high_low = high_low.replace(0, 0.0001)  # Sıfıra bölme koruması
    
    mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / high_low
    mf_volume = mf_multiplier * df['volume']
    
    cmf = mf_volume.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()
    return cmf.fillna(0)


def _calculate_mfi_fallback(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Money Flow Index hesaplama"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    money_flow = typical_price * df['volume']
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf.replace(0, 0.0001)))
    return mfi.fillna(50)

def _calculate_volume_indicators(df: pd.DataFrame) -> None:
    """Hacim göstergelerini hesapla"""
    # Volume ortalamaları
    df['Volume_10d_Avg'] = df['volume'].rolling(window=10, min_periods=1).mean()
    df['Volume_20d_Avg'] = df['volume'].rolling(window=20, min_periods=1).mean()
    
    # Relative Volume
    with np.errstate(divide='ignore', invalid='ignore'):
        df['Relative_Volume'] = df['volume'] / df['Volume_20d_Avg']
    
    df['Relative_Volume'] = df['Relative_Volume'].replace([np.inf, -np.inf], np.nan)
    df['Relative_Volume'] = df['Relative_Volume'].fillna(1.0)
    df['Relative_Volume'] = df['Relative_Volume'].clip(lower=0.1, upper=10.0)
    
    # Değişim yüzdeleri
    df['Daily_Change_Pct'] = df['close'].pct_change(1) * 100
    df['Weekly_Change_Pct'] = df['close'].pct_change(5) * 100

def _cleanup_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """NaN değerleri temizle"""
    # İlk değerleri doldur
    indicator_cols = ['RSI', 'MACD_Level', 'MACD_Signal', 'ADX', 'Relative_Volume', 'ATR14']
    
    for col in indicator_cols:
        if col in df.columns:
            if col == 'RSI':
                default = 50
            elif col == 'Relative_Volume':
                default = 1.0
            else:
                default = 0.0
            
            df[col] = df[col].fillna(default)
    
    # İlk birkaç satırı doldur
    df = df.ffill().bfill()
    
    return df