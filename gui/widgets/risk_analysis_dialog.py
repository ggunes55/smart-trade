# -*- coding: utf-8 -*-
"""
Risk Analysis Dialog (V3.0) - Detaylı Risk Analizi Penceresi
VaR, Bileşik Risk Skoru ve Bileşenlerini Gösterir
"""
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QProgressBar, QPushButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

class RiskAnalysisDialog(QDialog):
    """
    Hisse senedi risk analizi detaylarını gösteren pencere
    """
    def __init__(self, symbol: str, risk_data: dict, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.risk_data = risk_data or {}
        self.setWindowTitle(f"Risk Analizi Detayı: {symbol}")
        self.setMinimumSize(500, 600)
        self.setStyleSheet("background-color: #f8f9fa;")
        
        self._init_ui()
        
    def _init_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 1. Başlık ve Risk Skoru Göstergesi
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        # Risk Skoru
        score = self.risk_data.get('risk_score', 0.0)
        label = self.risk_data.get('risk_label', 'UNKNOWN')
        
        score_lbl = QLabel(f"{score:.1f} / 100")
        score_lbl.setAlignment(Qt.AlignCenter)
        score_lbl.setStyleSheet(f"""
            font-size: 32px; 
            font-weight: bold; 
            color: {self._get_score_color(score)};
        """)
        
        status_lbl = QLabel(f"RISK LEVEL: {label}")
        status_lbl.setAlignment(Qt.AlignCenter)
        status_lbl.setStyleSheet(f"""
            font-size: 14px; 
            font-weight: bold; 
            color: gray;
        """)
        
        # Progress Bar (Gauge gibi)
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(score))
        progress.setTextVisible(False)
        progress.setFixedHeight(10)
        progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #e0e0e0;
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background-color: {self._get_score_color(score)};
                border-radius: 5px;
            }}
        """)
        
        header_layout.addWidget(score_lbl)
        header_layout.addWidget(progress)
        header_layout.addWidget(status_lbl)
        
        layout.addWidget(header_frame)
        
        # 2. Risk Bileşenleri Tablosu
        comp_label = QLabel("Risk Bileşenleri")
        comp_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(comp_label)
        
        self.comp_table = QTableWidget()
        self.comp_table.setColumnCount(2)
        self.comp_table.setHorizontalHeaderLabels(["Bileşen", "Risk Puanı (0-100)"])
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.comp_table.verticalHeader().setVisible(False)
        self.comp_table.setStyleSheet("background-color: white;")
        
        components = self.risk_data.get('components', {})
        self._populate_components(components)
        
        layout.addWidget(self.comp_table)
        
        # 3. Metrikler (VaR, CVaR vb.)
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("background-color: white; border-radius: 5px; padding: 10px;")
        metrics_layout = QVBoxLayout(metrics_frame)
        
        metrics = [
            ("Value at Risk (95%)", f"{self.risk_data.get('var_95', 0):.2f}%"),
            ("Expected Shortfall (CVaR)", f"{self.risk_data.get('cvar_95', 0):.2f}%"),
            ("Max Drawdown", f"{self.risk_data.get('max_drawdown_pct', 0):.2f}%"),
            ("Yıllık Volatilite", f"{self.risk_data.get('annual_volatility_pct', 0):.2f}%")
        ]
        
        for name, value in metrics:
            row = QHBoxLayout()
            name_lbl = QLabel(name)
            val_lbl = QLabel(value)
            val_lbl.setStyleSheet("font-weight: bold;")
            row.addWidget(name_lbl)
            row.addStretch()
            row.addWidget(val_lbl)
            metrics_layout.addLayout(row)
            
        layout.addWidget(metrics_frame)
        
        # Kapat butonu
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        layout.addWidget(close_btn)
        
    def _populate_components(self, components):
        """Bileşen tablosunu doldur"""
        mapping = {
            'volatility_risk': 'Volatilite Riski',
            'drawdown_risk': 'Zirveden Düşüş (Drawdown)',
            'tail_risk': 'Kuyruk Riski (VaR)',
            'liquidity_risk': 'Likidite Riski',
            'momentum_risk': 'Trend/Momentum Riski'
        }
        
        self.comp_table.setRowCount(len(mapping))
        
        for i, (key, label) in enumerate(mapping.items()):
            val = components.get(key, 0.0)
            
            # Ad
            self.comp_table.setItem(i, 0, QTableWidgetItem(label))
            
            # Değer
            item = QTableWidgetItem(f"{val:.1f}")
            item.setTextAlignment(Qt.AlignCenter)
            
            # Renklendirme
            color = self._get_score_color(val)
            item.setForeground(QColor(color))
            item.setFont(QFont("Arial", 10, QFont.Bold))
            
            self.comp_table.setItem(i, 1, item)
            
    def _get_score_color(self, score):
        """0-100 arası skora göre renk döndür"""
        if score >= 75: return "#c0392b"  # Kırmızı (Critical)
        if score >= 50: return "#e67e22"  # Turuncu (High)
        if score >= 25: return "#f1c40f"  # Sarı (Medium)
        return "#27ae60"              # Yeşil (Low)
