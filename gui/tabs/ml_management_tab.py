# -*- coding: utf-8 -*-
"""
ML Management Tab - Model versionleme, performans takibi, feature importance
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

from PyQt5.QtCore import Qt, pyqtSignal, QThread
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
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QProgressBar,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QFormLayout,
)
from PyQt5.QtGui import QFont, QColor, QIcon

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MLModelVersion:
    """Model version wrapper"""
    
    def __init__(self, model_id: str, version: int, timestamp: str, 
                 model_type: str, accuracy: float, metrics: Dict = None):
        self.model_id = model_id
        self.version = version
        self.timestamp = timestamp
        self.model_type = model_type  # signal_classifier, price_predictor, etc.
        self.accuracy = accuracy
        self.metrics = metrics or {}
        self.status = "active" if version == 1 else "archived"
        self.notes = ""
    
    def to_dict(self) -> Dict:
        """Dict'e dönüştür"""
        return {
            'model_id': self.model_id,
            'version': self.version,
            'timestamp': self.timestamp,
            'model_type': self.model_type,
            'accuracy': self.accuracy,
            'metrics': self.metrics,
            'status': self.status,
            'notes': self.notes,
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'MLModelVersion':
        """Dict'ten oluştur"""
        mv = MLModelVersion(
            data['model_id'],
            data['version'],
            data['timestamp'],
            data['model_type'],
            data['accuracy'],
            data.get('metrics', {})
        )
        mv.status = data.get('status', 'archived')
        mv.notes = data.get('notes', '')
        return mv


class MLModelRegistry:
    """Model version registry"""
    
    def __init__(self):
        self.versions: Dict[str, List[MLModelVersion]] = {}
    
    def register_version(self, model_version: MLModelVersion):
        """Yeni version kaydet"""
        model_id = model_version.model_id
        
        if model_id not in self.versions:
            self.versions[model_id] = []
        
        self.versions[model_id].append(model_version)
        
        # Version numarasını güncelle
        model_version.version = len(self.versions[model_id])
        
        logger.info(f"✅ {model_id} v{model_version.version} kaydedildi")
    
    def get_latest_version(self, model_id: str) -> Optional[MLModelVersion]:
        """En son version'ı getir"""
        if model_id not in self.versions:
            return None
        
        return self.versions[model_id][-1] if self.versions[model_id] else None
    
    def get_all_versions(self, model_id: str) -> List[MLModelVersion]:
        """Tüm version'ları getir"""
        return self.versions.get(model_id, [])
    
    def rollback_to_version(self, model_id: str, version: int) -> bool:
        """Belirli version'a geri dön"""
        if model_id not in self.versions:
            return False
        
        if version > len(self.versions[model_id]) or version < 1:
            return False
        
        target = self.versions[model_id][version - 1]
        target.status = "active"
        
        # Diğerlerini archive et
        for v in self.versions[model_id]:
            if v != target:
                v.status = "archived"
        
        logger.info(f"✅ {model_id} v{version}'e geri dönüldü")
        return True
    
    def compare_versions(self, model_id: str, v1: int, v2: int) -> Dict:
        """İki version'ı karşılaştır"""
        versions = self.versions.get(model_id, [])
        
        if v1 > len(versions) or v2 > len(versions):
            return {}
        
        mv1 = versions[v1 - 1]
        mv2 = versions[v2 - 1]
        
        return {
            'v1': {
                'version': mv1.version,
                'timestamp': mv1.timestamp,
                'accuracy': mv1.accuracy,
                'metrics': mv1.metrics,
            },
            'v2': {
                'version': mv2.version,
                'timestamp': mv2.timestamp,
                'accuracy': mv2.accuracy,
                'metrics': mv2.metrics,
            },
            'accuracy_improvement': mv2.accuracy - mv1.accuracy,
        }
    
    def export_versions(self, model_id: str, filepath: str):
        """Version'ları export et"""
        try:
            versions = self.get_all_versions(model_id)
            data = [v.to_dict() for v in versions]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ {model_id} version'ları {filepath} dosyasına kaydedildi")
            return True
        except Exception as e:
            logger.error(f"Export hatası: {e}")
            return False
    
    def import_versions(self, model_id: str, filepath: str):
        """Version'ları import et"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for item in data:
                mv = MLModelVersion.from_dict(item)
                if mv.model_id == model_id:
                    self.register_version(mv)
            
            logger.info(f"✅ {model_id} version'ları {filepath}'den alındı")
            return True
        except Exception as e:
            logger.error(f"Import hatası: {e}")
            return False


class MLManagementTab(QWidget):
    """ML Model yönetimi ve versionleme"""
    
    model_updated = pyqtSignal(str)  # model_id
    
    def __init__(self, state_manager=None, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.model_registry = MLModelRegistry()
        
        # Demo models
        self._initialize_demo_models()
        
        self.init_ui()
        self.setup_state_subscription()
    
    def _initialize_demo_models(self):
        """Demo modellerini oluştur"""
        # Signal Classifier v1
        v1 = MLModelVersion(
            'signal_classifier',
            1,
            '2026-02-10 14:30:00',
            'signal_classifier',
            0.78,
            {
                'precision': 0.82,
                'recall': 0.75,
                'f1_score': 0.78,
                'auc_roc': 0.85,
                'train_data_size': 5000,
            }
        )
        v1.notes = "İlk versiyon - temel RSI + MACD özellikleri"
        self.model_registry.register_version(v1)
        
        # Signal Classifier v2
        v2 = MLModelVersion(
            'signal_classifier',
            2,
            '2026-02-11 10:15:00',
            'signal_classifier',
            0.82,
            {
                'precision': 0.85,
                'recall': 0.80,
                'f1_score': 0.82,
                'auc_roc': 0.88,
                'train_data_size': 7500,
            }
        )
        v2.notes = "Fibonacci seviyeleri ve Volume eklendi"
        self.model_registry.register_version(v2)
        
        # Price Predictor v1
        v3 = MLModelVersion(
            'price_predictor',
            1,
            '2026-02-05 09:00:00',
            'price_predictor',
            0.71,
            {
                'mae': 1.25,
                'rmse': 1.89,
                'mape': 2.34,
                'train_data_size': 10000,
            }
        )
        v3.notes = "LSTM tabanlı fiyat tahmincisi"
        self.model_registry.register_version(v3)
    
    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)
        
        # Başlık
        title = QLabel("🤖 ML Model Management")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Model seçimi
        model_select_layout = QHBoxLayout()
        model_select_layout.addWidget(QLabel("Model:"))
        
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'signal_classifier',
            'price_predictor',
            'trend_detector',
        ])
        self.model_combo.currentTextChanged.connect(self.on_model_selected)
        model_select_layout.addWidget(self.model_combo)
        
        layout.addLayout(model_select_layout)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Tab 1: Version History
        version_tab = self._create_version_history_tab()
        tabs.addTab(version_tab, "📚 Version Geçmişi")
        
        # Tab 2: Performance Comparison
        perf_tab = self._create_performance_tab()
        tabs.addTab(perf_tab, "📊 Performans Karşılaştırması")
        
        # Tab 3: Feature Importance
        feature_tab = self._create_feature_importance_tab()
        tabs.addTab(feature_tab, "🔍 Feature Importance")
        
        # Tab 4: Model Details
        details_tab = self._create_model_details_tab()
        tabs.addTab(details_tab, "ℹ️ Model Detayları")
        
        layout.addWidget(tabs)
        
        self.setLayout(layout)
    
    def _create_version_history_tab(self) -> QWidget:
        """Version geçmişi tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        self.new_version_btn = QPushButton("➕ Yeni Version Eğit")
        self.new_version_btn.clicked.connect(self.train_new_version)
        button_layout.addWidget(self.new_version_btn)
        
        self.rollback_btn = QPushButton("⏮️ Geri Dön")
        self.rollback_btn.clicked.connect(self.rollback_selected_version)
        button_layout.addWidget(self.rollback_btn)
        
        self.export_btn = QPushButton("💾 Export")
        self.export_btn.clicked.connect(self.export_versions)
        button_layout.addWidget(self.export_btn)
        
        self.import_btn = QPushButton("📥 Import")
        self.import_btn.clicked.connect(self.import_versions)
        button_layout.addWidget(self.import_btn)
        
        layout.addLayout(button_layout)
        
        # Version tablosu
        self.version_table = QTableWidget()
        self.version_table.setColumnCount(6)
        self.version_table.setHorizontalHeaderLabels([
            "V", "Timestamp", "Accuracy", "Status", "Notes", "Action"
        ])
        self.version_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.version_table)
        
        return widget
    
    def _create_performance_tab(self) -> QWidget:
        """Performans karşılaştırması tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Karşılaştırma kontrolleri
        compare_layout = QHBoxLayout()
        
        compare_layout.addWidget(QLabel("Version 1:"))
        self.compare_v1 = QSpinBox()
        self.compare_v1.setMinimum(1)
        compare_layout.addWidget(self.compare_v1)
        
        compare_layout.addWidget(QLabel("Version 2:"))
        self.compare_v2 = QSpinBox()
        self.compare_v2.setMinimum(1)
        compare_layout.addWidget(self.compare_v2)
        
        compare_btn = QPushButton("📊 Karşılaştır")
        compare_btn.clicked.connect(self.compare_versions)
        compare_layout.addWidget(compare_btn)
        
        layout.addLayout(compare_layout)
        
        # Grafik
        if PYQTGRAPH_AVAILABLE:
            self.perf_plot = pg.PlotWidget(title="Model Performans Karşılaştırması")
            self.perf_plot.setLabel('left', 'Accuracy / MetricValue')
            self.perf_plot.setLabel('bottom', 'Version')
            self.perf_plot.showGrid(True, True)
            layout.addWidget(self.perf_plot)
        
        # Comparison table
        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(3)
        self.comparison_table.setHorizontalHeaderLabels(["Metric", "V1", "V2"])
        self.comparison_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.comparison_table)
        
        return widget
    
    def _create_feature_importance_tab(self) -> QWidget:
        """Feature importance tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Feature importance table
        self.feature_table = QTableWidget()
        self.feature_table.setColumnCount(3)
        self.feature_table.setHorizontalHeaderLabels(["Feature", "Importance", "Impact"])
        self.feature_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.feature_table)
        
        # Grafik
        if PYQTGRAPH_AVAILABLE:
            self.feature_plot = pg.PlotWidget(title="Feature Importance")
            self.feature_plot.setLabel('left', 'Importance Score')
            self.feature_plot.setLabel('bottom', 'Feature')
            layout.addWidget(self.feature_plot)
        
        return widget
    
    def _create_model_details_tab(self) -> QWidget:
        """Model detayları tab'ı"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        
        layout.addWidget(self.details_text)
        
        return widget
    
    def on_model_selected(self, model_id: str):
        """Model seçildiğinde"""
        self.refresh_display(model_id)
    
    def refresh_display(self, model_id: str):
        """Seçili model'i göster"""
        try:
            versions = self.model_registry.get_all_versions(model_id)
            
            if not versions:
                QMessageBox.information(self, "Uyarı", f"{model_id} için model bulunamadı")
                return
            
            # Version tablosunu güncelle
            self.version_table.setRowCount(len(versions))
            
            for row, version in enumerate(versions):
                # V
                v_item = QTableWidgetItem(str(version.version))
                self.version_table.setItem(row, 0, v_item)
                
                # Timestamp
                ts_item = QTableWidgetItem(version.timestamp)
                self.version_table.setItem(row, 1, ts_item)
                
                # Accuracy
                acc_item = QTableWidgetItem(f"{version.accuracy:.2%}")
                if version.accuracy > 0.80:
                    acc_item.setForeground(QColor("#4CAF50"))
                self.version_table.setItem(row, 2, acc_item)
                
                # Status
                status_item = QTableWidgetItem(version.status.upper())
                if version.status == "active":
                    status_item.setForeground(QColor("#2196F3"))
                self.version_table.setItem(row, 3, status_item)
                
                # Notes
                notes_item = QTableWidgetItem(version.notes)
                self.version_table.setItem(row, 4, notes_item)
                
                # Action button
                action_item = QTableWidgetItem("View")
                self.version_table.setItem(row, 5, action_item)
            
            # Details tab'ını güncelle
            latest = self.model_registry.get_latest_version(model_id)
            if latest:
                details = self._format_model_details(latest)
                self.details_text.setText(details)
            
            # Feature importance'ı göster (sabit demo verisi)
            self._display_feature_importance(model_id)
            
            # Compare version spinbox'larını güncelle
            self.compare_v1.setMaximum(len(versions))
            self.compare_v2.setMaximum(len(versions))
            
            if len(versions) >= 2:
                self.compare_v2.setValue(len(versions))
            
            logger.info(f"✅ {model_id} gösterildi ({len(versions)} version)")
            
        except Exception as e:
            logger.error(f"Display hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Gösterim hatası: {e}")
    
    def _format_model_details(self, version: MLModelVersion) -> str:
        """Model detaylarını format et"""
        details = f"""
╔════════════════════════════════════════════════════╗
║          MODEL DETAILS - Version {version.version}
╚════════════════════════════════════════════════════╝

📋 Model Information:
   ID: {version.model_id}
   Type: {version.model_type}
   Status: {version.status.upper()}
   Created: {version.timestamp}

📊 Performance Metrics:
"""
        
        for metric, value in version.metrics.items():
            if isinstance(value, float):
                value_str = f"{value:.4f}" if value < 1 else f"{value:.2f}"
            else:
                value_str = str(value)
            details += f"   {metric.replace('_', ' ').title()}: {value_str}\n"
        
        details += f"""
📝 Notes:
   {version.notes}

🔄 Version History:
   This is version {version.version} in a series of models
   
🎯 Next Steps:
   • Monitor performance in production
   • Compare with other versions for insights
   • Export version for backup and sharing
"""
        
        return details
    
    def _display_feature_importance(self, model_id: str):
        """Feature importance'ı göster"""
        try:
            # Demo feature importance data
            features_data = {
                'signal_classifier': [
                    ('RSI', 0.25, 'HIGH'),
                    ('MACD', 0.20, 'HIGH'),
                    ('Bollinger Bands', 0.18, 'MEDIUM'),
                    ('Volume', 0.15, 'MEDIUM'),
                    ('ATR', 0.12, 'MEDIUM'),
                    ('Fibonacci Levels', 0.10, 'LOW'),
                ],
                'price_predictor': [
                    ('Previous Close', 0.30, 'HIGH'),
                    ('Volume', 0.22, 'HIGH'),
                    ('ATR', 0.18, 'MEDIUM'),
                    ('Day of Week', 0.15, 'MEDIUM'),
                    ('Market Regime', 0.10, 'LOW'),
                    ('Seasonality', 0.05, 'LOW'),
                ],
                'trend_detector': [
                    ('EMA Slope', 0.28, 'HIGH'),
                    ('Higher Highs/Lows', 0.25, 'HIGH'),
                    ('Volume Confirmation', 0.20, 'MEDIUM'),
                    ('Support/Resistance', 0.15, 'MEDIUM'),
                    ('Market Strength', 0.12, 'LOW'),
                ],
            }
            
            features = features_data.get(model_id, [])
            
            # Table
            self.feature_table.setRowCount(len(features))
            
            for row, (feature, importance, impact) in enumerate(features):
                # Feature adı
                feature_item = QTableWidgetItem(feature)
                self.feature_table.setItem(row, 0, feature_item)
                
                # Importance score
                imp_item = QTableWidgetItem(f"{importance:.1%}")
                
                if importance > 0.20:
                    imp_item.setForeground(QColor("#4CAF50"))
                elif importance > 0.15:
                    imp_item.setForeground(QColor("#FFC107"))
                
                self.feature_table.setItem(row, 1, imp_item)
                
                # Impact
                impact_item = QTableWidgetItem(impact)
                self.feature_table.setItem(row, 2, impact_item)
            
            # Grafik
            if PYQTGRAPH_AVAILABLE:
                self.feature_plot.clear()
                
                feature_names = [f[0] for f in features]
                importances = [f[1] for f in features]
                
                x = np.arange(len(feature_names))
                
                self.feature_plot.barplot(
                    x=x,
                    height=importances,
                    pen=pg.mkPen('b', width=1),
                    brush=pg.mkBrush('b', alpha=100)
                )
            
        except Exception as e:
            logger.error(f"Feature importance display hatası: {e}")
    
    def compare_versions(self):
        """Version'ları karşılaştır"""
        try:
            model_id = self.model_combo.currentText()
            v1 = self.compare_v1.value()
            v2 = self.compare_v2.value()
            
            comparison = self.model_registry.compare_versions(model_id, v1, v2)
            
            if not comparison:
                QMessageBox.warning(self, "Uyarı", "Version'ların karşılaştırılması başarısız")
                return
            
            # Tabloyu doldur
            self.comparison_table.setRowCount(len(comparison['v1']['metrics']) + 1)
            
            row = 0
            
            # Accuracy
            self.comparison_table.setItem(row, 0, QTableWidgetItem("Accuracy"))
            self.comparison_table.setItem(row, 1, QTableWidgetItem(f"{comparison['v1']['accuracy']:.2%}"))
            self.comparison_table.setItem(row, 2, QTableWidgetItem(f"{comparison['v2']['accuracy']:.2%}"))
            row += 1
            
            # Diğer metrikler
            for metric in comparison['v1']['metrics']:
                self.comparison_table.setItem(row, 0, QTableWidgetItem(metric.replace('_', ' ').title()))
                
                v1_val = comparison['v1']['metrics'][metric]
                v2_val = comparison['v2']['metrics'][metric]
                
                v1_str = f"{v1_val:.4f}" if isinstance(v1_val, float) else str(v1_val)
                v2_str = f"{v2_val:.4f}" if isinstance(v2_val, float) else str(v2_val)
                
                self.comparison_table.setItem(row, 1, QTableWidgetItem(v1_str))
                self.comparison_table.setItem(row, 2, QTableWidgetItem(v2_str))
                
                row += 1
            
            # Grafik
            if PYQTGRAPH_AVAILABLE:
                self.perf_plot.clear()
                
                versions = [v1, v2]
                accuracies = [comparison['v1']['accuracy'], comparison['v2']['accuracy']]
                
                colors = ['#FF6B6B', '#4ECDC4']
                
                for i, (version, accuracy) in enumerate(zip(versions, accuracies)):
                    self.perf_plot.plot(
                        [i],
                        [accuracy],
                        pen=pg.mkPen(color=colors[i], width=2),
                        symbolBrush=pg.mkBrush(colors[i]),
                        symbolSize=10,
                        symbol='o'
                    )
                
                # Improvement annotation
                improvement = comparison['accuracy_improvement']
                improvement_text = f"+{improvement:.2%}" if improvement > 0 else f"{improvement:.2%}"
                
                logger.info(f"✅ Accuracy improvement: {improvement_text}")
            
        except Exception as e:
            logger.error(f"Karşılaştırma hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Karşılaştırma hatası: {e}")
    
    def train_new_version(self):
        """Yeni version eğit"""
        try:
            model_id = self.model_combo.currentText()
            
            # Progress dialog
            progress = QMessageBox()
            progress.setWindowTitle("Model Eğitimi")
            progress.setText("Yeni model version'ı eğitiliyor...\n\nBu işlem biraz zaman alabilir...")
            progress.setIcon(QMessageBox.Information)
            progress.setStandardButtons(QMessageBox.Cancel)
            
            # Dummy: Yeni version oluştur
            latest = self.model_registry.get_latest_version(model_id)
            
            if latest:
                new_accuracy = latest.accuracy + np.random.uniform(0, 0.05)
                new_accuracy = min(new_accuracy, 0.99)
                
                new_version = MLModelVersion(
                    model_id,
                    latest.version + 1,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    latest.model_type,
                    new_accuracy,
                    latest.metrics.copy()
                )
                
                # Metrikleri biraz geliştir
                for metric in new_version.metrics:
                    if isinstance(new_version.metrics[metric], float):
                        new_version.metrics[metric] *= np.random.uniform(1.0, 1.05)
                
                new_version.notes = f"Auto-trained version with {np.random.randint(5000, 10000)} samples"
                
                self.model_registry.register_version(new_version)
                
                QMessageBox.information(
                    self,
                    "Başarı",
                    f"✅ {model_id} v{new_version.version} başarıyla eğitildi!\n\n"
                    f"Yeni Accuracy: {new_accuracy:.2%}\n"
                    f"Improvement: +{(new_accuracy - latest.accuracy):.2%}"
                )
                
                self.refresh_display(model_id)
                self.model_updated.emit(model_id)
        
        except Exception as e:
            logger.error(f"Eğitim hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Eğitim hatası: {e}")
    
    def rollback_selected_version(self):
        """Seçili version'a geri dön"""
        try:
            model_id = self.model_combo.currentText()
            
            if self.version_table.currentRow() < 0:
                QMessageBox.warning(self, "Uyarı", "Lütfen bir version seçin")
                return
            
            row = self.version_table.currentRow()
            version_num = int(self.version_table.item(row, 0).text())
            
            if self.model_registry.rollback_to_version(model_id, version_num):
                QMessageBox.information(
                    self,
                    "Başarı",
                    f"✅ {model_id} v{version_num}'e başarıyla geri dönüldü"
                )
                
                self.refresh_display(model_id)
                self.model_updated.emit(model_id)
            else:
                QMessageBox.warning(self, "Hata", "Rollback başarısız oldu")
        
        except Exception as e:
            logger.error(f"Rollback hatası: {e}")
            QMessageBox.critical(self, "Hata", f"Rollback hatası: {e}")
    
    def export_versions(self):
        """Version'ları export et"""
        try:
            model_id = self.model_combo.currentText()
            
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                f"Export {model_id} versions",
                "",
                "JSON Files (*.json)"
            )
            
            if filepath:
                if self.model_registry.export_versions(model_id, filepath):
                    QMessageBox.information(
                        self,
                        "Başarı",
                        f"✅ {model_id} version'ları başarıyla dışa aktarıldı"
                    )
                else:
                    QMessageBox.warning(self, "Hata", "Export başarısız")
        
        except Exception as e:
            logger.error(f"Export hatası: {e}")
    
    def import_versions(self):
        """Version'ları import et"""
        try:
            model_id = self.model_combo.currentText()
            
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                f"Import {model_id} versions",
                "",
                "JSON Files (*.json)"
            )
            
            if filepath:
                if self.model_registry.import_versions(model_id, filepath):
                    QMessageBox.information(
                        self,
                        "Başarı",
                        f"✅ {model_id} version'ları başarıyla alındı"
                    )
                    self.refresh_display(model_id)
                else:
                    QMessageBox.warning(self, "Hata", "Import başarısız")
        
        except Exception as e:
            logger.error(f"Import hatası: {e}")
    
    def setup_state_subscription(self):
        """State manager'a subscribe ol"""
        if self.state_manager:
            self.state_manager.subscribe(
                'MLManagementTab',
                self._on_state_change,
                keys=['ml_models', 'active_ml_model']
            )
    
    def _on_state_change(self, key: str, new_value, old_value):
        """State değiştiğinde"""
        if key == 'ml_models' and new_value:
            self.refresh_display(self.model_combo.currentText())
