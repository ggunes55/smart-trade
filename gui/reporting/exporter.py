# -*- coding: utf-8 -*-
"""
Reporting & Export System - Rapor ve export işlemleri
CSV, Excel, PDF formatlarını destekler
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


class CSVExporter:
    """CSV export işlemleri"""
    
    @staticmethod
    def export_scan_results(results: List[Dict], output_path: str) -> bool:
        """
        Tarama sonuçlarını CSV'ye export et
        
        Args:
            results: Tarama sonuçları listesi
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            df = pd.DataFrame(results)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"Scan results exported to {output_path}")
            return True
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return False
    
    @staticmethod
    def export_backtest_trades(trades: List[Dict], output_path: str) -> bool:
        """
        Backtest işlemlerini CSV'ye export et
        
        Args:
            trades: Trade listesi
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            df = pd.DataFrame(trades)
            
            # Kolonları düzenle
            column_order = [
                'symbol', 'entry_date', 'entry_price', 'entry_signal',
                'target1', 'target2', 'stoploss', 'exit_date', 'exit_price',
                'exit_reason', 'profit', 'profit_pct', 'duration', 'result'
            ]
            
            # Mevcut kolonları filtrele
            column_order = [col for col in column_order if col in df.columns]
            df = df[column_order]
            
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"Backtest trades exported to {output_path}")
            return True
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return False
    
    @staticmethod
    def export_portfolio(positions: List[Dict], output_path: str) -> bool:
        """
        Portfolio pozisyonlarını CSV'ye export et
        
        Args:
            positions: Pozisyon listesi
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            df = pd.DataFrame(positions)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"Portfolio exported to {output_path}")
            return True
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return False


class ExcelExporter:
    """Excel (.xlsx) export işlemleri"""
    
    @staticmethod
    def export_backtest_report(backtest_results: Dict, output_path: str) -> bool:
        """
        Backtest raporunu Excel'e export et (birden fazla sheet)
        
        Args:
            backtest_results: {trades: [...], metrics: {...}}
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                
                # Sheet 1: Trades
                trades = backtest_results.get('trades', [])
                if trades:
                    df_trades = pd.DataFrame(trades)
                    df_trades.to_excel(writer, sheet_name='Trades', index=False)
                
                # Sheet 2: Metrics
                metrics = backtest_results.get('metrics', {})
                if metrics:
                    df_metrics = pd.DataFrame([metrics])
                    df_metrics.to_excel(writer, sheet_name='Metrics', index=False)
                
                # Sheet 3: Statistics
                if trades:
                    stats = ExcelExporter._calculate_statistics(trades)
                    df_stats = pd.DataFrame([stats])
                    df_stats.to_excel(writer, sheet_name='Statistics', index=False)
            
            logger.info(f"Backtest report exported to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            return False
    
    @staticmethod
    def export_portfolio_report(positions: List[Dict], metrics: Dict, 
                               output_path: str) -> bool:
        """
        Portfolio raporunu Excel'e export et
        
        Args:
            positions: Pozisyon listesi
            metrics: Portfolio metrikleri
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                
                # Sheet 1: Positions
                if positions:
                    df_positions = pd.DataFrame(positions)
                    df_positions.to_excel(writer, sheet_name='Positions', index=False)
                
                # Sheet 2: Summary
                df_summary = pd.DataFrame([metrics])
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            logger.info(f"Portfolio report exported to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            return False
    
    @staticmethod
    def _calculate_statistics(trades: List[Dict]) -> Dict:
        """Ticaret istatistiklerini hesapla"""
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        
        results = df.get('result', [])
        wins = [r for r in results if r in ['WIN', 'W']]
        losses = [r for r in results if r in ['LOSS', 'L']]
        
        profits = df.get('profit_pct', [])
        
        return {
            'Total Trades': len(trades),
            'Winning Trades': len(wins),
            'Losing Trades': len(losses),
            'Win Rate %': (len(wins) / len(trades) * 100) if trades else 0,
            'Avg Profit %': df['profit_pct'].mean() if 'profit_pct' in df else 0,
            'Max Profit %': df['profit_pct'].max() if 'profit_pct' in df else 0,
            'Min Profit %': df['profit_pct'].min() if 'profit_pct' in df else 0,
            'Sharpe Ratio': ExcelExporter._calculate_sharpe_ratio(df),
        }
    
    @staticmethod
    def _calculate_sharpe_ratio(df: pd.DataFrame, risk_free_rate: float = 0.02) -> float:
        """Sharpe Ratio hesapla"""
        try:
            if 'profit_pct' not in df:
                return 0.0
            
            returns = df['profit_pct'] / 100
            excess_returns = returns - risk_free_rate / 252  # Daily
            
            if len(excess_returns) > 1:
                return (excess_returns.mean() / excess_returns.std()) * (252 ** 0.5)
            return 0.0
        except:
            return 0.0


class PDFExporter:
    """PDF export işlemleri"""
    
    @staticmethod
    def export_analysis_report(symbol: str, analysis: Dict, 
                             output_path: str) -> bool:
        """
        Hisse analiz raporunu PDF'ye export et
        
        Requires: reportlab
        
        Args:
            symbol: Hisse kodu
            analysis: Analiz verileri
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Başlık
            title = Paragraph(f"📊 {symbol} - Analiz Raporu", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 0.3*inch))
            
            # Tarih
            date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
            date_para = Paragraph(f"<i>Rapor Tarihi: {date_str}</i>", styles['Normal'])
            story.append(date_para)
            story.append(Spacer(1, 0.3*inch))
            
            # Analiz Tablosu
            if 'indicators' in analysis:
                indicators = analysis['indicators']
                table_data = [['İndikatör', 'Değer', 'Sinyal']]
                
                for ind_name, ind_value in indicators.items():
                    table_data.append([ind_name, str(ind_value), '↑'])
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                
                story.append(table)
                story.append(Spacer(1, 0.3*inch))
            
            # Build PDF
            doc.build(story)
            logger.info(f"PDF report exported to {output_path}")
            return True
            
        except ImportError:
            logger.warning("reportlab not installed. Install with: pip install reportlab")
            return False
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            return False
    
    @staticmethod
    def export_backtest_report_pdf(backtest_results: Dict, 
                                  output_path: str) -> bool:
        """
        Backtest raporunu PDF'ye export et
        
        Args:
            backtest_results: Backtest sonuçları
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Başlık
            title = Paragraph("📊 Backtest Raporu", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 0.2*inch))
            
            # Özet Metrikleri
            metrics = backtest_results.get('metrics', {})
            metric_data = [['Metrik', 'Değer']]
            
            for key, value in metrics.items():
                metric_data.append([str(key), str(value)])
            
            metric_table = Table(metric_data)
            metric_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            story.append(metric_table)
            
            doc.build(story)
            logger.info(f"Backtest PDF report exported to {output_path}")
            return True
            
        except ImportError:
            logger.warning("reportlab not installed")
            return False
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            return False


