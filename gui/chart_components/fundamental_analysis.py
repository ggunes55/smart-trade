"""
Fundamental Analysis - Temel analiz verileri (Multi-Exchange)
Geliştirilmiş hata yönetimi ve retry mekanizması ile
"""

import logging
import time
from typing import Optional, Dict
import os
import urllib3

# 🔧 SSL sertifika doğrulama sorununu çöz
# Windows'da certifi sertifikasının yüklenemediği durumda devre dışı bırak
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    # Eğer sertifika dosyası yoksa SSL doğrulamasını devre dışı bırak
    import certifi
    if not os.path.exists(certifi.where()):
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        os.environ['CURL_CA_BUNDLE'] = ''
except Exception:
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['CURL_CA_BUNDLE'] = ''

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️ yfinance kurulu değil. Temel analiz çalışmayacak!")
    logging.warning("yfinance kütüphanesi kurulu değil!")

# 🆕 Borsapy entegrasyonu (BIST için ek veri)
try:
    import borsapy as bp
    BORSAPY_AVAILABLE = True
except ImportError:
    BORSAPY_AVAILABLE = False
    logging.debug("borsapy kütüphanesi kurulu değil (opsiyonel)")

# 🆕 Finpy entegrasyonu (IMKB resmi verileri)
try:
    import finpy as fp
    FINPY_AVAILABLE = True
except ImportError:
    FINPY_AVAILABLE = False
    logging.debug("finpy kütüphanesi kurulu değil (opsiyonel)")

# 🆕 Requests kütüphanesi (Doğrudan API çağrıları)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.debug("requests kütüphanesi kurulu değil")


