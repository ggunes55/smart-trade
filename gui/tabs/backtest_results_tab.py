# -*- coding: utf-8 -*-
"""
Backtest Visualization - İnteraktif grafik ve istatistikler
Equity curve, Drawdown, Trade distribution, Risk metrics
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
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
    QTabWidget,
    QMessageBox,
    QProgressBar,
)
from PyQt5.QtGui import QFont, QColor

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    print("⚠️ PyQtGraph kurulu değil. Grafikler gösterilmeyecek!")

logger = logging.getLogger(__name__)


class BacktestVisualizer:
    """Backtest sonuçlarını görselleştir"""
    
    @staticmethod
    def calculate_equity_curve(trades: List[Dict]) -> tuple:
        """
        Equity curve hesapla
        
        Args:
            trades: [{date, entry_price, exit_price, quantity, ...}, ...]
        
        Returns:
            (dates, equity_values, cumulative_returns)
        """
        if not trades:
            return [], [], []
        
        df = pd.DataFrame(trades)
        
        if 'profit' not in df.columns or 'exit_date' not in df.columns:
            return [], [], []
        
        # Tarih sırasına göre sırala
        df['exit_date'] = pd.to_datetime(df['exit_date'], errors='coerce')
        df = df.dropna(subset=['exit_date']).sort_values('exit_date')
        
        if len(df) == 0:
            return [], [], []
        
        # Kümülatif kar/zarar
        df['cumulative_profit'] = df['profit'].cumsum()
        
        dates = df['exit_date'].tolist()
        equity = df['cumulative_profit'].tolist()
        returns = (df['profit_pct'] / 100).tolist()
        cumulative_returns = (1 + (df['profit_pct'] / 100)).cumprod().tolist()
        
        return dates, equity, cumulative_returns
    
    @staticmethod
    def calculate_drawdown(equity_curve: List[float]) -> tuple:
        """
        Drawdown hesapla (maximum düşüş)
        
        Args:
            equity_curve: Equity values
        
        Returns:
            (drawdown_values, max_drawdown_pct)
        """
        if not equity_curve:
            return [], 0.0
        
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max * 100
        
        max_drawdown = np.min(drawdown)
        
        return drawdown.tolist(), abs(max_drawdown)
    
    @staticmethod
    def calculate_monthly_returns(trades: List[Dict]) -> pd.DataFrame:
        """
        Aylık getiri hesapla (heatmap için)
        
        Args:
            trades: Trade listesi
        
        Returns:
            DataFrame: Year x Month matrix
        """
        if not trades:
            return pd.DataFrame()
        
        df = pd.DataFrame(trades)
        df['exit_date'] = pd.to_datetime(df['exit_date'], errors='coerce')
        df = df.dropna(subset=['exit_date'])
        
        if len(df) == 0:
            return pd.DataFrame()
        
        # Ay ve yıl ekle
        df['year'] = df['exit_date'].dt.year
        df['month'] = df['exit_date'].dt.month
        
        # Aylık getiri hesapla
        monthly = df.groupby(['year', 'month'])['profit_pct'].sum().unstack(fill_value=0)
        
        return monthly
    
    @staticmethod
    def calculate_trade_statistics(trades: List[Dict]) -> Dict:
        """
        Trade istatistikleri hesapla
        
        Args:
            trades: Trade listesi
        
        Returns:
            Dict: Komprehensif istatistikler
        """
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        
        # Sonuç analizi
        results = df.get('result', [])
        wins = len([r for r in results if r in ['WIN', 'W']])
        losses = len([r for r in results if r in ['LOSS', 'L']])
        
        # Kar/zarar
        profits = df.get('profit_pct', [])
        profit_array = np.array(profits)
        
        # Durations
        if 'duration' in df.columns:
            durations = df['duration'].tolist()
            avg_duration = np.mean(durations) if durations else 0
        else:
            avg_duration = 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': wins,
            'losing_trades': losses,
            'win_rate': (wins / len(trades) * 100) if trades else 0,
            'loss_rate': (losses / len(trades) * 100) if trades else 0,
            'avg_profit': np.mean(profit_array) if len(profit_array) > 0 else 0,
            'max_profit': np.max(profit_array) if len(profit_array) > 0 else 0,
            'min_profit': np.min(profit_array) if len(profit_array) > 0 else 0,
            'std_profit': np.std(profit_array) if len(profit_array) > 1 else 0,
            'sharpe_ratio': BacktestVisualizer._calculate_sharpe(profits),
            'profit_factor': BacktestVisualizer._calculate_profit_factor(df),
            'avg_trade_duration': avg_duration,
            'consecutive_wins': BacktestVisualizer._calc_consecutive(trades, 'WIN'),
            'consecutive_losses': BacktestVisualizer._calc_consecutive(trades, 'LOSS'),
        }
    
    @staticmethod
    def _calculate_sharpe(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Sharpe Ratio hesapla"""
        try:
            if not returns:
                return 0.0
            
            returns_array = np.array(returns) / 100
            excess_returns = returns_array - risk_free_rate / 252
            
            if len(excess_returns) > 1 and np.std(excess_returns) > 0:
                return (np.mean(excess_returns) / np.std(excess_returns)) * (252 ** 0.5)
            return 0.0
        except:
            return 0.0
    
    @staticmethod
    def _calculate_profit_factor(df: pd.DataFrame) -> float:
        """Profit Factor = Gross Profit / Gross Loss"""
        try:
            if 'profit' not in df.columns:
                return 0.0
            
            wins = df[df['profit'] > 0]['profit'].sum()
            losses = abs(df[df['profit'] < 0]['profit'].sum())
            
            if losses > 0:
                return wins / losses
            return 0.0 if wins == 0 else float('inf')
        except:
            return 0.0
    
    @staticmethod
    def _calc_consecutive(trades: List[Dict], result_type: str) -> int:
        """Ardışık win/loss sayısı"""
        try:
            results = [t.get('result', '') for t in trades]
            max_consecutive = 0
            current_consecutive = 0
            
            for result in results:
                if result in [result_type, result_type[0]]:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0
            
            return max_consecutive
        except:
            return 0


