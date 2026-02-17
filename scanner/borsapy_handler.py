# scanner/borsapy_handler.py
"""
Borsapy Data Handler - BIST için alternatif veri kaynağı
https://github.com/saidsurucu/borsapy

Avantajlar:
- BIST'e özgü ek veriler (KAP bildirimleri, finansallar, temettü)
- Analist tavsiyeleri ve hedef fiyatlar
- Hazır tarama şablonları
"""
import logging
from typing import Optional, Dict, List
import pandas as pd

# Borsapy'yi opsiyonel olarak import et
try:
    import borsapy as bp
    BORSAPY_AVAILABLE = True
except ImportError:
    BORSAPY_AVAILABLE = False
    logging.warning("⚠️ borsapy kütüphanesi yüklü değil. pip install borsapy ile yükleyin.")


class BorsapyHandler:
    """
    BIST hisseleri için alternatif veri sağlayıcı
    tvDatafeed ile paralel kullanılabilir
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("use_borsapy_for_bist", True) and BORSAPY_AVAILABLE
        
        if self.enabled:
            logging.info("✅ Borsapy entegrasyonu aktif (BIST ek verileri)")
        else:
            if not BORSAPY_AVAILABLE:
                logging.warning("⚠️ Borsapy yüklü değil, BIST ek verileri kullanılamayacak")
    
    def is_available(self) -> bool:
        """Borsapy kullanılabilir mi?"""
        return self.enabled
    
    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        Hisse temel bilgilerini al
        
        Returns:
            dict: Şirket bilgileri (sektör, piyasa değeri, vs.)
        """
        if not self.enabled:
            return None
        
        try:
            ticker = bp.Ticker(symbol)
            info = ticker.info
            return {
                "company_name": info.get("shortName", symbol),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": info.get("marketCap", 0),
                "pe_ratio": info.get("pe", 0),
                "pb_ratio": info.get("pb", 0),
                "dividend_yield": info.get("dividendYield", 0),
            }
        except Exception as e:
            logging.debug(f"Borsapy info hatası ({symbol}): {e}")
            return None
    
    def get_history(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """
        Fiyat geçmişi al (alternatif kaynak)
        
        Args:
            symbol: Hisse sembolü (ör: THYAO)
            period: Dönem (1ay, 3ay, 6ay, 1y, 2y, 5y, max)
        
        Returns:
            DataFrame: OHLCV verisi
        """
        if not self.enabled:
            return None
        
        try:
            ticker = bp.Ticker(symbol)
            df = ticker.history(period=period)
            
            if df is not None and not df.empty:
                # Sütun isimlerini standartlaştır
                df.columns = [c.lower() for c in df.columns]
                return df
            return None
        except Exception as e:
            logging.debug(f"Borsapy history hatası ({symbol}): {e}")
            return None
    
    def get_financials(self, symbol: str) -> Optional[Dict]:
        """
        Finansal tabloları al
        
        Returns:
            dict: Bilanço, gelir tablosu, vs.
        """
        if not self.enabled:
            return None
        
        try:
            ticker = bp.Ticker(symbol)
            return {
                "balance_sheet": ticker.balance_sheet,
                "income_statement": ticker.income_statement,
                "cash_flow": ticker.cash_flow,
            }
        except Exception as e:
            logging.debug(f"Borsapy financials hatası ({symbol}): {e}")
            return None
    
    def get_analyst_data(self, symbol: str) -> Optional[Dict]:
        """
        Analist verilerini al
        
        Returns:
            dict: Hedef fiyat, tavsiye, vs.
        """
        if not self.enabled:
            return None
        
        try:
            ticker = bp.Ticker(symbol)
            analyst = ticker.analyst_info
            return {
                "target_price": analyst.get("targetPrice", 0),
                "recommendation": analyst.get("recommendation", "N/A"),
                "upside_potential": analyst.get("upsidePotential", 0),
                "analyst_count": analyst.get("analystCount", 0),
            }
        except Exception as e:
            logging.debug(f"Borsapy analyst hatası ({symbol}): {e}")
            return None
    
    def screen_stocks(self, template: str = None, **filters) -> Optional[pd.DataFrame]:
        """
        Hazır şablonlarla hisse taraması
        
        Templates:
            - high_dividend: Yüksek temettü
            - low_pe: Düşük F/K
            - high_roe: Yüksek ROE
            - high_volume: Yüksek hacim
            - buy_recommendation: AL tavsiyeli
        
        Filters:
            - pe_max, pe_min: F/K aralığı
            - dividend_yield_min: Min temettü verimi
            - roe_min: Min ROE
            - sector: Sektör filtresi
        """
        if not self.enabled:
            return None
        
        try:
            if template:
                return bp.screen_stocks(template=template)
            else:
                return bp.screen_stocks(**filters)
        except Exception as e:
            logging.debug(f"Borsapy screen hatası: {e}")
            return None
    
    def get_kap_news(self, symbol: str, limit: int = 5) -> Optional[List[Dict]]:
        """
        KAP bildirimlerini al
        
        Returns:
            list: Son bildirimler
        """
        if not self.enabled:
            return None
        
        try:
            ticker = bp.Ticker(symbol)
            news = ticker.kap_news
            if news is not None:
                return news.head(limit).to_dict("records")
            return None
        except Exception as e:
            logging.debug(f"Borsapy KAP hatası ({symbol}): {e}")
            return None
    
    def enrich_stock_data(self, symbol: str, existing_data: Dict) -> Dict:
        """
        Mevcut hisse verisini Borsapy bilgileriyle zenginleştir
        
        Args:
            symbol: Hisse sembolü
            existing_data: tvDatafeed'den gelen mevcut veri
        
        Returns:
            Dict: Zenginleştirilmiş veri
        """
        if not self.enabled:
            return existing_data
        
        enriched = existing_data.copy()
        
        # Temel bilgiler
        info = self.get_stock_info(symbol)
        if info:
            enriched["Sektör"] = info.get("sector", "N/A")
            enriched["P/E"] = f"{info.get('pe_ratio', 0):.1f}"
            enriched["P/B"] = f"{info.get('pb_ratio', 0):.1f}"
            enriched["Temettü"] = f"%{info.get('dividend_yield', 0):.2f}"
        
        # Analist verileri
        analyst = self.get_analyst_data(symbol)
        if analyst:
            enriched["Hedef Fiyat"] = f"{analyst.get('target_price', 0):.2f}"
            enriched["Analist Tavsiye"] = analyst.get("recommendation", "N/A")
            upside = analyst.get("upside_potential", 0)
            if upside:
                enriched["Potansiyel"] = f"%{upside:.1f}"
        
        return enriched



    def get_tv_signals(self, symbol: str, exchange: str = "BIST", interval: str = "1d") -> Optional[Dict]:
        """
        TradingView'dan AL/SAT sinyalleri al (tradingview-ta)
        
        Args:
            symbol: Hisse sembolü (ör: THYAO)
            exchange: Borsa (BIST, NASDAQ, CRYPTO)
            interval: Zaman dilimi (1d, 4h, 1h, 15m, 5m, 1m)
            
        Returns:
            Dict: Sinyal özeti ve detayları
        """
        # Module level import to avoid dependency if not used
        try:
            from tradingview_ta import TA_Handler, Interval, Exchange
        except ImportError:
            logging.warning("⚠️ tradingview-ta yüklü değil. pip install tradingview-ta")
            return None
            
        try:
            # Exchange ve Screener belirle
            screener = "turkey"
            tv_exchange = "BIST"
            
            if exchange == "NASDAQ":
                screener = "america"
                tv_exchange = "NASDAQ"
            elif exchange == "NYSE":
                screener = "america"
                tv_exchange = "NYSE"
            elif exchange == "CRYPTO":
                screener = "crypto"
                tv_exchange = "BINANCE"
                # Crypto sembol düzeltme (BTC-USD -> BTCUSDT)
                if "-" in symbol:
                    symbol = symbol.replace("-", "").replace("USD", "USDT")

            # Interval belirle
            tv_interval = Interval.INTERVAL_1_DAY
            if interval == "4h": tv_interval = Interval.INTERVAL_4_HOURS
            elif interval == "1h": tv_interval = Interval.INTERVAL_1_HOUR
            elif interval == "15m": tv_interval = Interval.INTERVAL_15_MINUTES
            elif interval == "5m": tv_interval = Interval.INTERVAL_5_MINUTES
            elif interval == "1m": tv_interval = Interval.INTERVAL_1_MINUTE
            elif interval == "1w": tv_interval = Interval.INTERVAL_1_WEEK
            
            handler = TA_Handler(
                symbol=symbol,
                screener=screener,
                exchange=tv_exchange,
                interval=tv_interval
            )
            
            analysis = handler.get_analysis()
            
            # Renkli log
            log_icon = "⚪"
            if "BUY" in analysis.summary['RECOMMENDATION']:
                log_icon = "🟢"
            elif "SELL" in analysis.summary['RECOMMENDATION']:
                log_icon = "🔴"
                
            logging.debug(f"{log_icon} TV Signal ({symbol}): {analysis.summary['RECOMMENDATION']}")
            
            return {
                "recommendation": analysis.summary.get("RECOMMENDATION"),
                "buy_count": analysis.summary.get("BUY"),
                "sell_count": analysis.summary.get("SELL"),
                "neutral_count": analysis.summary.get("NEUTRAL"),
                "rsi": analysis.indicators.get("RSI"),
                "macd": analysis.indicators.get("MACD.macd"),
                "macd_signal": analysis.indicators.get("MACD.signal"),
                "adx": analysis.indicators.get("ADX"),
                "ema50": analysis.indicators.get("EMA50"),
                "ema200": analysis.indicators.get("EMA200"),
                "cci": analysis.indicators.get("CCI20"),
                "stoch_k": analysis.indicators.get("Stoch.K"),
                "stoch_d": analysis.indicators.get("Stoch.D"),
                "close": analysis.indicators.get("close"),
                "open": analysis.indicators.get("open"),
                "high": analysis.indicators.get("high"),
                "low": analysis.indicators.get("low"),
                "volume": analysis.indicators.get("volume"),
                "change": analysis.indicators.get("change"),
                # Detailed Analysis for Standard 26 Indicators Summary
                "oscillators": analysis.oscillators,
                "moving_averages": analysis.moving_averages,
                "all_indicators": analysis.indicators
            }
            
        except Exception as e:
            logging.debug(f"TV Signal hatası ({symbol}): {e}")
            return None

def get_borsapy_handler(config: dict) -> Optional[BorsapyHandler]:
    """
    Borsapy handler instance'ı al
    
    Returns:
        BorsapyHandler veya None (BIST değilse)
    """
    # Her zaman döndür, çünkü TV sinyalleri BIST dışı da çalışır
    return BorsapyHandler(config)