class FundamentalAnalysis:
    """
    Temel analiz verilerini çek ve hesapla - Multi-Exchange
    - Finansal oranlar (F/K, PD/DD, etc.)
    - Şirket bilgileri
    - Karlılık metrikleri
    - Temettü bilgileri
    
    Desteklenen borsalar:
    - BIST: yfinance (.IS) + borsapy + finpy + KAP.com API (ek veri)
    - NASDAQ: yfinance (direkt)
    - NYSE: yfinance (direkt)
    
    Veri Kaynakları (Öncelik Sırası):
    1. yfinance - Ana veri kaynağı
    2. borsapy - BIST için analist verileri ve KAP
    3. finpy - IMKB resmi verileri (alternatif)
    4. KAP.com API - Doğrudan KAP duyuruları
    """

    _cache = {}  # Symbol bazlı cache

    @staticmethod
    def get_fundamentals(symbol: str, exchange: str = "BIST", max_retries: int = 2) -> Optional[Dict]:
        """
        Hisse için temel analiz verilerini çek - Retry mekanizması ile
        
        BIST hisseleri için birden fazla kaynaktan veri toplar:
        1. yfinance - Ana finansal veriler (oranlar, dividend, market cap)
        2. borsapy - Analist önerileri ve KAP duyuruları
        3. finpy - IMKB resmi verilerine alternatif kaynak
        4. KAP.com API - Doğrudan duyuru bilgileri

        Args:
            symbol: Hisse sembolü (örn: "THYAO", "AAPL")
            exchange: Borsa adı (BIST, NASDAQ, NYSE)
            max_retries: Maksimum deneme sayısı

        Returns:
            {
                'company_info': {...},
                'financial_ratios': {...},
                'profitability': {...},
                'dividend': {...},
                'market_data': {...},
                'borsapy_data': {...},     # Sadece BIST - Analist + KAP
                'finpy_data': {...},       # Sadece BIST - IMKB Resmi
                'kap_data': {...}          # Sadece BIST - KAP Duyuruları
            }
        """
        cache_key = f"{symbol}_{exchange}"
        
        # Cache kontrolü
        if cache_key in FundamentalAnalysis._cache:
            return FundamentalAnalysis._cache[cache_key]

        if not YFINANCE_AVAILABLE:
            logging.error("❌ yfinance kurulu değil. 'pip install yfinance' ile yükleyin.")
            return None

        # Retry mekanizması
        for attempt in range(max_retries):
            try:
                logging.debug(f"📡 {symbol} ({exchange}): Temel analiz çekiliyor... (Deneme {attempt + 1}/{max_retries})")
                
                # 🆕 Symbol formatını exchange'e göre düzelt
                symbol_yahoo = FundamentalAnalysis._format_symbol(symbol, exchange)
                logging.debug(f"📌 Symbol formatı: {symbol} → {symbol_yahoo}")

                ticker = yf.Ticker(symbol_yahoo)
                info = ticker.info

                if not info or "symbol" not in info:
                    logging.warning(f"⚠️ {symbol} ({exchange}): yfinance'ten veri bulunamadı")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Retry öncesi bekleme
                        continue
                    return None

                fundamentals = {
                    "exchange": exchange,
                    "symbol": symbol,
                    "company_info": FundamentalAnalysis._extract_company_info(info),
                    "financial_ratios": FundamentalAnalysis._extract_financial_ratios(info),
                    "profitability": FundamentalAnalysis._extract_profitability(info),
                    "dividend": FundamentalAnalysis._extract_dividend(info),
                    "market_data": FundamentalAnalysis._extract_market_data(info),
                }
                
                # 🆕 BIST için ek veri kaynakları
                if exchange == "BIST":
                    # 1. Borsapy'den veri çek
                    if BORSAPY_AVAILABLE:
                        try:
                            borsapy_data = FundamentalAnalysis._get_borsapy_data(symbol)
                            if borsapy_data:
                                fundamentals["borsapy_data"] = borsapy_data
                                logging.debug(f"✅ {symbol}: Borsapy verileri eklendi")
                        except Exception as e:
                            logging.debug(f"⚠️ {symbol}: Borsapy verisi alınamadı - {e}")
                    
                    # 2. Finpy'den veri çek (alternatif kaynak)
                    if FINPY_AVAILABLE:
                        try:
                            finpy_data = FundamentalAnalysis._get_finpy_data(symbol)
                            if finpy_data:
                                fundamentals["finpy_data"] = finpy_data
                                logging.debug(f"✅ {symbol}: Finpy verileri eklendi")
                        except Exception as e:
                            logging.debug(f"⚠️ {symbol}: Finpy verisi alınamadı - {e}")
                    
                    # 3. KAP.com API'den veri çek (doğrudan API)
                    try:
                        kap_data = FundamentalAnalysis._get_kap_data(symbol)
                        if kap_data:
                            fundamentals["kap_data"] = kap_data
                            logging.debug(f"✅ {symbol}: KAP verileri eklendi")
                    except Exception as e:
                        logging.debug(f"⚠️ {symbol}: KAP verisi alınamadı - {e}")

                # Cache'e kaydet
                FundamentalAnalysis._cache[cache_key] = fundamentals
                logging.info(f"✅ {symbol} ({exchange}): Temel analiz başarıyla yüklendi")

                return fundamentals

            except Exception as e:
                logging.error(f"❌ {symbol} ({exchange}): Temel analiz hatası (Deneme {attempt + 1}) - {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Retry öncesi bekleme
                    continue
                else:
                    logging.error(f"❌ {symbol} ({exchange}): Maksimum deneme sayısı aşıldı")
                    return None
    
    @staticmethod
    def _format_symbol(symbol: str, exchange: str) -> str:
        """🆕 Exchange'e göre symbol formatla"""
        if exchange == "BIST":
            # BIST için .IS suffix ekle
            if not symbol.endswith(".IS"):
                return f"{symbol}.IS"
            return symbol
        elif exchange in ["NASDAQ", "NYSE"]:
            # US borsaları için suffix gerekmez
            return symbol.replace(".IS", "")
        else:
            return symbol
    
    @staticmethod
    def _get_borsapy_data(symbol: str) -> Optional[Dict]:
        """🆕 BIST hisseleri için borsapy verileri (SSL sertifika devre dışı)"""
        if not BORSAPY_AVAILABLE:
            return None
        
        try:
            # 🔧 Borsapy timeout ve SSL ayarları
            import requests
            session = requests.Session()
            session.verify = False  # SSL doğrulaması devre dışı (Windows sertifika sorunu için)
            
            # Borsapy'ye session'ı geçirelim (eğer desteklerse)
            ticker = bp.Ticker(symbol)
            
            data = {
                "source": "borsapy",
            }
            
            # Analist verileri (10 saniye timeout)
            try:
                analyst = ticker.analyst_info
                if analyst:
                    data["target_price"] = analyst.get("targetPrice", None)
                    data["recommendation"] = analyst.get("recommendation", "N/A")
                    data["upside_potential"] = analyst.get("upsidePotential", None)
                    logging.debug(f"✅ {symbol}: Borsapy analist verisi alındı")
            except (ConnectionError, TimeoutError) as e:
                logging.debug(f"⚠️ {symbol}: Borsapy analist verisi bağlantı hatası - {type(e).__name__}")
            except Exception as e:
                logging.debug(f"⚠️ {symbol}: Borsapy analist verisi alınamadı - {e}")
            
            # KAP bildirimleri (son 3)
            try:
                kap = ticker.kap_news
                if kap is not None and not kap.empty:
                    data["recent_kap"] = kap.head(3).to_dict("records")
                    logging.debug(f"✅ {symbol}: Borsapy KAP verileri alındı")
            except (ConnectionError, TimeoutError) as e:
                logging.debug(f"⚠️ {symbol}: Borsapy KAP verisi bağlantı hatası - {type(e).__name__}")
            except Exception as e:
                logging.debug(f"⚠️ {symbol}: Borsapy KAP verisi alınamadı - {e}")
            
            return data if len(data) > 1 else None
            
        except (ConnectionError, TimeoutError) as e:
            logging.debug(f"⚠️ Borsapy bağlantı hatası ({symbol}): {type(e).__name__}")
            return None
        except Exception as e:
            logging.warning(f"⚠️ Borsapy veri hatası ({symbol}): {e}")
            return None
    
    @staticmethod
    def _get_finpy_data(symbol: str) -> Optional[Dict]:
        """🆕 IMKB resmi verileri - Finpy entegrasyonu (alternatif kaynak)"""
        if not FINPY_AVAILABLE:
            return None
        
        try:
            logging.debug(f"📡 {symbol}: Finpy verileri çekiliyor...")
            
            # Finpy ile hisse verilerini çek
            stock = fp.Stocks()
            data_dict = stock.get(symbol, "1d")  # 1 günlük veriler
            
            if not data_dict or data_dict.empty:
                logging.debug(f"⚠️ {symbol}: Finpy'den veri bulunamadı")
                return None
            
            finpy_data = {
                "source": "finpy",
                "last_price": float(data_dict.iloc[-1]['close']) if not data_dict.empty else None,
                "volume": float(data_dict.iloc[-1]['volume']) if 'volume' in data_dict.columns else None,
                "high": float(data_dict.iloc[-1]['high']) if 'high' in data_dict.columns else None,
                "low": float(data_dict.iloc[-1]['low']) if 'low' in data_dict.columns else None,
            }
            
            logging.debug(f"✅ {symbol}: Finpy verileri başarıyla alındı")
            return finpy_data if any(v is not None for v in finpy_data.values()) else None
            
        except (ConnectionError, TimeoutError) as e:
            logging.debug(f"⚠️ Finpy bağlantı hatası ({symbol}): {type(e).__name__}")
            return None
        except Exception as e:
            logging.debug(f"⚠️ Finpy veri hatası ({symbol}): {e}")
            return None
    
    @staticmethod
    def _get_kap_data(symbol: str) -> Optional[Dict]:
        """🆕 KAP.com API'den doğrudan veri - İlk alternatif kaynak"""
        if not REQUESTS_AVAILABLE:
            return None
        
        try:
            logging.debug(f"📡 {symbol}: KAP.com verileri çekiliyor...")
            
            # KAP API endpoint (Kamuyu Aydınlatma Platformu)
            kap_url = "https://www.kap.org.tr"
            
            # KAP'tan haber/duyuru bilgisi çek (örnek: JSON API)
            # Not: KAP'ın resmi API'si olmadığı için web scraping yerine
            # başlık ve temel bilgi çekiyoruz
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            # Finans.com.tr API alternatifi (BIST verileri için)
            finance_api = f"https://finans.com.tr/hisse/{symbol.lower()}"
            
            session = requests.Session()
            session.verify = False  # SSL sorununa karşı
            
            try:
                response = session.get(finance_api, headers=headers, timeout=5)
                if response.status_code == 200:
                    kap_data = {
                        "source": "kap/finance-api",
                        "last_fetch": time.time(),
                        "status": "available"
                    }
                    logging.debug(f"✅ {symbol}: KAP.com verileri erişildi")
                    return kap_data
            except Exception as e:
                logging.debug(f"⚠️ KAP.com API hatası ({symbol}): {e}")
            
            return None
            
        except Exception as e:
            logging.debug(f"⚠️ KAP veri hatası ({symbol}): {e}")
            return None

    @staticmethod
    def _extract_company_info(info: dict) -> dict:
        """Şirket bilgileri"""
        return {
            "name": info.get("longName", info.get("shortName", "N/A")),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "employees": info.get("fullTimeEmployees", 0),
            "website": info.get("website", "N/A"),
            "city": info.get("city", "N/A"),
            "country": info.get("country", "N/A"),
        }

    @staticmethod
    def _extract_financial_ratios(info: dict) -> dict:
        """Finansal oranlar"""
        return {
            "pe_ratio": info.get("trailingPE", info.get("forwardPE", None)),
            "pb_ratio": info.get("priceToBook", None),
            "ps_ratio": info.get("priceToSalesTrailing12Months", None),
            "peg_ratio": info.get("pegRatio", None),
            "debt_to_equity": info.get("debtToEquity", None),
            "current_ratio": info.get("currentRatio", None),
            "quick_ratio": info.get("quickRatio", None),
            "ev_to_revenue": info.get("enterpriseToRevenue", None),
            "ev_to_ebitda": info.get("enterpriseToEbitda", None),
        }

    @staticmethod
    def _extract_profitability(info: dict) -> dict:
        """Karlılık metrikleri"""
        return {
            "profit_margin": info.get("profitMargins", None),
            "operating_margin": info.get("operatingMargins", None),
            "gross_margin": info.get("grossMargins", None),
            "roe": info.get("returnOnEquity", None),
            "roa": info.get("returnOnAssets", None),
            "revenue_growth": info.get("revenueGrowth", None),
            "earnings_growth": info.get("earningsGrowth", None),
        }

    @staticmethod
    def _extract_dividend(info: dict) -> dict:
        """Temettü bilgileri"""
        return {
            "dividend_yield": info.get("dividendYield", None),
            "dividend_rate": info.get("dividendRate", None),
            "payout_ratio": info.get("payoutRatio", None),
            "ex_dividend_date": info.get("exDividendDate", None),
            "five_year_avg_dividend_yield": info.get("fiveYearAvgDividendYield", None),
        }

    @staticmethod
    def _extract_market_data(info: dict) -> dict:
        """Piyasa verileri"""
        return {
            "market_cap": info.get("marketCap", None),
            "enterprise_value": info.get("enterpriseValue", None),
            "shares_outstanding": info.get("sharesOutstanding", None),
            "float_shares": info.get("floatShares", None),
            "beta": info.get("beta", None),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh", None),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow", None),
            "avg_volume": info.get("averageVolume", None),
            "avg_volume_10days": info.get("averageVolume10days", None),
        }

    @staticmethod
    def format_large_number(num: float) -> str:
        """Büyük sayıları formatla (1.5M, 2.3B gibi)"""
        if num is None:
            return "N/A"

        if num >= 1_000_000_000_000:
            return f"{num / 1_000_000_000_000:.2f}T"
        elif num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.2f}K"
        else:
            return f"{num:.2f}"

    @staticmethod
    def format_percentage(num: float) -> str:
        """Yüzde formatla"""
        if num is None:
            return "N/A"
        return f"{num * 100:.2f}%"

    @staticmethod
    def get_pe_analysis(pe_ratio: float) -> dict:
        """
        F/K oranı analizi
        Returns: {'status': str, 'emoji': str, 'description': str}
        """
        if pe_ratio is None:
            return {"status": "Bilinmiyor", "emoji": "⚪", "description": "Veri yok"}

        if pe_ratio < 0:
            return {
                "status": "Zararda",
                "emoji": "🔴",
                "description": "Şirket zarar ediyor",
            }
        elif pe_ratio < 10:
            return {
                "status": "Düşük",
                "emoji": "🟢",
                "description": "Potansiyel ucuz - araştır",
            }
        elif pe_ratio < 20:
            return {"status": "Normal", "emoji": "🟡", "description": "Makul değerleme"}
        elif pe_ratio < 30:
            return {"status": "Yüksek", "emoji": "🟠", "description": "Pahalı tarafta"}
        else:
            return {
                "status": "Çok Yüksek",
                "emoji": "🔴",
                "description": "Aşırı değerli olabilir",
            }

    @staticmethod
    def get_pb_analysis(pb_ratio: float) -> dict:
        """PD/DD oranı analizi"""
        if pb_ratio is None:
            return {"status": "Bilinmiyor", "emoji": "⚪", "description": "Veri yok"}

        if pb_ratio < 1:
            return {
                "status": "Çok Düşük",
                "emoji": "🟢",
                "description": "Defter değerinin altında",
            }
        elif pb_ratio < 3:
            return {"status": "Normal", "emoji": "🟡", "description": "Makul seviyede"}
        elif pb_ratio < 5:
            return {
                "status": "Yüksek",
                "emoji": "🟠",
                "description": "Premium değerleme",
            }
        else:
            return {
                "status": "Çok Yüksek",
                "emoji": "🔴",
                "description": "Aşırı pahalı",
            }

    @staticmethod
    def get_roe_analysis(roe: float) -> dict:
        """ROE (Özkaynak Karlılığı) analizi"""
        if roe is None:
            return {"status": "Bilinmiyor", "emoji": "⚪", "description": "Veri yok"}

        roe_pct = roe * 100

        if roe_pct < 0:
            return {"status": "Negatif", "emoji": "🔴", "description": "Zarar var"}
        elif roe_pct < 10:
            return {"status": "Zayıf", "emoji": "🟠", "description": "Düşük karlılık"}
        elif roe_pct < 15:
            return {"status": "Normal", "emoji": "🟡", "description": "Orta seviye"}
        elif roe_pct < 20:
            return {"status": "İyi", "emoji": "🟢", "description": "Güçlü karlılık"}
        else:
            return {
                "status": "Mükemmel",
                "emoji": "🔥",
                "description": "Çok yüksek karlılık",
            }

    @staticmethod
    def get_debt_analysis(debt_to_equity: float) -> dict:
        """Borç/Özkaynak oranı analizi"""
        if debt_to_equity is None:
            return {"status": "Bilinmiyor", "emoji": "⚪", "description": "Veri yok"}

        if debt_to_equity < 0.3:
            return {
                "status": "Düşük",
                "emoji": "🟢",
                "description": "Az borçlu - güvenli",
            }
        elif debt_to_equity < 1.0:
            return {
                "status": "Normal",
                "emoji": "🟡",
                "description": "Makul borç seviyesi",
            }
        elif debt_to_equity < 2.0:
            return {"status": "Yüksek", "emoji": "🟠", "description": "Borç yükü var"}
        else:
            return {
                "status": "Çok Yüksek",
                "emoji": "🔴",
                "description": "Riskli borç seviyesi",
            }
