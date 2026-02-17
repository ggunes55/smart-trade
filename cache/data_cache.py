# advanced_utils.py
# GÜVENLİK DÜZELTMESİ: Pickle yerine Parquet formatı kullanılıyor
import os
import logging
import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum

# Parquet desteği kontrolü
try:
    import pyarrow
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    logging.warning("⚠️ PyArrow yüklü değil. JSON fallback kullanılacak. 'pip install pyarrow' ile yükleyin.")

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM" 
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class ErrorInfo:
    message: str
    severity: ErrorSeverity
    timestamp: datetime
    symbol: str = ""
    function: str = ""

class ErrorHandler:
    """Gelişmiş hata yönetimi sınıfı"""
    
    def __init__(self, max_errors=1000):
        self.error_log: List[ErrorInfo] = []
        self.max_errors = max_errors
        self.lock = Lock()
    
    def log_error(self, message: str, severity: ErrorSeverity, symbol: str = "", function: str = ""):
        """Hata kaydet"""
        with self.lock:
            error_info = ErrorInfo(
                message=message,
                severity=severity,
                timestamp=datetime.now(),
                symbol=symbol,
                function=function
            )
            
            self.error_log.append(error_info)
            
            # Eski hataları temizle
            if len(self.error_log) > self.max_errors:
                self.error_log = self.error_log[-self.max_errors:]
            
            # Log seviyesine göre kaydet
            if severity == ErrorSeverity.CRITICAL:
                logger.critical(f"{symbol} - {function}: {message}")
            elif severity == ErrorSeverity.HIGH:
                logger.error(f"{symbol} - {function}: {message}")
            elif severity == ErrorSeverity.MEDIUM:
                logger.warning(f"{symbol} - {function}: {message}")
            else:
                logger.info(f"{symbol} - {function}: {message}")
    
    def get_recent_errors(self, count: int = 10) -> List[ErrorInfo]:
        """Son hataları getir"""
        with self.lock:
            return self.error_log[-count:]
    
    def clear_errors(self):
        """Hataları temizle"""
        with self.lock:
            self.error_log.clear()
    
    def get_error_stats(self) -> Dict[str, int]:
        """Hata istatistikleri"""
        with self.lock:
            severities = [error.severity for error in self.error_log]
            return {
                'total': len(self.error_log),
                'critical': severities.count(ErrorSeverity.CRITICAL),
                'high': severities.count(ErrorSeverity.HIGH),
                'medium': severities.count(ErrorSeverity.MEDIUM),
                'low': severities.count(ErrorSeverity.LOW)
            }

