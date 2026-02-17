# -*- coding: utf-8 -*-
"""
Symbol Analyzer - Tek sembol analizi
"""
import logging
import pandas as pd  # YENİ
from typing import Optional, Dict

from core.types import MultiTimeframeAnalysis, ConsolidationPattern
from indicators.ta_manager import calculate_indicators
from filters.basic_filters import basic_filters, pre_filter_junk_stocks
from risk.stop_target_manager import _calculate_stops_targets
from risk.trade_validator import validate_trade_parameters, calculate_trade_plan
from analysis.trend_score import calculate_advanced_trend_score
from analysis.multi_timeframe import analyze_multi_timeframe_from_data
from analysis.fibonacci import calculate_fibonacci_levels
from analysis.consolidation import detect_consolidation_pattern
from analysis.support_resistance import SupportResistanceFinder
from analysis.divergence import get_divergence_score  # YENİ: Divergence tespiti
from analysis.relative_strength import calculate_relative_strength  # YENİ: RS Analizi
from analysis.volatility import detect_volatility_squeeze  # YENİ: Squeeze tespiti
from analysis.market_regime_adapter import MarketRegimeAdapter  # YENİ v2.8: Rejim adaptasyonu
from analysis.entry_timing import EntryTimingOptimizer  # YENİ v2.8: Entry timing
from patterns.price_action import PriceActionDetector
from analysis.signal_confirmation import SignalConfirmationFilter # YENİ v3.0
from analysis.ml_signal_classifier import MLSignalClassifier # YENİ v3.0
from analysis.kalman_filter import apply_kalman_smoothing # YENİ v3.0: Kalman Filter
from analysis.integration_engine import AnalysisIntegrationEngine # FAZA 1: Integration Pipeline

