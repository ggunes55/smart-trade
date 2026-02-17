# -*- coding: utf-8 -*-
"""
Swing Hunter Ultimate - Modüler Orchestrator
Tüm bileşenleri koordine eder
"""
import logging
import threading
from typing import List, Dict, Optional

from core.utils import load_config, setup_logging
from smart_filter.smart_filter import SmartFilterSystem
from backtest.backtester import RealisticBacktester
from scanner.parallel_scanner import ParallelScanner

# Modüler bileşenler
from .data_handler import DataHandler
from .market_analyzer import MarketAnalyzer
from .symbol_analyzer import SymbolAnalyzer
from .trade_calculator import TradeCalculator
from .result_manager import ResultManager


class SwingHunterUltimate:
    """
    Ana scanner sınıfı - Orchestrator pattern
    Tüm analiz bileşenlerini koordine eder
    """

    def __init__(self, config_path="swing_config.json"):
        """
        Scanner'ı başlat

        Args:
            config_path: Config dosyası yolu
        """
        # Config yükle
        self.cfg = load_config(config_path)
        setup_logging(self.cfg.get("log_file", "swing_hunter_ultimate.log"))

        # Core bileşenler
        self.data_handler = DataHandler(self.cfg)
        self.market_analyzer = MarketAnalyzer(self.cfg, self.data_handler)

        # Smart filter
        exchange = self.cfg.get("exchange", "BIST")
        self.smart_filter = SmartFilterSystem(self.cfg, exchange=exchange)

        # Symbol analyzer
        self.symbol_analyzer = SymbolAnalyzer(
            self.cfg, self.data_handler, self.market_analyzer, self.smart_filter
        )

        # Trade calculator
        self.trade_calculator = TradeCalculator(self.cfg)

        # Result manager
        self.result_manager = ResultManager(self.cfg)

        # Backtest
        self.backtester = RealisticBacktester(self.cfg)

        # Benchmark verisi
        self.benchmark_df = None

        # Parallel scanner
        self.parallel_scanner = ParallelScanner(
            self, max_workers=self.cfg.get("max_workers", 4)
        )

        # Durdurma mekanizması
        self._stop_event = threading.Event()
        self.stop_scan = False

        logging.info("🚀 SwingHunterUltimate başlatıldı (modüler sürüm)")

    # ========================================================================
    # Ana Tarama Metodları
    # ========================================================================

    def run_advanced_scan(self, symbols: List[str], progress_callback=None) -> Dict:
        """
        Gelişmiş tarama - Ana metod

        Args:
            symbols: Taranacak semboller
            progress_callback: İlerleme callback fonksiyonu

        Returns:
            Sonuç dictionary
        """
        if not symbols:
            logging.warning("⚠️ Tarama için sembol listesi boş!")
            return {"Swing Uygun": [], "Filtrelenen": []}
        
        # Benchmark verisi (RS analizi için)
        # Benchmark verisi (RS analizi için)
        if self.cfg.get("use_relative_strength", True):
            try:
                from tvDatafeed import Interval
                
                # Exchange'e göre doğru endeksi seç
                exchange = self.cfg.get("exchange", "BIST")
                
                # Varsayılan endeks sembolleri
                index_map = {
                    "BIST": "XU100",
                    "NASDAQ": "SPY",  # veya QQQ
                    "NYSE": "SPY",    # S&P 500 genel benchmark
                    "CRYPTO": "BTC-USD"
                }
                
                # Config'de özel tanımlı yoksa map'ten al
                index_symbol = self.cfg.get("index_symbol")
                if not index_symbol or index_symbol == "XU100":  # Varsayılanı override et
                    index_symbol = index_map.get(exchange, "XU100")
                
                logging.info(f"Benchmark verisi ({index_symbol}) çekiliyor... Exchange: {exchange}")
                
                # 1. Deneme: tvDatafeed
                try:
                    self.benchmark_df = self.data_handler.safe_api_call(
                        index_symbol, exchange if exchange != "CRYPTO" else "BINANCE", Interval.in_daily, 250
                    )
                except Exception as e:
                    logging.warning(f"tvDatafeed benchmark hatası: {e}")
                    self.benchmark_df = None

                # 2. Deneme: yfinance Fallback (Eğer tvDatafeed başarısızsa)
                if self.benchmark_df is None or self.benchmark_df.empty:
                    import yfinance as yf
                    logging.info("yfinance fallback devreye giriyor...")
                    
                    # yfinance sembol dönüşümü
                    yf_symbol_map = {
                        "XU100": "XU100.IS",
                        "SPY": "SPY",
                        "QQQ": "QQQ",
                        "BTC-USD": "BTC-USD"
                    }
                    yf_symbol = yf_symbol_map.get(index_symbol, index_symbol)
                    
                    try:
                        yf_data = yf.download(yf_symbol, period="1y", progress=False)
                        if not yf_data.empty:
                            # Standardize et (lowercase columns)
                            yf_data.columns = [c.lower() for c in yf_data.columns]
                            self.benchmark_df = yf_data
                            logging.info(f"✅ yfinance benchmark verisi hazır: {yf_symbol}")
                    except Exception as yf_e:
                        logging.error(f"yfinance benchmark hatası: {yf_e}")

                if self.benchmark_df is not None:
                     logging.info(f"✅ Benchmark verisi hazır ({len(self.benchmark_df)} bar)")
            except Exception as e:
                logging.warning(f"Benchmark verisi genel hatası: {e}")
                self.benchmark_df = None

        # Parallel mi sequential mi?
        use_parallel = self.cfg.get("use_parallel_scan", True) and len(symbols) > 10

        if use_parallel:
            logging.info(f"🚀 Parallel tarama: {len(symbols)} sembol")
            try:
                results = self.parallel_scanner.scan_parallel(symbols, progress_callback)
                logging.info(f"✅ Parallel tarama tamamlandı: {len(results.get('Swing Uygun', []))} sonuç")
            except Exception as e:
                logging.error(f"❌ Parallel tarama hatası: {e}", exc_info=True)
                raise
        else:
            logging.info(f"🔍 Sequential tarama: {len(symbols)} sembol")
            try:
                results = self._sequential_scan(symbols, progress_callback)
                logging.info(f"✅ Sequential tarama tamamlandı: {len(results.get('Swing Uygun', []))} sonuç")
            except Exception as e:
                logging.error(f"❌ Sequential tarama hatası: {e}", exc_info=True)
                raise

        return results

    def _sequential_scan(self, symbols: List[str], progress_callback=None) -> Dict:
        """Sequential (sıralı) tarama"""
        results = []
        total = len(symbols)
        logging.info(f"🔍 Sequential tarama başlıyor: {total} sembol")

        for i, symbol in enumerate(symbols):
            if self.stop_scan:
                logging.info("⏸️ Tarama durduruldu")
                break

            # İlerleme callback
            if progress_callback:
                progress = int((i + 1) / total * 100)
                message = f"{i + 1}/{total} - {symbol}"
                progress_callback(progress, message)

            # Sembol analizi
            try:
                result = self.symbol_analyzer.analyze_symbol(symbol, self.benchmark_df)
                if result:
                    results.append(result)
                    logging.debug(f"✅ {symbol}: Analiz başarılı")
            except Exception as e:
                logging.warning(f"⚠️ {symbol} analiz hatası: {e}")

        logging.info(f"✅ Sequential tarama tamamlandı: {len(results)} sonuç bulundu")
        
        # Sonuçları formatla
        return self.result_manager.format_results(results)

    def process_symbol_advanced(self, symbol: str) -> Optional[Dict]:
        """
        Tek sembol analizi

        Args:
            symbol: Sembol adı

        Returns:
            Sonuç dictionary veya None
        """
        return self.symbol_analyzer.analyze_symbol(symbol, self.benchmark_df)

    # ========================================================================
    # Piyasa Analizi
    # ========================================================================

    def analyze_market_condition(self, force_refresh: bool = False):
        """
        Piyasa durumu analizi

        Args:
            force_refresh: Cache'i bypass et

        Returns:
            MarketAnalysis objesi
        """
        return self.market_analyzer.analyze_market_condition(force_refresh)

    # ========================================================================
    # Trade Hesaplamaları (GUI İçin)
    # ========================================================================

    def calculate_trade_plan(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        target1: float,
        capital: float = None,
    ) -> Dict:
        """Trade planı hesapla"""
        return self.trade_calculator.calculate_trade_plan(
            symbol, entry_price, stop_loss, target1, capital
        )

    def validate_trade_parameters(
        self, entry_price: float, stop_loss: float, target1: float, symbol: str = ""
    ) -> Dict:
        """Trade parametrelerini doğrula"""
        return self.trade_calculator.validate_trade_parameters(
            entry_price, stop_loss, target1, symbol
        )

    # ========================================================================
    # Backtest
    # ========================================================================

    def run_backtest(self, symbols: List[str], days: int = 180) -> Dict:
        """
        Batch backtest

        Args:
            symbols: Sembol listesi
            days: Gün sayısı

        Returns:
            Backtest sonuçları
        """
        from tvDatafeed import Interval

        try:
            all_results = []

            for i, symbol in enumerate(symbols):
                if self.stop_scan:
                    break

                logging.info(f"Backtest {i+1}/{len(symbols)}: {symbol}")

                # Veri çek
                df = self.data_handler.safe_api_call(
                    symbol, self.cfg["exchange"], Interval.in_daily, days + 50
                )

                if df is None or len(df) < 100:
                    logging.warning(f"{symbol}: Yetersiz veri")
                    continue

                # Backtest çalıştır
                result = self.backtester.run_backtest(
                    symbol=symbol,
                    df=df,
                    hunter=self,
                    initial_capital=self.cfg.get("initial_capital", 10000),
                )

                if result.get("success", False):
                    all_results.append(result)

            # Özet oluştur
            return self._create_backtest_summary(symbols, all_results)

        except Exception as e:
            logging.error(f"Batch backtest hatası: {e}")
            return {
                "summary": {"total_symbols": len(symbols), "total_trades": 0},
                "detailed": [],
                "error": str(e),
            }

    def _create_backtest_summary(self, symbols: List[str], results: List[Dict]) -> Dict:
        """Backtest özeti oluştur"""
        if not results:
            return {
                "summary": {
                    "total_symbols": len(symbols),
                    "total_trades": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                },
                "detailed": [],
                "note": "Hiç başarılı backtest yapılamadı",
            }

        # Metrikler
        total_trades = sum(r["metrics"]["total_trades"] for r in results)
        winning_trades = sum(r["metrics"]["winning_trades"] for r in results)
        total_profit = sum(r["metrics"]["total_profit"] for r in results)

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        best = max(results, key=lambda x: x["metrics"]["total_profit"])
        worst = min(results, key=lambda x: x["metrics"]["total_profit"])

        return {
            "summary": {
                "total_symbols": len(symbols),
                "tested_symbols": len(results),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": round(win_rate, 2),
                "total_profit": round(total_profit, 2),
                "avg_return": round(total_profit / len(results), 2),
                "best_symbol": best["symbol"],
                "worst_symbol": worst["symbol"],
            },
            "detailed": [
                {
                    "Symbol": r["symbol"],
                    "Trades": r["metrics"]["total_trades"],
                    "Win Rate %": r["metrics"]["win_rate"],
                    "Total Return %": r["metrics"]["total_return_pct"],
                    "Total Profit": r["metrics"]["total_profit"],
                    "Max Drawdown %": r["metrics"]["max_drawdown"],
                    "Sharpe Ratio": r["metrics"]["sharpe_ratio"],
                }
                for r in results
            ],
            "raw_results": results,
        }

    # ========================================================================
    # Sonuç Yönetimi
    # ========================================================================

    def save_to_excel(self, results: Dict, filename: str = None) -> Optional[str]:
        """Excel'e kaydet"""
        return self.result_manager.save_to_excel(results, filename)

    def save_to_csv(self, results: Dict, filename: str = None) -> Optional[str]:
        """CSV'ye kaydet"""
        return self.result_manager.save_to_csv(results, filename)

    # ========================================================================
    # Kontrol Metodları
    # ========================================================================

    def stop_scanning(self):
        """Taramayı durdur"""
        self.stop_scan = True
        self.symbol_analyzer.stop_analysis()
        self._stop_event.set()
        logging.info("⏹️ Durdurma sinyali gönderildi")

    def reset(self):
        """Scanner'ı sıfırla"""
        self.stop_scan = False
        self._stop_event.clear()
        self.symbol_analyzer.reset_stop_flag()
        self.market_analyzer.clear_cache()
        logging.info("🔄 Scanner sıfırlandı")

    # ========================================================================
    # Yardımcı Metodlar (Geriye Uyumluluk)
    # ========================================================================

    def calculate_indicators(self, df):
        """İndikatör hesaplama (wrapper)"""
        from indicators.ta_manager import calculate_indicators

        return calculate_indicators(df)

    def safe_api_call(self, symbol, exchange, interval, n_bars):
        """Veri çekme (wrapper)"""
        return self.data_handler.safe_api_call(symbol, exchange, interval, n_bars)