class DataCache:
    """Gelişmiş veri önbellekleme sistemi"""
    
    def __init__(self, cache_dir='data_cache', ttl_hours=1, max_size_mb=500):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.max_size_mb = max_size_mb
        self.lock = Lock()
        self.error_handler = ErrorHandler()
        
        os.makedirs(cache_dir, exist_ok=True)
        self._cleanup_old_cache()
    
    def _get_cache_filepath(self, symbol: str, interval: str, bars: int) -> str:
        """Cache dosya yolunu oluştur - GÜVENLİ FORMAT"""
        safe_symbol = "".join(c for c in symbol if c.isalnum() or c in ('-', '_'))
        # Parquet varsa .parquet, yoksa .json uzantısı
        ext = '.parquet' if PARQUET_AVAILABLE else '.json'
        filename = f"{safe_symbol}_{interval}_{bars}{ext}"
        return os.path.join(self.cache_dir, filename)
    
    def _cleanup_old_cache(self):
        """Eski cache dosyalarını temizle"""
        try:
            if not os.path.exists(self.cache_dir):
                return

            current_time = datetime.now()
            total_size = 0
            files_to_delete = []
            
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    # TTL kontrolü
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if current_time - file_time > self.ttl:
                        files_to_delete.append(filepath)
                        continue
                    
                    # Boyut kontrolü
                    total_size += os.path.getsize(filepath) / (1024 * 1024)  # MB
                    
                    # Eski dosyaları işaretle (boyut aşımı için)
                    if total_size > self.max_size_mb:
                        files_to_delete.append(filepath)
            
            # İşaretlenen dosyaları sil
            for filepath in files_to_delete:
                try:
                    os.remove(filepath)
                    logger.info(f"Eski cache dosyası silindi: {os.path.basename(filepath)}")
                except Exception as e:
                    pass
                        
        except Exception as e:
            self.error_handler.log_error(
                f"Cache temizleme hatası: {e}", 
                ErrorSeverity.MEDIUM,
                function="_cleanup_old_cache"
            )
    
    def get(self, symbol: str, interval: str, bars: int) -> Optional[pd.DataFrame]:
        """Cache'ten veri getir - GÜVENLİ FORMAT (Parquet/JSON)"""
        filepath = self._get_cache_filepath(symbol, interval, bars)
        
        with self.lock:
            try:
                if os.path.exists(filepath):
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if datetime.now() - file_time < self.ttl:
                        # Parquet veya JSON formatında oku
                        if PARQUET_AVAILABLE and filepath.endswith('.parquet'):
                            data = pd.read_parquet(filepath)
                        elif filepath.endswith('.json'):
                            data = pd.read_json(filepath, orient='table')
                        else:
                            # Eski .pkl dosyası - sadece sil (güvenlik)
                            logger.warning(f"Eski pickle cache atlanıyor: {symbol}")
                            os.remove(filepath)
                            return None
                        
                        # Veri bütünlüğü kontrolü
                        if self._validate_cached_data(data, symbol, bars):
                            logger.debug(f"Cache hit: {symbol} ({interval}, {bars} bars)")
                            return data
                        else:
                            logger.warning(f"Geçersiz cache verisi: {symbol}")
                            os.remove(filepath)
                    
                    else:
                        # TTL dolmuş, dosyayı sil
                        os.remove(filepath)
                        logger.debug(f"TTL doldu, cache silindi: {symbol}")
                
            except (IOError, ValueError, KeyError) as e:
                self.error_handler.log_error(
                    f"Cache okuma hatası: {e}", 
                    ErrorSeverity.MEDIUM,
                    symbol,
                    "cache_get"
                )
                # Bozuk cache dosyasını sil
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
        
        return None
    
    def _validate_cached_data(self, data: Any, symbol: str, bars: int) -> bool:
        """Cache verisini doğrula"""
        try:
            if not isinstance(data, pd.DataFrame):
                return False
            
            if data.empty:
                return False
            
            # Temel sütun kontrolleri
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in data.columns for col in required_columns):
                return False
            
            # Veri bütünlüğü kontrolleri
            if len(data) < max(10, bars * 0.5):  # En az 10 bar veya istenenin yarısı
                return False
            
            # Anormal değer kontrolleri
            if (data['high'] < data['low']).any():
                return False
            
            if (data['close'] > data['high']).any() or (data['close'] < data['low']).any():
                return False
            
            return True
            
        except Exception:
            return False
    
    def set(self, symbol: str, interval: str, bars: int, data: pd.DataFrame):
        """Veriyi cache'e kaydet - GÜVENLİ FORMAT (Parquet/JSON)"""
        if data is None or data.empty:
            return
        
        filepath = self._get_cache_filepath(symbol, interval, bars)
        
        with self.lock:
            try:
                # Önce temizlik yap
                self._cleanup_old_cache()
                
                # Klasörün varlığından emin ol
                if not os.path.exists(self.cache_dir):
                    os.makedirs(self.cache_dir, exist_ok=True)
                
                # Veriyi güvenli formatta kaydet
                if PARQUET_AVAILABLE:
                    data.to_parquet(filepath, engine='pyarrow')
                else:
                    # JSON fallback
                    data.to_json(filepath, orient='table', date_format='iso')
                
                logger.debug(f"Cache kaydedildi: {symbol} ({interval}, {bars} bars)")
                
            except (IOError, ValueError) as e:
                self.error_handler.log_error(
                    f"Cache yazma hatası: {e}", 
                    ErrorSeverity.MEDIUM,
                    symbol,
                    "cache_set"
                )

