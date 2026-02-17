import pandas as pd
import matplotlib.pyplot as plt
import io
from PyQt5.QtWidgets import QFileDialog

class ReportGenerator:
    """
    Analiz sonuçlarını PDF, PNG veya Excel olarak dışa aktaran modül
    """
    def __init__(self, parent=None):
        self.parent = parent

    def export_to_excel(self, df: pd.DataFrame, filename: str = None):
        if filename is None:
            filename, _ = QFileDialog.getSaveFileName(self.parent, "Excel Olarak Kaydet", "report.xlsx", "Excel Files (*.xlsx)")
        if filename:
            df.to_excel(filename, index=False)
            return filename
        return None

    def export_to_png(self, df: pd.DataFrame, filename: str = None):
        fig, ax = plt.subplots(figsize=(10, 4))
        df.tail(30).plot(ax=ax)
        ax.set_title("Son 30 Bar - Fiyat ve Göstergeler")
        plt.tight_layout()
        if filename is None:
            filename, _ = QFileDialog.getSaveFileName(self.parent, "PNG Olarak Kaydet", "report.png", "PNG Files (*.png)")
        if filename:
            fig.savefig(filename)
            plt.close(fig)
            return filename
        plt.close(fig)
        return None

    def export_to_pdf(self, df: pd.DataFrame, filename: str = None):
        from matplotlib.backends.backend_pdf import PdfPages
        if filename is None:
            filename, _ = QFileDialog.getSaveFileName(self.parent, "PDF Olarak Kaydet", "report.pdf", "PDF Files (*.pdf)")
        if filename:
            with PdfPages(filename) as pdf:
                fig, ax = plt.subplots(figsize=(10, 4))
                df.tail(30).plot(ax=ax)
                ax.set_title("Son 30 Bar - Fiyat ve Göstergeler")
                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            return filename
        return None
