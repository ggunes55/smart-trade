# -*- coding: utf-8 -*-
"""
Error Handler Dialog - Geliştirilmiş hata yönetimi
Detaylı hata mesajları, öneriler, log export
"""

import logging
import traceback
from typing import Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QGroupBox,
    QMessageBox,
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)


class ErrorDialog(QDialog):
    """Geliştirilmiş hata dialog'u"""
    
    def __init__(self, error_type: str, error_message: str, 
                 error_details: Optional[str] = None, parent=None):
        """
        ErrorDialog'u başlat
        
        Args:
            error_type: Hata tipi (ex: "Connection Error", "Data Error")
            error_message: Hata mesajı (kullanıcı dostu)
            error_details: Teknik detaylar
            parent: Parent widget
        """
        super().__init__(parent)
        self.error_type = error_type
        self.error_message = error_message
        self.error_details = error_details or ""
        self.init_ui()
    
    def init_ui(self):
        """UI başlangıcı"""
        self.setWindowTitle(f"❌ {self.error_type}")
        self.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout()
        
        # Başlık
        title = QLabel(f"❌ {self.error_type}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #f44336; padding: 10px;")
        layout.addWidget(title)
        
        # Ana hata mesajı
        message_label = QLabel(self.error_message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            background-color: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #f44336;
            font-size: 11pt;
        """)
        layout.addWidget(message_label)
        
        # Teknik detaylar grubu
        if self.error_details:
            detail_group = QGroupBox("🔧 Teknik Detaylar")
            detail_layout = QVBoxLayout()
            
            detail_text = QTextEdit()
            detail_text.setReadOnly(True)
            detail_text.setText(self.error_details)
            detail_text.setStyleSheet("""
                background-color: #f5f5f5;
                color: #333333;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
                padding: 5px;
                border: 1px solid #cccccc;
            """)
            detail_text.setMaximumHeight(150)
            detail_layout.addWidget(detail_text)
            
            detail_group.setLayout(detail_layout)
            layout.addWidget(detail_group)
        
        # Öneriler
        suggestions = self._get_suggestions()
        if suggestions:
            suggestion_group = QGroupBox("💡 Öneriler")
            suggestion_layout = QVBoxLayout()
            
            suggestion_text = QTextEdit()
            suggestion_text.setReadOnly(True)
            suggestion_text.setText("\n".join([f"• {s}" for s in suggestions]))
            suggestion_text.setStyleSheet("""
                background-color: #e8f5e9;
                color: #2e7d32;
                padding: 10px;
                border: 1px solid #4caf50;
                border-radius: 4px;
            """)
            suggestion_text.setMaximumHeight(100)
            suggestion_layout.addWidget(suggestion_text)
            
            suggestion_group.setLayout(suggestion_layout)
            layout.addWidget(suggestion_group)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 Log'u Kopyala")
        copy_btn.clicked.connect(self.copy_log)
        copy_btn.setStatusTip("Hata log'unu panoya kopyala")
        
        retry_btn = QPushButton("🔄 Yeniden Dene")
        retry_btn.clicked.connect(self.retry)
        
        close_btn = QPushButton("✓ Kapat")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(retry_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def copy_log(self):
        """Hata log'unu panoya kopyala"""
        import pyperclip
        
        log_text = f"""
ERROR REPORT
============
Type: {self.error_type}
Message: {self.error_message}
Time: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}

Technical Details:
{self.error_details}
"""
        try:
            pyperclip.copy(log_text)
            QMessageBox.information(self, "Başarılı", "Log panoya kopyalandı!")
        except ImportError:
            # pyperclip yoksa fallback
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(log_text)
            QMessageBox.information(self, "Başarılı", "Log panoya kopyalandı!")
    
    def retry(self):
        """Yeniden dene"""
        self.done(1)  # Custom return code
    
    def _get_suggestions(self) -> list:
        """Hata tipine göre öneriler döndür"""
        suggestions = []
        
        error_lower = self.error_type.lower()
        message_lower = self.error_message.lower()
        
        # Connection errors
        if 'connection' in error_lower or 'timeout' in error_lower:
            suggestions = [
                "İnternet bağlantınızı kontrol edin",
                "Firewall/VPN ayarlarınızı kontrol edin",
                "API sunucusu durumunu kontrol edin",
                "Momentleri bekleyerek yeniden deneyin",
            ]
        
        # Data errors
        elif 'data' in error_lower or 'format' in error_lower:
            suggestions = [
                "Giriş verilerinin formatını kontrol edin",
                "Dosyayı yeniden kaydetmeyi deneyin",
                "Türkçe karakterleri kontrol edin",
            ]
        
        # Memory errors
        elif 'memory' in error_lower:
            suggestions = [
                "Açık uygulamaları kapatmayı deneyin",
                "Sistem RAM'ini boşaltın",
                "Daha az sayıda sembol taramasını deneyin",
            ]
        
        # File errors
        elif 'file' in error_lower:
            suggestions = [
                "Dosya yolunun doğru olduğunu kontrol edin",
                "Dosya/klasör izinlerini kontrol edin",
                "Dosyanın açık olmadığını kontrol edin (Excel vb.)",
            ]
        
        # Default suggestions
        else:
            suggestions = [
                "Hata log'unu kontrol edin",
                "Ayarları kontrol edin",
                "Yardım dosyasını okuyun",
                "Destek ile iletişime geçin",
            ]
        
        return suggestions


class WarningDialog(QDialog):
    """Uyarı dialog'u"""
    
    def __init__(self, title: str, message: str, details: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"⚠️ {title}")
        self.setGeometry(100, 100, 500, 250)
        
        layout = QVBoxLayout()
        
        # Başlık
        title_label = QLabel(f"⚠️ {title}")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #FF9800; padding: 10px;")
        layout.addWidget(title_label)
        
        # Mesaj
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("""
            background-color: #fff3e0;
            color: #e65100;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #FF9800;
        """)
        layout.addWidget(msg_label)
        
        # Detaylar
        if details:
            detail_text = QTextEdit()
            detail_text.setReadOnly(True)
            detail_text.setText(details)
            detail_text.setMaximumHeight(80)
            layout.addWidget(detail_text)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("✓ Anlaşıldı")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)


