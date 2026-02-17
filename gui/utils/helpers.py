# -*- coding: utf-8 -*-
"""
GUI Yardımcı Fonksiyonlar
"""
import sys
import os
from PyQt5.QtGui import QColor


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



def get_score_color(score):
    """Skora göre renk döndür"""
    if score >= 85:
        return QColor(50, 205, 50)  # LimeGreen
    elif score >= 75:
        return QColor(144, 238, 144)  # LightGreen
    elif score >= 65:
        return QColor(255, 255, 153)  # LightYellow
    return QColor(255, 255, 255)  # White


def get_signal_color(value):
    """Sinyal gücüne göre renk döndür"""
    if "🔥🔥🔥" in value:
        return QColor(50, 205, 50)
    elif "🔥🔥" in value:
        return QColor(144, 238, 144)
    elif "🎯" in value:
        return QColor(255, 215, 0)  # Gold
    return None


def get_pattern_color(score):
    """Pattern skoruna göre renk döndür"""
    if score >= 15:
        return QColor(255, 182, 193)  # LightPink
    elif score >= 10:
        return QColor(255, 228, 225)  # MistyRose
    return None


def get_rr_color(rr_value):
    """Risk/Reward oranına göre renk döndür"""
    if rr_value >= 3.0:
        return QColor(152, 251, 152)  # PaleGreen
    elif rr_value >= 2.5:
        return QColor(144, 238, 144)
    return None


def safe_float_conversion(text):
    """Güvenli float dönüşümü (aralık formatını destekler)"""
    if not text:
        return None

    # "96.98-100.94" gibi aralık formatı
    if "-" in text and text.count("-") == 1:
        parts = text.split("-")
        try:
            return (float(parts[0]) + float(parts[1])) / 2
        except (ValueError, IndexError):
            return None

    # Normal float dönüşümü
    try:
        return float(text)
    except ValueError:
        if "/" in text:
            return None
        return None


