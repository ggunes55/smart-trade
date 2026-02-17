# -*- coding: utf-8 -*-
"""
Readme Tab - Proje Hakkında
"""
import os
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
)
from PyQt5.QtCore import Qt


class ReadmeTab(QWidget):
    """Proje README dosyasını gösteren sekme"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_readme()

    def init_ui(self):
        """UI başlangıcı"""
        layout = QVBoxLayout(self)

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFrameShape(QTextEdit.NoFrame)
        # Markdown stilini iyileştirmek için biraz CSS
        self.text_display.setStyleSheet("""
            QTextEdit {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                background-color: #ffffff;
                color: #333333;
                padding: 20px;
            }
        """)
        
        layout.addWidget(self.text_display)
        self.setLayout(layout)

    def load_readme(self):
        """README.md dosyasını yükle"""
        try:
            import sys
            
            # Proje kök dizinini bul
            if getattr(sys, 'frozen', False):
                # EXE olarak çalışıyorsa (PyInstaller)
                base_path = sys._MEIPASS
            else:
                # Normal Python betiği olarak çalışıyorsa
                # gui/tabs/readme_tab.py -> gui/tabs -> gui -> root
                current_dir = os.path.dirname(os.path.abspath(__file__))
                base_path = os.path.dirname(os.path.dirname(current_dir))
            
            readme_path = os.path.join(base_path, "README.md")

            if os.path.exists(readme_path):
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.text_display.setMarkdown(content)
            else:
                self.text_display.setPlainText(f"README.md dosyası bulunamadı!\nKonum: {readme_path}")
                
        except Exception as e:
            self.text_display.setPlainText(f"README yüklenirken hata oluştu: {str(e)}")
