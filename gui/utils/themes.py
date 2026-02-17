# -*- coding: utf-8 -*-
"""
Themes System - Tema yönetim sistemi
Light, Dark, Professional, Colorblind temalar
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ThemeManager:
    """Tema yöneticisi"""
    
    THEMES = {
        'light': 'LIGHT_THEME',
        'dark': 'DARK_THEME',
        'professional': 'PROFESSIONAL_THEME',
        'colorblind': 'COLORBLIND_THEME',
    }
    
    def __init__(self, default_theme: str = 'light'):
        """
        ThemeManager'ı başlat
        
        Args:
            default_theme: Varsayılan tema ('light', 'dark', 'professional', 'colorblind')
        """
        self.current_theme = default_theme
        self.callbacks = []
    
    def register_theme_change_callback(self, callback):
        """Tema değişim callback'i ekle"""
        self.callbacks.append(callback)
    
    def set_theme(self, theme_name: str) -> bool:
        """
        Temayı ayarla
        
        Args:
            theme_name: Tema adı
        
        Returns:
            bool: Başarılı mı?
        """
        if theme_name not in self.THEMES:
            logger.warning(f"Unknown theme: {theme_name}")
            return False
        
        self.current_theme = theme_name
        
        # Callbacks'i çalıştır
        for callback in self.callbacks:
            try:
                callback(theme_name)
            except Exception as e:
                logger.error(f"Error in theme callback: {e}")
        
        logger.info(f"Theme changed to: {theme_name}")
        return True
    
    def get_stylesheet(self) -> str:
        """Mevcut tema için stylesheet al"""
        theme_map = {
            'light': LIGHT_THEME,
            'dark': DARK_THEME,
            'professional': PROFESSIONAL_THEME,
            'colorblind': COLORBLIND_THEME,
        }
        
        return theme_map.get(self.current_theme, LIGHT_THEME)


# ============ LIGHT THEME ============
LIGHT_THEME = """
QWidget {
    background-color: #FFFFFF;
    color: #000000;
}

QMainWindow {
    background-color: #FFFFFF;
}

QGroupBox {
    border: 2px solid #CCCCCC;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QTabWidget::pane {
    border: 1px solid #CCCCCC;
}

QTabBar::tab {
    background-color: #E8E8E8;
    color: #000000;
    padding: 8px 20px;
    margin: 2px;
    border: 1px solid #CCCCCC;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #1976D2;
    color: #FFFFFF;
    border: 1px solid #1976D2;
}

QPushButton {
    background-color: #E8E8E8;
    color: #000000;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #D0D0D0;
}

QPushButton:pressed {
    background-color: #B0B0B0;
}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #F5F5F5;
    color: #000000;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 4px;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
    border: 2px solid #1976D2;
}

QTableWidget {
    background-color: #FFFFFF;
    color: #000000;
    alternate-background-color: #F5F5F5;
    border: 1px solid #CCCCCC;
}

QTableWidget::item:selected {
    background-color: #1976D2;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #E8E8E8;
    color: #000000;
    padding: 4px;
    border: 1px solid #CCCCCC;
}

QLabel {
    color: #000000;
}

QCheckBox {
    color: #000000;
    spacing: 5px;
}

QComboBox {
    background-color: #F5F5F5;
    color: #000000;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 4px;
}

QProgressBar {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    text-align: center;
    background-color: #E8E8E8;
}

QProgressBar::chunk {
    background-color: #4CAF50;
}

QSlider::groove:horizontal {
    border: 1px solid #CCCCCC;
    height: 8px;
    background: #E8E8E8;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #1976D2;
    border: 1px solid #1976D2;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}
"""

# ============ DARK THEME ============
DARK_THEME = """
QWidget {
    background-color: #1E1E1E;
    color: #E0E0E0;
}

QMainWindow {
    background-color: #1E1E1E;
}

QGroupBox {
    border: 2px solid #404040;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #E0E0E0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QTabWidget::pane {
    border: 1px solid #404040;
}

QTabBar::tab {
    background-color: #2D2D2D;
    color: #E0E0E0;
    padding: 8px 20px;
    margin: 2px;
    border: 1px solid #404040;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #00BCD4;
    color: #000000;
    border: 1px solid #00BCD4;
}

QPushButton {
    background-color: #2D2D2D;
    color: #E0E0E0;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #3D3D3D;
}

QPushButton:pressed {
    background-color: #404040;
}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #2D2D2D;
    color: #E0E0E0;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 4px;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
    border: 2px solid #00BCD4;
}

QTableWidget {
    background-color: #1E1E1E;
    color: #E0E0E0;
    alternate-background-color: #2D2D2D;
    border: 1px solid #404040;
}

QTableWidget::item:selected {
    background-color: #00BCD4;
    color: #000000;
}

QHeaderView::section {
    background-color: #2D2D2D;
    color: #E0E0E0;
    padding: 4px;
    border: 1px solid #404040;
}

QLabel {
    color: #E0E0E0;
}

QCheckBox {
    color: #E0E0E0;
    spacing: 5px;
}

QComboBox {
    background-color: #2D2D2D;
    color: #E0E0E0;
    border: 1px solid #404040;
    border-radius: 4px;
    padding: 4px;
}

QComboBox::drop-down {
    background-color: #2D2D2D;
}

QProgressBar {
    border: 1px solid #404040;
    border-radius: 4px;
    text-align: center;
    background-color: #2D2D2D;
}

QProgressBar::chunk {
    background-color: #00BCD4;
}

QSlider::groove:horizontal {
    border: 1px solid #404040;
    height: 8px;
    background: #2D2D2D;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #00BCD4;
    border: 1px solid #00BCD4;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}

QScrollBar:vertical {
    border: 1px solid #404040;
    background-color: #1E1E1E;
    width: 15px;
}

QScrollBar::handle:vertical {
    background-color: #404040;
    border-radius: 7px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #505050;
}
"""

