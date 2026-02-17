import PyInstaller.__main__
import os
import shutil

print("🚀 Smart Trade Swing Scanner EXE Oluşturucu başlatılıyor...")

# Dist klasörünü temizle
if os.path.exists("dist"):
    shutil.rmtree("dist")
    print("🧹 Eski dist klasörü temizlendi.")

if os.path.exists("build"):
    shutil.rmtree("build")
    print("🧹 Eski build klasörü temizlendi.")

# PyInstaller komutu
# --add-data "SOURCE;DEST" formatı kullanılır.
# Windows'ta ; ayırıcıdır. Linux/Mac'te : kullanılır.

args = [
    'run.py',                         # Ana dosya
    '--name=SmartTrade_SwingScanner', # EXE adı
    '--onefile',                      # Tek dosya modu
    '--noconsole',                    # Konsol penceresi olmasın (GUI için)
    '--add-data=README.md;.',         # README.md dosyasını kök dizine ekle
    '--add-data=endexler;endexler',   # Endexler klasörünü ekle
    '--clean',                        # Önbelleği temizle
    '--icon=NONE',                    # İkon eklemek isterseniz burayı değiştirebilirsiniz
    # Gerekli hidden importlar varsa buraya ekleyin
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=pyqtgraph',
    '--hidden-import=tvDatafeed',
    '--hidden-import=talib.stream',
]

print(f"🛠️ Derleme başlatılıyor... Argümanlar: {args}")

try:
    PyInstaller.__main__.run(args)
    print("\n✅ EXE başarıyla oluşturuldu!")
    print(f"📂 Dosya konumu: {os.path.abspath('dist/SmartTrade_SwingScanner.exe')}")
except Exception as e:
    print(f"\n❌ Hata oluştu: {e}")
