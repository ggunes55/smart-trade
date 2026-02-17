# -*- coding: utf-8 -*-
"""
Trade Collector - ML Eğitimi İçin İşlem Verisi Toplayıcı

Başarılı ve başarısız işlemleri, işlem sırasındaki teknik göstergelerle birlikte kaydeder.
Bu veriler daha sonra MLSignalClassifier'ı eğitmek için kullanılır.
"""
import os
import csv
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class TradeCollector:
    """
    İşlem verilerini CSV dosyasına kaydeder.
    """
    
    def __init__(self, data_dir: str = "data_cache", filename: str = "ml_training_data.csv"):
        self.data_dir = data_dir
        self.filename = filename
        self.file_path = os.path.join(data_dir, filename)
        
        # Dosya ve başlık kontrolü
        self._ensure_file_exists()
        
    def _ensure_file_exists(self):
        """Dosya yoksa oluştur ve başlıkları yaz"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Header: Tarih, Sembol, Kar%, Features...
                headers = [
                    "date", "symbol", "profit_pct", 
                    "rsi", "macd", "adx", "volume_ratio", 
                    "trend_score", "atr_percent", "volatility",
                    "outcome" # 1: Win, 0: Loss, 2: BreakEven
                ]
                writer.writerow(headers)
                
    def log_trade(self, symbol: str, entry_date: str, profit_pct: float, features: Dict):
        """
        Bir işlemi kaydet
        
        Args:
            symbol: Hisse sembolü
            entry_date: Giriş tarihi
            profit_pct: Kar/Zarar yüzdesi
            features: Giriş anındaki teknik veriler (rsi, macd vs)
        """
        try:
            # Outcome belirle
            if profit_pct > 2.0:
                outcome = 1 # Win
            elif profit_pct < -1.0:
                outcome = 0 # Loss
            else:
                outcome = 2 # Neutral
                
            # Feature'ları güvenli al - CASE-INSENSITIVE düzeltmesi
            # Hem 'RSI' hem de 'rsi' formatını destekle
            def get_feature(key, default):
                return features.get(key, features.get(key.lower(), features.get(key.upper(), default)))
            
            rsi = get_feature('rsi', 50)
            macd = get_feature('macd', 0)
            adx = get_feature('adx', 0)
            vol_ratio = get_feature('volume_ratio', get_feature('rvol', 1.0))
            trend_score = get_feature('trend_score', 0)
            atr_pct = get_feature('atr_percent', get_feature('atr_pct', 0))
            volatility = get_feature('volatility', 0)
            
            row = [
                entry_date, symbol, f"{profit_pct:.2f}",
                f"{rsi:.2f}", f"{macd:.4f}", f"{adx:.2f}", f"{vol_ratio:.2f}",
                f"{trend_score:.2f}", f"{atr_pct:.2f}", f"{volatility:.2f}",
                outcome
            ]
            
            with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
                
            # logger.debug(f"Trade logged: {symbol}, Profit: {profit_pct:.2f}%")
            
        except Exception as e:
            logger.error(f"Error logging trade for {symbol}: {e}")

    def load_data(self) -> List[Dict]:
        """Eğitim verilerini oku ve dictionary listesi olarak döndür"""
        if not os.path.exists(self.file_path):
            return []
            
        data = []
        try:
            df = pd.read_csv(self.file_path)
            # MLClassifier formatına çevir
            for _, row in df.iterrows():
                item = {
                    'profit_pct': float(row['profit_pct']),
                    'features': {
                        'rsi': float(row['rsi']),
                        'macd': float(row['macd']),
                        'adx': float(row['adx']),
                        'volume_ratio': float(row['volume_ratio']),
                        'trend_score': float(row['trend_score']),
                        'atr_percent': float(row['atr_percent']),
                        'volatility': float(row['volatility'])
                    }
                }
                data.append(item)
            return data
        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return []