class JSONExporter:
    """JSON export işlemleri"""
    
    @staticmethod
    def export_analysis(symbol: str, analysis: Dict, output_path: str) -> bool:
        """
        Analiz verilerini JSON'a export et
        
        Args:
            symbol: Hisse kodu
            analysis: Analiz verileri
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        import json
        
        try:
            # Datetime'ları string'e çevir
            serializable_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'analysis': analysis,
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"Analysis exported to JSON: {output_path}")
            return True
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return False
    
    @staticmethod
    def export_backtest(backtest_results: Dict, output_path: str) -> bool:
        """
        Backtest sonuçlarını JSON'a export et
        
        Args:
            backtest_results: Backtest sonuçları
            output_path: Çıktı dosya yolu
        
        Returns:
            bool: Başarılı mı?
        """
        import json
        
        try:
            serializable_results = {
                'timestamp': datetime.now().isoformat(),
                'metrics': backtest_results.get('metrics', {}),
                'trades': backtest_results.get('trades', []),
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"Backtest results exported to JSON: {output_path}")
            return True
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return False


class ExportManager:
    """Tüm export işlemlerini yönetir"""
    
    def __init__(self, export_dir: str = "./exports"):
        """
        ExportManager'ı başlat
        
        Args:
            export_dir: Export dosyalarının klasörü
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def export_scan_results(self, results: List[Dict], 
                          format: str = 'csv') -> Optional[str]:
        """
        Tarama sonuçlarını export et
        
        Args:
            results: Tarama sonuçları
            format: 'csv', 'xlsx', 'json'
        
        Returns:
            Dosya yolu veya None
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scan_results_{timestamp}"
        
        if format == 'csv':
            output_path = self.export_dir / f"{filename}.csv"
            if CSVExporter.export_scan_results(results, str(output_path)):
                return str(output_path)
        
        elif format == 'xlsx':
            output_path = self.export_dir / f"{filename}.xlsx"
            df = pd.DataFrame(results)
            try:
                df.to_excel(output_path, index=False)
                return str(output_path)
            except Exception as e:
                logger.error(f"Excel export failed: {e}")
        
        elif format == 'json':
            output_path = self.export_dir / f"{filename}.json"
            JSONExporter.export_analysis(f"scan_results", results, str(output_path))
            return str(output_path)
        
        return None
    
    def export_portfolio(self, positions: List[Dict], metrics: Dict,
                        format: str = 'xlsx') -> Optional[str]:
        """Portfolio export et"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == 'xlsx':
            filename = f"portfolio_{timestamp}.xlsx"
            output_path = self.export_dir / filename
            if ExcelExporter.export_portfolio_report(positions, metrics, str(output_path)):
                return str(output_path)
        
        elif format == 'csv':
            filename = f"portfolio_{timestamp}.csv"
            output_path = self.export_dir / filename
            if CSVExporter.export_portfolio(positions, str(output_path)):
                return str(output_path)
        
        return None
    
    def export_backtest(self, backtest_results: Dict, 
                       format: str = 'xlsx') -> Optional[str]:
        """Backtest sonuçlarını export et"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == 'xlsx':
            filename = f"backtest_{timestamp}.xlsx"
            output_path = self.export_dir / filename
            if ExcelExporter.export_backtest_report(backtest_results, str(output_path)):
                return str(output_path)
        
        elif format == 'pdf':
            filename = f"backtest_{timestamp}.pdf"
            output_path = self.export_dir / filename
            if PDFExporter.export_backtest_report_pdf(backtest_results, str(output_path)):
                return str(output_path)
        
        elif format == 'json':
            filename = f"backtest_{timestamp}.json"
            output_path = self.export_dir / filename
            if JSONExporter.export_backtest(backtest_results, str(output_path)):
                return str(output_path)
        
        return None
