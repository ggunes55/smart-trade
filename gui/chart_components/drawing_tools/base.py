"""
Base Tool - Tüm çizim araçları için temel sınıf
"""

import pyqtgraph as pg
from PyQt5.QtWidgets import QMessageBox


class BaseTool:
    """
    Çizim araçları için temel sınıf
    - Ortak metodlar
    - Mouse event handling
    - Item yönetimi
    """

    def __init__(self, plot_widget, parent_dialog):
        self.plot = plot_widget
        self.parent = parent_dialog
        self.items = []  # Çizilen öğeler
        self.is_active = False
        self.points = []
        self.proxy = None

    def activate(self):
        """Aracı aktifleştir (override edilmeli)"""
        raise NotImplementedError("activate() metodu override edilmeli!")

    def on_click(self, evt):
        """Mouse tıklama olayı (override edilmeli)"""
        raise NotImplementedError("on_click() metodu override edilmeli!")

    def clear(self):
        """Tüm çizimleri temizle"""
        for item in self.items:
            try:
                self.plot.removeItem(item)
            except Exception:
                pass
        self.items = []
        self.points = []

    def clear_last(self):
        """Son çizimi sil"""
        if self.items:
            item = self.items.pop()
            try:
                self.plot.removeItem(item)
            except Exception:
                pass

    def deactivate(self):
        """Aracı deaktive et"""
        self.is_active = False
        self.points = []
        if self.proxy:
            try:
                self.proxy.disconnect()
            except Exception:
                pass
            self.proxy = None

    def _get_mouse_position(self, pos):
        """
        Mouse pozisyonunu grafik koordinatlarına çevir

        Returns:
            (x, y) veya None
        """
        if self.plot.sceneBoundingRect().contains(pos):
            mouse_point = self.plot.vb.mapSceneToView(pos)
            return mouse_point.x(), mouse_point.y()
        return None

    def _add_item(self, item):
        """Çizilen öğeyi kaydet ve grafiğe ekle"""
        self.plot.addItem(item)
        self.items.append(item)
        return item

    def _show_info(self, title: str, message: str):
        """Bilgilendirme mesajı göster"""
        QMessageBox.information(self.parent, title, message)

    def _show_warning(self, title: str, message: str):
        """Uyarı mesajı göster"""
        QMessageBox.warning(self.parent, title, message)

    def _connect_mouse_click(self, handler):
        """Mouse click olayını bağla"""
        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseClicked, rateLimit=60, slot=handler
        )
