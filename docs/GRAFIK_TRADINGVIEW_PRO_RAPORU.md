# Grafik Bölümünü TradingView Pro Seviyesine Çıkarma Raporu

**Tarih:** Şubat 2026  
**Proje:** Swing-Trade v3.3.2  
**Amaç:** Mevcut grafik modülünü TradingView Pro / Advanced Charts seviyesine taşımak için yapılabileceklerin özeti.

---

## 1. Mevcut Grafik Altyapısı (Özet)

| Bileşen | Teknoloji | Özellikler |
|--------|-----------|------------|
| **Görüntüleme** | PyQt5 + PyQtGraph | Candlestick, Heikin Ashi, çizim araçları |
| **Veri** | tvDatafeed, yfinance fallback | Günlük/haftalık bar, BIST/NYSE/CRYPTO |
| **Göstergeler** | Özel (IndicatorCalculator) | EMA, SMA, BB, RSI, MACD, ADX, Stochastic, VWAP, Volume Profile, Pivot Points |
| **Çizim araçları** | chart_components/drawing_tools | Trend çizgisi, Fibonacci, yatay çizgi, kanal, dikdörtgen, metin, ölçü, risk/ödül |
| **Pattern** | SwingPatternRecognizer, divergence | Klasik mum pattern’leri, swing pattern’ler, RSI/MACD uyumsuzluk |
| **Multi-timeframe** | MultiTimeframeManager | Çoklu zaman dilimi analizi |
| **Raporlama** | PDF/Excel export | Grafik ve analiz dışa aktarım |

**Eksikler (TradingView Pro’ya göre):**
- Gerçek zamanlı tick/stream (şu an tarihsel bar + canlı ayrı ticker)
- Yüzlerce hazır indikatör ve Pine Script benzeri özelleştirme
- Profesyonel UI (toolbar, çoklu grafik, layout kaydetme)
- Resmî TradingView veri kalitesi ve gecikme
- Sosyal/paylaşım ve alert sistemi (grafik üzerinden)

---

## 2. TradingView Pro Seviyesine Ulaşmak İçin Seçenekler

### Seçenek A: TradingView Charting Library (Resmî) – En Yüksek Seviye

**Ne:** TradingView’ın ticari **Advanced Charting Library** (JavaScript). WebView içinde PyQt’te gömülebilir.

**Artıları:**
- Gerçek TradingView deneyimi (indikatörler, çizimler, çoklu grafik, layout)
- Resmî veri entegrasyonu ve dokümantasyon
- Düzenli güncellemeler ve destek

**Eksileri:**
- **Lisans gerekir**: Başvuru yapılır, fiyat ve kullanım koşulları TradingView ile görüşülür; genelde ücretli ve yeniden dağıtım kısıtlı.
- Uygulama **WebView** (Qt WebEngine / CEF) kullanmalı; Python–JS köprüsü (veri, olaylar) yazılmalı.
- Veri kaynağı: Kütüphane “datafeed” bekler; mevcut tvDatafeed/yfinance’ı datafeed API’ye uyarlamak gerekir.

**Yapılacaklar (yüksek seviye):**
1. TradingView’a Charting Library lisans başvurusu.
2. PyQt5/6 içinde `QWebEngineView` ile HTML/JS sayfası açmak; sayfa içinde Charting Library’yi yüklemek.
3. Datafeed API implementasyonu (Python backend veya JS tarafında proxy): OHLCV’yi tvDatafeed/yfinance’dan alıp kütüphaneye vermek.
4. Sembol değişimi, zaman dilimi, ayarlar için Python ↔ JavaScript mesajlaşması (e.g. `runJavaScript` / `window.postMessage`).
5. Alert / çizim kaydetme gibi olayları JS’den Python’a taşımak (opsiyonel).

**Tahmini efor:** 2–4 hafta (lisans + WebView + datafeed + temel entegrasyon). Lisans maliyeti TradingView’a sorulmalı.

---

