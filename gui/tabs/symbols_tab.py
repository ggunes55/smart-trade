# -*- coding: utf-8 -*-
"""
Symbols Tab - Hisse yönetimi sekmesi
"""
import logging
import os
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QListWidget,
    QLineEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QSpinBox,
    QMessageBox,
    QFileDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from ..utils.styles import GREEN_BUTTON, RED_BUTTON, ORANGE_BUTTON
from ..utils.helpers import get_resource_path


class SymbolsTab(QWidget):
    """Hisse yönetimi sekmesi"""

    symbol_selected = pyqtSignal(object)  # Hisse seçildiğinde sinyal
    exchange_changed = pyqtSignal(str)  # Exchange değiştiğinde sinyal

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.init_ui()

    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)

        # Hisse listesi grubu
        symbol_group = self._create_symbol_group()
        layout.addWidget(symbol_group)

        # Genel ayarlar grubu
        general_group = self._create_general_group()
        layout.addWidget(general_group)

        layout.addStretch()

    def _create_symbol_group(self):
        """Hisse listesi grubu"""
        group = QGroupBox("📊 Taranacak Hisseler")
        layout = QVBoxLayout()

        # Liste widget
        # Arama Kutusu
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Listede ara (örn: BANKA, THY)")
        self.search_input.textChanged.connect(self.filter_symbols)
        layout.addWidget(self.search_input)

        self.symbol_list_widget = QListWidget()
        self.symbol_list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.symbol_list_widget.itemClicked.connect(self.on_symbol_clicked)

        # Ekleme bölümü
        input_layout = QHBoxLayout()
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Hisse kodu (örn: GARAN)")
        self.symbol_input.returnPressed.connect(self.add_symbol)

        add_btn = QPushButton("➕ Ekle")
        add_btn.clicked.connect(self.add_symbol)
        add_btn.setStyleSheet(GREEN_BUTTON)

        input_layout.addWidget(self.symbol_input)
        input_layout.addWidget(add_btn)

        # Yönetim butonları
        manage_layout = QHBoxLayout()

        remove_btn = QPushButton("🗑️ Sil")
        remove_btn.clicked.connect(self.remove_symbol)
        remove_btn.setStyleSheet(RED_BUTTON)

        clear_btn = QPushButton("🧹 Temizle")
        clear_btn.clicked.connect(self.clear_all_symbols)
        clear_btn.setStyleSheet(ORANGE_BUTTON)

        manage_layout.addWidget(remove_btn)
        manage_layout.addWidget(clear_btn)
        manage_layout.addStretch()

        # Hızlı ekleme
        quick_group = QGroupBox("⚡ Hızlı Ekle")
        quick_layout = QHBoxLayout()

        import_btn = QPushButton("📂 CSV")
        import_btn.clicked.connect(self.import_symbols_from_csv)
        import_btn.setStyleSheet(ORANGE_BUTTON)

        quick_layout.addWidget(import_btn)
        quick_group.setLayout(quick_layout)

        layout.addWidget(self.symbol_list_widget, 1)
        layout.addLayout(input_layout)
        layout.addLayout(manage_layout)
        layout.addWidget(quick_group)

        group.setLayout(layout)
        return group

    def _create_general_group(self):
        """Genel ayarlar grubu"""
        group = QGroupBox("⚙️ Genel Ayarlar")
        layout = QVBoxLayout()

        # Exchange seçimi
        exchange_layout = QHBoxLayout()
        exchange_layout.addWidget(QLabel("Borsa:"))
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["BIST", "NASDAQ", "NYSE", "CRYPTO"])
        self.exchange_combo.currentTextChanged.connect(self.on_exchange_changed)
        exchange_layout.addWidget(self.exchange_combo)
        exchange_layout.addStretch()

        # Lookback ayarı
        lookback_layout = QHBoxLayout()
        lookback_layout.addWidget(QLabel("Veri Aralığı (Gün):"))
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(50, 500)
        self.lookback_spin.setValue(250)
        lookback_layout.addWidget(self.lookback_spin)
        lookback_layout.addStretch()

        layout.addLayout(exchange_layout)
        layout.addLayout(lookback_layout)

        group.setLayout(layout)
        return group

    def add_symbol(self):
        """Hisse ekle"""
        symbol = self.symbol_input.text().upper().strip()
        if symbol:
            items = self.symbol_list_widget.findItems(symbol, Qt.MatchExactly)
            if not items:
                self.symbol_list_widget.addItem(symbol)
                self.symbol_input.clear()
                logging.info(f"✅ Hisse eklendi: {symbol}")
            else:
                QMessageBox.information(self, "Bilgi", f"{symbol} zaten listede!")

    def remove_symbol(self):
        """Seçili hisseyi sil"""
        selected_items = self.symbol_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen silmek için hisse seçin!")
            return

        for item in selected_items:
            self.symbol_list_widget.takeItem(self.symbol_list_widget.row(item))
            logging.info(f"🗑️ Hisse silindi: {item.text()}")

    def clear_all_symbols(self):
        """Tüm hisseleri temizle"""
        reply = QMessageBox.question(
            self,
            "Onay",
            "Tüm hisseleri silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.symbol_list_widget.clear()
            logging.info("🧹 Tüm hisseler temizlendi")

    def import_symbols_from_csv(self):
        """CSV'den import"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "CSV Dosyası Seç", "", "CSV Files (*.csv);;All Files (*)"
            )

            if file_path:
                df = pd.read_csv(file_path)

                symbol_col = None
                for col in df.columns:
                    if "symbol" in col.lower() or "hisse" in col.lower():
                        symbol_col = col
                        break

                if symbol_col is None:
                    symbol_col = df.columns[0]

                symbols = df[symbol_col].astype(str).str.upper().tolist()
                self.add_symbols_to_list(symbols)

                QMessageBox.information(
                    self, "Başarılı", f"{len(symbols)} hisse içe aktarıldı!"
                )

        except Exception as e:
            logging.error(f"CSV import hatası: {e}")
            QMessageBox.critical(self, "Hata", f"CSV import hatası:\n{e}")

    def add_symbols_to_list(self, symbols):
        """Sembolleri listeye ekle"""
        added = 0
        for symbol in symbols:
            items = self.symbol_list_widget.findItems(symbol, Qt.MatchExactly)
            if not items:
                self.symbol_list_widget.addItem(symbol)
                added += 1
        logging.info(f"✅ {added} hisse eklendi")

    def on_symbol_clicked(self, item):
        """Hisse tıklandığında"""
        self.symbol_selected.emit(item)

    def on_exchange_changed(self, exchange):
        """Exchange değiştiğinde"""
        # Otomatik CSV yükleme
        self.load_market_csv(exchange)
        
        self.exchange_changed.emit(exchange)

    def load_market_csv(self, exchange):
        """Exchange'e göre otomatik CSV yükle"""
        csv_map = {
            "BIST": "BIST_YILDIZ.csv",
            "NASDAQ": "NASDAQ_100.csv",
            "NYSE": "NYSE_Composite.csv",
            "CRYPTO": "CRYPTO_TOP_50.csv"
        }
        
        filename = csv_map.get(exchange)
        if not filename:
            return

        try:
            # Resource path kullanarak dosya yolunu bul
            file_path = get_resource_path(f"endexler/{filename}")
            
            # Eğer dosya yoksa normal path dene (dev ortamı için)
            if not os.path.exists(file_path):
                file_path = f"endexler/{filename}"
                
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                
                # Sembol kolonunu bul
                symbol_col = None
                for col in df.columns:
                    if "symbol" in col.lower() or "hisse" in col.lower():
                        symbol_col = col
                        break
                
                if symbol_col is None:
                    symbol_col = df.columns[0]
                
                symbols = df[symbol_col].astype(str).str.upper().tolist()
                
                # Listeyi temizle ve yenilerini ekle
                self.symbol_list_widget.clear()
                self.add_symbols_to_list(symbols)
                
                logging.info(f"✅ {exchange} için {len(symbols)} hisse yüklendi ({filename})")
            else:
                logging.warning(f"⚠️ Market dosyası bulunamadı: {file_path}")
                
        except Exception as e:
            logging.error(f"Otomatik CSV yükleme hatası: {e}")

    def get_symbols(self):
        """Tüm hisseleri al"""
        return [
            self.symbol_list_widget.item(i).text()
            for i in range(self.symbol_list_widget.count())
        ]

    def load_symbols(self, symbols):
        """Hisseleri yükle"""
        self.symbol_list_widget.clear()
        self.symbol_list_widget.addItems(symbols)

    def load_settings(self, cfg):
        """Ayarları yükle"""
        self.exchange_combo.setCurrentText(cfg.get("exchange", "BIST"))
        self.lookback_spin.setValue(cfg.get("lookback_bars", 250))
        self.load_symbols(cfg.get("symbols", []))
        
        # Eğer liste boşsa ve default BIST ise otomatik yükle
        if self.symbol_list_widget.count() == 0:
             self.load_market_csv(self.exchange_combo.currentText())

    def filter_symbols(self, text):
        """Hisse listesini filtrele"""
        text = text.upper().strip()
        
        # Eğer banka araması yapılıyorsa özel filtre (Basit örnek)
        bank_keywords = ["BANKA", "BANK"]
        is_bank_search = any(k in text for k in bank_keywords)
        
        for i in range(self.symbol_list_widget.count()):
            item = self.symbol_list_widget.item(i)
            symbol = item.text()
            
            if not text:
                item.setHidden(False)
                continue
                
            if is_bank_search:
                # Banka hisseleri için basit bir liste (Geliştirilebilir: Sektör datasından bakılabilir)
                bank_stocks = ["AKBNK", "GARAN", "ISCTR", "YKBNK", "HALKB", "VAKBN", "TSKB", "SKBNK", "ALBRK"]
                if symbol in bank_stocks:
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            else:
                # Normal arama (contains)
                if text in symbol:
                    item.setHidden(False)
                else:
                    item.setHidden(True)
