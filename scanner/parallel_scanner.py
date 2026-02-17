# scanner/parallel_scanner.py - DÜZELTİLMİŞ VERSİYON
import concurrent.futures
import threading
import time
import logging
from typing import List, Dict, Optional, Callable, Any

logger = logging.getLogger(__name__)


class ParallelScanner:
    """Paralel hisse tarayıcı - THREAD-SAFE ve GÜVENLİ"""

    def __init__(self, hunter, max_workers: int = 4):
        self.hunter = hunter
        self.max_workers = min(max_workers, 16)  # 16 ile sınırla
        self.results_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.scan_results: List[Dict] = []
        self.processed_count = 0
        self.total_count = 0
        self.progress_callback: Optional[Callable] = None
        self._stop_event = threading.Event()

        logger.info(f"ParallelScanner başlatıldı (max_workers: {self.max_workers})")

    def stop(self):
        """Tarama işlemini durdur"""
        self._stop_event.set()
        logger.info("Paralel tarama durdurma sinyali gönderildi")

    def is_stopped(self):
        """Tarama durduruldu mu?"""
        return self._stop_event.is_set()

    def process_symbol_safe(self, symbol: str) -> Optional[Dict]:
        """Güvenli sembol işleme - exception handling ile"""
        if self.is_stopped():
            return None

        try:
            # İlerleme bilgisini güncelle
            with self.progress_lock:
                self.processed_count += 1
                progress_pct = (
                    int((self.processed_count / self.total_count) * 100)
                    if self.total_count > 0
                    else 0
                )

                if self.progress_callback:
                    message = f"{self.processed_count}/{self.total_count} - {symbol}"
                    self.progress_callback(progress_pct, message)

            # Sembolü işle
            logger.debug(f"Tarama: {symbol}")
            result = self.hunter.process_symbol_advanced(symbol)

            if result:
                logger.info(
                    f"✅ {symbol}: {result.get('Sinyal', 'N/A')} - Skor: {result.get('Skor', 'N/A')}"
                )
            else:
                logger.debug(f"❌ {symbol}: Filtrelendi")

            return result

        except Exception as e:
            logger.error(f"⚠️ {symbol} tarama hatası: {e}", exc_info=False)
            return None

    def scan_parallel(
        self, symbols: List[str], progress_callback: Optional[Callable] = None
    ) -> Dict[str, List]:
        """Sembolleri paralel olarak tara"""
        if not symbols:
            logger.warning("⚠️ Tarama için sembol listesi boş")
            return {"Swing Uygun": [], "Filtrelenen": []}

        # Durumu sıfırla
        self._stop_event.clear()
        self.scan_results = []
        self.processed_count = 0
        self.total_count = len(symbols)
        self.progress_callback = progress_callback

        start_time = time.time()
        logger.info(
            f"🚀 Paralel tarama başlıyor: {self.total_count} sembol, {self.max_workers} worker"
        )

        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers, thread_name_prefix="Scanner_"
            ) as executor:
                # Tüm sembolleri schedule et
                future_to_symbol = {
                    executor.submit(self.process_symbol_safe, symbol): symbol
                    for symbol in symbols
                }

                # Sonuçları topla
                for future in concurrent.futures.as_completed(future_to_symbol):
                    if self.is_stopped():
                        logger.info(
                            "⏸️ Tarama durduruldu, kalan işlemler iptal ediliyor..."
                        )
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    symbol = future_to_symbol[future]
                    try:
                        result = future.result(timeout=30)  # 30 saniye timeout (API çağrıları için)
                        if result:
                            with self.results_lock:
                                self.scan_results.append(result)
                    except concurrent.futures.TimeoutError:
                        logger.warning(f"⏱️ {symbol}: Timeout (30s) - atlanıyor")
                    except Exception as e:
                        logger.warning(f"⚠️ {symbol} işleme hatası: {e}")

        except Exception as e:
            logger.error(f"Paralel tarama sistemi hatası: {e}", exc_info=True)

        # Sonuçları sırala
        if self.scan_results:
            self.scan_results.sort(
                key=lambda x: float(
                    x.get("Skor", "0/100").split("/")[0]
                    if isinstance(x.get("Skor"), str)
                    else 0
                ),
                reverse=True,
            )

        elapsed_time = time.time() - start_time
        logger.info(
            f"✅ Paralel tarama tamamlandı: "
            f"{len(self.scan_results)}/{self.total_count} uygun, "
            f"{elapsed_time:.1f}s ({elapsed_time/self.total_count:.2f}s/hisse)"
        )

        # Filtrelenen sembolleri de raporla
        filtered_symbols = [
            s for s in symbols if s not in [r.get("Hisse") for r in self.scan_results]
        ]
        if filtered_symbols and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Filtrelenen semboller ({len(filtered_symbols)}): {filtered_symbols[:10]}{'...' if len(filtered_symbols) > 10 else ''}"
            )

        return {
            "Swing Uygun": self.scan_results,
            "Filtrelenen": filtered_symbols,
            "metadata": {
                "total_symbols": self.total_count,
                "filtered_count": len(filtered_symbols),
                "elapsed_time": elapsed_time,
                "avg_time_per_symbol": (
                    elapsed_time / self.total_count if self.total_count > 0 else 0
                ),
            },
        }

    def get_progress(self) -> Dict[str, Any]:
        """Mevcut ilerlemeyi al"""
        with self.progress_lock:
            return {
                "processed": self.processed_count,
                "total": self.total_count,
                "progress_pct": (
                    int((self.processed_count / self.total_count) * 100)
                    if self.total_count > 0
                    else 0
                ),
                "results_count": len(self.scan_results),
                "is_stopped": self.is_stopped(),
            }
