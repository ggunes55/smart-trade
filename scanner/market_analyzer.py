# -*- coding: utf-8 -*-
"""
Market Analyzer - Piyasa durumu analizi
"""
import logging
from typing import Optional
import pandas as pd
from tvDatafeed import Interval

from core.types import MarketAnalysis, IDataProvider
from analysis.market_condition import _empty_market_analysis
from indicators.ta_manager import calculate_indicators


class MarketAnalyzer:
    """Piyasa durumu analizi"""

    def __init__(self, cfg: dict, data_handler: IDataProvider):
        self.cfg = cfg
        self.data_handler = data_handler
        self._cached_analysis: Optional[MarketAnalysis] = None

    def analyze_market_condition(self, force_refresh: bool = False) -> MarketAnalysis:
        """
        Piyasa durumu analizi - Exchange-aware

        Args:
            force_refresh: Cache'i bypass et

        Returns:
            MarketAnalysis objesi
        """
        # Cache kontrolü
        if not force_refresh and self._cached_analysis is not None:
            return self._cached_analysis

        try:
            # 🆕 Exchange'e göre index belirle
            exchange = self.cfg.get("exchange", "BIST")
            index_map = {
                "BIST": ("XU100", "BIST"),      # BIST100
                "NASDAQ": ("QQQ", "NASDAQ"),     # NASDAQ 100 ETF
                "NYSE": ("SPY", "NYSE"),         # S&P 500 ETF
                "CRYPTO": ("BTC-USD", "CRYPTO"), # Bitcoin (Piyasa Göstergesi)
            }
            
            index_symbol, index_exchange = index_map.get(exchange, ("XU100", "BIST"))
            
            # Index verisi çek (timeout: 3 saniye - çok hızlı olmalı)
            logging.debug(f"{index_symbol} ({exchange}) verisi çekiliyor...")
            index_data = self.data_handler.safe_api_call(
                index_symbol, index_exchange, Interval.in_daily, 100, timeout=3
            )

            if index_data is None or len(index_data) < 50:
                logging.warning(f"{index_symbol} verisi yetersiz: {len(index_data) if index_data is not None else 0} bar")
                self._cached_analysis = _empty_market_analysis()
                return self._cached_analysis
            
            logging.debug(f"{index_symbol} verisi alındı: {len(index_data)} bar")

            # İndikatörleri hesapla
            df = calculate_indicators(index_data)
            latest = df.iloc[-1]

            # Trend gücü hesapla
            trend_strength = self._calculate_trend_strength(df, latest)

            # Volatilite hesapla
            volatility = self._calculate_volatility(df)

            # Hacim trendi
            volume_trend = self._calculate_volume_trend(df, latest)

            # Piyasa skoru
            market_score = self._calculate_market_score(
                trend_strength, volatility, volume_trend
            )

            # Rejim belirle
            regime = self._determine_regime(trend_strength, volatility)

            # Öneri
            recommendation = self._get_recommendation(regime)

            # Sonuç oluştur
            self._cached_analysis = MarketAnalysis(
                regime=regime,
                trend_strength=round(trend_strength, 1),
                volatility=round(volatility, 1),
                volume_trend=round(volume_trend, 2),
                market_score=round(market_score, 1),
                recommendation=recommendation,
            )

            logging.info(f"📊 {exchange} Piyasa analizi: {regime} (skor: {market_score:.0f})")
            return self._cached_analysis

        except Exception as e:
            logging.error(f"Piyasa analizi hatası: {e}", exc_info=True)
            self._cached_analysis = _empty_market_analysis()
            return self._cached_analysis

    def _calculate_trend_strength(self, df: pd.DataFrame, latest: pd.Series) -> float:
        """Trend gücü hesapla"""
        strength = 0

        # EMA pozisyonu
        if latest["close"] > latest["EMA20"] > latest["EMA50"]:
            strength += 40
        elif latest["close"] > latest["EMA20"]:
            strength += 20

        # ADX
        adx = latest.get("ADX", 0)
        if adx > 25:
            strength += 30
        elif adx > 20:
            strength += 15

        # MACD
        if latest.get("MACD_Level", 0) > latest.get("MACD_Signal", 0):
            strength += 30

        return min(strength, 100)

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Volatilite hesapla (yıllık)"""
        returns = df["close"].pct_change().dropna()

        if len(returns) < 2:
            return 25.0  # Varsayılan

        # Yıllık volatilite
        volatility = returns.std() * (252**0.5) * 100

        return volatility

    def _calculate_volume_trend(self, df: pd.DataFrame, latest: pd.Series) -> float:
        """Hacim trendi hesapla"""
        if "volume" not in df.columns:
            return 1.0

        avg_volume = df["volume"].rolling(20).mean().iloc[-1]

        if avg_volume == 0:
            return 1.0

        return latest["volume"] / avg_volume

    def _calculate_market_score(
        self, trend_strength: float, volatility: float, volume_trend: float
    ) -> float:
        """Piyasa skoru hesapla"""
        # Volatilite skoru (düşük volatilite = yüksek skor)
        vol_score = max(0, 100 - volatility * 2)

        # Hacim trend skoru
        vol_trend_score = min(volume_trend * 50, 100)

        # Ağırlıklı toplam
        market_score = trend_strength * 0.4 + vol_score * 0.3 + vol_trend_score * 0.3

        return market_score

    def _determine_regime(self, trend_strength: float, volatility: float) -> str:
        """Piyasa rejimini belirle"""
        if trend_strength >= 70 and volatility < 25:
            return "bullish"
        elif trend_strength <= 30 and volatility > 35:
            return "bearish"
        elif volatility > 40:
            return "volatile"
        elif 40 <= trend_strength <= 60 and volatility < 30:
            return "sideways"
        else:
            return "neutral"

    def _get_recommendation(self, regime: str) -> str:
        """Rejime göre öneri"""
        recommendations = {
            "bullish": "🟢 AĞIRLIKLI ALIM",
            "bearish": "🔴 DİKKATLİ ALIM",
            "volatile": "🟡 SEÇİCİ ALIM",
            "sideways": "🔵 DİKEY PAZAR",
            "neutral": "⚪ NÖTR",
        }
        return recommendations.get(regime, "⚪ NÖTR")

    def clear_cache(self):
        """Önbelleği temizle"""
        self._cached_analysis = None
        logging.info("Piyasa analizi cache'i temizlendi")

    def get_cached_analysis(self) -> Optional[MarketAnalysis]:
        """Önbellekteki analizi döndür"""
        return self._cached_analysis
