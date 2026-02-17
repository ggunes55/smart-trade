# 📘 Smart Trade - Kullanıcı Kılavuzu

Hoşgeldiniz! **Smart Trade Swing Hunter**, borsadaki yüzlerce hisse senedini saniyeler içinde tarayıp, sizin için en uygun "Swing Trade" (kısa-orta vadeli al-sat) fırsatlarını bulan akıllı bir yardımcıdır.

Bu kılavuz, hiçbir finansal tecrübesi olmayan birinin bile sistemi anlaması için hazırlanmıştır.

---

## 🎯 1. Bu Program Ne Yapar?

Borsada 500+ hisse senedi vardır ve hepsini tek tek incelemek imkansızdır. Bu program sizin yerinize şunları yapar:
1.  **Tarama:** Tüm hisseleri belirlediğiniz kriterlere göre (örneğin "Yükseliş trendinde olanlar") eler.
2.  **Puanlama:** Kalan hisselere 0 ile 100 arasında bir karne notu verir.
3.  **Risk Analizi:** "Bu hisse çok mu tehlikeli?", "Geçmişte yatırımcısını üzmüş mü?" sorularına cevap arar.
4.  **Al-Sat Planı:** Eğer hisseyi beğenirse, "Şuradan al, şuraya stop koy, şurada sat" diye size bir plan hazırlar.

---

## 🏆 2. Skorlama Sistemi (Karne Notu)

Program her hisseye **0-100** arası bir puan verir. Bu puan 3 ana dersten oluşur:

### A. Teknik Trend (%70 Etki)
Hissenin yönü yukarı mı? Güçlü mü gidiyor?
*   **EMA (Ortalamalar):** Fiyat ortalamaların (20 ve 50 günlük) üzerindeyse puan artar.
*   **RSI (Hız Göstergesi):** Araba çok mu hızlı gidiyor (Aşırı Alım) yoksa benzini mi bitti (Aşırı Satım)? Dengeli hızda gidenlere yüksek puan verir.
*   **MACD (Trend Yönü):** Yükseliş trendinin başladığını teyit eder.
*   **Hacim (Volume):** Yükselişe para girişi eşlik ediyor mu? "Kuru gürültü" mü yoksa "gerçek alıcı" mı var?

### B. Risk Profili (%15 Etki) - YENİ!
Hisse ne kadar güvenli?
*   **Sharpe Oranı:** "Aldığım riske değer mi?" sorusunun cevabıdır. Hem çok kazandırıp hem az düşen hisseler yüksek puan alır.
*   **Volatilite (Stability):** Hisse bir gün %10 artıp ertesi gün %10 düşüyor mu? Çok dengesiz (oynak) hisselerin puanı kırılır. **Biz "Merdiven gibi istikrarlı çıkan" hisseleri severiz.**

### C. Swing Kalitesi (%15 Etki) - YENİ!
Yükseliş "temiz" mi?
*   **Efficiency (Verimlilik):** Hissenin grafiği zikzaklı/testere gibi mi yoksa ip gibi düz mü? Düz ve temiz trendler yüksek puan alır.
*   **Pullback (Geri Çekilme):** Eğer hisse biraz düşmüşse (soluklanıyorsa), bu düşüşün "sağlıklı" bir alım fırsatı olup olmadığını ölçer.

**Özet Tablo:**
| Skor | Anlamı | Ne Yapmalı? |
| :--- | :--- | :--- |
| **80-100** | 🔥 **Süper Fırsat** | Çok güçlü trend, düşük risk. Detaylı incele ve alım düşün. |
| **65-79** | 📈 **İyi Aday** | Trend var ama bazı kusurları olabilir. İzleme listene al. |
| **50-64** | 😐 **Nötr/Zayıf** | Henüz tam olgunlaşmamış. Acele etme. |
| **0-49** | ❌ **Uzak Dur** | Düşüş trendinde veya çok riskli. |

---

## 📊 3. Terimler Sözlüğü (Nedir Bu Sayılar?)

Raporlarda göreceğiniz terimlerin Türkçe meali:

### 🔹 RSI (Relative Strength Index)
*   **Nedir:** Hissenin "gaz pedalı".
*   **İdeal:** 50-70 arası (Güçlü ama motor yanmamış).
*   **Kötü:** 30'un altı (Çok düşmüş), 80'in üstü (Çok şişmiş, düşebilir).

### 🔹 Volatility Squeeze (Sıkışma)
*   **Nedir:** Fiyatın bir yayın gerilmesi gibi dar bir alana sıkışmasıdır.
*   **Önemi:** Sıkışma bittiğinde genellikle çok sert bir patlama (yukarı veya aşağı) olur. Program bunu "🔥 SQUEEZE" olarak haber verir.

### 🔹 Sharpe Oranı
*   **Nedir:** "Kalite" puanı.
*   **Örnek:** A hissesi %20 kazandırmış ama kalbinizi yerinden çıkarmış. B hissesi %18 kazandırmış ama mışıl mışıl uyutmuş. B'nin Sharpe oranı daha yüksektir ve bizim için daha değerlidir.

### 🔹 Efficiency Ratio (Verimlilik)
*   **Nedir:** Trendin temizliği.
*   **Değer:** 1.0'a ne kadar yakınsa, hisse o kadar "cetvelle çizilmiş gibi" gidiyordur. 0.1 gibi düşükse "testere piyasası" vardır, para kaybetmenize (stop olmanıza) neden olabilir.

---

## 🛡️ 4. Risk Yönetimi (Nasıl Batmam?)

Bu programın en önemli özelliği size sadece "Ne alacağını" değil, "Ne kadar alacağını" ve "Nerede kaçacağını" söylemesidir.

*   **Stop Loss (Zarar Kes):** "Bu fiyata düşerse sat ve çık, inatlaşma" seviyesidir. Program bunu otomatik hesaplar. **ASLA STOP SEVİYESİNİ İHMAL ETMEYİN.**
*   **Target (Hedef):** "Karını al ve cebine koy" seviyeleridir.
    *   **Hedef 1:** Pozisyonun yarısını satıp ana paranı güvenceye al.
    *   **Hedef 2:** Kalanı ile trendi sür.
*   **Risk/Reward (R/R):** "1 TL kaybetme riskine karşılık kaç TL kazanacağım?"
    *   Örn: R/R 3.0 ise, 1 kaybedip 3 kazanmayı hedefliyorsunuz demektir. **2.0'ın altındaki R/R oranlarına işlem açmayın.**

---

Bu kılavuz, Smart Trade'i daha verimli kullanmanız ve sadece "yukarı giden" değil, "kaliteli" hisselere yatırım yapmanız için hazırlanmıştır. Bol kazançlar! 🚀