### Seçenek B: TradingView Lightweight Charts (Açık Kaynak) – Orta/Pro Görünüm

**Ne:** TradingView **Lightweight Charts** (Apache 2.0). Hafif, embed edilebilir mum/hacim grafiği. Python tarafında **bn-lightweight-charts-python** gibi sarmalayıcılar var; PyQt + WebView ile kullanılabilir.

**Artıları:**
- Ücretsiz, açık kaynak; lisans başvurusu yok.
- Görsel kalite ve etkileşim (zoom, crosshair, temalar) iyi.
- PyQt/PySide ile WebView içinde çalıştırılabilir.

**Eksileri:**
- Advanced Charting kadar zengin değil: sınırlı indikatör, Pine Script yok, çizim araçları sınırlı.
- Veri ve indikatör mantığı sizin tarafta (Python/JS); mevcut IndicatorCalculator ile beslenebilir.

**Yapılacaklar:**
1. `QWebEngineView` ile bir HTML sayfası; sayfada Lightweight Charts (veya bn-lightweight-charts-python örneği) kullanmak.
2. Veri akışı: Python’dan OHLCV + isteğe bağlı hesaplanmış indikatörleri JSON ile göndermek; grafikte güncellemek.
3. Sembol/zaman dilimi değişince yeni veri seti göndermek.
4. (Opsiyonel) Basit çizim (yatay çizgi, trend) kendi overlay’leriniz veya kütüphanenin imkânlarıyla.

**Tahmini efor:** 1–2 hafta (WebView + veri pipeline + temel kullanım).

---

### Seçenek C: Mevcut PyQtGraph Stack’i Güçlendirmek – Pro’ya Yaklaştırma

**Ne:** Şu anki `chart_widget.py` ve `chart_components` yapısı korunur; eksikler tek tek kapatılır.

**Yapılabilecekler (öncelik sırasıyla):**

| Öncelik | İyileştirme | Açıklama |
|--------|--------------|----------|
| 1 | **Grafik içinde canlı fiyat** | WebSocket worker’dan gelen fiyatı mevcut grafik penceresinde son bar’a veya ayrı bir “last price” çizgisine yansıtmak; böylece “canlı” hissi artar. |
| 2 | **Daha fazla indikatör** | İsteğe bağlı: Ichimoku, VWAP (zaten var, iyileştirme), Order Block, basit Volume Delta; hepsi mevcut `IndicatorCalculator` mimarisine eklenebilir. |
| 3 | **Zaman dilimi seçimi (UI)** | Grafik toolbar’da 1m/5m/15m/1saat/4saat/günlük/haftalık seçimi; veri tvDatafeed/yfinance’dan ilgili interval ile çekilir. |
| 4 | **Layout / şablon kaydetme** | Açık indikatör seti ve çizimleri JSON’a yazıp tekrar yükleyebilme (kullanıcı “Pro” layout hissi kazanır). |
| 5 | **Grafik alert’leri** | Fiyat > X, RSI < 30 vb. kurallar; tetiklenince mevcut NotificationManager ile bildirim. |
| 6 | **Çoklu grafik (2–4 panel)** | Aynı pencerede 2 veya 4 sembol (veya aynı sembol farklı timeframe); PyQtGraph’ta ek `PlotItem` ve veri senkronizasyonu. |
| 7 | **Performans ve tema** | Büyük bar sayısında (örn. 5000+) downsampling, lazy loading; koyu/açık tema seçimi (CURRENT_THEME ile uyumlu). |

**Artıları:** Lisans yok, tam kontrol, mevcut kod tabanına sadık.  
**Eksileri:** TradingView’ın “her şey hazır” hissine tam ulaşmak zor; süreç iteratif.

**Tahmini efor:** Öncelik 1–4 için 1–2 hafta; 5–7 için ek 1–2 hafta.

---

### Seçenek D: Hibrit (Lightweight Charts + Mevcut Analiz)

