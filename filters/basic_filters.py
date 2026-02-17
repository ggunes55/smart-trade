# filters/basic_filters.py - EXCHANGE-SPECIFIC VERSION
"""
Basic Filters - Exchange'e özgü ön filtreleme sistemi
Çöp hisseleri (düşük likidite, manipülasyona açık) erken aşamada eler
"""
import pandas as pd
import numpy as np
import logging

# 🆕 EXCHANGE-SPECIFIC FILTER CONFIGURATIONS
# Her borsa için optimize edilmiş değerler
EXCHANGE_FILTER_CONFIGS = {
    'BIST': {
        'name': 'Borsa Istanbul',
        'description': 'Volatil piyasa - geniş toleranslar',
        # RSI aralığı
        'min_rsi': 25,
        'max_rsi': 75,
        # Hacim kriterleri
        'min_relative_volume': 0.8,
        'min_volume_20d_avg': 100000,  # Min 100K ortalama hacim (çöp hisse filtresi)
        # Fiyat kriterleri
        'min_avg_price': 1.0,  # Min 1 TL (penny stock filtresi)
        'max_daily_change_pct': 10.0,  # %10 max günlük değişim
        # Trend kriterleri
        'min_adx': 18,
        'min_liquidity_ratio': 0.3,
        # Opsiyonel kontroller (auto modda pasif)
        'price_above_ema20': False,
        'price_above_ema50': False,
        'macd_positive': False,
        'check_adx': True,
        'check_institutional_flow': False,
        'check_momentum_divergence': False,
        'min_higher_lows': 1,
    },
    'NASDAQ': {
        'name': 'NASDAQ',
        'description': 'Momentum odaklı - sıkı kriterler',
        'min_rsi': 30,
        'max_rsi': 70,
        'min_relative_volume': 1.0,
        'min_volume_20d_avg': 500000,  # Min 500K ortalama hacim
        'min_avg_price': 5.0,  # Min $5 (SEC kuralları)
        'max_daily_change_pct': 8.0,
        'min_adx': 22,
        'min_liquidity_ratio': 0.5,
        'price_above_ema20': True,
        'price_above_ema50': False,
        'macd_positive': True,
        'check_adx': True,
        'check_institutional_flow': True,
        'check_momentum_divergence': True,
        'min_higher_lows': 2,
    },
    'NYSE': {
        'name': 'New York Stock Exchange',
        'description': 'Dengeli yaklaşım - orta seviye kriterler',
        'min_rsi': 32,
        'max_rsi': 68,
        'min_relative_volume': 0.9,
        'min_volume_20d_avg': 300000,  # Min 300K ortalama hacim
        'min_avg_price': 3.0,  # Min $3
        'max_daily_change_pct': 7.0,
        'min_adx': 20,
        'min_liquidity_ratio': 0.4,
        'price_above_ema20': True,
        'price_above_ema50': False,
        'macd_positive': False,
        'check_adx': True,
        'check_institutional_flow': True,
        'check_momentum_divergence': False,
        'min_higher_lows': 2,
    }
}


def get_exchange_filter_config(exchange: str) -> dict:
    """Exchange'e özgü filtre konfigürasyonunu döndür"""
    exchange = exchange.upper()
    return EXCHANGE_FILTER_CONFIGS.get(exchange, EXCHANGE_FILTER_CONFIGS['BIST'])


def get_effective_filter_values(config: dict, exchange: str, auto_mode: bool = True) -> dict:
    """
    Efektif filtre değerlerini döndür
    
    Args:
        config: Kullanıcı config'i (manuel mod için)
        exchange: Borsa adı
        auto_mode: True ise exchange-specific değerler, False ise config değerleri
    
    Returns:
        Kullanılacak filtre değerleri dictionary'si
    """
    if auto_mode:
        exchange_config = get_exchange_filter_config(exchange)
        logging.debug(f"🤖 Otomatik filtre modu: {exchange_config['name']} değerleri kullanılıyor")
        return exchange_config
    else:
        logging.debug("⚙️ Manuel filtre modu: Config değerleri kullanılıyor")
        return config


def has_higher_lows(df: pd.DataFrame, min_count: int = 2) -> bool:
    """Son 20 barda en az min_count adet yükselen dip kontrolü"""
    if df is None or len(df) < 20:
        return False
    
    lows = df['low'].tail(20).values
    higher_low_count = 0
    
    for i in range(1, len(lows)):
        if lows[i] > lows[i-1]:
            higher_low_count += 1
    
    return higher_low_count >= min_count