class SymbolAnalyzer:
    """Tek sembol için detaylı analiz"""

    def __init__(self, cfg: dict, data_handler, market_analyzer, smart_filter):
        self.cfg = cfg
        self.data_handler = data_handler
        self.market_analyzer = market_analyzer
        self.smart_filter = smart_filter

        # Alt bileşenler
        self.pattern_detector = PriceActionDetector()
        self.sr_finder = SupportResistanceFinder()
        
        # YENİ v2.8: Market Regime ve Entry Timing
        self.regime_adapter = MarketRegimeAdapter(cfg)
        self.entry_optimizer = EntryTimingOptimizer(cfg)

        # YENİ v3.0: Advanced Analysis Engines
        self.signal_confirmer = None # Initialized per symbol due to DataFrame dependency
        
        if cfg.get('use_ml_classifier', True):
            try:
                self.ml_classifier = MLSignalClassifier()
            except Exception as e:
                logging.warning(f"ML Classifier init failed: {e}")
                self.ml_classifier = None
        else:
            self.ml_classifier = None

        # FAZA 1: Integration Engine
        try:
            self.integration_engine = AnalysisIntegrationEngine(
                cfg,
                signal_confirmer=None,
                ml_classifier=self.ml_classifier,
                entry_optimizer=self.entry_optimizer
            )
            logging.info("✅ Integration Engine initialized (FAZA 1)")
        except Exception as e:
            logging.warning(f"Integration Engine init failed: {e}")
            self.integration_engine = None

        # Durdurma bayrağı
        self.stop_flag = False

    def analyze_symbol(self, symbol: str, benchmark_df: Optional[pd.DataFrame] = None, skip_filters: bool = False) -> Optional[Dict]:
        """
        Sembol için tam analiz
        
        Args:
            symbol: Hisse sembolü
            benchmark_df: Karşılaştırma için endeks verisi (opsiyonel)

        Returns:
            Sonuç dictionary'si veya None
        """
        if self.stop_flag:
            return None

        try:
            logging.debug(f"🔍 {symbol} analiz ediliyor...")

            # 1. Piyasa analizi (cache'den al, yoksa boş bırak)
            try:
                market_analysis = self.market_analyzer.get_cached_analysis()
                if market_analysis is None:
                    # Cache yoksa boş analiz kullan
                    from analysis.market_condition import _empty_market_analysis
                    market_analysis = _empty_market_analysis()
            except Exception:
                from analysis.market_condition import _empty_market_analysis
                market_analysis = _empty_market_analysis()
            
            # YENİ v2.8: Piyasa rejimini tespit et ve adaptif parametreler al
            adaptive_cfg = self.cfg.copy()
            if self.cfg.get('use_market_regime_adapter', True):
                try:
                    # Benchmark varsa kullan, yoksa boş bırak
                    regime = self.regime_adapter.detect_regime(benchmark_df) if benchmark_df is not None else 'CONSOLIDATION'
                    
                    # Trading yasak mı kontrol et
                    if not self.regime_adapter.is_trading_allowed(regime):
                        logging.debug(f"{symbol}: Trading disabled for regime {regime}")
                        return None
                    
                    # Adaptif parametreleri al ve config'e merge et
                    adaptive_params = self.regime_adapter.get_adaptive_parameters(regime)
                    adaptive_cfg.update(adaptive_params)
                    logging.debug(f"{symbol}: Using adaptive params for {regime}")
                except Exception as e:
                    logging.debug(f"{symbol}: Regime adaptation failed: {e}")

            # 2. Veri çek (timeout ile)
            df = self.data_handler.get_daily_data(symbol, self.cfg["exchange"])

            # --- Zorunlu veri temizleme ve kalite kontrolü ---
            from core.utils import clean_and_validate_df
            try:
                df = clean_and_validate_df(df)
            except Exception as e:
                logging.warning(f"{symbol}: Veri temizleme/kalite kontrol hatası: {e}")
                return None

            if df is None or len(df) < 50:
                logging.debug(f"{symbol}: Yetersiz veri")
                return None

            # 🆕 ÖN FİLTRE: Çöp hisseleri erken aşamada ele (exchange-specific)
            exchange = self.cfg.get("exchange", "BIST")
            auto_mode = self.cfg.get("filter_mode", "auto") == "auto"
            
            passed, reason = pre_filter_junk_stocks(df, exchange)
            if not skip_filters and not passed:
                logging.debug(f"{symbol}: Ön filtre başarısız - {reason}")
                return None

            # YENİ v3.0: Kalman Filter ile gürültü temizleme
            if self.cfg.get('use_kalman_filter', True):
                try:
                    df = apply_kalman_smoothing(df)
                    # Noise level logla
                    if 'price_noise' in df.columns:
                        avg_noise = df['price_noise'].mean()
                        logging.debug(f"{symbol}: Kalman noise level: {avg_noise:.4f}")
                except Exception as e:
                    logging.debug(f"{symbol}: Kalman filter error: {e}")

            # İndikatörleri hesapla
            df = calculate_indicators(df)
            if df.empty:
                return None

            latest = df.iloc[-1]

            # 3. Temel filtreler (exchange-specific) - skip_filters varsa geç
            if not skip_filters and not basic_filters(latest, self.cfg, df, exchange=exchange, auto_mode=auto_mode):
                logging.debug(f"{symbol}: Temel filtreleri geçemedi")
                return None

            # 4. Pattern analizi
            patterns = self.pattern_detector.analyze_patterns(df)
            pattern_score = self.pattern_detector.get_pattern_score(patterns)

            # 5. Teknik analizler
            analyses = self._perform_technical_analysis(df, symbol)

            # 6. Trend skoru
            
            # Trend skoru hesaplaması için benchmark verisini df'e ekle
            if benchmark_df is not None and not benchmark_df.empty:
                try:
                    # Index hizalaması yaparak merge et
                    # Sadece kapanış fiyatını al ve yeniden adlandır
                    bench_series = benchmark_df['close'].rename('benchmark_close')
                    
                    # Join işlemi (bunu yaparken orijinal df'in bozulmamasına dikkat et)
                    if 'benchmark_close' not in df.columns:
                        df = df.join(bench_series, how='left')
                        
                        # Forward fill ile eksik verileri doldur (tatil günleri vs için)
                        df['benchmark_close'] = df['benchmark_close'].ffill()
                except Exception as e:
                    logging.warning(f"{symbol}: Benchmark verisi merge edilemedi: {e}")

            score = calculate_advanced_trend_score(
                df,
                symbol,
                self.cfg,
                market_analysis={
                    "regime": market_analysis.regime,
                    "levels": analyses["sr_levels"],
                },
            )
            
            # YENİ: Risk ve Kalite metriklerini al
            risk_metrics = score.get("risk_metrics", {})
            quality_metrics = score.get("quality_metrics", {})

            # 7. YENİ: Divergence skoru
            divergence_score = 0
            divergence_desc = ""
            if self.cfg.get("use_divergence_detection", True):
                divergence_score, divergence_desc = get_divergence_score(df)
                logging.debug(f"{symbol}: Divergence {divergence_desc} (+{divergence_score})")

            # 8. YENİ: Relative Strength (RS) Analizi
            rs_data = {'rs_score': 0, 'rs_rating': 0, 'status': 'N/A'}
            if benchmark_df is not None:
                rs_data = calculate_relative_strength(df, benchmark_df)
                logging.debug(f"{symbol}: RS Score {rs_data['rs_score']}")

            # 9. YENİ: Volatility Squeeze Analizi
            squeeze_on, squeeze_status, squeeze_score = detect_volatility_squeeze(df)
            if squeeze_on:
                logging.debug(f"{symbol}: {squeeze_status} (+{squeeze_score})")

            # 10. YENİ: TV Sinyalleri (borsapy_handler üzerinden)
            tv_signals = None
            try:
                # Exchange'e göre TV sinyali (BIST, NASDAQ, vs.)
                # BorsapyHandler instance'ını swing_hunter üzerinden veya doğrudan oluşturabiliriz.
                # Ancak burada self.data_handler üzerinden erişim yok. 
                # Geçici olarak yeni instance oluşturup config'i paslayalım.
                from scanner.borsapy_handler import get_borsapy_handler
                bp_handler = get_borsapy_handler(self.cfg)
                if bp_handler:
                    tv_signals = bp_handler.get_tv_signals(symbol, self.cfg.get("exchange", "BIST"))
                    if tv_signals:
                        logging.debug(f"{symbol}: TV Sinyali alındı ({tv_signals.get('recommendation')})")
            except Exception as e:
                logging.debug(f"{symbol}: TV signal error: {e}")

            # -------------------------------------------------------------------------
            # YENİ v3.0: Signal Confirmation & ML Classification
            # -------------------------------------------------------------------------
            
            confirmation_data = None
            ml_prediction = None
            
            # 1. Signal Confirmation
            if self.cfg.get('use_signal_confirmation', True):
                try:
                    confirmer = SignalConfirmationFilter(df, self.cfg)
                    is_valid, confirmation_details = confirmer.multi_source_confirmation()
                    
                    confirmation_data = confirmation_details
                    
                    # Eğer konfirmasyon başarısızsa ve katı moddaysa, sinyali iptal et
                    if not is_valid and self.cfg.get('strict_confirmation_mode', False):
                        logging.debug(f"{symbol}: Signal confirmation failed. Skipping.")
                        return None
                        
                except Exception as e:
                    logging.debug(f"{symbol}: Signal confirmation error: {e}")

            # 2. ML Classifier
            if self.ml_classifier:
                try:
                    # ML için features hazırla
                    ml_features = {
                        'rsi': latest.get('RSI', 50),
                        'macd': latest.get('MACD_Level', 0),
                        'adx': latest.get('ADX', 0),
                        'volume_ratio': latest.get('Relative_Volume', 1.0),
                        'trend_score': score.get('total_score', 0),
                        'atr_percent': (latest.get('ATR14', 0) / latest['close'] * 100) if latest['close'] > 0 else 0,
                        'volatility': risk_metrics.get('volatility_annualized', 0) if risk_metrics else 0
                    }
                    
                    ml_prediction = self.ml_classifier.predict_signal_quality(ml_features)
                except Exception as e:
                    logging.debug(f"{symbol}: ML prediction error: {e}")

            # Toplam Skor Hesabı (RS ve Squeeze ekli)

            # Mevcut: TrendScore + Pattern/2 + Divergence/3
            # Yeni: TrendScore + Pattern/2 + Divergence/3 + Squeeze/4 + RS_Bonus
            
            rs_bonus = 0
            if rs_data['rs_score'] > 60: rs_bonus = 5
            if rs_data['rs_score'] > 80: rs_bonus = 10
            
            total_score = min(
                score["total_score"] + 
                pattern_score * 0.5 + 
                divergence_score * 0.3 + 
                squeeze_score * 0.4 +
                rs_bonus, 
                100
            )

            if not skip_filters and not score["passed"]:
                logging.debug(f"{symbol}: Trend skorunu geçemedi ({total_score:.0f})")
                return None



            # 7. Stop/Target hesaplama
            stop_loss, target1, target2 = self._calculate_trade_levels(
                df, symbol, latest
            )

            # Risk/Reward
            rr_ratio = self._calculate_rr_ratio(latest["close"], stop_loss, target1)
            risk_pct = ((latest["close"] - stop_loss) / latest["close"]) * 100

            # 8. Trade validasyonu
            validation = validate_trade_parameters(
                latest["close"], stop_loss, target1, target2, self.cfg
            )

            if not skip_filters and not validation["valid"]:
                logging.debug(f"{symbol}: Trade validasyonu başarısız")
                return None

            # 9. Trade planı
            trade = calculate_trade_plan(
                latest["close"],
                stop_loss,
                target1,
                target2,
                self.cfg,
                self.cfg.get("initial_capital", 10000),
            )

            if trade is None:
                # Trade planı oluşamadıysa (ör. stop >= price) ama skip_filters ise devam et
                if skip_filters:
                     # Dummy trade object for display
                     from core.types import TradePlan
                     trade = TradePlan(0, 0, 0, 0, 0, 0)
                else: 
                     logging.debug(f"{symbol}: Trade planı oluşturulamadı")
                     return None

            # 10. Smart filter
            if self.cfg.get("use_smart_filter", True):
                passed, smart_score, _ = self.smart_filter.evaluate_stock(
                    df, latest, {"rr_ratio": rr_ratio, "risk_pct": risk_pct}, symbol
                )

                if not skip_filters and not passed:
                    logging.debug(f"{symbol}: Smart filter'ı geçemedi")
                    return None

                total_score = max(total_score, smart_score)

            # YENİ v2.8: Entry Timing analizi
            entry_recommendation = None
            if self.cfg.get('use_entry_timing_optimizer', True):
                try:
                    entry_recommendation = self.entry_optimizer.get_entry_recommendation(df, symbol)
                except Exception as e:
                    logging.debug(f"{symbol}: Entry timing failed: {e}")

            # ⭐ FAZA 1: INTEGRATION ENGINE PIPELINE
            # =========================================================================
            # Tüm advanced analiz modüllerini bir pipeline'da birleştir
            integrated_signal = None
            if self.integration_engine and self.cfg.get('use_integration_engine', True):
                try:
                    # Base signal oluştur
                    base_signal = {
                        'symbol': symbol,
                        # Trend skoru geçtiyse BUY, aksi halde SELL
                        'signal_type': 'BUY' if score.get('passed') else 'SELL',
                        'score': total_score,
                        'rsi': latest.get('RSI', 50),
                        'macd': latest.get('MACD_Level', 0),
                        'macd_signal': latest.get('MACD_Signal', 0),
                        'atr': latest.get('ATR14', 0),
                        'atr_percent': (latest.get('ATR14', 0) / latest['close'] * 100) if latest['close'] > 0 else 0,
                        'volume_ratio': latest.get('Relative_Volume', 1.0),
                        'adx': latest.get('ADX', 0),
                        'volatility': risk_metrics.get('volatility_annualized', 0) if risk_metrics else 0,
                        'trend_score': score.get('total_score', total_score),  # Trend strength 0-100
                    }
                    
                    # Integration engine üzerinden tam pipeline'ı çalıştır
                    integrated_signal = self.integration_engine.full_analysis_pipeline(
                        symbol=symbol,
                        data=df,
                        base_signal=base_signal,
                        market_context=market_analysis
                    )
                    
                    # Entegre edilen sinyale göre toplam skoru güncelle
                    if integrated_signal and integrated_signal.is_valid:
                        old_score = total_score
                        total_score = integrated_signal.final_score
                        logging.info(
                            f"🔗 {symbol}: Integration Pipeline"
                            f" | Base={old_score:.0f} → Integrated={total_score:.0f}"
                            f" | {integrated_signal.recommendation}"
                        )
                        
                        # Eğer filtered out ise buradan dön
                        if total_score < self.cfg.get('min_signal_score', 60):
                            logging.debug(f"{symbol}: Integration filter rejected (score: {total_score:.0f})")
                            return None
                    else:
                        logging.debug(f"{symbol}: Integration pipeline did not validate signal")
                        if self.cfg.get('strict_integration_mode', False):
                            return None
                
                except Exception as e:
                    logging.debug(f"{symbol}: Integration engine error: {e}", exc_info=False)

            # 11. Sonuç oluştur
            result = self._build_result(
                symbol,
                latest,
                total_score,
                pattern_score,
                patterns,
                stop_loss,
                target1,
                target2,
                rr_ratio,
                risk_pct,
                trade,
                market_analysis,
                risk_metrics=risk_metrics,    # YENİ
                quality_metrics=quality_metrics, # YENİ
                rs_data=rs_data,      # YENİ
                squeeze_data={        # YENİ
                    "on": squeeze_on,
                    "status": squeeze_status,
                    "score": squeeze_score
                },
                divergence_desc=divergence_desc,  # YENİ
                entry_recommendation=entry_recommendation,  # YENİ v2.8
                regime=regime if 'regime' in dir() else None,  # YENİ v2.8
                tv_signals=tv_signals, # YENİ v2.10
                confirmation_data=confirmation_data, # YENİ v3.0
                ml_prediction=ml_prediction, # YENİ v3.0
                trend_score_data=score, # YENİ: Full trend score data pass
                integrated_signal=integrated_signal # FAZA 1: Integration Engine
            )

            logging.info(f"✅ {symbol}: Uygun (skor: {total_score:.0f})")
            return result

        except Exception as e:
            logging.error(f"❌ {symbol} analiz hatası: {e}", exc_info=True)
            return None

    def _perform_technical_analysis(self, df, symbol: str) -> Dict:
        """Teknik analizleri yap"""
        analyses = {}

        # Fibonacci
        if self.cfg.get("use_fibonacci", True):
            analyses["fib_analysis"] = calculate_fibonacci_levels(df)
        else:
            analyses["fib_analysis"] = {}

        # Support/Resistance
        if self.cfg.get("use_support_resistance", True):
            analyses["sr_levels"] = self.sr_finder.find_levels(df)
            analyses["breakout_info"] = self.sr_finder.check_breakout(
                df, analyses["sr_levels"]
            )
        else:
            analyses["sr_levels"] = {}
            analyses["breakout_info"] = {"breakout": False}

        # Konsolidasyon
        if self.cfg.get("use_consolidation", True):
            analyses["consolidation"] = detect_consolidation_pattern(df)
        else:
            analyses["consolidation"] = ConsolidationPattern(False, 0, 0, "", 0, 0, 0)

        # Multi-timeframe
        if self.cfg.get("use_multi_timeframe", True):
            daily, weekly = self.data_handler.get_multi_timeframe_data(
                symbol, self.cfg["exchange"]
            )
            if daily is not None and weekly is not None:
                analyses["mtf_analysis"] = analyze_multi_timeframe_from_data(
                    daily, weekly
                )
            else:
                analyses["mtf_analysis"] = MultiTimeframeAnalysis(
                    "unknown", "unknown", False, 50.0, False, "hold"
                )
        else:
            analyses["mtf_analysis"] = MultiTimeframeAnalysis(
                "unknown", "unknown", False, 50.0, False, "hold"
            )

        return analyses

    def _calculate_trade_levels(self, df, symbol: str, latest):
        """Stop/Target seviyelerini hesapla"""
        stop_loss, target1, target2 = _calculate_stops_targets(df, symbol, self.cfg)

        # Geçersiz değerleri düzelt
        if stop_loss is None or stop_loss >= latest["close"]:
            stop_loss = latest["close"] * 0.95
            risk = latest["close"] - stop_loss
            target1 = latest["close"] + risk * 2
            target2 = latest["close"] + risk * 3

        return stop_loss, target1, target2

    def _calculate_rr_ratio(self, price: float, stop: float, target: float) -> float:
        """Risk/Reward oranı hesapla"""
        if stop >= price:
            return 0.0

        risk = price - stop
        reward = target - price

        return reward / risk if risk > 0 else 0.0

    def _build_result(
        self,
        symbol: str,
        latest,
        total_score: float,
        pattern_score: float,
        patterns: dict,
        stop_loss: float,
        target1: float,
        target2: float,
        rr_ratio: float,
        risk_pct: float,
        trade,
        market_analysis,
        risk_metrics: dict = None,
        quality_metrics: dict = None,
        rs_data: dict = None,
        squeeze_data: dict = None,
        divergence_desc: str = "",
        entry_recommendation: dict = None,  # YENİ v2.8
        regime: str = None,  # YENİ v2.8
        tv_signals: dict = None, # YENİ v2.10
        confirmation_data: dict = None, # YENİ v3.0
        ml_prediction: dict = None, # YENİ v3.0
        trend_score_data: dict = None, # YENİ: Trend detail data
        integrated_signal = None # FAZA 1: Integration Engine
    ) -> Dict:
        """Sonuç dictionary'si oluştur"""

        # Sinyal gücü
        signal_strength = "🔥 Güçlü" if total_score >= 75 else "⚡ Orta"
        if pattern_score >= 15:
            signal_strength = "🎯 " + signal_strength
            
        # Squeeze durumunu ekle
        if squeeze_data and squeeze_data.get("on"):
            signal_strength += " [SQUEEZE]"

        # Bullish pattern listesi
        bullish_patterns = [p for p, detected in patterns.items() if detected]

        result = {
            "Hisse": symbol,
            "Borsa": self.cfg.get("exchange", "BIST"),
            "Fiyat": f"{latest['close']:.2f}",
            "Sinyal": signal_strength,
            "Skor": f"{int(total_score)}/100",
            "Pattern Skor": f"{pattern_score}/20",
            "Bullish Patternler": ", ".join(bullish_patterns) or "Yok",
            "Optimal Giriş": f"{latest['close']:.2f}",
            "Stop Loss": f"{stop_loss:.2f}",
            "Hedef 1": f"{target1:.2f}",
            "Hedef 2": f"{target2:.2f}",
            "R/R": f"1:{rr_ratio:.1f}",
            "Risk %": f"{risk_pct:.1f}",
            "Pozisyon": f"{trade.shares} adet",
            "Yatırım": f"{trade.shares * latest['close']:,.0f} TL",
            "Piyasa": market_analysis.regime.title(),
            "Piyasa Skoru": f"{market_analysis.market_score:.0f}/100",
        }
        
        # YENİ v2.8: Rejim bilgisi
        if regime:
            result["Market Rejimi"] = regime
        
        # YENİ v2.8: Entry timing bilgisi
        if entry_recommendation:
            rec = entry_recommendation.get('recommendation', 'N/A')
            confidence = entry_recommendation.get('overall_confidence', 0)
            result["Entry Önerisi"] = rec
            result["Entry Güven"] = f"{confidence:.0%}"
            
            # Entry info varsa optimal girişi güncelle
            entry_info = entry_recommendation.get('entry_info')
            if entry_info and 'entry_price' in entry_info:
                result["Optimal Giriş"] = f"{entry_info['entry_price']:.2f}"
                result["Sinyal Tipi"] = entry_info.get('signal_type', 'N/A')
        
        # Yeni verileri ekle
        if rs_data:
            result["RS Rating"] = f"{rs_data.get('rs_rating', 0)}/100"
            if rs_data.get('alpha'):
                result["Alpha"] = f"%{rs_data['alpha']:.2f}"
                
        if divergence_desc:
            result["Uyarı"] = divergence_desc
            
        if squeeze_data and squeeze_data.get("on"):
            result["Volatility Durumu"] = squeeze_data["status"] # Key name changed to avoid conflict
            
        # Risk ve Kalite metriklerini ekle
        if risk_metrics:
            result["Sharpe"] = f"{risk_metrics.get('sharpe_ratio', 0):.2f}"
            result["Volatilite"] = f"%{int(risk_metrics.get('volatility_annualized', 0))}"
            
        if quality_metrics:
            result["Efficiency"] = f"{quality_metrics.get('efficiency_ratio', 0):.2f}"
            
        # TV Sinyal (Her zaman ekle)
        tv_signal_str = "N/A"
        if tv_signals:
            rec = tv_signals.get('recommendation', 'N/A')
            # Türkçeleştirme
            if rec == "STRONG_BUY": tv_signal_str = "GÜÇLÜ AL"
            elif rec == "BUY": tv_signal_str = "AL"
            elif rec == "SELL": tv_signal_str = "SAT"
            elif rec == "STRONG_SELL": tv_signal_str = "GÜÇLÜ SAT"
            else: tv_signal_str = "NÖTR"
            
            # Detaylı verileri ekle (GUI'de gösterim için)
            result["tv_signal_details"] = {
                "buy": tv_signals.get("buy_count", 0),
                "sell": tv_signals.get("sell_count", 0),
                "neutral": tv_signals.get("neutral_count", 0),
                "rec": tv_signal_str,
                "oscillators": tv_signals.get("oscillators"),
                "moving_averages": tv_signals.get("moving_averages"),
                "all_indicators": tv_signals.get("all_indicators")
            }
            
        result["TV Sinyal"] = tv_signal_str
        
        # ⭐ FAZA 1: Integration Engine Results
        if integrated_signal:
            result["Integration Score"] = f"{integrated_signal.final_score:.0f}/100"
            result["Integration Status"] = "✅" if integrated_signal.is_valid else "❌"
            result["Integration Recommendation"] = integrated_signal.recommendation
            result["Integration Confidence"] = integrated_signal.confidence_level
            
            # Detaylı integration verileri (watchlist/database için)
            result["integration_data"] = {
                'final_score': integrated_signal.final_score,
                'is_valid': integrated_signal.is_valid,
                'recommendation': integrated_signal.recommendation,
                'confidence_level': integrated_signal.confidence_level,
                'confirmation_score': integrated_signal.confirmation_score,
                'ml_confidence': integrated_signal.ml_confidence,
                'entry_timing_score': integrated_signal.entry_timing_score,
                'optimal_entry_price': integrated_signal.optimal_entry_price,
                'confirmation_reasons': integrated_signal.confirmation_reasons,
                'rejection_reasons': integrated_signal.rejection_reasons,
            }
            
            logging.debug(f"Integration data stored: {len(result['integration_data'])} fields")
        
        # YENİ v3.0: Advanced Analysis sonuçları
        if confirmation_data:
            result["Onay"] = f"{confirmation_data.get('confirmation_count', 0)}/{confirmation_data.get('required_confirmations', 4)}"
            result["Onay Güven"] = f"{confirmation_data.get('confidence', 0):.0%}"
            
        if ml_prediction:
            pred_text = ml_prediction.get('prediction', 'N/A')
            prob = ml_prediction.get('probability', 0)
            
            # Formatla
            if pred_text == 'HIGH_QUALITY': pred_lbl = "YÜKSEK KALİTE"
            elif pred_text == 'MEDIUM_QUALITY': pred_lbl = "ORTA KALİTE"
            else: pred_lbl = "DÜŞÜK KALİTE"
            
            result["YZ Tahmini"] = f"{pred_lbl} ({prob:.0f}%)"
            
            result["YZ Tahmini"] = f"{pred_lbl} ({prob:.0f}%)"
            
        # -------------------------------------------------------------------------
        # RAW DATA FOR WATCHLIST (Hidden in UI but essential for persistence)
        # -------------------------------------------------------------------------
        
        # 0. Critical Price & Trade Parametrs (Floats)
        result['current_price'] = float(latest['close'])
        result['entry'] = float(latest['close']) # Scan time price is entry candidate
        result['stop'] = float(stop_loss)
        result['target1'] = float(target1)
        result['target2'] = float(target2)
        result['target3'] = 0.0 # Default
        result['rr_ratio'] = float(rr_ratio)
        result['risk_pct'] = float(risk_pct)
        
        # 1. Technical Indicators
        result['rsi'] = latest.get('RSI')
        result['adx'] = latest.get('ADX')
        result['macd'] = latest.get('MACD_Level')
        result['macd_signal'] = latest.get('MACD_Signal')
        result['macd_histogram'] = latest.get('MACD_Hist')
        result['rvol'] = latest.get('Relative_Volume')
        result['volume_ratio'] = latest.get('Relative_Volume')
        result['volume'] = latest.get('volume')
        
        # 2. Trend Info (Derived)
        main_trend = "SIDEWAYS"
        trend_strength = "WEAK"
        
        if total_score >= 80:
            main_trend = "UP"
            trend_strength = "STRONG"
        elif total_score >= 60:
            main_trend = "UP"
            trend_strength = "MEDIUM"
        elif total_score <= 30:
            main_trend = "DOWN"
            trend_strength = "WEAK"
        
        result['main_trend'] = main_trend
        result['trend_strength'] = trend_strength
        result['trend_score'] = total_score
        
        # 3. Setup Info
        # Best guess from patterns
        found_patterns = [p for p, detected in patterns.items() if detected]
        result['setup_type'] = found_patterns[0] if found_patterns else "GENERIC_SWING"

        return result

    def get_adaptive_rsi_thresholds(self, df: pd.DataFrame) -> tuple:
        """
        RSI eşiklerini volatiliteye göre uyarlı ayarla
        
        Standart: Oversold=30, Overbought=70
        Yüksek volatilite: Oversold=25, Overbought=75
        Düşük volatilite: Oversold=35, Overbought=65
        
        Returns:
            (oversold_threshold, overbought_threshold)
        """
        volatility = df['close'].pct_change().std() * 100  # Yüzde cinsinden
        
        if volatility > 3.0:  # Yüksek volatilite
            return 25, 75
        elif volatility < 1.0:  # Düşük volatilite
            return 35, 65
        else:  # Normal volatilite
            return 30, 70

    def stop_analysis(self):
        """Analizi durdur"""
        self.stop_flag = True

    def reset_stop_flag(self):
        """Durdurma bayrağını sıfırla"""
        self.stop_flag = False
