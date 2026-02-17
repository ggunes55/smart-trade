"""
Crosshair Cursor - İmleç takip sistemi
"""

import pyqtgraph as pg
import pandas as pd
from PyQt5.QtCore import Qt


class CrosshairCursor:
    """
    Crosshair imleç
    - Mouse'u takip eden dikey/yatay çizgiler
    - OHLCV + gösterge bilgileri
    """

    def __init__(self, plot_widget, df: pd.DataFrame):
        self.plot = plot_widget
        self.df = df

        # Dikey ve yatay çizgiler
        self.vLine = pg.InfiniteLine(
            angle=90, movable=False, pen=pg.mkPen("#666", width=1, style=Qt.DashLine)
        )
        self.hLine = pg.InfiniteLine(
            angle=0, movable=False, pen=pg.mkPen("#666", width=1, style=Qt.DashLine)
        )

        self.plot.addItem(self.vLine, ignoreBounds=True)
        self.plot.addItem(self.hLine, ignoreBounds=True)

        # Bilgi etiketi
        self.label = pg.TextItem(anchor=(0, 1), color="#000", fill="#FFFFCC")
        self.plot.addItem(self.label)

        # Mouse hareket olayını dinle
        self.proxy = pg.SignalProxy(
            self.plot.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved
        )

    def mouse_moved(self, evt):
        """Mouse hareket ettiğinde çağrılır"""
        pos = evt[0]
        if self.plot.sceneBoundingRect().contains(pos):
            mouse_point = self.plot.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()

            # Çizgileri güncelle
            self.vLine.setPos(x)
            self.hLine.setPos(y)

            # Bar bilgilerini göster
            idx = int(x)
            if 0 <= idx < len(self.df):
                row = self.df.iloc[idx]
                date_str = row.get("date", idx)

                if isinstance(date_str, pd.Timestamp):
                    date_str = date_str.strftime("%Y-%m-%d")

                # OHLCV
                text = f"📅 {date_str}\n"
                text += f"O: {row['open']:.2f} H: {row['high']:.2f}\n"
                text += f"L: {row['low']:.2f} C: {row['close']:.2f}\n"
                text += f"Vol: {row['volume']:,.0f}"

                # Göstergeler (varsa)
                if "RSI" in row and not pd.isna(row["RSI"]):
                    text += f"\n📊 RSI: {row['RSI']:.1f}"
                if "MACD" in row and not pd.isna(row["MACD"]):
                    text += f"\n📈 MACD: {row['MACD']:.2f}"
                if "ADX" in row and not pd.isna(row["ADX"]):
                    text += f"\n💪 ADX: {row['ADX']:.1f}"

                self.label.setText(text)
                self.label.setPos(x, y)