def pre_filter_junk_stocks(df: pd.DataFrame, exchange: str) -> tuple:
    """
    🆕 ÖN FİLTRE: Çöp hisseleri erken aşamada ele
    Smart filter'a göndermeden önce bariz uygunsuz hisseleri filtreler
    
    Args:
        df: OHLCV DataFrame
        exchange: Borsa adı
    
    Returns:
        (passed: bool, reason: str)
    """
    if df is None or len(df) < 50:
        return False, "Yetersiz veri (<50 bar)"
    
    exchange_cfg = get_exchange_filter_config(exchange)
    
    # 1. Minimum ortalama hacim kontrolü
    avg_volume = df['volume'].tail(20).mean()
    min_vol = exchange_cfg.get('min_volume_20d_avg', 100000)
    if avg_volume < min_vol:
        return False, f"Düşük hacim: {avg_volume:,.0f} < {min_vol:,.0f}"
    
    # 2. Minimum fiyat kontrolü (penny stock)
    avg_price = df['close'].tail(20).mean()
    min_price = exchange_cfg.get('min_avg_price', 1.0)
    if avg_price < min_price:
        return False, f"Düşük fiyat: {avg_price:.2f} < {min_price:.2f}"
    
    # 3. Aşırı volatilite kontrolü (manipülasyon riski)
    daily_returns = df['close'].pct_change().tail(20)
    max_daily_change = exchange_cfg.get('max_daily_change_pct', 10.0) / 100
    extreme_moves = (daily_returns.abs() > max_daily_change).sum()
    if extreme_moves > 5:  # Son 20 günde 5'ten fazla aşırı hareket
        return False, f"Aşırı volatil: {extreme_moves} aşırı hareket"
    
    # 4. Sıfır hacim kontrolü (likidite sorunu)
    zero_volume_days = (df['volume'].tail(20) == 0).sum()
    if zero_volume_days > 3:  # Son 20 günde 3'ten fazla sıfır hacim
        return False, f"Likidite sorunu: {zero_volume_days} gün sıfır hacim"
    
    return True, "Ön filtre geçti"


