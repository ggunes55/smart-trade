"""
Text Annotation Tool - Metin ekleme aracı
"""

import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QInputDialog
from .base import BaseTool


class TextAnnotationTool(BaseTool):
    """
    Metin ekleme aracı
    - Grafik üzerine not ekle
    - Önemli noktaları işaretle
    """

    def __init__(self, plot_widget, parent_dialog):
        super().__init__(plot_widget, parent_dialog)
        self.texts = []

    def activate(self):
        """Metin ekleme modunu aktifleştir"""
        self.is_active = True
        self._connect_mouse_click(self.on_click)

        self._show_info(
            "📝 Metin Ekle", "Grafik üzerinde metin eklemek istediğiniz yeri tıklayın"
        )

    def on_click(self, evt):
        """Mouse tıklama olayını yakala"""
        if not self.is_active:
            return

        click_event = evt[0]
        if click_event.button() == Qt.LeftButton:
            pos = click_event.scenePos()
            mouse_pos = self._get_mouse_position(pos)

            if mouse_pos:
                x, y = mouse_pos

                # Kullanıcıdan metin al
                text, ok = QInputDialog.getText(
                    self.parent, "📝 Metin Gir", "Eklemek istediğiniz metni yazın:"
                )

                if ok and text:
                    text_item = pg.TextItem(
                        text=text,
                        anchor=(0.5, 0.5),
                        color="k",
                        fill=pg.mkBrush(255, 235, 59, 200),
                        border=pg.mkPen("#FFC107", width=2),
                    )
                    font = QFont()
                    font.setPointSize(12)
                    font.setBold(True)
                    text_item.setFont(font)
                    text_item.setPos(x, y)

                    self._add_item(text_item)
                    self.texts.append(text_item)

                self.deactivate()

    def clear_all(self):
        """Tüm metinleri sil"""
        for text in self.texts:
            try:
                self.plot.removeItem(text)
            except Exception:
                pass
        self.texts = []
        self.items = []
