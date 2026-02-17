# -*- coding: utf-8 -*-
"""
Correlation Analyzer (V3.0) - Hisseler Arası Korelasyon Analizi
Portföy çeşitlendirme ve risk yoğunlaşma analizi
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    Watchlist hisseleri arasında korelasyon analizi yapar.
    
    Kullanım:
        analyzer = CorrelationAnalyzer(data_handler_config)
        matrix = analyzer.calculate_correlation_matrix(['GARAN', 'THYAO', 'EREGL'], 'BIST')
        pairs = analyzer.find_highly_correlated_pairs(threshold=0.7)
        score = analyzer.get_diversification_score()
    """
    
    def __init__(self, data_handler_config: dict = None):
        """
        Args:
            data_handler_config: DataHandler config dict (None = sadece synthetic/manual veri)
        """
        self._config = data_handler_config or {}
        self._price_data: Dict[str, pd.Series] = {}
        self._correlation_matrix: Optional[pd.DataFrame] = None
        self._last_symbols: List[str] = []
        
    def set_price_data(self, symbol: str, prices: pd.Series):
        """
        Fiyat verisini manuel olarak set et (test ve entegrasyon için)
        
        Args:
            symbol: Sembol adı
            prices: close fiyat serisi (DatetimeIndex)
        """
        self._price_data[symbol] = prices
        self._correlation_matrix = None  # Invalidate cache
    
    def set_price_data_bulk(self, price_dict: Dict[str, pd.Series]):
        """
        Birden fazla sembol için fiyat verisi set et
        
        Args:
            price_dict: {'GARAN': pd.Series, 'THYAO': pd.Series, ...}
        """
        self._price_data.update(price_dict)
        self._correlation_matrix = None
    
    def load_from_datahandler(
        self,
        symbols: List[str],
        exchange: str = "BIST",
        n_bars: int = 120
    ) -> bool:
        """
        DataHandler üzerinden fiyat verisi çek
        
        Args:
            symbols: Sembol listesi
            exchange: Borsa
            n_bars: Bar sayısı (default: 120 günlük = ~6 ay)
        
        Returns:
            True = başarılı
        """
        try:
            from scanner.data_handler import DataHandler
            handler = DataHandler(self._config)
            
            loaded = 0
            for symbol in symbols:
                df = handler.get_daily_data(symbol, exchange, n_bars=n_bars)
                if df is not None and len(df) > 20 and 'close' in df.columns:
                    self._price_data[symbol] = df['close'].copy()
                    loaded += 1
                else:
                    logger.warning(f"⚠️ {symbol}: Yeterli veri yok")
            
            self._correlation_matrix = None
            logger.info(f"✅ {loaded}/{len(symbols)} sembol yüklendi")
            return loaded >= 2  # En az 2 sembol lazım
            
        except ImportError:
            logger.error("❌ DataHandler import edilemedi")
            return False
        except Exception as e:
            logger.error(f"❌ Veri yükleme hatası: {e}")
            return False
    
    def calculate_correlation_matrix(
        self,
        symbols: List[str] = None,
        method: str = 'pearson'
    ) -> Optional[pd.DataFrame]:
        """
        Korelasyon matrisi hesapla
        
        Args:
            symbols: Hangi semboller (None = tümü)
            method: 'pearson', 'spearman', 'kendall'
        
        Returns:
            NxN korelasyon matrisi (pd.DataFrame) veya None
        """
        try:
            syms = symbols or list(self._price_data.keys())
            
            if len(syms) < 2:
                logger.warning("⚠️ Korelasyon için en az 2 sembol gerekli")
                return None
            
            # Returns matrisi oluştur
            returns_dict = {}
            for sym in syms:
                if sym in self._price_data:
                    prices = self._price_data[sym]
                    returns = prices.pct_change().dropna()
                    if len(returns) >= 20:
                        returns_dict[sym] = returns
            
            if len(returns_dict) < 2:
                logger.warning("⚠️ Yeterli veri olan sembol sayısı < 2")
                return None
            
            # DataFrame oluştur - ortak tarihlerle hizala
            returns_df = pd.DataFrame(returns_dict)
            returns_df = returns_df.dropna()
            
            if len(returns_df) < 20:
                logger.warning("⚠️ Ortak tarih sayısı yetersiz")
                return None
            
            # Korelasyon hesapla
            self._correlation_matrix = returns_df.corr(method=method)
            self._last_symbols = list(returns_dict.keys())
            
            logger.info(
                f"✅ {len(self._last_symbols)}x{len(self._last_symbols)} "
                f"korelasyon matrisi hesaplandı ({method})"
            )
            return self._correlation_matrix
            
        except Exception as e:
            logger.error(f"❌ Korelasyon hesaplama hatası: {e}")
            return None
    
    def find_highly_correlated_pairs(
        self,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Yüksek korelasyonlu çiftleri bul (risk yoğunlaşması uyarısı)
        
        Args:
            threshold: Korelasyon eşiği (0.0 - 1.0)
        
        Returns:
            [{'pair': ('GARAN', 'AKBNK'), 'correlation': 0.85, 'risk_level': 'HIGH'}, ...]
        """
        if self._correlation_matrix is None:
            self.calculate_correlation_matrix()
        
        if self._correlation_matrix is None:
            return []
        
        pairs = []
        matrix = self._correlation_matrix
        symbols = matrix.columns.tolist()
        
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                corr = matrix.iloc[i, j]
                abs_corr = abs(corr)
                
                if abs_corr >= threshold:
                    if abs_corr >= 0.9:
                        risk_level = "CRITICAL"
                    elif abs_corr >= 0.8:
                        risk_level = "HIGH"
                    elif abs_corr >= 0.7:
                        risk_level = "MEDIUM"
                    else:
                        risk_level = "LOW"
                    
                    pairs.append({
                        'pair': (symbols[i], symbols[j]),
                        'correlation': round(corr, 4),
                        'abs_correlation': round(abs_corr, 4),
                        'risk_level': risk_level,
                        'direction': 'POSITIVE' if corr > 0 else 'NEGATIVE'
                    })
        
        # En yüksek korelasyondan sırala
        pairs.sort(key=lambda x: x['abs_correlation'], reverse=True)
        return pairs
    
    def get_diversification_score(self) -> float:
        """
        Portföy çeşitlendirme puanı hesapla
        
        Yüksek puan = iyi çeşitlendirme (düşük korelasyon)
        Düşük puan = yoğunlaşma riski (yüksek korelasyon)
        
        Returns:
            0-100 float (100 = mükemmel çeşitlendirme)
        """
        if self._correlation_matrix is None:
            self.calculate_correlation_matrix()
        
        if self._correlation_matrix is None or len(self._correlation_matrix) < 2:
            return 0.0
        
        try:
            matrix = self._correlation_matrix.values
            n = len(matrix)
            
            # Üst üçgen ortalaması (diagonal hariç)
            upper_triangle = []
            for i in range(n):
                for j in range(i + 1, n):
                    upper_triangle.append(abs(matrix[i, j]))
            
            if not upper_triangle:
                return 100.0
            
            avg_abs_corr = np.mean(upper_triangle)
            
            # 0 korelasyon = 100 puan (mükemmel çeşitlendirme)
            # 1 korelasyon = 0 puan (hiç çeşitlendirme yok)
            score = (1.0 - avg_abs_corr) * 100.0
            
            return round(max(0.0, min(100.0, score)), 1)
            
        except Exception as e:
            logger.error(f"❌ Diversification score hatası: {e}")
            return 0.0
    
    def get_correlation_summary(self) -> Dict:
        """
        Korelasyon analizi özet raporu
        
        Returns:
            {
                'matrix_size': int,
                'avg_correlation': float,
                'diversification_score': float,
                'high_risk_pairs': int,
                'critical_pairs': List,
                'recommendation': str
            }
        """
        if self._correlation_matrix is None:
            self.calculate_correlation_matrix()
        
        if self._correlation_matrix is None:
            return {'error': 'Korelasyon hesaplanamadı'}
        
        pairs = self.find_highly_correlated_pairs(threshold=0.7)
        critical = [p for p in pairs if p['risk_level'] == 'CRITICAL']
        div_score = self.get_diversification_score()
        
        # Recommendation
        if div_score >= 80:
            rec = "✅ Portföy iyi çeşitlendirilmiş"
        elif div_score >= 60:
            rec = "⚠️ Orta düzeyde çeşitlendirme - bazı korelasyon riskleri var"
        elif div_score >= 40:
            rec = "🔶 Yetersiz çeşitlendirme - yoğun korelasyon riski"
        else:
            rec = "🔴 Kritik: Portföy çok yoğunlaşmış, acil çeşitlendirme gerekli"
        
        matrix = self._correlation_matrix.values
        n = len(matrix)
        upper = [abs(matrix[i, j]) for i in range(n) for j in range(i+1, n)]
        
        return {
            'matrix_size': n,
            'symbols': self._last_symbols,
            'avg_abs_correlation': round(np.mean(upper), 4) if upper else 0,
            'max_correlation': round(max(upper), 4) if upper else 0,
            'min_correlation': round(min(upper), 4) if upper else 0,
            'diversification_score': div_score,
            'high_risk_pairs_count': len(pairs),
            'critical_pairs': critical,
            'recommendation': rec
        }
