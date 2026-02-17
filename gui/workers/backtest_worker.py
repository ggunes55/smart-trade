# -*- coding: utf-8 -*-
"""
Backtest Worker - Backtest işlemleri için worker sınıfı
"""
from PyQt5.QtCore import QObject, pyqtSignal


class BacktestWorker(QObject):
    """Backtest işlemleri için worker"""

    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(self, hunter, symbols, backtest_config):
        super().__init__()
        self.hunter = hunter
        self.symbols = symbols
        self.backtest_config = backtest_config
        self.is_running = True

    def stop(self):
        """Worker'ı durdur"""
        self.is_running = False

    def run(self):
        """Ana backtest işlemi"""
        try:
            if not self.is_running:
                return

            self.progress.emit(5, "🎯 Backtest başlıyor...")

            # Hunter backtest işlemini güvenli blokta çalıştır
            try:
                results = self.hunter.run_backtest(
                    self.symbols, days=self.backtest_config["days"]
                )
            except Exception as e:
                if self.is_running:
                    self.error.emit(f"Backtest motoru hatası: {str(e)}")
                return

            if self.is_running:
                self.progress.emit(100, "✅ Backtest tamamlandı!")
                if results:
                    self.finished.emit(results)
                else:
                    self.error.emit("Backtest sonuç döndürmedi.")

        except Exception as e:
            # Kritik worker hatası
            if self.is_running:
                self.error.emit(f"Worker kritik hata: {str(e)}")
        finally:
            # Temizlik gerekirse buraya
            pass