**Ne:** Ana görüntüleme için Lightweight Charts (WebView), analiz/sinyal/backtest tarafı mevcut Python (scanner, backtest, ML) kalır.

**Akış:**
- Grafik: WebView’da Lightweight Charts; veri Python’dan gelir (tvDatafeed/yfinance).
- Sinyal/pattern/indikatör: Python’da hesaplanır; sonuçlar (çizgi, bölge, işaret) JSON ile grafiğe gönderilir (overlay veya işaret olarak).
- Alert ve bildirim: Yine mevcut NotificationManager.

**Artıları:** Görsel kalite ve etkileşim iyileşir, analiz tarafı değişmez.  
**Eksileri:** İki sistem (Python + JS) senkron tutulmalı; geliştirme ve bakım iki taraflı.

---

## 3. Önerilen Yol Haritası

**Kısa vade (1–2 ay):**
- **Seçenek C** ile mevcut grafiği güçlendirin: grafikte canlı fiyat, zaman dilimi seçimi, layout kaydetme, basit alert. Bu, “Pro’ya yakın” hissi verir ve lisans gerektirmez.
- İsteğe bağlı: **Seçenek B** ile bir “Lightweight Charts” deneme sekmesi açın; kullanıcı geri bildirimine göre ilerleyin.

**Orta/uzun vade (3–6 ay):**
- Resmî **TradingView Charting Library** kullanmak istiyorsanız: lisans başvurusu yapın; onay ve maliyet sonrası **Seçenek A** için WebView + datafeed projesini planlayın.
- Lisans uygun değilse: **Seçenek D** (Lightweight Charts + Python analiz) ile “Pro” görünümü ve performansı hedefleyin.

---

## 4. Teknik Notlar (Mevcut Kodla Uyum)

- **Veri:** `chart_tab.show_chart()` → `tvDatafeed` / `yfinance`; aynı pipeline WebView datafeed’e de beslenebilir (JSON/ REST veya WebSocket).
- **Göstergeler:** `gui/chart_components/` altındaki yapı; yeni indikatörler aynı pattern ile eklenebilir.
- **Tema:** `chart_components/config.py` → `THEMES`, `CURRENT_THEME`; WebView kullanılırsa JS tarafında aynı renk paleti verilebilir.
- **WebView:** PyQt5 için `QtWebEngineWidgets.QWebEngineView`; kurulum `pip install PyQtWebEngine`.

---

## 5. Özet Tablo

| Seçenek | Pro seviyesine yakınlık | Lisans | Efor | Not |
|---------|--------------------------|--------|------|-----|
| A – Charting Library | ★★★★★ | Gerekli (ücretli) | Yüksek | En “gerçek” TradingView deneyimi |
| B – Lightweight Charts | ★★★★☆ | Yok (Apache 2.0) | Orta | Görsel kalite, sınırlı indikatör/çizim |
| C – PyQtGraph iyileştirme | ★★★☆☆ | Yok | Orta | Mevcut yapı, adım adım Pro’ya yaklaşma |
| D – Hibrit (B + Python) | ★★★★☆ | Yok | Orta–Yüksek | İyi görsel + mevcut analiz gücü |

### Seçenek C uygulananlar (Şubat 2026)
- **Canlı fiyat çizgisi:** Grafikte turkuaz "Canlı" yatay çizgi; WebSocket fiyat güncellemesi ile hareket eder.
- **Şablon kaydetme/yükleme:** "Şablon Kaydet" / "Şablon Yükle" butonları; indikatör + timeframe JSON’a kaydedilir.

**Sonuç:** Grafik bölümünü “TradingView Pro” seviyesine çıkarmak için hem **lisanslı resmî kütüphane** (Seçenek A) hem **ücretsiz ama güçlü** (B veya D) hem de **mevcut sistemi geliştirme** (C) yolları var. Önce C ile hızlı kazanımlar alıp, bütçe ve hedefe göre A veya B/D’ye geçmek mantıklı bir sıralama olur.