class SuccessDialog(QDialog):
    """Başarı dialog'u"""
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"✓ {title}")
        self.setGeometry(100, 100, 400, 150)
        
        layout = QVBoxLayout()
        
        # Başlık
        title_label = QLabel(f"✓ {title}")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #4CAF50; padding: 10px;")
        layout.addWidget(title_label)
        
        # Mesaj
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("""
            background-color: #e8f5e9;
            color: #2e7d32;
            padding: 15px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        """)
        layout.addWidget(msg_label)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("✓ Tamam")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)


class ErrorHandler:
    """Merkezi hata yöneticisi"""
    
    @staticmethod
    def handle_exception(exception: Exception, context: str = "") -> ErrorDialog:
        """
        İstisna işle ve dialog göster
        
        Args:
            exception: Python exception
            context: Hata bağlamı
        
        Returns:
            ErrorDialog instance
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        error_details = traceback.format_exc()
        
        # Log'a kaydet
        logger.error(f"[{context}] {error_type}: {error_message}", exc_info=exception)
        
        # Dialog oluştur ve göster
        dialog = ErrorDialog(
            error_type=error_type,
            error_message=error_message,
            error_details=error_details
        )
        
        return dialog
    
    @staticmethod
    def show_error(title: str, message: str, details: str = "", parent=None):
        """Hata göster"""
        dialog = ErrorDialog(title, message, details, parent)
        return dialog.exec_()
    
    @staticmethod
    def show_warning(title: str, message: str, details: str = "", parent=None):
        """Uyarı göster"""
        dialog = WarningDialog(title, message, details, parent)
        return dialog.exec_()
    
    @staticmethod
    def show_success(title: str, message: str, parent=None):
        """Başarı göster"""
        dialog = SuccessDialog(title, message, parent)
        return dialog.exec_()
