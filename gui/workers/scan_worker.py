# -*- coding: utf-8 -*-
"""
Scan Worker - Tarama işlemleri için worker sınıfı
"""
import logging
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ScanWorker(QObject):
    """Tarama işlemleri için worker"""

    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(self, hunter, symbols):
        super().__init__()
        self.hunter = hunter
        self.symbols = symbols
        self.is_running = True

    def stop(self):
        """Worker'ı durdur"""
        self.is_running = False
        self.hunter.stop_scanning()

    def run(self):
        """Ana tarama işlemi"""
        try:
            logger.info("🔍 Tarama worker başlatıldı")
            
            if not self.is_running:
                logger.warning("⚠️ Worker zaten durdurulmuş")
                return
            
            # Piyasa analizini hızlıca yap (cache'den varsa) veya atla
            self.progress.emit(5, "📈 Piyasa durumu kontrol ediliyor...")
            logger.info("📈 Piyasa analizi başlatılıyor...")
            
            if not self.is_running:
                return
            
            # Cache'den piyasa analizini al (eğer varsa)
            market_analysis = None
            try:
                cached = self.hunter.market_analyzer.get_cached_analysis()
                if cached:
                    market_analysis = cached
                    logger.info(f"✅ Piyasa analizi cache'den alındı: {market_analysis.regime}")
                    self.progress.emit(10, f"✅ Piyasa: {market_analysis.regime}")
                else:
                    # Cache yoksa, çok kısa timeout ile dene (2 saniye)
                    logger.info("📈 Piyasa analizi yapılıyor (2s timeout)...")
                    self.progress.emit(8, "📈 Piyasa analizi yapılıyor...")
                    
                    # Timeout mekanizması ile piyasa analizi
                    result_container = {"analysis": None, "done": False, "error": None}
                    
                    def run_analysis():
                        try:
                            result_container["analysis"] = self.hunter.analyze_market_condition()
                            result_container["done"] = True
                        except Exception as e:
                            logger.warning(f"Piyasa analizi exception: {e}")
                            result_container["error"] = str(e)
                            result_container["done"] = True
                    
                    # Thread'de çalıştır
                    analysis_thread = threading.Thread(target=run_analysis, daemon=True)
                    analysis_thread.start()
                    analysis_thread.join(timeout=2.0)  # 2 saniye bekle
                    
                    if result_container["done"] and result_container["analysis"]:
                        market_analysis = result_container["analysis"]
                        logger.info(f"✅ Piyasa analizi tamamlandı: {market_analysis.regime}")
                        self.progress.emit(10, f"✅ Piyasa: {market_analysis.regime}")
                    else:
                        # Timeout veya hata - direkt atla
                        if not result_container["done"]:
                            logger.warning("⚠️ Piyasa analizi timeout (2s) - atlanıyor, taramaya devam ediliyor")
                        else:
                            logger.warning(f"⚠️ Piyasa analizi hatası - atlanıyor: {result_container.get('error', 'Unknown')}")
                        from analysis.market_condition import _empty_market_analysis
                        market_analysis = _empty_market_analysis()
                        self.progress.emit(10, "⏩ Piyasa analizi atlandı, tarama başlıyor...")
            except Exception as e:
                logger.warning(f"⚠️ Piyasa analizi hatası (atlanıyor): {e}")
                # Piyasa analizi hatası olsa bile taramaya devam et
                from analysis.market_condition import _empty_market_analysis
                market_analysis = _empty_market_analysis()
                self.progress.emit(10, "⚠️ Piyasa analizi atlandı")

            if not self.is_running:
                logger.warning("⚠️ Worker durduruldu, tarama iptal ediliyor")
                return

            self.progress.emit(
                15, f"🚀 Tarama başlıyor... ({len(self.symbols)} sembol)"
            )

            # Taramayı çalıştır
            logger.info(f"🚀 Tarama başlatılıyor: {len(self.symbols)} sembol")
            self.progress.emit(20, f"🔍 {len(self.symbols)} sembol taranıyor...")
            
            if not self.is_running:
                return
            
            try:
                results = self.hunter.run_advanced_scan(
                    self.symbols, progress_callback=self.progress.emit
                )
                logger.info(f"✅ Tarama tamamlandı: {len(results.get('Swing Uygun', []))} sonuç bulundu")
            except Exception as e:
                logger.error(f"❌ Tarama hatası: {e}", exc_info=True)
                if self.is_running:
                    raise

            if not self.is_running:
                logger.warning("⚠️ Worker durduruldu, sonuçlar kaydedilmiyor")
                return

            logger.info("💾 Sonuçlar Excel'e kaydediliyor...")
            self.progress.emit(95, "💾 Sonuçlar kaydediliyor...")
            
            try:
                excel_file = self.hunter.save_to_excel(results)
                logger.info(f"✅ Excel dosyası oluşturuldu: {excel_file}")
            except Exception as e:
                logger.warning(f"⚠️ Excel kaydetme hatası: {e}")
                excel_file = None
            
            output = {
                "results": results,
                "excel_file": excel_file,
                "market_analysis": market_analysis,
            }
            
            self.progress.emit(100, "✅ Tarama tamamlandı!")
            self.finished.emit(output)
            logger.info("✅ Tarama worker tamamlandı")
        except Exception as e:
            logger.error(f"❌ Tarama worker kritik hatası: {e}", exc_info=True)
            if self.is_running:
                self.error.emit(f"Tarama hatası: {str(e)}")
