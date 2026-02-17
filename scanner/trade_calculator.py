# -*- coding: utf-8 -*-
"""
Trade Calculator - Trade plan ve validasyon hesaplamaları
"""
import logging
from typing import Dict

from risk.trade_validator import validate_trade_parameters, calculate_trade_plan


class TradeCalculator:
    """Trade planı ve validasyon hesaplamaları"""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def calculate_trade_plan(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        target1: float,
        capital: float = None,
    ) -> Dict:
        """
        Trade planını hesapla

        Args:
            symbol: Hisse sembolü
            entry_price: Giriş fiyatı
            stop_loss: Stop loss
            target1: Hedef 1
            capital: Sermaye (None ise config'den al)

        Returns:
            Trade plan dictionary
        """
        try:
            if capital is None:
                capital = self.cfg.get("initial_capital", 10000)

            # Phase 1: Multi-Level Exit Strategy
            use_multi_level = self.cfg.get("use_multi_level_exit", True)
            
            if use_multi_level:
                # 3 seviyeli hedefler
                from risk.multi_level_exit import MultiLevelExitStrategy
                
                ml_strategy = MultiLevelExitStrategy(self.cfg)
                ml_targets = ml_strategy.calculate_multi_level_targets(entry_price, stop_loss)
                
                target1 = ml_targets.get('target_1', target1)
                target2 = ml_targets.get('target_2', target1 * 1.3)
                target3 = ml_targets.get('target_3', target1 * 1.5)
            else:
                # Legacy: Single target
                target2 = target1 * 1.3
                target3 = None

            # Trade planını hesapla
            trade = calculate_trade_plan(
                entry_price=entry_price,
                stop_loss=stop_loss,
                target1=target1,
                target2=target2,
                config=self.cfg,
                account_balance=capital,
            )

            if trade:
                # Detaylı hesaplamalar
                risk_per_share = abs(entry_price - stop_loss)
                max_loss_tl = risk_per_share * trade.shares
                max_gain_tl = (target1 - entry_price) * trade.shares
                rr_ratio = (
                    (target1 - entry_price) / risk_per_share
                    if risk_per_share > 0
                    else 0
                )

                plan = {
                    "risk_per_share": risk_per_share,
                    "capital": capital,
                    "risk_pct": self.cfg.get("max_risk_pct", 2.0),
                    "shares": trade.shares,
                    "investment": entry_price * trade.shares,
                    "max_loss_tl": max_loss_tl,
                    "max_loss_pct": (max_loss_tl / capital) * 100 if capital > 0 else 0,
                    "max_gain_tl": max_gain_tl,
                    "rr_ratio": rr_ratio,
                    "recommendation": (
                        "✅ Uygun" if trade.shares > 0 else "❌ Risk yüksek"
                    ),
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "target1": target1,
                    "target2": target2,
                }
                
                # Add target3 if multi-level enabled
                if use_multi_level and target3:
                    plan["target3"] = target3
                    plan["exit_strategy"] = "MULTI_LEVEL"
                
                return plan
            else:
                return self._empty_trade_plan(capital, entry_price, stop_loss)

        except Exception as e:
            logging.error(f"Trade plan hesaplama hatası ({symbol}): {e}")
            return self._error_trade_plan(capital, str(e))


    def validate_trade_parameters(
        self, entry_price: float, stop_loss: float, target1: float, symbol: str = ""
    ) -> Dict:
        """
        Trade parametrelerini doğrula

        Returns:
            Validasyon sonuçları
        """
        try:
            target2 = target1 * 1.3

            # Ana validasyon
            result = validate_trade_parameters(
                entry_price=entry_price,
                stop_loss=stop_loss,
                target1=target1,
                target2=target2,
                config=self.cfg,
            )

            # Skor hesapla
            score = 80 if result.get("valid", False) else 40

            # Uyarılar ve hatalar
            warnings = []
            errors = []

            if not result.get("valid", False):
                errors.append(result.get("reason", "Bilinmeyen hata"))

            # Risk/Reward kontrolü
            rr_ratio = result.get("rr_ratio", 0)
            if rr_ratio < 1.5:
                warnings.append(f"Risk/Ödül oranı düşük: {rr_ratio:.1f}")

            # Stop loss mesafe kontrolü
            risk_distance = abs(entry_price - stop_loss)
            if risk_distance / entry_price > 0.15:
                warnings.append(
                    "Stop loss çok uzak "
                    f"(%{(risk_distance / entry_price) * 100:.1f} risk)"
                )

            return {
                "score": score,
                "is_valid": result.get("valid", False),
                "has_warnings": len(warnings) > 0,
                "warnings": warnings,
                "errors": errors,
                "rr_ratio": rr_ratio,
                "risk_distance_pct": (risk_distance / entry_price) * 100,
            }

        except Exception as e:
            logging.error(f"Trade validasyon hatası: {e}")
            return {
                "score": 0,
                "is_valid": False,
                "has_warnings": True,
                "warnings": [],
                "errors": [f"Validasyon hatası: {str(e)}"],
                "rr_ratio": 0,
                "risk_distance_pct": 0,
            }

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        capital: float = None,
        risk_pct: float = None,
    ) -> Dict:
        """
        Pozisyon büyüklüğü hesapla

        Returns:
            Pozisyon detayları
        """
        if capital is None:
            capital = self.cfg.get("initial_capital", 10000)

        if risk_pct is None:
            risk_pct = self.cfg.get("max_risk_pct", 2.0)

        try:
            # Risk miktarı
            risk_amount = capital * (risk_pct / 100)

            # Hisse başı risk
            risk_per_share = abs(entry_price - stop_loss)

            if risk_per_share <= 0:
                return {
                    "shares": 0,
                    "investment": 0,
                    "risk_amount": risk_amount,
                    "error": "Geçersiz stop loss seviyesi",
                }

            # Hisse sayısı
            shares = int(risk_amount / risk_per_share)

            # Yatırım tutarı
            investment = shares * entry_price

            return {
                "shares": shares,
                "investment": investment,
                "risk_amount": risk_amount,
                "risk_per_share": risk_per_share,
                "risk_pct": risk_pct,
                "capital": capital,
            }

        except Exception as e:
            logging.error(f"Pozisyon hesaplama hatası: {e}")
            return {"shares": 0, "investment": 0, "risk_amount": 0, "error": str(e)}

    def _empty_trade_plan(self, capital: float, entry: float, stop: float) -> Dict:
        """Boş trade plan döndür"""
        return {
            "risk_per_share": abs(entry - stop),
            "capital": capital,
            "risk_pct": 0,
            "shares": 0,
            "investment": 0,
            "max_loss_tl": 0,
            "max_loss_pct": 0,
            "max_gain_tl": 0,
            "rr_ratio": 0,
            "recommendation": "❌ Trade planı oluşturulamadı",
            "entry_price": entry,
            "stop_loss": stop,
            "target1": 0,
            "target2": 0,
        }

    def _error_trade_plan(self, capital: float, error_msg: str) -> Dict:
        """Hatalı trade plan döndür"""
        return {
            "risk_per_share": 0,
            "capital": capital,
            "risk_pct": 0,
            "shares": 0,
            "investment": 0,
            "max_loss_tl": 0,
            "max_loss_pct": 0,
            "max_gain_tl": 0,
            "rr_ratio": 0,
            "recommendation": f"❌ Hata: {error_msg}",
            "entry_price": 0,
            "stop_loss": 0,
            "target1": 0,
            "target2": 0,
        }
