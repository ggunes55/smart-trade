# core/utils.py
import json
import logging
import os
import random
import time
from tvDatafeed import TvDatafeed

import numpy as np
import pandas as pd


def setup_logging(log_file='swing_hunter_ultimate.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def load_config(path):
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        default = {
            "symbols": ["AKBNK", "GARAN"],
            "exchange": "BIST",
            "lookback_bars": 250,
            "min_rsi": 30,
            "max_rsi": 70,
            "min_trend_score": 50,
            "min_relative_volume": 1.0,
            "max_daily_change_pct": 8.0,
            "min_risk_reward_ratio": 2.0,
            "max_risk_pct": 5.0,
            "use_multi_timeframe": True,
            "use_fibonacci": True,
            "use_consolidation": True,
            "use_smart_filter": True,
            "min_total_score": 60,
            "max_workers": 4,
            "use_parallel_scan": True,
            "cache_ttl_hours": 1,
            "initial_capital": 10000
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default

def safe_api_call(tv: TvDatafeed, cache, symbol, exchange, interval, n_bars):
    """
    Tekrarlayan veri çekme işlemleri için ortak utility fonksiyonu.
    Cache, retry ve hata yönetimi içerir.
    """
    cached = cache.get(symbol, str(interval), n_bars)
    if cached is not None:
        return cached
    for attempt in range(3):
        try:
            time.sleep(random.uniform(0.1, 0.3))
            data = tv.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars)
            if data is not None and not data.empty:
                cache.set(symbol, str(interval), n_bars, data)
                return data
        except Exception as e:
            logging.warning(f"API denemesi {attempt+1}/3 hata: {symbol}: {e}")
    logging.error(f"API hatası {symbol}: {e}")
    return None

# --- Merkezi Veri Temizleme ve Kalite Kontrol Fonksiyonu ---
def clean_and_validate_df(df: pd.DataFrame, required_columns=None, min_rows=50) -> pd.DataFrame:
    """
    DataFrame için temel kalite ve temizlik kontrolleri uygular.
    - Eksik kolonları kontrol eder
    - NaN/Inf değerleri doldurur veya uyarı verir
    - Uç değerleri (outlier) tespit eder (z-score ile)
    - Minimum satır sayısı kontrolü yapar
    """
    if required_columns is None:
        required_columns = ["open", "high", "low", "close", "volume"]

    # Kolon kontrolü
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Eksik kolonlar: {missing}")

    # NaN/Inf temizliği
    for col in required_columns:
        if df[col].isnull().any():
            if col == "volume":
                df[col] = df[col].fillna(0)
            else:
                df[col] = df[col].fillna(method="ffill").fillna(method="bfill")
        if np.isinf(df[col]).any():
            df[col] = df[col].replace([np.inf, -np.inf], np.nan).fillna(method="ffill").fillna(method="bfill")

    # Uç değer (outlier) tespiti (z-score > 5 olanlar)
    for col in ["open", "high", "low", "close"]:
        if df[col].std() > 0:
            z = (df[col] - df[col].mean()) / df[col].std()
            outliers = (np.abs(z) > 5).sum()
            if outliers > 0:
                logging.warning(f"{col} kolonunda {outliers} uç değer tespit edildi.")

    # Minimum satır kontrolü
    if len(df) < min_rows:
        raise ValueError(f"Yetersiz veri: {len(df)} satır (min {min_rows})")

    return df