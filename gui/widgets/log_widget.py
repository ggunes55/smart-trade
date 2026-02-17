# -*- coding: utf-8 -*-
"""
Log Widget - Log görüntüleme widget'ı
"""
from PyQt5.QtCore import QObject, pyqtSignal
import logging
from PyQt5.QtWidgets import QApplication

class LogSignal(QObject):
    """Log mesajlarını ana threade taşımak için sinyal taşıyıcı"""
    log_signal = pyqtSignal(str)

class QTextEditLogger(logging.Handler):
    """
    Thread-safe QTextEdit log handler.
    Log mesajını sinyal ile ana thread'e gönderir.
    """

    def __init__(self, parent):
        super().__init__()
        self.widget = parent
        self.widget.setReadOnly(True)
        
        # Sinyal mekanizması
        self.signals = LogSignal()
        self.signals.log_signal.connect(self.append_log)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.signals.log_signal.emit(msg)
        except RuntimeError:
            # Pencere kapanırken Qt objesi silinmiş olabilir
            pass
        except Exception:
            self.handleError(record)

    def append_log(self, msg):
        """Ana thread'de çalışır"""
        try:
            self.widget.append(msg)
            # Scroll to bottom
            sb = self.widget.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())
        except Exception:
            pass