def format_trade_plan(trade_plan, validation, tv_details=None):
    """Trade planını formatla"""
    
    # Giriş stratejisi açıklaması
    entry_price = trade_plan.get('entry_price', 0)
    current_price = trade_plan.get('current_price', entry_price)
    signal_type = trade_plan.get('signal_type', '')
    
    # Giriş stratejisi belirleme
    if entry_price > current_price * 1.01:  # %1'den fazla yukarıda
        entry_strategy = "⏳ BREAKOUT STRATEJİSİ"
        entry_explanation = f"Fiyat {entry_price:.2f} TL seviyesini geçtiğinde GİRİŞ yapın.\nŞu an beklemede - direnç kırılmasını izleyin."
    elif entry_price < current_price * 0.99:  # %1'den fazla aşağıda
        entry_strategy = "📉 PULLBACK STRATEJİSİ"
        entry_explanation = f"Fiyat {entry_price:.2f} TL seviyesine düştüğünde GİRİŞ yapın.\nDestek bölgesinden dönüş bekleniyor."
    else:
        entry_strategy = "✅ ANINDA GİRİŞ"
        entry_explanation = "Mevcut fiyat optimal giriş bölgesinde.\nPozisyon hemen açılabilir."
    
    details = f"""
🎯 DETAYLI TRADE PLANI
{'='*50}

{entry_strategy}
{'-'*50}
{entry_explanation}

📊 TEMEL BİLGİLER:
• Güncel Fiyat: {current_price:.2f} TL
• Optimal Giriş: {entry_price:.2f} TL
• Stop Loss: {trade_plan.get('stop_loss', 0):.2f} TL
• Hedef 1: {trade_plan.get('target1', 0):.2f} TL
• Risk/Hisse: {trade_plan.get('risk_per_share', 0):.2f} TL

💰 POZİSYON BOYUTU:
• Sermaye: {trade_plan.get('capital', 0):,.0f} TL
• Risk Oranı: {trade_plan.get('risk_pct', 0):.1f}%
• Alınacak Hisse: {trade_plan.get('shares', 0)} adet
• Toplam Yatırım: {trade_plan.get('investment', 0):,.0f} TL

⚠️ RİSK ANALİZİ:
• Maksimum Kayıp: {trade_plan.get('max_loss_tl', 0):,.0f} TL ({trade_plan.get('max_loss_pct', 0):.1f}%)
• Maksimum Kâr: {trade_plan.get('max_gain_tl', 0):,.0f} TL
• R/R Oranı: 1:{trade_plan.get('rr_ratio', 0):.1f}
• Validasyon Skoru: {validation.get('score', 0)}/100

💡 ÖNERİ: {trade_plan.get('recommendation', 'N/A')}
"""

    # TV Sinyal Detayları (varsa)
    if tv_details:
        buy_c = tv_details.get("buy", 0)
        sell_c = tv_details.get("sell", 0)
        neutral_c = tv_details.get("neutral", 0)
        rec = tv_details.get("rec", "N/A")
        
        # Sinyal özeti
        details += f"""
📡 TRADINGVIEW ANALİZİ (26 Gösterge):
• Özet Sinyal: {rec}
• ✅ Al: {buy_c} | ❌ Sat: {sell_c} | ➖ Nötr: {neutral_c}
"""
        
        # Detaylı Göstergeler
        oscillators = tv_details.get("oscillators", {})
        moving_averages = tv_details.get("moving_averages", {})
        all_indicators = tv_details.get("all_indicators", {})
        
        if oscillators and moving_averages and all_indicators:
            details += "\n📊 GÖSTERGE DETAYLARI:\n"
            details += "-" * 30 + "\n"
            
            # Yardımcı fonksiyon: Sinyal rengi/ikonu
            def get_sig_icon(sig):
                if sig == "BUY": return "🟢 AL"
                if sig == "SELL": return "🔴 SAT"
                return "⚪ NÖTR"

            # 1. Osilatörler
            details += "OSİLATÖRLER:\n"
            osc_map = {
                "RSI": ("RSI", "RSI"),
                "Stoch.K": ("Stoch %K", "Stoch.K"),
                "CCI20": ("CCI", "CCI20"),
                "ADX": ("ADX", "ADX"),
                "AO": ("Awesome O.", "AO"),
                "Mom": ("Momentum", "Mom"),
                "MACD.macd": ("MACD", "MACD"),
                "Stoch.RSI.K": ("Stoch RSI", "Stoch.RSI.K"),
                "W.R": ("Williams %R", "W.R"),
                "BBP": ("Bull Bear", "BBP"),
                "UO": ("Ult. Osc.", "UO")
            }
            
            computed_osc = oscillators.get("COMPUTE", {})
            
            for key, (label, sig_key) in osc_map.items():
                val = all_indicators.get(key)
                sig = computed_osc.get(sig_key, "NEUTRAL")
                if val is not None:
                    details += f"• {label:<12} {val:>8.2f}  [{get_sig_icon(sig)}]\n"

            # 2. Hareketli Ortalamalar
            details += "\nHAREKETLİ ORTALAMALAR:\n"
            ma_map = {
                "EMA10": "EMA 10", "SMA10": "SMA 10",
                "EMA20": "EMA 20", "SMA20": "SMA 20",
                "EMA50": "EMA 50", "SMA50": "SMA 50",
                "EMA100": "EMA 100", "SMA100": "SMA 100",
                "EMA200": "EMA 200", "SMA200": "SMA 200"
            }
            
            computed_ma = moving_averages.get("COMPUTE", {})
            
            for key, label in ma_map.items():
                val = all_indicators.get(key)
                sig = computed_ma.get(key, "NEUTRAL")
                if val is not None:
                    details += f"• {label:<12} {val:>8.2f}  [{get_sig_icon(sig)}]\n"


    # Uyarıları ekle
    if validation.get("has_warnings", False):
        details += "\n⚠️ UYARILAR:\n"
        for warning in validation.get("warnings", []):
            details += f"• {warning}\n"

    # Hataları göster
    if not validation.get("is_valid", False):
        details += "\n❌ HATALAR:\n"
        for error in validation.get("errors", []):
            details += f"• {error}\n"

    return details


