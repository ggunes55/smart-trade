# -*- coding: utf-8 -*-
"""
Settings Tab - Ayarlar sekmesi
Tarama, indikatör, sinyal ve UI ayarları
"""

import json
import logging
from typing import Dict, Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QSlider,
    QLineEdit,
    QMessageBox,
    QTabWidget,
    QScrollArea,
)
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class SettingsTab(QWidget):
    """
    Ayarlar sekmesi - Sistem konfigürasyonu
    """
    
    settings_changed = pyqtSignal(dict)  # Ayarlar değiştiğinde
    
    def __init__(self, config=None, state_manager=None, parent=None):
        super().__init__(parent)
        self.config = config or {}
        self.state_manager = state_manager
        self.settings = {}
        self.init_ui()
        self.load_settings()
        self.setup_state_subscription()
    
    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)
        
        # Başlık
        title = QLabel("⚙️ Ayarlar")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Sekmeli yapı
        tabs = QTabWidget()
        
        # Tab 1: Tarama Ayarları
        scan_tab = self._create_scan_settings()
        tabs.addTab(scan_tab, "🔍 Tarama")
        
        # Tab 2: İndikatör Ayarları
        indicator_tab = self._create_indicator_settings()
        tabs.addTab(indicator_tab, "📊 İndikatörler")
        
        # Tab 3: Sinyal Ayarları
        signal_tab = self._create_signal_settings()
        tabs.addTab(signal_tab, "🎯 Sinyaller")
        
        # Tab 4: UI Ayarları
        ui_tab = self._create_ui_settings()
        tabs.addTab(ui_tab, "🎨 Görünüm")
        
        # Tab 5: Bildirim Ayarları
        notification_tab = self._create_notification_settings()
        tabs.addTab(notification_tab, "🔔 Bildirimler")
        
        layout.addWidget(tabs)
        
        # Butonlar
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_scan_settings(self) -> QScrollArea:
        """Tarama ayarları tab'ı"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Process count
        process_layout = QHBoxLayout()
        process_layout.addWidget(QLabel("İşlem Sayısı (CPU core'ları):"))
        self.process_spin = QSpinBox()
        self.process_spin.setMinimum(1)
        self.process_spin.setMaximum(64)
        self.process_spin.setValue(8)
        process_layout.addWidget(self.process_spin)
        process_layout.addStretch()
        layout.addLayout(process_layout)
        
        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (saniye):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(5)
        self.timeout_spin.setMaximum(300)
        self.timeout_spin.setValue(30)
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)
        
        # Cache enabled
        cache_layout = QHBoxLayout()
        self.cache_checkbox = QCheckBox("Veri Cache'i Etkinleştir")
        self.cache_checkbox.setChecked(True)
        cache_layout.addWidget(self.cache_checkbox)
        cache_layout.addStretch()
        layout.addLayout(cache_layout)
        
        # Cache TTL
        ttl_layout = QHBoxLayout()
        ttl_layout.addWidget(QLabel("Cache Geçerlilik Süresi (saat):"))
        self.ttl_spin = QSpinBox()
        self.ttl_spin.setMinimum(1)
        self.ttl_spin.setMaximum(168)
        self.ttl_spin.setValue(24)
        ttl_layout.addWidget(self.ttl_spin)
        ttl_layout.addStretch()
        layout.addLayout(ttl_layout)
        
        # Auto-sync
        autosync_layout = QHBoxLayout()
        self.autosync_checkbox = QCheckBox("Otomatik Senkronizasyon")
        self.autosync_checkbox.setChecked(True)
        autosync_layout.addWidget(self.autosync_checkbox)
        autosync_layout.addStretch()
        layout.addLayout(autosync_layout)
        
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll
    
    def _create_indicator_settings(self) -> QScrollArea:
        """İndikatör ayarları tab'ı"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # RSI Period
        rsi_layout = QHBoxLayout()
        rsi_layout.addWidget(QLabel("RSI Periyodu:"))
        self.rsi_period_spin = QSpinBox()
        self.rsi_period_spin.setMinimum(5)
        self.rsi_period_spin.setMaximum(50)
        self.rsi_period_spin.setValue(14)
        rsi_layout.addWidget(self.rsi_period_spin)
        rsi_layout.addStretch()
        layout.addLayout(rsi_layout)
        
        # MACD Parameters
        macd_layout = QHBoxLayout()
        macd_layout.addWidget(QLabel("MACD Parametreleri (fast,slow,signal):"))
        self.macd_fast_spin = QSpinBox()
        self.macd_fast_spin.setValue(12)
        self.macd_slow_spin = QSpinBox()
        self.macd_slow_spin.setValue(26)
        self.macd_signal_spin = QSpinBox()
        self.macd_signal_spin.setValue(9)
        macd_layout.addWidget(self.macd_fast_spin)
        macd_layout.addWidget(self.macd_slow_spin)
        macd_layout.addWidget(self.macd_signal_spin)
        macd_layout.addStretch()
        layout.addLayout(macd_layout)
        
        # Bollinger Bands
        bb_layout = QHBoxLayout()
        bb_layout.addWidget(QLabel("Bollinger Bands Std Dev:"))
        self.bb_std_spin = QDoubleSpinBox()
        self.bb_std_spin.setMinimum(0.5)
        self.bb_std_spin.setMaximum(5.0)
        self.bb_std_spin.setSingleStep(0.1)
        self.bb_std_spin.setValue(2.0)
        bb_layout.addWidget(self.bb_std_spin)
        bb_layout.addStretch()
        layout.addLayout(bb_layout)
        
        # ATR Multiplier
        atr_layout = QHBoxLayout()
        atr_layout.addWidget(QLabel("ATR Multiplier (StopLoss):"))
        self.atr_mult_spin = QDoubleSpinBox()
        self.atr_mult_spin.setMinimum(0.5)
        self.atr_mult_spin.setMaximum(3.0)
        self.atr_mult_spin.setSingleStep(0.1)
        self.atr_mult_spin.setValue(2.0)
        atr_layout.addWidget(self.atr_mult_spin)
        atr_layout.addStretch()
        layout.addLayout(atr_layout)
        
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll
    
    def _create_signal_settings(self) -> QScrollArea:
        """Sinyal ayarları tab'ı"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Min Accuracy
        acc_layout = QHBoxLayout()
        acc_layout.addWidget(QLabel("Min. Sinyal Doğruluğu (%):"))
        self.min_accuracy_spin = QSpinBox()
        self.min_accuracy_spin.setMinimum(50)
        self.min_accuracy_spin.setMaximum(100)
        self.min_accuracy_spin.setValue(85)
        acc_layout.addWidget(self.min_accuracy_spin)
        acc_layout.addStretch()
        layout.addLayout(acc_layout)
        
        # Confirmation Count
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Sinyal Onayı Gereken İndikatör Sayısı:"))
        self.confirmation_spin = QSpinBox()
        self.confirmation_spin.setMinimum(1)
        self.confirmation_spin.setMaximum(5)
        self.confirmation_spin.setValue(2)
        conf_layout.addWidget(self.confirmation_spin)
        conf_layout.addStretch()
        layout.addLayout(conf_layout)
        
        # ML Weight
        ml_layout = QHBoxLayout()
        ml_layout.addWidget(QLabel("ML Model Ağırlığı (%):"))
        self.ml_weight_spin = QSpinBox()
        self.ml_weight_spin.setMinimum(0)
        self.ml_weight_spin.setMaximum(100)
        self.ml_weight_spin.setValue(30)
        ml_layout.addWidget(self.ml_weight_spin)
        ml_layout.addStretch()
        layout.addLayout(ml_layout)
        
        # Entry Timing
        entry_layout = QHBoxLayout()
        entry_layout.addWidget(QLabel("Giriş Zamanlaması:"))
        self.entry_combo = QComboBox()
        self.entry_combo.addItems(["Immediate", "Confirmation", "Doji Pattern"])
        entry_layout.addWidget(self.entry_combo)
        entry_layout.addStretch()
        layout.addLayout(entry_layout)
        
        # Risk/Reward Ratio
        rr_layout = QHBoxLayout()
        rr_layout.addWidget(QLabel("Min R/R Oranı:"))
        self.rr_ratio_spin = QDoubleSpinBox()
        self.rr_ratio_spin.setMinimum(1.0)
        self.rr_ratio_spin.setMaximum(5.0)
        self.rr_ratio_spin.setSingleStep(0.1)
        self.rr_ratio_spin.setValue(2.0)
        rr_layout.addWidget(self.rr_ratio_spin)
        rr_layout.addStretch()
        layout.addLayout(rr_layout)
        
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll
    
    def _create_ui_settings(self) -> QScrollArea:
        """UI ayarları tab'ı"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tema
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Tema:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light 🌞", "Dark 🌙", "Professional 💼", "Colorblind 👓"])
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        
        # Dil
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Dil:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Türkçe 🇹🇷", "English 🇬🇧", "Deutsch 🇩🇪"])
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # Font Size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Boyutu:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(8)
        self.font_size_spin.setMaximum(20)
        self.font_size_spin.setValue(11)
        font_layout.addWidget(self.font_size_spin)
        font_layout.addStretch()
        layout.addLayout(font_layout)
        
        # Window Mode
        window_layout = QHBoxLayout()
        self.fullscreen_checkbox = QCheckBox("Başlangıçta Tam Ekran")
        self.fullscreen_checkbox.setChecked(False)
        window_layout.addWidget(self.fullscreen_checkbox)
        window_layout.addStretch()
        layout.addLayout(window_layout)
        
        # Remember Window Size
        remember_layout = QHBoxLayout()
        self.remember_size_checkbox = QCheckBox("Pencere Boyutunu Hatırla")
        self.remember_size_checkbox.setChecked(True)
        remember_layout.addWidget(self.remember_size_checkbox)
        remember_layout.addStretch()
        layout.addLayout(remember_layout)
        
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll
    
    def _create_notification_settings(self) -> QScrollArea:
        """Bildirim ayarları tab'ı"""
        scroll = QScrollArea()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Signal Alerts
        signal_alert_layout = QHBoxLayout()
        self.signal_alert_checkbox = QCheckBox("Sinyal Uyarıları")
        self.signal_alert_checkbox.setChecked(True)
        signal_alert_layout.addWidget(self.signal_alert_checkbox)
        signal_alert_layout.addStretch()
        layout.addLayout(signal_alert_layout)
        
        # High Score Results
        highscore_layout = QHBoxLayout()
        self.highscore_checkbox = QCheckBox("Yüksek Skor Sonuçları")
        self.highscore_checkbox.setChecked(True)
        highscore_layout.addWidget(self.highscore_checkbox)
        highscore_layout.addStretch()
        layout.addLayout(highscore_layout)
        
        # Watchlist Updates
        watchlist_layout = QHBoxLayout()
        self.watchlist_checkbox = QCheckBox("Watchlist Güncellemeleri")
        self.watchlist_checkbox.setChecked(True)
        watchlist_layout.addWidget(self.watchlist_checkbox)
        watchlist_layout.addStretch()
        layout.addLayout(watchlist_layout)
        
        # Sound
        sound_layout = QHBoxLayout()
        self.sound_checkbox = QCheckBox("Ses Uyarısı")
        self.sound_checkbox.setChecked(True)
        sound_layout.addWidget(self.sound_checkbox)
        
        self.sound_volume_slider = QSlider(Qt.Horizontal)
        self.sound_volume_slider.setMinimum(0)
        self.sound_volume_slider.setMaximum(100)
        self.sound_volume_slider.setValue(75)
        self.sound_volume_slider.setMaximumWidth(200)
        sound_layout.addWidget(self.sound_volume_slider)
        sound_layout.addWidget(QLabel("Ses Düzeyi"))
        sound_layout.addStretch()
        layout.addLayout(sound_layout)
        
        # Toast Notifications
        toast_layout = QHBoxLayout()
        self.toast_checkbox = QCheckBox("Toast Bildirimleri")
        self.toast_checkbox.setChecked(True)
        toast_layout.addWidget(self.toast_checkbox)
        toast_layout.addStretch()
        layout.addLayout(toast_layout)
        
        layout.addStretch()
        scroll.setWidget(widget)
        return scroll
    
    def _create_button_layout(self) -> QHBoxLayout:
        """Button layout'ı"""
        layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Kaydet")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("QPushButton { padding: 8px; background-color: #4CAF50; color: white; }")
        
        apply_btn = QPushButton("✓ Uygula")
        apply_btn.clicked.connect(self.apply_settings)
        apply_btn.setStyleSheet("QPushButton { padding: 8px; background-color: #2196F3; color: white; }")
        
        reset_btn = QPushButton("↺ Varsayılanları Geri Yükle")
        reset_btn.clicked.connect(self.reset_to_defaults)
        reset_btn.setStyleSheet("QPushButton { padding: 8px; background-color: #f44336; color: white; }")
        
        layout.addWidget(save_btn)
        layout.addWidget(apply_btn)
        layout.addStretch()
        layout.addWidget(reset_btn)
        
        return layout
    
    def load_settings(self):
        """Ayarları config'den yükle"""
        # Tarama ayarları
        if hasattr(self, 'process_spin'):
            self.process_spin.setValue(
                self.config.get('process_count', 8)
            )
            self.timeout_spin.setValue(
                self.config.get('timeout_seconds', 30)
            )
            self.cache_checkbox.setChecked(
                self.config.get('enable_cache', True)
            )
        
        # İndikatör ayarları
        if hasattr(self, 'rsi_period_spin'):
            indicators = self.config.get('indicators', {})
            self.rsi_period_spin.setValue(
                indicators.get('rsi_period', 14)
            )
    
    def save_settings(self) -> bool:
        """Ayarları config'e kaydet"""
        try:
            settings = self._get_current_settings()
            
            # Config güncelle
            self.config.update(settings)
            
            # File'a kaydet (eğer config file path varsa)
            if hasattr(self.config, 'save'):
                self.config.save()
            
            logger.info("Settings saved successfully")
            QMessageBox.information(self, "Başarılı", "Ayarlar kaydedildi!")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.warning(self, "Hata", f"Ayarlar kaydedilemedi: {e}")
            return False
    
    def apply_settings(self):
        """Ayarları uygula"""
        settings = self._get_current_settings()
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "Başarılı", "Ayarlar uygulandı!")
    
    def reset_to_defaults(self):
        """Varsayılan ayarlara dön"""
        reply = QMessageBox.question(
            self, "Onayla",
            "Tüm ayarları varsayılanlarına geri yüklemek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._set_default_values()
            QMessageBox.information(self, "Başarılı", "Ayarlar varsayılanlarına geri yüklendi!")
    
    def _set_default_values(self):
        """Varsayılan değerleri ayarla"""
        if hasattr(self, 'process_spin'):
            self.process_spin.setValue(8)
            self.timeout_spin.setValue(30)
            self.cache_checkbox.setChecked(True)
        
        if hasattr(self, 'rsi_period_spin'):
            self.rsi_period_spin.setValue(14)
            self.macd_fast_spin.setValue(12)
            self.macd_slow_spin.setValue(26)
            self.macd_signal_spin.setValue(9)
        
        if hasattr(self, 'theme_combo'):
            self.theme_combo.setCurrentIndex(0)
            self.min_accuracy_spin.setValue(85)
    
    def _get_current_settings(self) -> Dict[str, Any]:
        """Mevcut ayarları dict olarak döndür"""
        return {
            'process_count': self.process_spin.value(),
            'timeout_seconds': self.timeout_spin.value(),
            'enable_cache': self.cache_checkbox.isChecked(),
            'cache_ttl_hours': self.ttl_spin.value(),
            'auto_sync': self.autosync_checkbox.isChecked(),
            'indicators': {
                'rsi_period': self.rsi_period_spin.value(),
                'macd_fast': self.macd_fast_spin.value(),
                'macd_slow': self.macd_slow_spin.value(),
                'macd_signal': self.macd_signal_spin.value(),
                'bb_std_dev': self.bb_std_spin.value(),
                'atr_multiplier': self.atr_mult_spin.value(),
            },
            'signals': {
                'min_accuracy': self.min_accuracy_spin.value(),
                'confirmation_count': self.confirmation_spin.value(),
                'ml_weight': self.ml_weight_spin.value(),
                'entry_timing': self.entry_combo.currentText(),
                'min_rr_ratio': self.rr_ratio_spin.value(),
            },
            'ui': {
                'theme': self.theme_combo.currentText().split()[0].lower(),
                'language': self.lang_combo.currentText().split()[0].lower(),
                'font_size': self.font_size_spin.value(),
                'fullscreen': self.fullscreen_checkbox.isChecked(),
                'remember_window_size': self.remember_size_checkbox.isChecked(),
            },
            'notifications': {
                'signal_alerts': self.signal_alert_checkbox.isChecked(),
                'highscore_alerts': self.highscore_checkbox.isChecked(),
                'watchlist_alerts': self.watchlist_checkbox.isChecked(),
                'sound': self.sound_checkbox.isChecked(),
                'sound_volume': self.sound_volume_slider.value(),
                'toast_notifications': self.toast_checkbox.isChecked(),
            },
        }
    
    def setup_state_subscription(self):
        """State manager'a subscribe ol"""
        if self.state_manager:
            self.state_manager.subscribe(
                'SettingsTab',
                self._on_state_change,
                keys=['settings', 'theme']
            )
    
    def _on_state_change(self, key: str, new_value, old_value):
        """State değiştiğinde"""
        if key == 'theme':
            # Tema değişirse uygulay
            self.theme_combo.blockSignals(True)
            idx = self.theme_combo.findText(new_value, Qt.MatchContains)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
            self.theme_combo.blockSignals(False)
