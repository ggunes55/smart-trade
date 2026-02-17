# -*- coding: utf-8 -*-
"""
GUI Stilleri - Merkezi stil yönetimi
"""

# Ana uygulama stili
MAIN_STYLESHEET = """
    QWidget {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10pt;
    }
    QGroupBox {
        font-weight: bold;
        border: 2px solid #4CAF50;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 10px;
        background-color: #f8f9fa;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 8px;
        color: #2E7D32;
    }
    QPushButton {
        padding: 10px 15px;
        font-weight: bold;
        border-radius: 6px;
        border: 1px solid #ccc;
    }
    QPushButton:hover {
        background-color: #e9ecef;
    }
    QTableWidget {
        gridline-color: #d0d0d0;
        border: 1px solid #ddd;
    }
    QTableWidget::item:selected {
        background-color: #4CAF50;
        color: white;
    }
"""

# Başlık stilleri
TITLE_STYLE = "font-size: 16pt; font-weight: bold; color: #1976D2; padding: 10px;"

# Başarı butonu
SUCCESS_BUTTON = """
    QPushButton {
        background-color: #4CAF50;
        color: white;
        font-size: 12pt;
        padding: 12px;
    }
    QPushButton:hover {
        background-color: #45a049;
    }
"""

# Durdur butonu
STOP_BUTTON = """
    QPushButton {
        background-color: #f44336;
        color: white;
        font-size: 12pt;
        padding: 12px;
    }
    QPushButton:hover {
        background-color: #da190b;
    }
"""

# Durum etiketi
STATUS_LABEL = (
    "font-size: 11pt; padding: 10px; " "background-color: #e8f5e9; border-radius: 4px;"
)

# Exchange bilgisi
EXCHANGE_INFO = (
    "padding: 10px; background-color: #E3F2FD; " "border-radius: 4px; font-size: 9pt;"
)

# Log widget
LOG_WIDGET = "font-family: 'Courier New'; font-size: 9pt; background-color: #f5f5f5;"

# Chart label
CHART_LABEL = "border: 1px solid #ccc; background-color: #ffffff;"

# Trade details
TRADE_DETAILS = (
    "font-family: 'Courier New'; font-size: 9pt; "
    "background-color: #f0f8ff; border: 1px solid #4CAF50;"
)

# Market details
MARKET_DETAILS = "font-family: 'Segoe UI'; font-size: 10pt; background-color: #f0f8ff;"

# Yeşil buton
GREEN_BUTTON = "background-color: #4CAF50; color: white;"

# Mavi buton
BLUE_BUTTON = "background-color: #2196F3; color: white;"

# Turuncu buton
ORANGE_BUTTON = "background-color: #FF9800; color: white;"

# Kırmızı buton
RED_BUTTON = "background-color: #f44336; color: white;"