# ============ PROFESSIONAL THEME ============
PROFESSIONAL_THEME = """
QWidget {
    background-color: #0A0E27;
    color: #E0E0E0;
}

QMainWindow {
    background-color: #0A0E27;
}

QGroupBox {
    border: 1px solid #00AA66;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #00FF99;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QTabWidget::pane {
    border: 1px solid #00AA66;
}

QTabBar::tab {
    background-color: #0F1636;
    color: #00FF99;
    padding: 8px 20px;
    margin: 2px;
    border: 1px solid #00AA66;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #00AA66;
    color: #000000;
    border: 1px solid #00FF99;
}

QPushButton {
    background-color: #0F1636;
    color: #00FF99;
    border: 1px solid #00AA66;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #00AA66;
    color: #000000;
    border: 1px solid #00FF99;
}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #0F1636;
    color: #00FF99;
    border: 1px solid #00AA66;
    border-radius: 4px;
    padding: 4px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 2px solid #00FF99;
}

QTableWidget {
    background-color: #0A0E27;
    color: #00FF99;
    alternate-background-color: #0F1636;
    border: 1px solid #00AA66;
}

QTableWidget::item:selected {
    background-color: #00AA66;
    color: #000000;
}

QHeaderView::section {
    background-color: #0F1636;
    color: #00FF99;
    padding: 4px;
    border: 1px solid #00AA66;
}

QLabel {
    color: #00FF99;
}

QCheckBox {
    color: #00FF99;
    spacing: 5px;
}

QComboBox {
    background-color: #0F1636;
    color: #00FF99;
    border: 1px solid #00AA66;
    border-radius: 4px;
    padding: 4px;
}

QProgressBar {
    border: 1px solid #00AA66;
    border-radius: 4px;
    text-align: center;
    background-color: #0F1636;
}

QProgressBar::chunk {
    background-color: #00FF99;
}

QSlider::groove:horizontal {
    border: 1px solid #00AA66;
    height: 8px;
    background: #0F1636;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #00FF99;
    border: 1px solid #00AA66;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}
"""

# ============ COLORBLIND THEME ============
COLORBLIND_THEME = """
QWidget {
    background-color: #FFFFFF;
    color: #000000;
}

QMainWindow {
    background-color: #FFFFFF;
}

QGroupBox {
    border: 3px solid #000000;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QTabWidget::pane {
    border: 2px solid #000000;
}

QTabBar::tab {
    background-color: #EEEEEE;
    color: #000000;
    padding: 8px 20px;
    margin: 2px;
    border: 2px solid #000000;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background-color: #000000;
    color: #FFFFFF;
    border: 2px solid #000000;
}

QPushButton {
    background-color: #EEEEEE;
    color: #000000;
    border: 2px solid #000000;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #CCCCCC;
    border: 2px solid #000000;
}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #F5F5F5;
    color: #000000;
    border: 2px solid #000000;
    border-radius: 4px;
    padding: 4px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 3px solid #000000;
    background-color: #FFFFCC;
}

QTableWidget {
    background-color: #FFFFFF;
    color: #000000;
    alternate-background-color: #F5F5F5;
    border: 2px solid #000000;
}

QTableWidget::item:selected {
    background-color: #CCCCCC;
    color: #000000;
}

QHeaderView::section {
    background-color: #000000;
    color: #FFFFFF;
    padding: 4px;
    border: 2px solid #000000;
    font-weight: bold;
}

QLabel {
    color: #000000;
}

QCheckBox {
    color: #000000;
    spacing: 5px;
}

QComboBox {
    background-color: #F5F5F5;
    color: #000000;
    border: 2px solid #000000;
    border-radius: 4px;
    padding: 4px;
    font-weight: bold;
}

QProgressBar {
    border: 2px solid #000000;
    border-radius: 4px;
    text-align: center;
    background-color: #EEEEEE;
}

QProgressBar::chunk {
    background-color: #000000;
}

QSlider::groove:horizontal {
    border: 2px solid #000000;
    height: 8px;
    background: #EEEEEE;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #000000;
    border: 2px solid #000000;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}
"""


def apply_theme(app, theme_name: str = 'light'):
    """
    Uygulamaya tema uygula
    
    Args:
        app: QApplication instance
        theme_name: Tema adı
    """
    theme_manager = ThemeManager(theme_name)
    stylesheet = theme_manager.get_stylesheet()
    app.setStyleSheet(stylesheet)
    logger.info(f"Theme applied: {theme_name}")
    return theme_manager
