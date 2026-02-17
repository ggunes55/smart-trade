# -*- coding: utf-8 -*-
"""
Results Tab - Sonuçlar sekmesi
"""
import logging
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QMenu,
    QAction,
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QFont
from ..utils.styles import GREEN_BUTTON, BLUE_BUTTON, TRADE_DETAILS
from ..utils.helpers import (
    get_score_color,
    get_signal_color,
    get_pattern_color,
    get_rr_color,
)
from ..utils.translations import translate, format_trend_turkish, format_strength_turkish


class ResultsTab(QWidget):
    """Sonuçlar sekmesi"""

    row_selected = pyqtSignal(dict)  # Satır seçildiğinde sinyal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)

        # Başlık
        header_layout = QHBoxLayout()

        self.results_title = QLabel("📊 Tarama Sonuçları")
        self.results_title.setStyleSheet(
            "font-size: 14pt; font-weight: bold; color: #1976D2;"
        )

        self.results_stats = QLabel("Sonuç: 0 hisse")
        self.results_stats.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #4CAF50;"
        )

        header_layout.addWidget(self.results_title)
        header_layout.addStretch()
        header_layout.addWidget(self.results_stats)

        layout.addLayout(header_layout)

        # Tablo
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.ExtendedSelection)  # Çoklu seçim desteği
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Sağ tık menüsü
        self.results_table.setContextMenuPolicy(3)  # Qt.CustomContextMenu
        self.results_table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.results_table)

        # Trade detayları
        details_group = self._create_details_group()
        layout.addWidget(details_group)

        # Export butonları
        export_layout = self._create_export_layout()
        layout.addLayout(export_layout)

    def _create_details_group(self):
        """Trade detayları grubu"""
        group = QGroupBox("📋 Seçili Hisse Detayları")
        layout = QVBoxLayout()

        self.trade_details_text = QTextEdit()
        self.trade_details_text.setReadOnly(True)
        self.trade_details_text.setMaximumHeight(200)
        self.trade_details_text.setStyleSheet(TRADE_DETAILS)
        self.trade_details_text.setPlainText("Bir hisse seçin...")

        layout.addWidget(self.trade_details_text)
        group.setLayout(layout)
        return group


    def _create_export_layout(self):
        """Export butonları"""
        layout = QHBoxLayout()

        excel_btn = QPushButton("📊 Excel'e Aktar")
        excel_btn.clicked.connect(self.export_to_excel)
        excel_btn.setStyleSheet(GREEN_BUTTON)

        csv_btn = QPushButton("💾 CSV'ye Aktar")
        csv_btn.clicked.connect(self.export_to_csv)
        csv_btn.setStyleSheet(BLUE_BUTTON)

        png_btn = QPushButton("🖼️ PNG Grafik")
        png_btn.clicked.connect(self.export_to_png)
        png_btn.setStyleSheet("background-color: #FFC107; font-weight: bold;")

        pdf_btn = QPushButton("📄 PDF Rapor")
        pdf_btn.clicked.connect(self.export_to_pdf)
        pdf_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        
        # Phase 1: Add to Watchlist button
        watchlist_btn = QPushButton("➕ Add to Watchlist")
        watchlist_btn.clicked.connect(self.add_to_watchlist)
        watchlist_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold;")
        watchlist_btn.setToolTip("Add selected symbols to watchlist for tracking")
        
        # Detaylı Analiz butonu
        analysis_btn = QPushButton("🔍 Detaylı Analiz")
        analysis_btn.clicked.connect(self.open_detailed_analysis)
        analysis_btn.setStyleSheet("background-color: #667eea; color: white; font-weight: bold;")
        analysis_btn.setToolTip("Seçili hisse için kapsamlı analiz raporu oluştur")

        layout.addWidget(excel_btn)
        layout.addWidget(csv_btn)
        layout.addWidget(png_btn)
        layout.addWidget(pdf_btn)
        layout.addWidget(watchlist_btn)
        layout.addWidget(analysis_btn)
        layout.addStretch()

        return layout

    def export_to_png(self):
        from gui.reporting.report_generator import ReportGenerator
        df = self._get_table_as_dataframe()
        ReportGenerator(self).export_to_png(df)

    def export_to_pdf(self):
        from gui.reporting.report_generator import ReportGenerator
        df = self._get_table_as_dataframe()
        ReportGenerator(self).export_to_pdf(df)

    def _get_table_as_dataframe(self):
        # Tabloyu DataFrame'e çevir
        row_count = self.results_table.rowCount()
        col_count = self.results_table.columnCount()
        data = []
        headers = [self.results_table.horizontalHeaderItem(i).text() for i in range(col_count)]
        for row in range(row_count):
            row_data = []
            for col in range(col_count):
                item = self.results_table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        return pd.DataFrame(data, columns=headers)

    def populate_table(self, data):
        """Tabloyu doldur"""
        self.results_data = data  # Veriyi sakla
        
        if not data:
            self.results_stats.setText("Sonuç: 0 hisse")
            return

        if data and isinstance(data[0], dict):
            # Görüntülenecek sütunları belirle (Gizli verileri hariç tut)
            hidden_keys = [
                "tv_signal_details", 
                "volume_ratio",  # rvol ile duplicate
                "macd_signal", "MACD_Signal", "macd_hist", "MACD_Histogram",  # Gereksiz MACD detayları
                "histogram", "signal"  # Ek MACD alanları
            ]
            headers = [k for k in data[0].keys() if k not in hidden_keys]
        else:
            return

        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        self.results_table.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, key in enumerate(headers):
                raw_value = row_data.get(key, "")
                
                # Sayısal değerleri formatla (1.05000086 -> 1.05)
                value = self._format_value(raw_value)
                
                # Çeviri uygula (Sadece metin içerikli temiz sütunlar için)
                if isinstance(value, str) and not value.replace('.','',1).isdigit():
                    # Trend ve Güç için özel formatlayıcılar
                    if key in ['Trend', 'Main Trend']:
                        value = format_trend_turkish(value)
                    elif key in ['Güç', 'Strength']:
                        value = format_strength_turkish(value)
                    # Sinyal için özel
                    elif key in ['Sinyal', 'Signal', 'TV Sinyal']:
                         # Sinyal değerleri genelde zaten çevrili olabilir ama tekrar geçelim
                         # Ancak "GÜÇLÜ AL" gibi ifadeler translate içinde olmayabilir, parça parça bakalım
                         if value in ['AL', 'SAT', 'BEKLE']:
                             value = translate(value)
                         elif 'BUY' in value.upper():
                             value = value.replace('BUY', 'AL').replace('STRONG', 'GÜÇLÜ')
                         elif 'SELL' in value.upper():
                             value = value.replace('SELL', 'SAT').replace('STRONG', 'GÜÇLÜ')
                    else:
                        # Genel çeviri
                        value = translate(value)

                item = QTableWidgetItem(value)

                # Renklendirme
                self._apply_cell_color(item, key, value)

                self.results_table.setItem(row_idx, col_idx, item)

        self.results_table.resizeColumnsToContents()
        self.results_stats.setText(f"Sonuç: {len(data)} hisse")
    
    def _format_value(self, value):
        """Değeri formatla - uzun ondalıklı sayıları kısalt"""
        if value is None or value == "":
            return "-"
        
        # Float ise direkt formatla
        if isinstance(value, float):
            if abs(value) >= 1000:
                return f"{value:,.0f}"
            return f"{value:.2f}"
        
        # String ise float'a çevirmeyi dene
        if isinstance(value, str):
            # Zaten kısa veya özel format ise dokunma
            if len(value) <= 6 or '%' in value or ':' in value or '/' in value:
                return value
            try:
                float_val = float(value.replace(',', '.'))
                if abs(float_val) >= 1000:
                    return f"{float_val:,.0f}"
                return f"{float_val:.2f}"
            except (ValueError, TypeError):
                return str(value)
        
        return str(value)

    def _apply_cell_color(self, item, key, value):
        """Hücre rengini uygula"""
        if key == "Skor":
            try:
                score = float(value.split("/")[0])
                color = get_score_color(score)
                item.setBackground(color)
                if score >= 85:
                    item.setForeground(QColor(255, 255, 255))
            except (ValueError, IndexError):
                pass

        elif key == "Sinyal":
            color = get_signal_color(value)
            if color:
                item.setBackground(color)
                if "🔥🔥🔥" in value:
                    item.setForeground(QColor(255, 255, 255))

        elif key == "Pattern Skor":
            try:
                pattern_score = float(value.split("/")[0])
                color = get_pattern_color(pattern_score)
                if color:
                    item.setBackground(color)
                    if pattern_score >= 15:
                        item.setForeground(QColor(139, 0, 0))
            except (ValueError, IndexError):
                pass

        elif key == "Bullish Patternler" and value != "Yok":
            item.setBackground(QColor(230, 230, 250))
            item.setFont(QFont("Arial", 9, QFont.Bold))

        elif key == "R/R":
            try:
                rr_value = float(value.split(":")[1])
                color = get_rr_color(rr_value)
                if color:
                    item.setBackground(color)
                    if rr_value >= 3.0:
                        item.setFont(QFont("Arial", 9, QFont.Bold))
            except (ValueError, IndexError):
                pass

            except (ValueError, IndexError):
                pass
        
        elif key == "TV Sinyal":
            if "GÜÇLÜ AL" in value:
                item.setBackground(QColor(46, 125, 50)) # Koyu Yeşil
                item.setForeground(QColor(255, 255, 255))
                item.setFont(QFont("Arial", 9, QFont.Bold))
            elif "AL" == value:
                item.setBackground(QColor(200, 230, 201)) # Açık Yeşil
            elif "GÜÇLÜ SAT" in value:
                item.setBackground(QColor(198, 40, 40)) # Koyu Kırmızı
                item.setForeground(QColor(255, 255, 255))
            elif "SAT" == value:
                item.setBackground(QColor(255, 205, 210)) # Açık Kırmızı

        elif key == "Piyasa Skoru":
            try:
                market_score = float(value.split("/")[0])
                if market_score >= 70:
                    item.setBackground(QColor(135, 206, 250))
            except (ValueError, IndexError):
                pass

    def on_selection_changed(self):
        """Seçim değiştiğinde"""
        selected_items = self.results_table.selectedItems()

        if not selected_items:
            self.trade_details_text.setPlainText("Bir hisse seçin...")
            return

        try:
            row = selected_items[0].row()
            
            # Orijinal veriden al (varsa)
            if hasattr(self, 'results_data') and self.results_data and row < len(self.results_data):
                # Sıralama değişmiş olabilir, bu yüzden table row index güvenilir olmayabilir eğer sorting açıks
                # QTableWidget sorting kullandığında row indexler karışır.
                # En güvenlisi: Tablodan sembolü al, original data'da bul.
                pass 
            
            # Basit Yöntem: Tablodan veriyi al (mevcut yöntem)
            headers = []
            for col in range(self.results_table.columnCount()):
                header_item = self.results_table.horizontalHeaderItem(col)
                if header_item:
                    headers.append(header_item.text())

            row_data = {}
            for col, header in enumerate(headers):
                item = self.results_table.item(row, col)
                if item:
                    row_data[header] = item.text()
            
            # Eğer orijinal veri varsa ve sembol eşleşiyorsa, gizli verileri de ekle
            if hasattr(self, 'results_data'):
                symbol = row_data.get("Hisse")
                original_item = next((item for item in self.results_data if item.get("Hisse") == symbol), None)
                if original_item:
                    row_data.update(original_item)

            # Sinyal gönder
            self.row_selected.emit(row_data)

        except Exception as e:
            logging.error(f"Seçim değişikliği hatası: {e}")
            self.trade_details_text.setPlainText(f"Hata: {e}")

    def set_trade_details(self, details_text):
        """Trade detaylarını ayarla"""
        self.trade_details_text.setPlainText(details_text)

    def export_to_excel(self):
        """Excel'e aktar"""
        try:
            if self.results_table.rowCount() == 0:
                QMessageBox.warning(self, "Uyarı", "Aktarılacak veri yok!")
                return

            data = self._get_table_data()
            df = pd.DataFrame(data)

            filename = f"Swing_Advanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)

            logging.info(f"📊 Excel raporu: {filename}")
            QMessageBox.information(
                self, "Başarılı", f"Excel raporu oluşturuldu:\n{filename}"
            )

        except Exception as e:
            logging.error(f"Excel aktarım hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Excel hatası:\n{e}")

    def export_to_csv(self):
        """CSV'ye aktar"""
        try:
            if self.results_table.rowCount() == 0:
                QMessageBox.warning(self, "Uyarı", "Aktarılacak veri yok!")
                return

            data = self._get_table_data()
            df = pd.DataFrame(data)

            filename = f"Swing_Advanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding="utf-8-sig")

            logging.info(f"💾 CSV raporu: {filename}")
            QMessageBox.information(
                self, "Başarılı", f"CSV raporu oluşturuldu:\n{filename}"
            )

        except Exception as e:
            logging.error(f"CSV aktarım hatası: {e}")
            QMessageBox.critical(self, "Hata", f"CSV hatası:\n{e}")

    def _get_table_data(self):
        """Tablo verisini al"""
        data = []
        headers = []

        for col in range(self.results_table.columnCount()):
            headers.append(self.results_table.horizontalHeaderItem(col).text())

        for row in range(self.results_table.rowCount()):
            row_data = {}
            for col, header in enumerate(headers):
                item = self.results_table.item(row, col)
                row_data[header] = item.text() if item else ""
            data.append(row_data)

        return data
    
    def show_context_menu(self, position):
        """Sağ tık menüsünü göster"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        menu = QMenu(self)
        
        # Detaylı Analiz
        analysis_action = QAction("🔍 Detaylı Analiz", self)
        analysis_action.triggered.connect(self.open_detailed_analysis)
        menu.addAction(analysis_action)
        
        # Grafikte Göster
        chart_action = QAction("📊 Grafikte Göster", self)
        chart_action.triggered.connect(self._show_in_chart)
        menu.addAction(chart_action)
        
        menu.addSeparator()
        
        # Watchlist'e Ekle
        watchlist_action = QAction("➕ Watchlist'e Ekle", self)
        watchlist_action.triggered.connect(self.add_to_watchlist)
        menu.addAction(watchlist_action)
        
        menu.exec_(self.results_table.viewport().mapToGlobal(position))
    
    def _show_in_chart(self):
        """Seçili hisseyi grafikte göster"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        headers = [self.results_table.horizontalHeaderItem(i).text() 
                   for i in range(self.results_table.columnCount())]
        
        symbol = None
        for col, header in enumerate(headers):
            if header in ['Hisse', 'Sembol', 'Symbol']:
                item = self.results_table.item(row, col)
                if item:
                    symbol = item.text()
                    break
        
        if symbol:
            parent_window = self.window()
            if hasattr(parent_window, 'chart_tab'):
                parent_window.chart_tab.show_chart(symbol)
    
    def open_detailed_analysis(self):
        """Seçili hisse için detaylı analiz aç"""
        selected_rows = self.results_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Uyarı", "Lütfen analiz için bir hisse seçin!")
            return
        
        # İlk seçili satırın sembolünü al
        row = selected_rows[0].row()
        headers = [self.results_table.horizontalHeaderItem(i).text() 
                   for i in range(self.results_table.columnCount())]
        
        symbol = None
        for col, header in enumerate(headers):
            if header in ['Hisse', 'Sembol', 'Symbol', 'Ticker']:
                item = self.results_table.item(row, col)
                if item:
                    symbol = item.text()
                    break
        
        if not symbol:
            QMessageBox.warning(self, "Uyarı", "Sembol bulunamadı!")
            return
        
        # Analysis tab'a yönlendir
        parent_window = self.window()
        if hasattr(parent_window, 'analysis_tab'):
            parent_window.analysis_tab.analyze_symbol_directly(symbol)
            
            # Analysis tab'ı aktif yap
            tabs = parent_window.findChild(type(parent_window.analysis_tab.parent()))
            if tabs:
                for i in range(tabs.count() if hasattr(tabs, 'count') else 0):
                    if hasattr(tabs, 'widget') and tabs.widget(i) == parent_window.analysis_tab:
                        tabs.setCurrentIndex(i)
                        break
        else:
            QMessageBox.warning(self, "Uyarı", "Analiz sekmesi bulunamadı!")

    def clear_results(self):
        """Sonuçları temizle"""
        self.results_table.setRowCount(0)
        self.results_stats.setText("Sonuç: 0 hisse")
        self.trade_details_text.setPlainText("Bir hisse seçin...")
    
    def add_to_watchlist(self):
        """Seçili satırları watchlist'e ekle (Phase 1)"""
        try:
            selected_rows = self.results_table.selectionModel().selectedRows()
            
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "Lütfen watchlist'e eklemek için bir veya daha fazla sembol seçin")
                return
            
            # Watchlist manager'a erişim (parent window'dan)
            parent_window = self.window()
            if not hasattr(parent_window, 'watchlist_tab'):
                QMessageBox.critical(self, "Error", "Watchlist sekmesi bulunamadı")
                return
            
            added_count = 0
            already_exists_count = 0
            
            # Get headers for scraping fallback
            headers = [self.results_table.horizontalHeaderItem(i).text() 
                      for i in range(self.results_table.columnCount())]
            
            logging.info(f"Adding to watchlist. Available columns: {headers}")
            
            for row_index in selected_rows:
                row = row_index.row()
                
                # 1. Tablodan görünen sembolü al
                row_data_visible = {}
                for col, header in enumerate(headers):
                    item = self.results_table.item(row, col)
                    if item:
                        row_data_visible[header] = item.text()
                
                # Sembolü bul
                symbol = (row_data_visible.get('Sembol') or 
                         row_data_visible.get('Hisse') or 
                         row_data_visible.get('Symbol') or 
                         row_data_visible.get('Ticker') or '')
                
                if not symbol:
                    logging.warning(f"No symbol found in row {row}. Row data: {row_data_visible}")
                    continue
                
                # 2. RAW VERİYİ BUL (self.results_data içinde)
                # Bu çok önemli çünkü ekrandaki veriler formatlı/yuvarlanmış olabilir veya bazı sütunlar gizli olabilir.
                raw_data = None
                if hasattr(self, 'results_data') and self.results_data:
                    # Sembol eşleşmesi ile bulmaya çalış
                    for item in self.results_data:
                        item_symbol = (item.get('Sembol') or item.get('Hisse') or 
                                      item.get('Symbol') or item.get('Ticker'))
                        if item_symbol == symbol:
                            raw_data = item
                            break
                    
                    # Eğer sembolle bulunamazsa ve data uzunluğu satır sayısı ile aynıysa index ile dene
                    if not raw_data and len(self.results_data) == self.results_table.rowCount():
                        try:
                            # Sorting kapalıysa veya indexler eşleşiyorsa
                            raw_data = self.results_data[row]
                            # Kontrol et
                            item_symbol = (raw_data.get('Sembol') or raw_data.get('Hisse') or 
                                          raw_data.get('Symbol') or raw_data.get('Ticker'))
                            if item_symbol != symbol:
                                raw_data = None # Eşleşmedi, risk alma
                        except:
                            pass
                
                # 3. Veriyi hazırla
                source_data = raw_data if raw_data else row_data_visible
                logging.info(f"Using {'RAW' if raw_data else 'VISIBLE'} data for {symbol}")
                
                # Exchange bul
                exchange = (source_data.get('Borsa') or 
                           source_data.get('Exchange') or 
                           source_data.get('Market') or 'BIST')
                
                # Convert to scan result format
                scan_result = self._convert_row_to_scan_result(source_data)
                
                # 4. Watchlist'e ekle
                success = parent_window.watchlist_tab.manager.add_to_watchlist(symbol, exchange, scan_result)
                
                if success:
                    added_count += 1
                    logging.info(f"✅ Added {symbol} to watchlist")
                else:
                    already_exists_count += 1
                    logging.info(f"⚠️ {symbol} already in watchlist")
            
            # Show result
            if added_count == 0 and already_exists_count == 0:
                QMessageBox.warning(
                    self, 
                    "Uyarı", 
                    "Hiçbir sembol eklenemedi.\n\n"
                    "Tabloda 'Sembol' veya 'Hisse' sütunu bulunamadı."
                )
            else:
                message = f"{added_count} sembol watchlist'e eklendi"
                if already_exists_count > 0:
                    message += f"\n{already_exists_count} sembol zaten listede"
                    
                # Parent tab refresh
                if hasattr(parent_window.watchlist_tab, '_refresh_all'):
                     parent_window.watchlist_tab._load_watchlist()
                     
                QMessageBox.information(self, "Başarılı", message)
            
        except Exception as e:
            logging.error(f"Error adding to watchlist: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Watchlist'e eklenirken hata:\n{e}")
    
    def _convert_row_to_scan_result(self, row_data: dict) -> dict:
        """Convert results table row to scan result format with comprehensive parameter capture"""
        
        def safe_parse_float(value: str, default: float = None) -> float:
            """Safely parse a float from string, handling various formats"""
            if not value or value in ['-', 'N/A', '', 'None']:
                return default
            try:
                # Remove common suffixes and clean up
                cleaned = str(value).replace(',', '.').replace('%', '').replace('x', '').replace('₺', '')
                # Handle "50.5 (neutral)" format and "1:2.5" R/R format
                if ':' in cleaned:
                    cleaned = cleaned.split(':')[-1]  # Take part after colon for R/R
                cleaned = cleaned.split()[0].split('/')[0]
                return float(cleaned)
            except (ValueError, IndexError):
                return default
        
        def get_value(*keys, default=None):
            """Try multiple column name variations"""
            for key in keys:
                val = row_data.get(key)
                if val and val not in ['-', 'N/A', '', 'None']:
                    return val
            return default
        
        try:
            # Log available columns for debugging
            logging.debug(f"Row data keys: {list(row_data.keys())}")
            
            # Price - try multiple column names
            current_price = safe_parse_float(
                get_value('Fiyat', 'Price', 'Güncel Fiyat', 'Son Fiyat', 'Close'),
                default=100.0
            )
            
            # Entry, Stop, Target - read from table if available
            entry = safe_parse_float(
                get_value('Giriş', 'Entry', 'Entry Price', 'Giriş Fiyatı'),
                default=None
            )
            stop = safe_parse_float(
                get_value('Stop', 'Stop Loss', 'SL', 'Stop-Loss', 'Zarar Kes'),
                default=None
            )
            target1 = safe_parse_float(
                get_value('Hedef 1', 'T1', 'Target 1', 'Target1', 'Hedef1'),
                default=None
            )
            target2 = safe_parse_float(
                get_value('Hedef 2', 'T2', 'Target 2', 'Target2', 'Hedef2'),
                default=None
            )
            target3 = safe_parse_float(
                get_value('Hedef 3', 'T3', 'Target 3', 'Target3', 'Hedef3'),
                default=None
            )
            
            # R/R ratio - try to extract for calculating targets if not directly available
            rr_ratio = safe_parse_float(
                get_value('R/R', 'Risk/Reward', 'RR', 'Risk Ödül'),
                default=None
            )
            
            # If entry/stop/targets not directly available, calculate based on R/R or use defaults
            if entry is None:
                entry = current_price * 0.99  # %1 altında giriş
            if stop is None:
                stop = current_price * 0.95  # %5 stop
            
            # Calculate risk for target estimation
            risk = entry - stop if entry and stop else current_price * 0.05
            
            if target1 is None:
                target1 = entry + (risk * 1.5) if entry else current_price * 1.05
            if target2 is None:
                target2 = entry + (risk * 2.5) if entry else current_price * 1.10
            if target3 is None:
                target3 = entry + (risk * 4.0) if entry else current_price * 1.15
            
            # Technical indicators - comprehensive column name search
            rsi = safe_parse_float(
                get_value('RSI', 'RSI (14)', 'rsi', 'RSI14', 'Rsi'),
                default=None
            )
            
            adx = safe_parse_float(
                get_value('ADX', 'ADX (14)', 'adx', 'ADX14', 'Adx', 'Trend Gücü'),
                default=None
            )
            
            macd = safe_parse_float(
                get_value('MACD', 'MACD Hist', 'macd', 'MACD Histogram'),
                default=None
            )
            
            # Score/Trend - handle "85/100" format
            score_str = get_value('Skor', 'Score', 'Trend Skor', 'Trend Score', 'Kalite', 'Quality', 'trend_score')
            trend_score = safe_parse_float(score_str, default=None)
            
            # Volume ratio
            volume_ratio = safe_parse_float(
                get_value('Vol Ratio', 'Hacim Oranı', 'Volume Ratio', 'Hacim', 'Vol', 'RelVol', 'volume_ratio'),
                default=None
            )
            
            # Advanced metrics
            sharpe = safe_parse_float(
                get_value('Sharpe', 'Sharpe Ratio', 'Sharpe Oranı', 'sharpe'),
                default=None
            )
            
            alpha = safe_parse_float(
                get_value('Alpha', 'Alfa', 'RS Rating', 'RS', 'alpha'),
                default=None
            )
            
            swing_efficiency = safe_parse_float(
                get_value('Swing Eff', 'Swing Efficiency', 'Efficiency', 'Verimlilik', 'swing_efficiency'),
                default=None
            )
            
            # Text fields
            volatility_status = get_value('Volatilite', 'Volatility', 'Vol Status', 'Vol Durumu', 'volatility_status')
            if not volatility_status or volatility_status in ['-', 'N/A', '']:
                volatility_status = 'NORMAL'
            
            market_regime = get_value('Market Regime', 'Piyasa Rejimi', 'Regime', 'Rejim', 'market_regime')
            if not market_regime or market_regime in ['-', 'N/A', '']:
                market_regime = 'UNKNOWN'
            
            # Signal type
            signal_type = get_value('Sinyal', 'Signal', 'signal_type', 'Tip', 'Signal Type')
            if not signal_type or signal_type in ['-', 'N/A', '']:
                signal_type = 'SCAN'
            
            # Confidence calculation based on score
            confidence = min(trend_score / 100.0, 1.0) if trend_score and trend_score > 0 else 0.7
            
            # Confirmations
            confirmations = int(safe_parse_float(
                get_value('Onay', 'Confirmations', 'Doğrulama', 'Conf', 'confirmations'),
                default=3
            ) or 3)
            
            # Main trend and trend strength
            main_trend = get_value('main_trend', 'Trend', 'Main Trend', 'Ana Trend', 'Trend Yönü')
            if main_trend:
                # Normalize trend values
                main_trend_upper = str(main_trend).upper()
                if 'YÜK' in main_trend_upper or 'UP' in main_trend_upper or '↑' in main_trend:
                    main_trend = 'UP'
                elif 'DÜŞ' in main_trend_upper or 'DOWN' in main_trend_upper or '↓' in main_trend:
                    main_trend = 'DOWN'
                elif 'YAT' in main_trend_upper or 'SIDE' in main_trend_upper or '→' in main_trend:
                    main_trend = 'SIDEWAYS'
            
            trend_strength = get_value('trend_strength', 'Güç', 'Trend Strength', 'Trend Gücü', 'Strength', 'Kuvvet')
            if trend_strength:
                trend_strength_upper = str(trend_strength).upper()
                if 'GÜÇ' in trend_strength_upper or 'STRONG' in trend_strength_upper:
                    trend_strength = 'STRONG'
                elif 'ORTA' in trend_strength_upper or 'MEDIUM' in trend_strength_upper or 'MED' in trend_strength_upper:
                    trend_strength = 'MEDIUM'
                elif 'ZAYIF' in trend_strength_upper or 'WEAK' in trend_strength_upper:
                    trend_strength = 'WEAK'
            
            # RVOL (Relative Volume)
            rvol = safe_parse_float(
                get_value('rvol', 'RVOL', 'Rel Vol', 'Relative Volume', 'RVol', 'Hacim Oranı', 'Vol Ratio'),
                default=None
            )
            if rvol is None and volume_ratio is not None:
                rvol = volume_ratio  # Fallback to volume_ratio
            
            # Setup type
            setup_type = get_value('setup_type', 'Setup', 'Setup Tipi', 'Setup Type', 'Pattern', 'Formasyon')
            
            # Sector, Index, Liquidity for identity_info
            sector = get_value('sector', 'Sektör', 'Sector', 'Sektor', 'Industry')
            index_membership = get_value('index_membership', 'Endeks', 'Index', 'Indeks', 'Index Membership', 'BIST100', 'BIST30')
            liquidity_score = safe_parse_float(
                get_value('liquidity_score', 'Likidite', 'Liquidity', 'Liq Score', 'Liquidity Score'),
                default=None
            )
            
            # RS Data
            rs_rating = safe_parse_float(
                get_value('RS', 'RS Rating', 'Relative Strength', 'RSRating'),
                default=None
            )
            
            result = {
                'current_price': current_price,
                'entry': entry,
                'stop': stop,
                'target1': target1,
                'target2': target2,
                'target3': target3,
                'rsi': rsi,
                'macd': macd,
                'adx': adx,
                'trend_score': trend_score,
                'volume_ratio': volume_ratio,
                'rvol': rvol,
                'sharpe': sharpe,
                'alpha': alpha,
                'swing_efficiency': swing_efficiency,
                'volatility_status': volatility_status,
                'market_regime': market_regime,
                'signal_type': signal_type,
                'confidence': confidence,
                'confirmations': confirmations,
                # New fields for watchlist
                'main_trend': main_trend,
                'trend_strength': trend_strength,
                'setup_type': setup_type,
                # Identity info fields (will be extracted in add_to_watchlist)
                'sector': sector,
                'index_membership': index_membership,
                'liquidity_score': liquidity_score,
                'rs_data': {'rs_rating': rs_rating} if rs_rating else None,
            }
            
            logging.debug(f"Converted scan result: RSI={rsi}, ADX={adx}, Entry={entry}, Stop={stop}, T1={target1}")
            return result
            
        except Exception as e:
            logging.error(f"Error parsing row data: {e}", exc_info=True)
            return {
                'current_price': 100.0,
                'entry': 98.0,
                'stop': 95.0,
                'target1': 105.0,
                'target2': 110.0,
                'target3': 115.0,
                'rsi': None,
                'macd': None,
                'adx': None,
                'trend_score': None,
                'volume_ratio': None,
                'sharpe': None,
                'swing_efficiency': None,
                'volatility_status': 'NORMAL',
                'market_regime': 'UNKNOWN',
                'signal_type': 'SCAN',
                'confidence': 0.7,
                'confirmations': 3,
            }
