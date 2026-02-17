# -*- coding: utf-8 -*-
"""
Market Analysis Worker - Piyasa analizi için worker sınıfı
"""
from PyQt5.QtCore import QObject, pyqtSignal


class MarketAnalysisWorker(QObject):
    """Piyasa analizi için worker"""

    finished = pyqtSignal(object)  # MarketAnalysis objesi
    error = pyqtSignal(str)

    def __init__(self, hunter):
        super().__init__()
        self.hunter = hunter

    def run(self):
        """Piyasa analizini çalıştır"""
        try:
            analysis = self.hunter.analyze_market_condition()
            self.finished.emit(analysis)
        except Exception as e:
            self.error.emit(str(e))