class ConfigValidator:
    """Config doğrulama sınıfı"""
    
    @staticmethod
    def validate_swing_config(config: Dict) -> List[str]:
        """Swing config doğrulama"""
        errors = []
        
        # Gerekli anahtarlar
        required_keys = [
            'min_rsi', 'max_rsi', 'symbols', 'exchange', 
            'lookback_bars', 'min_trend_score'
        ]
        
        for key in required_keys:
            if key not in config:
                errors.append(f"Gerekli config anahtarı eksik: {key}")
        
        # Değer aralığı kontrolleri
        if 'min_rsi' in config and 'max_rsi' in config:
            if config['min_rsi'] >= config['max_rsi']:
                errors.append("Min RSI, Max RSI'dan küçük olmalı")
            
            if config['min_rsi'] < 0 or config['max_rsi'] > 100:
                errors.append("RSI değerleri 0-100 arasında olmalı")
        
        if 'min_trend_score' in config:
            if config['min_trend_score'] < 0 or config['min_trend_score'] > 100:
                errors.append("Trend skoru 0-100 arasında olmalı")
        
        # Sembol listesi kontrolü
        if 'symbols' in config:
            if not isinstance(config['symbols'], list):
                errors.append("Symbols bir liste olmalı")
            elif len(config['symbols']) == 0:
                errors.append("En az bir sembol gerekiyor")
            else:
                for symbol in config['symbols']:
                    if not isinstance(symbol, str) or len(symbol.strip()) == 0:
                        errors.append(f"Geçersiz sembol: {symbol}")
        
        # Lookback bars kontrolü
        if 'lookback_bars' in config:
            if config['lookback_bars'] < 20 or config['lookback_bars'] > 1000:
                errors.append("Lookback bars 20-1000 arasında olmalı")
        
        return errors
    
    @staticmethod
    def validate_backtest_config(config: Dict) -> List[str]:
        """Backtest config doğrulama"""
        errors = []
        
        required_keys = ['days', 'initial_capital']
        for key in required_keys:
            if key not in config:
                errors.append(f"Backtest için gerekli anahtar eksik: {key}")
        
        if 'days' in config and (config['days'] < 30 or config['days'] > 730):
            errors.append("Backtest gün sayısı 30-730 arasında olmalı")
        
        if 'initial_capital' in config and config['initial_capital'] <= 0:
            errors.append("Başlangıç sermayesi pozitif olmalı")
        
        return errors


class SafeCalculator:
    """Güvenli hesaplama wrapper'ı - TAMAMEN DÜZELTİLMİŞ VERSİYON"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
    
    def safe_execute(self, func, *args, symbol: str = "", default_value=None, **kwargs):
        """Fonksiyonu güvenli şekilde çalıştır"""
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            self.error_handler.log_error(
                f"Hesaplama hatası: {e}",
                ErrorSeverity.MEDIUM,
                symbol,
                func.__name__
            )
            return default_value
    
    def safe_dataframe_operation(self, df: pd.Series, operation: str, symbol: str = "", **kwargs):
        """DataFrame operasyonlarını güvenli şekilde yap - TAMAMEN DÜZELTİLMİŞ"""
        try:
            if df is None or df.empty:
                return df
            
            if operation == 'pct_change':
                periods = kwargs.get('periods', 1)
                result = df.pct_change(periods=periods)
                return result.fillna(0)
                
            elif operation == 'rolling':
                window = kwargs.get('window', 10)
                roll_operation = kwargs.get('operation', 'mean')
                
                if roll_operation == 'mean':
                    return df.rolling(window=window).mean()
                elif roll_operation == 'std':
                    return df.rolling(window=window).std()
                elif roll_operation == 'min':
                    return df.rolling(window=window).min()
                elif roll_operation == 'max':
                    return df.rolling(window=window).max()
                else:
                    return df.rolling(window=window).mean()
                    
            elif operation == 'ewm':
                span = kwargs.get('span', 10)
                return df.ewm(span=span).mean()
                
            else:
                return df
                
        except Exception as e:
            self.error_handler.log_error(
                f"DataFrame operasyon hatası ({operation}): {e}",
                ErrorSeverity.MEDIUM,
                symbol,
                "safe_dataframe_operation"
            )
            # Hata durumunda orijinal seriyi döndür
            return df