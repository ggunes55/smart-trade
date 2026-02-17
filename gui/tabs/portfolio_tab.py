# -*- coding: utf-8 -*-
"""
Portfolio Tab - Portföy yönetimi sekmesi
Pozisyonlar, risk metrikleri, rebalancing önerileri
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QMessageBox,
    QDialog,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QInputDialog,
    QProgressDialog,
)

logger = logging.getLogger(__name__)


class PortfolioCalculator:
    """Portfolio metrikleri hesaplayıcısı"""
    
    @staticmethod
    def calculate_metrics(positions: List[Dict]) -> Dict:
        """
        Portfolio metrikleri hesapla
        
        Args:
            positions: [{symbol, quantity, entry_price, current_price, ...}, ...]
        
        Returns:
            Metrik dict'i
        """
        if not positions:
            return {
                'total_value': 0.0,
                'total_cost': 0.0,
                'total_gain': 0.0,
                'total_gain_pct': 0.0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0.0,
                'largest_gain': 0.0,
                'largest_loss': 0.0,
                'avg_rr': 0.0,
                'correlation_avg': 0.0,
            }
        
        total_value = sum(p.get('quantity', 0) * p.get('current_price', 0) 
                         for p in positions)
        total_cost = sum(p.get('quantity', 0) * p.get('entry_price', 0) 
                        for p in positions)
        total_gain = total_value - total_cost
        total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0.0
        
        # Win/Loss sayıları
        wins = [p for p in positions if p.get('current_price', 0) > p.get('entry_price', 0)]
        losses = [p for p in positions if p.get('current_price', 0) < p.get('entry_price', 0)]
        
        win_gains = [p.get('current_price', 0) - p.get('entry_price', 0) for p in wins]
        loss_losses = [p.get('current_price', 0) - p.get('entry_price', 0) for p in losses]
        
        return {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_gain': total_gain,
            'total_gain_pct': total_gain_pct,
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_rate': (len(wins) / len(positions) * 100) if positions else 0.0,
            'largest_gain': max(win_gains) if win_gains else 0.0,
            'largest_loss': min(loss_losses) if loss_losses else 0.0,
            'position_count': len(positions),
            'avg_position_size': (total_cost / len(positions)) if positions else 0.0,
        }
    
    @staticmethod
    def suggest_rebalancing(positions: List[Dict]) -> List[Dict]:
        """
        Rebalancing önerisi (Kelly Criterion bazlı)
        
        Args:
            positions: Pozisyon listesi
        
        Returns:
            [{symbol, current_size, suggested_size, action}, ...]
        """
        metrics = PortfolioCalculator.calculate_metrics(positions)
        total_value = metrics['total_value']
        
        if total_value == 0:
            return []
        
        # Kelly Criterion: f = (p*b - q) / b
        # p = win rate, b = win/loss ratio, q = 1-p
        win_rate = metrics['win_rate'] / 100
        
        # Win/loss ratio hesapla
        if metrics['loss_count'] > 0:
            avg_win = metrics['largest_gain'] / metrics['win_count'] if metrics['win_count'] > 0 else 0
            avg_loss = abs(metrics['largest_loss']) / metrics['loss_count']
            b = avg_win / avg_loss if avg_loss > 0 else 1.0
        else:
            b = 1.0
        
        # Kelly optimal fraction
        q = 1 - win_rate
        kelly_f = (win_rate * b - q) / b if b > 0 else 0.0
        kelly_f = max(0.01, min(kelly_f, 0.25))  # Min 1%, Max 25%
        
        suggestions = []
        for position in positions:
            current_size = (position.get('quantity', 0) * position.get('current_price', 0)) / total_value
            suggested_size = kelly_f / len(positions)  # Risk parity
            
            suggestions.append({
                'symbol': position.get('symbol', 'N/A'),
                'current_size_pct': current_size * 100,
                'suggested_size_pct': suggested_size * 100,
                'action': 'HOLD',  # HOLD, BUY, SELL
                'kelly_f': kelly_f,
            })
        
        return suggestions


class PortfolioTab(QWidget):
    """Portfolio yönetimi sekmesi"""
    
    positions_updated = pyqtSignal(list)  # Pozisyonlar güncellendiğinde
    rebalance_requested = pyqtSignal(list)  # Rebalance istendiğinde
    
    def __init__(self, state_manager=None, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.positions = []
        self.metrics = {}
        self.init_ui()
        self.setup_state_subscription()
    
    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)
        
        # Başlık
        header = self._create_header()
        layout.addWidget(header)
        
        # Metrikleri Özeti
        metrics_group = self._create_metrics_summary()
        layout.addWidget(metrics_group)
        
        # Pozisyonlar Tablosu
        positions_group = self._create_positions_table()
        layout.addWidget(positions_group)
        
        # Risk Analizi
        risk_group = self._create_risk_analysis()
        layout.addWidget(risk_group)
        
        # Action Butonları
        action_group = self._create_action_buttons()
        layout.addWidget(action_group)
        
        self.setLayout(layout)
    
    def _create_header(self) -> QGroupBox:
        """Başlık grubu"""
        group = QGroupBox("📊 Portfolio Özeti")
        layout = QHBoxLayout()
        
        self.portfolio_title = QLabel("Portfolio Oluştur / Yükle")
        self.portfolio_title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        
        load_btn = QPushButton("📂 Yükle")
        load_btn.clicked.connect(self.load_portfolio)
        load_btn.setStyleSheet("QPushButton { padding: 8px; }")
        
        new_btn = QPushButton("➕ Yeni Pozisyon")
        new_btn.clicked.connect(self.add_position)
        new_btn.setStyleSheet("QPushButton { padding: 8px; background-color: #4CAF50; color: white; }")
        
        layout.addWidget(self.portfolio_title)
        layout.addStretch()
        layout.addWidget(load_btn)
        layout.addWidget(new_btn)
        
        group.setLayout(layout)
        return group
    
    def _create_metrics_summary(self) -> QGroupBox:
        """Metrikleri özet grubu"""
        group = QGroupBox("📈 Metrikler")
        layout = QHBoxLayout()
        
        # Total Value
        total_layout = QVBoxLayout()
        total_layout.addWidget(QLabel("Toplam Değer"))
        self.total_value_label = QLabel("₺ 0.00")
        self.total_value_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #1976D2;")
        total_layout.addWidget(self.total_value_label)
        layout.addLayout(total_layout)
        
        # Total Gain
        gain_layout = QVBoxLayout()
        gain_layout.addWidget(QLabel("Toplam Kazanç"))
        self.total_gain_label = QLabel("₺ 0.00 (+0.00%)")
        self.total_gain_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50;")
        gain_layout.addWidget(self.total_gain_label)
        layout.addLayout(gain_layout)
        
        # Win Rate
        wr_layout = QVBoxLayout()
        wr_layout.addWidget(QLabel("Kazanç Oranı"))
        self.win_rate_label = QLabel("0%")
        self.win_rate_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #FF9800;")
        wr_layout.addWidget(self.win_rate_label)
        layout.addLayout(wr_layout)
        
        # Position Count
        pos_layout = QVBoxLayout()
        pos_layout.addWidget(QLabel("Pozisyon Sayısı"))
        self.pos_count_label = QLabel("0")
        self.pos_count_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        pos_layout.addWidget(self.pos_count_label)
        layout.addLayout(pos_layout)
        
        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _create_positions_table(self) -> QGroupBox:
        """Pozisyonlar tablosu"""
        group = QGroupBox("💼 Pozisyonlar")
        layout = QVBoxLayout()
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(8)
        self.positions_table.setHorizontalHeaderLabels([
            "Hisse", "Miktar", "Giriş Fiyatı", "Cari Fiyat", 
            "Kazanç (₺)", "Kazanç (%)", "Yüzde", "İşlem"
        ])
        self.positions_table.setAlternatingRowColors(True)
        self.positions_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.positions_table)
        group.setLayout(layout)
        return group
    
    def _create_risk_analysis(self) -> QGroupBox:
        """Risk analizi grubu"""
        group = QGroupBox("⚠️ Risk Analizi")
        layout = QVBoxLayout()
        
        risk_info_layout = QHBoxLayout()
        
        # Correlation
        corr_layout = QVBoxLayout()
        corr_layout.addWidget(QLabel("Ort. Korelasyon"))
        self.correlation_label = QLabel("-")
        self.correlation_label.setStyleSheet("font-size: 11pt;")
        corr_layout.addWidget(self.correlation_label)
        risk_info_layout.addLayout(corr_layout)
        
        # VaR (Value at Risk)
        var_layout = QVBoxLayout()
        var_layout.addWidget(QLabel("VaR (95%)"))
        self.var_label = QLabel("-")
        self.var_label.setStyleSheet("font-size: 11pt;")
        var_layout.addWidget(self.var_label)
        risk_info_layout.addLayout(var_layout)
        
        # Max Drawdown
        md_layout = QVBoxLayout()
        md_layout.addWidget(QLabel("Maks. Düşüş"))
        self.max_drawdown_label = QLabel("-")
        self.max_drawdown_label.setStyleSheet("font-size: 11pt;")
        md_layout.addWidget(self.max_drawdown_label)
        risk_info_layout.addLayout(md_layout)
        
        layout.addLayout(risk_info_layout)
        
        # Risk Notes
        self.risk_notes = QTextEdit()
        self.risk_notes.setReadOnly(True)
        self.risk_notes.setMaximumHeight(100)
        layout.addWidget(QLabel("Risk Uyarıları:"))
        layout.addWidget(self.risk_notes)
        
        group.setLayout(layout)
        return group
    
    def _create_action_buttons(self) -> QGroupBox:
        """Action butonları grubu"""
        group = QGroupBox("🔧 İşlemler")
        layout = QHBoxLayout()
        
        optimize_btn = QPushButton("🎯 Rebalance Öner")
        optimize_btn.clicked.connect(self.suggest_rebalancing)
        optimize_btn.setStyleSheet(
            "QPushButton { padding: 8px; background-color: #FF9800; color: white; }"
        )
        
        apply_btn = QPushButton("✓ Rebalance Uygula")
        apply_btn.clicked.connect(self.apply_rebalancing)
        apply_btn.setStyleSheet(
            "QPushButton { padding: 8px; background-color: #4CAF50; color: white; }"
        )
        
        export_btn = QPushButton("📥 Excel'e Aktar")
        export_btn.clicked.connect(self.export_portfolio)
        export_btn.setStyleSheet("QPushButton { padding: 8px; }")
        
        clear_btn = QPushButton("🗑️ Temizle")
        clear_btn.clicked.connect(self.clear_portfolio)
        clear_btn.setStyleSheet(
            "QPushButton { padding: 8px; background-color: #f44336; color: white; }"
        )
        
        layout.addWidget(optimize_btn)
        layout.addWidget(apply_btn)
        layout.addWidget(export_btn)
        layout.addWidget(clear_btn)
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def update_positions(self, positions: List[Dict]):
        """Pozisyonları güncelle"""
        self.positions = positions
        self._refresh_display()
    
    def add_position(self):
        """Yeni pozisyon ekle"""
        dialog = AddPositionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            position = dialog.get_position()
            self.positions.append(position)
            self._refresh_display()
            self.positions_updated.emit(self.positions)
    
    def load_portfolio(self):
        """Portfolio yükle"""
        # TODO: CSV/JSON dosyasından yükle
        QMessageBox.information(self, "Info", "Portfolio yükleme özelliği yapılıyor...")
    
    def suggest_rebalancing(self):
        """Rebalancing önerisi göster"""
        if not self.positions:
            QMessageBox.warning(self, "Uyarı", "Pozisyon yok!")
            return
        
        suggestions = PortfolioCalculator.suggest_rebalancing(self.positions)
        
        # Rebalancing dialog'u göster
        dialog = RebalancingDialog(suggestions, self)
        dialog.exec_()
    
    def apply_rebalancing(self):
        """Rebalancing'i uygula"""
        if not self.positions:
            QMessageBox.warning(self, "Uyarı", "Pozisyon yok!")
            return
        
        suggestions = PortfolioCalculator.suggest_rebalancing(self.positions)
        self.rebalance_requested.emit(suggestions)
        QMessageBox.information(self, "Başarılı", "Rebalancing uygulandı!")
    
    def export_portfolio(self):
        """Portfolio'yu export et"""
        if not self.positions:
            QMessageBox.warning(self, "Uyarı", "Pozisyon yok!")
            return
        
        # Export işlemi yapılacak
        QMessageBox.information(self, "Info", "Excel export özelliği uygulanıyor...")
    
    def clear_portfolio(self):
        """Portfolio'yu temizle"""
        reply = QMessageBox.question(self, "Onayla", 
                                    "Tüm pozisyonları temizlemek istediğinize emin misiniz?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.positions = []
            self._refresh_display()
            self.positions_updated.emit([])
    
    def _refresh_display(self):
        """Üzeyi yenile"""
        self.metrics = PortfolioCalculator.calculate_metrics(self.positions)
        self._update_metrics_display()
        self._update_positions_table()
        self._update_risk_analysis()
    
    def _update_metrics_display(self):
        """Metrik labellerini güncelle"""
        m = self.metrics
        
        self.total_value_label.setText(f"₺ {m.get('total_value', 0):,.2f}")
        
        gain = m.get('total_gain', 0)
        gain_pct = m.get('total_gain_pct', 0)
        gain_color = "#4CAF50" if gain >= 0 else "#f44336"
        self.total_gain_label.setText(f"₺ {gain:,.2f} ({gain_pct:+.2f}%)")
        self.total_gain_label.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {gain_color};")
        
        self.win_rate_label.setText(f"{m.get('win_rate', 0):.1f}%")
        self.pos_count_label.setText(str(m.get('position_count', 0)))
    
    def _update_positions_table(self):
        """Pozisyonlar tablosunu güncelle"""
        self.positions_table.setRowCount(len(self.positions))
        total_value = self.metrics.get('total_value', 0)
        
        for row, pos in enumerate(self.positions):
            symbol = pos.get('symbol', '')
            qty = pos.get('quantity', 0)
            entry = pos.get('entry_price', 0)
            current = pos.get('current_price', 0)
            
            gain = (current - entry) * qty
            gain_pct = ((current - entry) / entry * 100) if entry > 0 else 0
            pos_value = current * qty
            pos_pct = (pos_value / total_value * 100) if total_value > 0 else 0
            
            # Tablo itemlerini ekle
            items = [
                QTableWidgetItem(symbol),
                QTableWidgetItem(f"{qty:.0f}"),
                QTableWidgetItem(f"₺ {entry:.2f}"),
                QTableWidgetItem(f"₺ {current:.2f}"),
                QTableWidgetItem(f"₺ {gain:,.2f}"),
                QTableWidgetItem(f"{gain_pct:+.2f}%"),
                QTableWidgetItem(f"{pos_pct:.1f}%"),
                QTableWidgetItem("❌"),  # Remove button
            ]
            
            # Kazanç/zarar rengi
            gain_color = QColor("#4CAF50") if gain >= 0 else QColor("#f44336")
            items[4].setForeground(gain_color)
            items[5].setForeground(gain_color)
            
            for col, item in enumerate(items):
                self.positions_table.setItem(row, col, item)
    
    def _update_risk_analysis(self):
        """Risk analizini güncelle"""
        if not self.positions:
            self.correlation_label.setText("N/A")
            self.var_label.setText("N/A")
            self.max_drawdown_label.setText("N/A")
            self.risk_notes.setText("")
            return
        
        # Basit risk analizi
        gains = [(p.get('current_price', 0) - p.get('entry_price', 0)) * p.get('quantity', 0) 
                for p in self.positions]
        
        if gains:
            max_dd = min(gains) if gains else 0
            self.max_drawdown_label.setText(f"₺ {max_dd:,.2f}")
        
        # Risk uyarıları
        risk_alerts = []
        if self.metrics.get('position_count', 0) > 10:
            risk_alerts.append("⚠️ Çok sayıda pozisyon (>10) - diversifikasyon kontrol edin")
        
        if self.metrics.get('loss_count', 0) > self.metrics.get('win_count', 0):
            risk_alerts.append("⚠️ Zarar pozisyonları kazanç pozisyonlarından fazla")
        
        self.risk_notes.setText("\n".join(risk_alerts) if risk_alerts else "✓ Tüm risk göstergeleri normal")
    
    def setup_state_subscription(self):
        """State manager'a subscribe ol"""
        if self.state_manager:
            self.state_manager.subscribe(
                'PortfolioTab',
                self._on_state_change,
                keys=['portfolio_positions', 'portfolio_metrics']
            )
    
    def _on_state_change(self, key: str, new_value, old_value):
        """State değiştiğinde"""
        if key == 'portfolio_positions':
            self.update_positions(new_value)


class AddPositionDialog(QDialog):
    """Позиция ekle dialog'u"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.position = {}
        self.init_ui()
    
    def init_ui(self):
        """UI başlangıcı"""
        self.setWindowTitle("Pozisyon Ekle")
        layout = QVBoxLayout()
        
        # Symbol
        sym_layout = QHBoxLayout()
        sym_layout.addWidget(QLabel("Hisse:"))
        self.symbol_input = QLineEdit()
        sym_layout.addWidget(self.symbol_input)
        layout.addLayout(sym_layout)
        
        # Quantity
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Miktar:"))
        self.qty_spin = QSpinBox()
        self.qty_spin.setMinimum(1)
        self.qty_spin.setMaximum(10000)
        qty_layout.addWidget(self.qty_spin)
        layout.addLayout(qty_layout)
        
        # Entry Price
        entry_layout = QHBoxLayout()
        entry_layout.addWidget(QLabel("Giriş Fiyatı:"))
        self.entry_spin = QDoubleSpinBox()
        self.entry_spin.setMinimum(0.01)
        self.entry_spin.setMaximum(100000.0)
        self.entry_spin.setDecimals(2)
        entry_layout.addWidget(self.entry_spin)
        layout.addLayout(entry_layout)
        
        # Current Price
        curr_layout = QHBoxLayout()
        curr_layout.addWidget(QLabel("Cari Fiyat:"))
        self.current_spin = QDoubleSpinBox()
        self.current_spin.setMinimum(0.01)
        self.current_spin.setMaximum(100000.0)
        self.current_spin.setDecimals(2)
        curr_layout.addWidget(self.current_spin)
        layout.addLayout(curr_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Ekle")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("İptal")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def get_position(self) -> Dict:
        """Pozisyon bilgisini döndür"""
        return {
            'symbol': self.symbol_input.text().upper(),
            'quantity': self.qty_spin.value(),
            'entry_price': self.entry_spin.value(),
            'current_price': self.current_spin.value(),
        }


class RebalancingDialog(QDialog):
    """Rebalancing önerisi dialog'u"""
    
    def __init__(self, suggestions: List[Dict], parent=None):
        super().__init__(parent)
        self.suggestions = suggestions
        self.init_ui()
    
    def init_ui(self):
        """UI başlangıcı"""
        self.setWindowTitle("Rebalancing Önerileri")
        self.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout()
        
        title = QLabel("📊 Kelly Criterion Bazlı Rebalancing Önerileri")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Öneriler tablosu
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Hisse", "Cari %", "Önerilen %", "İşlem"])
        
        for i, sugg in enumerate(self.suggestions):
            table.insertRow(i)
            table.setItem(i, 0, QTableWidgetItem(sugg.get('symbol', '')))
            table.setItem(i, 1, QTableWidgetItem(f"{sugg.get('current_size_pct', 0):.1f}%"))
            table.setItem(i, 2, QTableWidgetItem(f"{sugg.get('suggested_size_pct', 0):.1f}%"))
            table.setItem(i, 3, QTableWidgetItem(sugg.get('action', 'HOLD')))
        
        layout.addWidget(table)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Kapat")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)


from PyQt5.QtWidgets import QLineEdit