class BacktestResultsTab(QWidget):
    """Backtest sonuçları - İnteraktif görselleştirme"""
    
    def __init__(self, state_manager=None, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.backtest_data = None
        self.init_ui()
        self.setup_state_subscription()
    
    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)
        
        # Başlık
        title = QLabel("📊 Backtest Sonuçları")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Tab 1: Equity Curve
        equity_tab = self._create_equity_curve_tab()
        tabs.addTab(equity_tab, "📈 Equity Curve")
        
        # Tab 2: Drawdown
        drawdown_tab = self._create_drawdown_tab()
        tabs.addTab(drawdown_tab, "📉 Drawdown")
        
        # Tab 3: Trade Distribution
        distribution_tab = self._create_distribution_tab()
        tabs.addTab(distribution_tab, "📊 Trade Dağılımı")
        
        # Tab 4: Statistics
        stats_tab = self._create_statistics_tab()
        tabs.addTab(stats_tab, "📋 İstatistikler")
        
        # Tab 5: Monthly Returns
        monthly_tab = self._create_monthly_returns_tab()
        tabs.addTab(monthly_tab, "🗓️ Aylık Getiri")
        
        layout.addWidget(tabs)
        
        self.setLayout(layout)
    
    def _create_equity_curve_tab(self) -> QWidget:
        """Equity curve tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Grafik placeholder (PyQtGraph)
        if PYQTGRAPH_AVAILABLE:
            self.equity_plot = pg.PlotWidget(title="Kümülatif Kâr/Zarar")
            self.equity_plot.setLabel('left', 'Equity', units='TL')
            self.equity_plot.setLabel('bottom', 'Date')
            self.equity_plot.showGrid(True, True)
            self.equity_plot.addLegend()
            layout.addWidget(self.equity_plot)
        else:
            info_label = QLabel("⚠️ PyQtGraph kurulu değil. Grafikleri görmek için pip install pyqtgraph")
            layout.addWidget(info_label)
        
        # Info box
        info_group = QGroupBox("📊 Equity Curve Bilgisi")
        info_layout = QVBoxLayout()
        
        self.equity_info = QTextEdit()
        self.equity_info.setReadOnly(True)
        self.equity_info.setMaximumHeight(100)
        
        info_layout.addWidget(self.equity_info)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        return widget
    
    def _create_drawdown_tab(self) -> QWidget:
        """Drawdown tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Grafik
        if PYQTGRAPH_AVAILABLE:
            self.drawdown_plot = pg.PlotWidget(title="Drawdown Analizi")
            self.drawdown_plot.setLabel('left', 'Drawdown', units='%')
            self.drawdown_plot.setLabel('bottom', 'Date')
            self.drawdown_plot.showGrid(True, True)
            
            # Renklendirme (negatif alan kırmızı)
            self.drawdown_plot.plot([], [], pen=pg.mkPen('b', width=2))
            layout.addWidget(self.drawdown_plot)
        else:
            info_label = QLabel("⚠️ PyQtGraph kurulu değil.")
            layout.addWidget(info_label)
        
        # Max Drawdown info
        info_group = QGroupBox("⚠️ Risk Metrikleri")
        info_layout = QVBoxLayout()
        
        self.drawdown_info = QTextEdit()
        self.drawdown_info.setReadOnly(True)
        self.drawdown_info.setMaximumHeight(100)
        
        info_layout.addWidget(self.drawdown_info)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        return widget
    
    def _create_distribution_tab(self) -> QWidget:
        """Trade dağılımı tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Histogram
        if PYQTGRAPH_AVAILABLE:
            self.distribution_plot = pg.PlotWidget(title="P&L Dağılımı")
            self.distribution_plot.setLabel('left', 'Frequency')
            self.distribution_plot.setLabel('bottom', 'Profit %')
            layout.addWidget(self.distribution_plot)
        else:
            info_label = QLabel("⚠️ PyQtGraph kurulu değil.")
            layout.addWidget(info_label)
        
        return widget
    
    def _create_statistics_tab(self) -> QWidget:
        """İstatistikler tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Statistics table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metrik", "Değer"])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.stats_table)
        
        return widget
    
    def _create_monthly_returns_tab(self) -> QWidget:
        """Aylık getiri tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Monthly returns table
        self.monthly_table = QTableWidget()
        self.monthly_table.setColumnCount(12)
        self.monthly_table.setHorizontalHeaderLabels([
            "Oca", "Şub", "Mar", "Nis", "May", "Haz",
            "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"
        ])
        
        layout.addWidget(self.monthly_table)
        
        # Info
        info_label = QLabel("🗓️ Yeşil: Kar | Kırmızı: Zarar")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        return widget
    
    def display_backtest_results(self, backtest_results: Dict):
        """Backtest sonuçlarını göster"""
        self.backtest_data = backtest_results
        
        try:
            trades = backtest_results.get('trades', [])
            
            if not trades:
                QMessageBox.warning(self, "Uyarı", "Backtest sonucu yok!")
                return
            
            # Equity curve
            dates, equity, cum_returns = BacktestVisualizer.calculate_equity_curve(trades)
            self._display_equity_curve(dates, equity)
            
            # Drawdown
            drawdown_values, max_dd = BacktestVisualizer.calculate_drawdown(equity)
            self._display_drawdown(dates, drawdown_values, max_dd)
            
            # Trade distribution
            self._display_trade_distribution(trades)
            
            # Statistics
            stats = BacktestVisualizer.calculate_trade_statistics(trades)
            self._display_statistics(stats)
            
            # Monthly returns
            monthly = BacktestVisualizer.calculate_monthly_returns(trades)
            self._display_monthly_returns(monthly)
            
            logger.info("✅ Backtest sonuçları gösterildi")
            
        except Exception as e:
            logger.error(f"Backtest gösterim hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Grafik gösterim hatası: {e}")
    
    def _display_equity_curve(self, dates, equity_values):
        """Equity curve göster"""
        if not PYQTGRAPH_AVAILABLE or not equity_values:
            return
        
        try:
            self.equity_plot.clear()
            
            # X axis: Trade sayısı
            x_data = np.arange(len(equity_values))
            y_data = np.array(equity_values)
            
            # Plot
            self.equity_plot.plot(x_data, y_data, pen=pg.mkPen('b', width=2), 
                                 name='Equity Curve')
            
            # Info
            info_text = f"""
            Starting Equity: ₺ {equity_values[0]:,.2f}
            Ending Equity: ₺ {equity_values[-1]:,.2f}
            Total Profit: ₺ {equity_values[-1] - equity_values[0]:,.2f}
            Total Return: {((equity_values[-1] - equity_values[0]) / equity_values[0] * 100):.2f}%
            """
            
            self.equity_info.setText(info_text)
            
        except Exception as e:
            logger.error(f"Equity curve gösterim hatası: {e}")
    
    def _display_drawdown(self, dates, drawdown_values, max_dd):
        """Drawdown göster"""
        if not PYQTGRAPH_AVAILABLE or not drawdown_values:
            return
        
        try:
            self.drawdown_plot.clear()
            
            x_data = np.arange(len(drawdown_values))
            y_data = np.array(drawdown_values)
            
            # Plot (kırmızı renk negatif için)
            self.drawdown_plot.plot(x_data, y_data, pen=pg.mkPen('r', width=2),
                                   brush=pg.mkBrush('r', alpha=50))
            
            # Info
            info_text = f"""
            Maximum Drawdown: {max_dd:.2f}%
            
            Drawdown, stratejinin maksimum düşüş riski gösterir.
            Daha düşük drawdown daha iyi risk yönetimini belirtir.
            """
            
            self.drawdown_info.setText(info_text)
            
        except Exception as e:
            logger.error(f"Drawdown gösterim hatası: {e}")
    
    def _display_trade_distribution(self, trades):
        """Trade dağılımı göster"""
        if not PYQTGRAPH_AVAILABLE or not trades:
            return
        
        try:
            self.distribution_plot.clear()
            
            df = pd.DataFrame(trades)
            profits = df.get('profit_pct', [])
            
            if not profits:
                return
            
            # Histogram
            hist, bin_edges = np.histogram(profits, bins=20)
            
            self.distribution_plot.plot(bin_edges[:-1], hist, stepMode=True,
                                       fillLevel=0, fillBrush=pg.mkBrush('b', alpha=50),
                                       pen=pg.mkPen('b', width=2))
            
        except Exception as e:
            logger.error(f"Dağılım gösterim hatası: {e}")
    
    def _display_statistics(self, stats):
        """İstatistikleri tablo olarak göster"""
        try:
            self.stats_table.setRowCount(len(stats))
            
            row = 0
            for key, value in stats.items():
                # Key
                key_item = QTableWidgetItem(key.replace('_', ' ').title())
                key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
                self.stats_table.setItem(row, 0, key_item)
                
                # Value
                if isinstance(value, float):
                    value_text = f"{value:.2f}"
                else:
                    value_text = str(value)
                
                value_item = QTableWidgetItem(value_text)
                value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
                
                # Renklendirme
                if key == 'win_rate' and value > 50:
                    value_item.setForeground(QColor("#4CAF50"))
                elif key in ['sharpe_ratio', 'profit_factor'] and value > 1:
                    value_item.setForeground(QColor("#4CAF50"))
                
                self.stats_table.setItem(row, 1, value_item)
                row += 1
            
        except Exception as e:
            logger.error(f"İstatistik gösterim hatası: {e}")
    
    def _display_monthly_returns(self, monthly_df):
        """Aylık getiri heatmap göster"""
        try:
            if monthly_df.empty:
                return
            
            self.monthly_table.setRowCount(len(monthly_df))
            
            for row, (year, data) in enumerate(monthly_df.iterrows()):
                # Yıl başlığı
                year_item = QTableWidgetItem(str(year))
                year_item.setFlags(year_item.flags() & ~Qt.ItemIsEditable)
                self.monthly_table.setItem(row, 0, year_item)
                
                # Her ay
                for col, value in enumerate(data, start=1):
                    item = QTableWidgetItem(f"{value:.1f}%")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    
                    # Renk (heatmap)
                    if value > 0:
                        intensity = min(int(value * 2), 255)
                        item.setBackground(QColor(100, 200 + intensity, 100))
                    else:
                        intensity = min(abs(int(value * 2)), 255)
                        item.setBackground(QColor(255, 100 + intensity, 100))
                    
                    self.monthly_table.setItem(row, col, item)
            
        except Exception as e:
            logger.error(f"Aylık getiri gösterim hatası: {e}")
    
    def setup_state_subscription(self):
        """State manager'a subscribe ol"""
        if self.state_manager:
            self.state_manager.subscribe(
                'BacktestResultsTab',
                self._on_state_change,
                keys=['backtest_results']
            )
    
    def _on_state_change(self, key: str, new_value, old_value):
        """State değiştiğinde"""
        if key == 'backtest_results' and new_value:
            self.display_backtest_results(new_value)
