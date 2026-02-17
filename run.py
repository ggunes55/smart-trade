# -*- coding: utf-8 -*-
"""
Swing Hunter Advanced Plus - Ana Çalıştırma Dosyası
Modüler GUI ile çalışır
"""
import sys
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox

# GUI'yi import et
from gui import SwingGUIAdvancedPlus


def main():
    """Ana fonksiyon"""
    # Temel logging ayarı
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # QApplication oluştur
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Swing Hunter Advanced Plus")
    app.setOrganizationName("Trading Tools")

    try:
        # Ana GUI'yi başlat
        logging.info("🚀 Swing Hunter Advanced Plus başlatılıyor...")
        gui = SwingGUIAdvancedPlus()
        gui.show()

        logging.info("✅ GUI başarıyla yüklendi")

        # Event loop'u başlat
        sys.exit(app.exec_())

    except Exception as e:
        logging.critical(f"❌ GUI başlatma hatası: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "Kritik Hata",
            f"Program başlatılamadı:\n\n{e}\n\nDetaylar için log dosyasını kontrol edin.",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