def get_market_strategy(regime):
    """Piyasa rejimine göre strateji"""
    strategies = {
        "bullish": "• Trend takip stratejileri kullan\n• EMA üstü kırılımlara odaklan\n• Risk/Ödül oranını 2.0+ tut",
        "bearish": "• Kısa pozisyonlardan kaçın\n• Sadece güçlü desteklerde alım\n• Risk/Ödül oranını 3.0+ yap",
        "volatile": "• Pozisyon büyüklüğünü küçült\n• Daha geniş stop loss kullan\n• Günlük işlemlerden kaçın",
        "sideways": "• Range breakout stratejileri\n• Destek/direnç seviyelerine odaklan\n• Hacim konfirmasyonu önemli",
        "neutral": "• Seçici alım stratejisi\n• Temel analiz önem kazanır\n• Risk yönetimine dikkat",
    }
    return strategies.get(regime, "• Standart strateji uygula")


def format_backtest_results(results):
    """Backtest sonuçlarını formatla"""
    if isinstance(results, dict) and "error" in results:
        return f"❌ HATA: {results['error']}"

    if not isinstance(results, dict) or "summary" not in results:
        return "❌ Geçersiz backtest sonuç formatı"

    summary = results.get("summary", {})
    detailed = results.get("detailed", [])

    report_lines = []
    report_lines.append("🎯 BACKTEST SONUÇ RAPORU")
    report_lines.append("=" * 50)
    report_lines.append("")

    # Summary bölümü
    report_lines.append("📊 PERFORMANS ÖZETİ:")
    report_lines.append(f"• Test edilen hisse: {summary.get('total_symbols', 0)}")
    report_lines.append(f"• Toplam işlem: {summary.get('total_trades', 0)}")
    report_lines.append(f"• Kazanan işlem: {summary.get('winning_trades', 0)}")
    report_lines.append(f"• Başarı oranı: {summary.get('win_rate', 0):.1f}%")
    report_lines.append(f"• Toplam kâr: {summary.get('total_profit', 0):,.0f} TL")
    report_lines.append(f"• Ortalama getiri: {summary.get('avg_return', 0):.1f}%")
    report_lines.append(f"• En iyi hisse: {summary.get('best_symbol', 'N/A')}")
    report_lines.append(f"• En kötü hisse: {summary.get('worst_symbol', 'N/A')}")
    report_lines.append("")

    # Detaylı sonuçlar
    if detailed:
        report_lines.append("📈 DETAYLI SONUÇLAR:")
        report_lines.append("-" * 40)

        for idx, result in enumerate(detailed[:10], 1):
            symbol = result.get("Symbol", f"Hisse-{idx}")
            trades = result.get("Trades", 0)
            win_rate = result.get("Win Rate %", 0)
            total_return = result.get("Total Return %", 0)
            total_profit = result.get("Total Profit", 0)
            max_dd = result.get("Max Drawdown %", 0)
            sharpe = result.get("Sharpe Ratio", 0)

            report_lines.append(f"\n{idx}. {symbol}:")
            report_lines.append(f"   • İşlem: {trades} | Başarı: {win_rate:.1f}%")
            report_lines.append(
                f"   • Getiri: {total_return:.1f}% | Kâr: {total_profit:,.0f} TL"
            )
            report_lines.append(
                f"   • Maks. Düşüş: {max_dd:.1f}% | Sharpe: {sharpe:.2f}"
            )

    # Not
    if results.get("note"):
        report_lines.append(f"\n💡 NOT: {results['note']}")

    return "\n".join(report_lines)
