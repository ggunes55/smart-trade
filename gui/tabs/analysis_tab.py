# -*- coding: utf-8 -*-
"""
Analysis Tab - Detaylı Hisse Analizi Sekmesi

Kullanıcının istediği hisseyi projenin tüm özelliklerini kullanarak
analiz edip, detaylı trade uygunluk raporu sunan sekme.
"""

import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QProgressBar,
    QMessageBox,
    QFileDialog,
    QComboBox,
    QSplitter,
    QFrame,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    """Analiz işlemini arka planda çalıştır"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    
    def __init__(self, symbol: str, exchange: str, report_generator, data_handler=None):
        super().__init__()
        self.symbol = symbol
        self.exchange = exchange
        self.report_generator = report_generator
        self.data_handler = data_handler
    
    def run(self):
        try:
            self.progress.emit(10, "Veri çekiliyor...")
            
            # Veri çek
            df = None
            if self.data_handler:
                # get_data yerine get_daily_data kullanıyoruz ve exchange bilgisini geçiriyoruz
                try:
                    df = self.data_handler.get_daily_data(self.symbol, self.exchange)
                except AttributeError:
                    # Fallback if get_daily_data doesn't exist (e.g. older DataHandler)
                    if hasattr(self.data_handler, 'get_data'):
                        df = self.data_handler.get_data(self.symbol)
                    else:
                        raise AttributeError("DataHandler metodları bulunamadı (get_daily_data)")
            
            if df is None or len(df) < 50:
                self.error.emit(f"{self.symbol} için yeterli veri bulunamadı.")
                return
            
            self.progress.emit(30, "Teknik analiz yapılıyor...")
            
            # Analiz yap - df zaten çekildiği için tekrar çekilmeyecek
            analysis = self.report_generator.analyze_symbol(self.symbol, df)
            
            self.progress.emit(70, "Rapor oluşturuluyor...")
            
            # HTML rapor oluştur
            html_report = self.report_generator.generate_report_html(analysis)
            analysis['html_report'] = html_report
            
            self.progress.emit(100, "Tamamlandı!")
            self.finished.emit(analysis)
            
        except Exception as e:
            logger.error(f"Analiz hatası: {e}")
            self.error.emit(str(e))


class AnalysisTab(QWidget):
    """Detaylı Hisse Analizi Sekmesi"""
    
    def __init__(self, parent=None, config=None, data_handler=None, symbol_analyzer=None):
        super().__init__(parent)
        self.config = config or {}
        self.data_handler = data_handler
        self.symbol_analyzer = symbol_analyzer
        self.current_analysis = None
        self.worker = None
        
        # Report generator
        try:
            from ..reporting.detailed_analysis_report import DetailedAnalysisReport
            self.report_generator = DetailedAnalysisReport(
                self.config, 
                self.data_handler, 
                self.symbol_analyzer
            )
        except ImportError as e:
            logger.error(f"DetailedAnalysisReport import hatası: {e}")
            self.report_generator = None
        
        self.init_ui()
    
    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Input section
        input_group = self._create_input_section()
        layout.addWidget(input_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Report display
        self.report_browser = QTextBrowser()
        self.report_browser.setOpenExternalLinks(True)
        self.report_browser.setMinimumHeight(400)
        self.report_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #1a1a2e;
                color: #eee;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Başlangıç mesajı
        self.report_browser.setHtml(self._get_welcome_html())
        layout.addWidget(self.report_browser, 1)
        
        # Export buttons
        export_layout = self._create_export_section()
        layout.addLayout(export_layout)
    
    def _create_header(self) -> QWidget:
        """Header oluştur"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 10px;
                padding: 15px;
            }
            QLabel {
                color: white;
            }
        """)
        
        layout = QVBoxLayout(header)
        
        title = QLabel("📊 Detaylı Hisse Analizi")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Projenin tüm özelliklerini kullanarak kapsamlı analiz raporu")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; opacity: 0.9;")
        layout.addWidget(subtitle)
        
        return header
    
    def _create_input_section(self) -> QGroupBox:
        """Input bölümü oluştur"""
        group = QGroupBox("Analiz Parametreleri")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #333;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QHBoxLayout(group)
        
        # Symbol input
        layout.addWidget(QLabel("Sembol:"))
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Örn: THYAO, ASELS, BIMAS")
        self.symbol_input.setMinimumWidth(150)
        self.symbol_input.returnPressed.connect(self.start_analysis)
        layout.addWidget(self.symbol_input)
        
        # Periyot seçimi
        layout.addWidget(QLabel("Periyot:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Günlük", "Haftalık", "Aylık"])
        self.period_combo.setCurrentIndex(0)
        layout.addWidget(self.period_combo)
        
        # Analiz butonu
        self.analyze_btn = QPushButton("🔍 Analiz Et")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #764ba2;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_btn)
        
        layout.addStretch()
        
        return group
    
    def _create_export_section(self) -> QHBoxLayout:
        """Export butonları"""
        layout = QHBoxLayout()
        
        # PDF Export
        self.pdf_btn = QPushButton("📄 PDF Kaydet")
        self.pdf_btn.setEnabled(False)
        self.pdf_btn.clicked.connect(self.export_pdf)
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        layout.addWidget(self.pdf_btn)
        
        # Excel Export
        self.excel_btn = QPushButton("📊 Excel Kaydet")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.export_excel)
        self.excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        layout.addWidget(self.excel_btn)
        
        # Yazdır
        self.print_btn = QPushButton("🖨️ Yazdır")
        self.print_btn.setEnabled(False)
        self.print_btn.clicked.connect(self.print_report)
        self.print_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        layout.addWidget(self.print_btn)
        
        layout.addStretch()
        
        # Temizle butonu
        clear_btn = QPushButton("🗑️ Temizle")
        clear_btn.clicked.connect(self.clear_report)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        layout.addWidget(clear_btn)
        
        return layout
    
    def _get_welcome_html(self) -> str:
        """Karşılama HTML'i"""
        return """
        <html>
        <head>
            <style>
                body { 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    color: #eee; 
                    text-align: center; 
                    padding: 50px;
                }
                h2 { color: #667eea; }
                .info { color: #888; font-size: 14px; margin-top: 20px; }
                .feature { 
                    background: #16213e; 
                    padding: 10px; 
                    margin: 5px; 
                    border-radius: 5px;
                    display: inline-block;
                }
            </style>
        </head>
        <body>
            <h2>📊 Detaylı Hisse Analizi</h2>
            <p>Yukarıdaki alana hisse sembolünü yazın ve "Analiz Et" butonuna tıklayın.</p>
            
            <div class="info">
                <p><strong>Bu analiz şunları içerir:</strong></p>
                <span class="feature">📈 Trend Analizi</span>
                <span class="feature">📊 26+ Gösterge</span>
                <span class="feature">📍 Destek/Direnç</span>
                <span class="feature">💰 Trade Planı</span>
                <span class="feature">⚠️ Risk Metrikleri</span>
                <span class="feature">✅ Giriş Doğrulama</span>
            </div>
            
            <p class="info" style="margin-top: 30px;">
                Örnek semboller: THYAO, ASELS, BIMAS, KCHOL, TUPRS
            </p>
        </body>
        </html>
        """
    
    def start_analysis(self):
        """Analizi başlat"""
        symbol = self.symbol_input.text().strip().upper()
        
        if not symbol:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir hisse sembolü girin!")
            return
        
        # Exchange bilgisini al
        exchange = self.config.get('exchange', 'BIST')
        
        # Sadece BIST için ve eğer yoksa suffix ekle
        if exchange == 'BIST' and not symbol.endswith('.IS'):
            symbol += '.IS'
        
        if not self.report_generator:
            QMessageBox.critical(self, "Hata", "Rapor modülü yüklenemedi!")
            return
        
        # UI'ı disable et
        self.analyze_btn.setEnabled(False)
        self.symbol_input.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Worker başlat
        self.worker = AnalysisWorker(
            symbol, 
            exchange,
            self.report_generator,
            self.data_handler
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()
    
    def on_progress(self, value: int, message: str):
        """İlerleme güncelle"""
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{message} ({value}%)")
    
    def on_analysis_finished(self, analysis: dict):
        """Analiz tamamlandığında"""
        self.current_analysis = analysis
        
        # HTML raporu göster
        html_report = analysis.get('html_report', '')
        if html_report:
            self.report_browser.setHtml(html_report)
        
        # Export butonlarını aktifleştir
        self.pdf_btn.setEnabled(True)
        self.excel_btn.setEnabled(True)
        self.print_btn.setEnabled(True)
        
        # UI'ı enable et
        self.analyze_btn.setEnabled(True)
        self.symbol_input.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        logger.info(f"Analiz tamamlandı: {analysis.get('symbol', '')}")
    
    def on_analysis_error(self, error_msg: str):
        """Analiz hatası"""
        QMessageBox.critical(self, "Analiz Hatası", error_msg)
        
        # UI'ı enable et
        self.analyze_btn.setEnabled(True)
        self.symbol_input.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def export_pdf(self):
        """PDF olarak kaydet"""
        if not self.current_analysis:
            return
        
        symbol = self.current_analysis.get('symbol', 'report')
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        default_name = f"{symbol}_analiz_{date_str}.pdf"
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "PDF Olarak Kaydet", 
            default_name, 
            "PDF Files (*.pdf)"
        )
        
        if filename:
            html_report = self.current_analysis.get('html_report', '')
            success = self.report_generator.export_to_pdf(html_report, filename)
            
            if success:
                QMessageBox.information(self, "Başarılı", f"PDF kaydedildi:\n{filename}")
            else:
                # HTML olarak kaydet
                html_filename = filename.replace('.pdf', '.html')
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(html_report)
                QMessageBox.information(
                    self, 
                    "Bilgi", 
                    f"PDF kütüphanesi bulunamadı.\nHTML olarak kaydedildi:\n{html_filename}"
                )
    
    def export_excel(self):
        """Excel olarak kaydet"""
        if not self.current_analysis:
            return
        
        symbol = self.current_analysis.get('symbol', 'report')
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        default_name = f"{symbol}_analiz_{date_str}.xlsx"
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Excel Olarak Kaydet", 
            default_name, 
            "Excel Files (*.xlsx)"
        )
        
        if filename:
            success = self.report_generator.export_to_excel(self.current_analysis, filename)
            
            if success:
                QMessageBox.information(self, "Başarılı", f"Excel kaydedildi:\n{filename}")
            else:
                QMessageBox.warning(self, "Hata", "Excel kaydedilemedi!")
    
    def print_report(self):
        """Raporu yazdır"""
        try:
            from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
            
            printer = QPrinter(QPrinter.HighResolution)
            dialog = QPrintDialog(printer, self)
            
            if dialog.exec_() == QPrintDialog.Accepted:
                self.report_browser.print_(printer)
                
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Yazdırma hatası: {e}")
    
    def clear_report(self):
        """Raporu temizle"""
        self.current_analysis = None
        self.report_browser.setHtml(self._get_welcome_html())
        self.symbol_input.clear()
        self.pdf_btn.setEnabled(False)
        self.excel_btn.setEnabled(False)
        self.print_btn.setEnabled(False)
    
    def set_symbol(self, symbol: str):
        """Dışarıdan sembol ayarla"""
        self.symbol_input.setText(symbol.replace('.IS', ''))
    
    def analyze_symbol_directly(self, symbol: str):
        """Dışarıdan doğrudan analiz başlat"""
        self.symbol_input.setText(symbol.replace('.IS', ''))
        self.start_analysis()
