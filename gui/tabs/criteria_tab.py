# -*- coding: utf-8 -*-
"""
Criteria Tab - Kriter ayarları sekmesi
"""
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QDoubleSpinBox,
    QCheckBox,
    QScrollArea,
    QComboBox,
    QFrame,
)
from PyQt5.QtCore import pyqtSignal


class CriteriaTab(QWidget):
    """Kriter ayarları sekmesi"""
    
    # 🆕 Filter mode değiştiğinde sinyal gönder
    filter_mode_changed = pyqtSignal(str)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.spin_widgets = {}
        self.check_widgets = {}
        self.filter_mode_combo = None
        self.init_ui()

    def init_ui(self):
        """UI başlangıcı"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)

        # 🆕 Filtre modu seçimi (EN ÜSTTE)
        filter_mode_group = self._create_filter_mode_group()
        layout.addWidget(filter_mode_group)

        # Sayısal kriterler
        numeric_group = self._create_numeric_group()
        layout.addWidget(numeric_group)
        self.numeric_group = numeric_group  # Referans tut

        # Checkbox kriterler
        check_group = self._create_check_group()
        layout.addWidget(check_group)
        self.check_group = check_group  # Referans tut

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        
        # 🆕 Başlangıçta auto mode aktifse manuel kontrolleri devre dışı bırak
        self._update_widgets_state()

    def _create_filter_mode_group(self):
        """🆕 Filtre modu seçim grubu"""
        group = QGroupBox("🎛️ Filtreleme Modu")
        layout = QVBoxLayout()
        
        # Açıklama
        info_label = QLabel(
            "💡 <b>Otomatik:</b> Exchange'e özgü optimize değerler | "
            "<b>Manuel:</b> Aşağıdaki değerleri kullan"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        layout.addWidget(info_label)
        
        # Dropdown
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Filtre Modu:")
        mode_label.setMinimumWidth(120)
        
        self.filter_mode_combo = QComboBox()
        self.filter_mode_combo.addItems([
            "🤖 Otomatik (Exchange'e Özgü)",
            "⚙️ Manuel (Aşağıdaki Değerler)"
        ])
        
        # Config'den modu yükle (varsayılan: auto)
        current_mode = self.cfg.get("filter_mode", "auto")
        self.filter_mode_combo.setCurrentIndex(0 if current_mode == "auto" else 1)
        
        self.filter_mode_combo.currentIndexChanged.connect(self._on_filter_mode_changed)
        self.filter_mode_combo.setMinimumWidth(250)
        self.filter_mode_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                font-size: 13px;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                background-color: #d6d4d4;
            }
            QComboBox:hover {
                border-color: #66BB6A;
            }
        """)
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.filter_mode_combo)
        mode_layout.addStretch()
        
        layout.addLayout(mode_layout)
        
        # Ayırıcı çizgi
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #444;")
        layout.addWidget(line)
        
        group.setLayout(layout)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        return group
    
    def _on_filter_mode_changed(self, index):
        """🆕 Filtre modu değiştiğinde"""
        mode = "auto" if index == 0 else "manual"
        self._update_widgets_state()
        self.filter_mode_changed.emit(mode)
    
    def _update_widgets_state(self):
        """🆕 Mod'a göre widget'ları aktif/pasif yap"""
        is_auto = self.filter_mode_combo.currentIndex() == 0
        
        # Sayısal kriterler
        for spin in self.spin_widgets.values():
            spin.setEnabled(not is_auto)
            if is_auto:
                spin.setStyleSheet("background-color: #d6d4d4; color: #666;")
            else:
                spin.setStyleSheet("")
        
        # Checkbox kriterler  
        for cb in self.check_widgets.values():
            cb.setEnabled(not is_auto)
            if is_auto:
                cb.setStyleSheet("color: #666;")
            else:
                cb.setStyleSheet("padding: 5px;")

    def _create_numeric_group(self):
        """Sayısal kriterler grubu"""
        group = QGroupBox("📈 Sayısal Kriterler (Manuel Mod)")
        layout = QVBoxLayout()

        numeric_settings = [
            ("Min RSI", "min_rsi", 0, 100, 1, 30),
            ("Max RSI", "max_rsi", 0, 100, 1, 70),
            ("Min Göreceli Hacim", "min_relative_volume", 0.1, 10.0, 0.1, 1.0),
            ("Max Günlük Değişim %", "max_daily_change_pct", 0, 20.0, 0.5, 8.0),
            ("Min Trend Skoru", "min_trend_score", 0, 100, 5, 50),
            ("Min Likidite Oranı", "min_liquidity_ratio", 0.1, 5.0, 0.1, 0.5),
            ("Min Hacim Patlaması", "min_volume_surge", 1.0, 5.0, 0.1, 1.2),
            ("Min Yükselen Dipler", "min_higher_lows", 0, 10, 1, 2),
        ]

        for label, key, min_val, max_val, step, default in numeric_settings:
            row_layout = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(200)
            spin = QDoubleSpinBox()
            spin.setRange(min_val, max_val)
            spin.setSingleStep(step)
            spin.setValue(self.cfg.get(key, default))
            spin.setMinimumWidth(100)

            row_layout.addWidget(lbl)
            row_layout.addWidget(spin)
            row_layout.addStretch()

            layout.addLayout(row_layout)
            self.spin_widgets[key] = spin

        group.setLayout(layout)
        return group

    def _create_check_group(self):
        """Checkbox kriterler grubu"""
        group = QGroupBox("✅ Aktif/Pasif Kriterler (Manuel Mod)")
        layout = QVBoxLayout()

        check_settings = [
            ("🔵 Fiyat EMA20 Üstünde", "price_above_ema20"),
            ("🟢 Fiyat EMA50 Üstünde", "price_above_ema50"),
            ("📈 MACD Pozitif", "macd_positive"),
            ("💪 ADX Kontrolü", "check_adx"),
            ("💰 Kurumsal Akış Kontrolü", "check_institutional_flow"),
            ("📊 Momentum Uyumsuzluk Kontrolü", "check_momentum_divergence"),
        ]

        for label, key in check_settings:
            cb = QCheckBox(label)
            cb.setChecked(self.cfg.get(key, True))
            cb.setStyleSheet("padding: 5px;")
            layout.addWidget(cb)
            self.check_widgets[key] = cb

        group.setLayout(layout)
        return group

    def get_settings(self):
        """Tüm ayarları al"""
        settings = {}

        # 🆕 Filtre modu
        settings["filter_mode"] = "auto" if self.filter_mode_combo.currentIndex() == 0 else "manual"

        # Sayısal değerler
        for key, spin in self.spin_widgets.items():
            settings[key] = spin.value()

        # Checkbox değerler
        for key, cb in self.check_widgets.items():
            settings[key] = cb.isChecked()

        return settings

    def load_settings(self, cfg):
        """Ayarları yükle"""
        # 🆕 Filtre modu
        if self.filter_mode_combo:
            mode = cfg.get("filter_mode", "auto")
            self.filter_mode_combo.setCurrentIndex(0 if mode == "auto" else 1)
            self._update_widgets_state()
        
        for key, spin in self.spin_widgets.items():
            spin.setValue(cfg.get(key, spin.value()))

        for key, cb in self.check_widgets.items():
            cb.setChecked(cfg.get(key, True))