def basic_filters(latest: dict, config: dict, df: pd.DataFrame = None, 
                  exchange: str = 'BIST', auto_mode: bool = True) -> bool:
    """
    Temel filtreleri uygular - EXCHANGE-SPECIFIC VERSION
    
    Args:
        latest: Son bar verisi (dict)
        config: Kullanıcı config'i
        df: OHLCV DataFrame (opsiyonel, yükselen dip kontrolü için)
        exchange: Borsa adı (BIST, NASDAQ, NYSE)
        auto_mode: True ise exchange-specific değerler kullanılır
    
    Returns:
        bool: Tüm filtrelerden geçti mi?
    """
    symbol = latest.get('symbol', 'UNKNOWN')
    debug_mode = config.get('debug_mode', False)
    
    # Efektif değerleri al
    effective = get_effective_filter_values(config, exchange, auto_mode)
    
    if debug_mode:
        mode_text = "OTOMATİK" if auto_mode else "MANUEL"
        print(f"\n🔍 {symbol} - FİLTRE ANALİZİ ({mode_text} - {exchange}):")
    
    # 1. RSI kontrolü
    rsi = latest.get('RSI', 50)
    min_rsi = effective.get('min_rsi', 30)
    max_rsi = effective.get('max_rsi', 70)
    if not (min_rsi <= rsi <= max_rsi):
        if debug_mode:
            print(f"   ❌ RSI: {rsi:.1f} → [{min_rsi}-{max_rsi}] aralığında DEĞİL")
        return False
    if debug_mode:
        print(f"   ✅ RSI: {rsi:.1f}")
    
    # 2. Relative volume - GÜVENLİ
    rel_vol = latest.get('Relative_Volume', 1.0)
    min_rel_vol = effective.get('min_relative_volume', 0.6)
    if rel_vol < min_rel_vol:
        if debug_mode:
            print(f"   ❌ RelVol: {rel_vol:.3f} → Min {min_rel_vol}'ten DÜŞÜK")
        return False
    if debug_mode:
        print(f"   ✅ RelVol: {rel_vol:.3f}")
    
    # 3. EMA20 kontrolü - OPSİYONEL
    if effective.get('price_above_ema20', False):
        price = latest.get('close', 0)
        ema20 = latest.get('EMA20', 0)
        if price <= ema20:
            if debug_mode:
                print(f"   ❌ EMA20: {price:.2f} ≤ {ema20:.2f}")
            return False
        if debug_mode:
            print(f"   ✅ EMA20: {price:.2f} > {ema20:.2f}")
    
    # 4. EMA50 kontrolü - OPSİYONEL
    if effective.get('price_above_ema50', False):
        price = latest.get('close', 0)
        ema50 = latest.get('EMA50', 0)
        if price <= ema50:
            if debug_mode:
                print(f"   ❌ EMA50: {price:.2f} ≤ {ema50:.2f}")
            return False
        if debug_mode:
            print(f"   ✅ EMA50: {price:.2f} > {ema50:.2f}")
    
    # 5. MACD kontrolü
    if effective.get('macd_positive', False):
        macd_level = latest.get('MACD_Level', 0)
        macd_signal = latest.get('MACD_Signal', 0)
        if macd_level <= macd_signal:
            if debug_mode:
                print(f"   ❌ MACD: {macd_level:.4f} ≤ {macd_signal:.4f}")
            return False
        if debug_mode:
            print(f"   ✅ MACD: {macd_level:.4f} > {macd_signal:.4f}")
    
    # 6. ADX kontrolü
    if effective.get('check_adx', False):
        adx = latest.get('ADX', 0)
        min_adx = effective.get('min_adx', 20)
        if adx < min_adx:
            if debug_mode:
                print(f"   ❌ ADX: {adx:.1f} → Min {min_adx}'ten DÜŞÜK")
            return False
        if debug_mode:
            print(f"   ✅ ADX: {adx:.1f}")
    
    # 7. CMF kontrolü (kurumsal akış)
    if effective.get('check_institutional_flow', False):
        cmf = latest.get('CMF', 0)
        if cmf < 0:
            if debug_mode:
                print(f"   ❌ CMF: {cmf:.3f} → Negatif (kurumsal satış)")
            return False
        if debug_mode:
            print(f"   ✅ CMF: {cmf:.3f}")
    
    # 8. Momentum divergens kontrolü
    if effective.get('check_momentum_divergence', False):
        rsi_val = latest.get('RSI', 50)
        daily_pct = latest.get('Daily_Change_Pct', 0)
        
        if rsi_val > 70 and daily_pct < 0:
            if debug_mode:
                print(f"   ❌ Momentum: AŞIRI alımda düşüş (RSI={rsi_val:.1f}, Change={daily_pct:.1f}%)")
            return False
        
        if rsi_val < 30 and daily_pct > 0:
            if debug_mode:
                print(f"   ❌ Momentum: AŞIRI satımda yükseliş (RSI={rsi_val:.1f}, Change={daily_pct:.1f}%)")
            return False
        if debug_mode:
            print(f"   ✅ Momentum: Uyumlu")
    
    # ✅ 9. Yükselen dipler kontrolü - GÜVENLİ
    min_higher_lows_cfg = effective.get('min_higher_lows', 0)
    if min_higher_lows_cfg > 0:
        if df is not None and len(df) >= 20:
            if not has_higher_lows(df, min_higher_lows_cfg):
                if debug_mode:
                    print(f"   ❌ Yükselen Dip: {min_higher_lows_cfg} adet bulunamadı")
                return False
            if debug_mode:
                print(f"   ✅ Yükselen Dip: {min_higher_lows_cfg}+ adet")
        else:
            if debug_mode:
                print(f"   ⚠️ Yükselen Dip: Veri yetersiz (df: {len(df) if df is not None else 0} bar)")
    
    # 10. Likidite kontrolü
    min_liquidity = effective.get('min_liquidity_ratio', 0.3)
    volume_20d_avg = latest.get('Volume_20d_Avg', 0)
    current_volume = latest.get('volume', 0)
    
    if volume_20d_avg > 0:
        liquidity_ratio = current_volume / volume_20d_avg
        if liquidity_ratio < min_liquidity:
            if debug_mode:
                print(f"   ❌ Likidite: {liquidity_ratio:.2f} → Min {min_liquidity}'ten DÜŞÜK")
            return False
        if debug_mode:
            print(f"   ✅ Likidite: {liquidity_ratio:.2f}")
    
    if debug_mode:
        print(f"   🎉 {symbol}: TÜM FİLTRELERDEN GEÇTİ!")
    
    return True

