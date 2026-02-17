# -*- coding: utf-8 -*-
"""
Result Manager - Sonuç yönetimi ve export
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd


class ResultManager:
    """Tarama sonuçlarını yönetme"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def format_results(self, results: List[Dict]) -> Dict:
        """
        Sonuçları formatla ve sırala

        Args:
            results: Ham sonuç listesi

        Returns:
            Formatlanmış sonuç dictionary
        """
        if not results:
            return {"Swing Uygun": []}

        # Skora göre sırala
        sorted_results = sorted(
            results, key=lambda x: float(x["Skor"].split("/")[0]), reverse=True
        )

        return {"Swing Uygun": sorted_results}

    def save_to_excel(self, results: Dict, filename: str = None) -> Optional[str]:
        """
        Sonuçları Excel'e kaydet

        Args:
            results: Sonuç dictionary
            filename: Dosya adı (None ise otomatik oluşturulur)

        Returns:
            Dosya adı veya None
        """
        try:
            swing_results = results.get("Swing Uygun", [])

            if not swing_results:
                logging.warning("Kaydedilecek sonuç yok")
                return None

            # DataFrame oluştur
            df = pd.DataFrame(swing_results)

            # Dosya adı
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"Swing_Rapor_{timestamp}.xlsx"

            # Kaydet
            df.to_excel(filename, index=False)

            logging.info(f"✅ Excel raporu: {filename}")
            return filename

        except Exception as e:
            logging.error(f"Excel kaydetme hatası: {e}")
            return None

    def save_to_csv(self, results: Dict, filename: str = None) -> Optional[str]:
        """
        Sonuçları CSV'ye kaydet

        Args:
            results: Sonuç dictionary
            filename: Dosya adı

        Returns:
            Dosya adı veya None
        """
        try:
            swing_results = results.get("Swing Uygun", [])

            if not swing_results:
                return None

            df = pd.DataFrame(swing_results)

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"Swing_Rapor_{timestamp}.csv"

            df.to_csv(filename, index=False, encoding="utf-8-sig")

            logging.info(f"✅ CSV raporu: {filename}")
            return filename

        except Exception as e:
            logging.error(f"CSV kaydetme hatası: {e}")
            return None

    def get_summary_stats(self, results: Dict) -> Dict:
        """
        Sonuç özet istatistikleri

        Returns:
            Özet dictionary
        """
        swing_results = results.get("Swing Uygun", [])

        if not swing_results:
            return {
                "total_stocks": 0,
                "avg_score": 0,
                "avg_rr_ratio": 0,
                "high_score_count": 0,
            }

        # İstatistikler
        scores = [float(r["Skor"].split("/")[0]) for r in swing_results]
        rr_ratios = [float(r["R/R"].split(":")[1]) for r in swing_results]
        
        # Güvenlik kontrolü yaparak yeni metrikleri topla
        sharpes = [float(r.get("Sharpe", 0)) for r in swing_results if "Sharpe" in r]
        efficiencies = [float(r.get("Efficiency", 0)) for r in swing_results if "Efficiency" in r]

        stats = {
            "total_stocks": len(swing_results),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "avg_rr_ratio": sum(rr_ratios) / len(rr_ratios),
            "avg_sharpe": sum(sharpes) / len(sharpes) if sharpes else 0,
            "avg_efficiency": sum(efficiencies) / len(efficiencies) if efficiencies else 0,
            "high_score_count": sum(1 for s in scores if s >= 75),
            "medium_score_count": sum(1 for s in scores if 60 <= s < 75),
            "low_score_count": sum(1 for s in scores if s < 60),
        }

    def filter_results(
        self,
        results: Dict,
        min_score: float = None,
        min_rr: float = None,
        max_risk: float = None,
        market_regime: str = None,
        min_sharpe: float = None,      # YENİ
        min_efficiency: float = None,   # YENİ
    ) -> Dict:
        """
        Sonuçları filtrele

        Args:
            results: Sonuç dictionary
            min_score: Minimum skor
            min_rr: Minimum R/R oranı
            max_risk: Maksimum risk %
            market_regime: Piyasa rejimi

        Returns:
            Filtrelenmiş sonuçlar
        """
        swing_results = results.get("Swing Uygun", [])

        if not swing_results:
            return results

        filtered = swing_results

        # Skor filtresi
        if min_score is not None:
            filtered = [
                r for r in filtered if float(r["Skor"].split("/")[0]) >= min_score
            ]

        # R/R filtresi
        if min_rr is not None:
            filtered = [r for r in filtered if float(r["R/R"].split(":")[1]) >= min_rr]

        # Risk filtresi
        if max_risk is not None:
            filtered = [r for r in filtered if float(r["Risk %"]) <= max_risk]

        # Piyasa rejimi filtresi
        if market_regime is not None:
            filtered = [
                r for r in filtered if r["Piyasa"].lower() == market_regime.lower()
            ]
            
        # Sharpe filtresi (YENİ)
        if min_sharpe is not None:
            filtered = [r for r in filtered if float(r.get("Sharpe", 0)) >= min_sharpe]

        # Efficiency filtresi (YENİ)
        if min_efficiency is not None:
            filtered = [r for r in filtered if float(r.get("Efficiency", 0)) >= min_efficiency]

        logging.info(f"Filtre: {len(swing_results)} -> {len(filtered)} sonuç")

        return {"Swing Uygun": filtered}

    def export_summary_report(
        self, results: Dict, filename: str = None
    ) -> Optional[str]:
        """
        Özet raporu oluştur

        Returns:
            Dosya adı veya None
        """
        try:
            stats = self.get_summary_stats(results)
            swing_results = results.get("Swing Uygun", [])

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"Swing_Summary_{timestamp}.txt"

            # Rapor metni
            report_lines = [
                "=" * 50,
                "SWING HUNTER - TARAMA ÖZET RAPORU",
                "=" * 50,
                f"\nTarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "\n📊 GENEL İSTATİSTİKLER:",
                f"  • Toplam Uygun Hisse: {stats['total_stocks']}",
                f"  • Ortalama Skor: {stats['avg_score']:.1f}",
                f"  • En Yüksek Skor: {stats.get('max_score', 0):.1f}",
                f"  • Ortalama R/R Oranı: {stats['avg_rr_ratio']:.2f}",
                "\n🎯 SKOR DAĞILIMI:",
                f"  • Yüksek Skor (75+): {stats['high_score_count']} hisse",
                f"  • Orta Skor (60-75): {stats['medium_score_count']} hisse",
                f"  • Düşük Skor (<60): {stats['low_score_count']} hisse",
            ]

            # İlk 10 hisse
            if swing_results:
                report_lines.append("\n🔝 EN İYİ 10 HİSSE:")
                for i, result in enumerate(swing_results[:10], 1):
                    report_lines.append(
                        f"  {i}. {result['Hisse']}: "
                        f"{result['Skor']} - "
                        f"R/R {result['R/R']}"
                    )

            # Dosyaya yaz
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))

            logging.info(f"✅ Özet raporu: {filename}")
            return filename

        except Exception as e:
            logging.error(f"Özet rapor hatası: {e}")
            return None
