# -*- coding: utf-8 -*-
"""
Watchlist Manager (V2.0) - Enhanced Business Logic
CRUD operations, alert management, status tracking, and archive functionality
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import (
    WatchlistEntry, WatchlistSnapshot, WatchlistAlert,
    WatchlistAuditLog, TradeExecution, TradeJournal,
    SectorPerformanceHistory,
    get_session, StatusLabel, SetupStatus, AlertType
)
from .risk_manager import RiskManager
from .correlation_analyzer import CorrelationAnalyzer

logger = logging.getLogger(__name__)


class WatchlistManager:
    """
    Watchlist CRUD operasyonları ve business logic (V2.0)
    - Genişletilmiş veri yönetimi
    - Alarm sistemi
    - Durum etiketleri
    - Otomatik temizleme ve arşivleme
    """
    
    def __init__(self, db_path: str = 'watchlist.db'):
        """
        Args:
            db_path: SQLite database dosya yolu
        """
        self.db_path = db_path
        self.session: Optional[Session] = None
    
    def _get_session(self) -> Session:
        """Session lazy loading"""
        if self.session is None:
            self.session = get_session(self.db_path)
        return self.session
    
    # =========================================================================
    # AUDIT LOGGING (V3.0)
    # =========================================================================

    def _log_audit(
        self, 
        entry_id: int, 
        action: str, 
        old_val: str = None, 
        new_val: str = None, 
        desc: str = None,
        context: str = "Manual",
        session: Session = None
    ):
        """
        Değişiklikleri denetim günlüğüne kaydet
        """
        try:
            should_close = False
            if session is None:
                session = self._get_session()
                # If we are creating a new transaction, allow commit? 
                # Ideally audit is part of the main transaction.
                
            audit = WatchlistAuditLog(
                watchlist_entry_id=entry_id,
                timestamp=datetime.now(),
                action_type=action,
                old_value=str(old_val) if old_val is not None else None,
                new_value=str(new_val) if new_val is not None else None,
                user_context=context,
                description=desc
            )
            session.add(audit)
            # Commit is handled by the caller transaction usually
            
        except Exception as e:
            logger.error(f"❌ Audit log error: {e}")

    # =========================================================================
    # TEMEL CRUD OPERASYONLARİ
    # =========================================================================
    
    def add_to_watchlist(
        self, 
        symbol: str, 
        exchange: str, 
        scan_result: Dict,
        notes: str = "",
        identity_info: Dict = None,
        psychological_flags: Dict = None
    ) -> bool:
        """
        Hisseyi watchlist'e ekle ve ilk snapshot'ı oluştur
        """
        try:
            session = self._get_session()
            
            # Duplicate kontrolü
            existing = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if existing:
                logger.warning(f"⚠️ {symbol} zaten watchlist'te (ID: {existing.id})")
                return False
            
            # Identity info
            identity = identity_info or {}
            psych = psychological_flags or {}
            
            # Yeni entry oluştur
            entry = WatchlistEntry(
                symbol=symbol,
                exchange=exchange,
                added_date=datetime.now(),
                notes=notes,
                is_active=True,
                
                # Kimlik bilgileri
                sector=identity.get('sector'),
                sub_sector=identity.get('sub_sector'),
                index_membership=identity.get('index_membership'),
                float_ratio=identity.get('float_ratio'),
                avg_daily_volume=identity.get('avg_daily_volume'),
                liquidity_score=identity.get('liquidity_score'),
                market_cap=identity.get('market_cap'),
                
                # Durum
                status_label="ACTIVE",
                setup_status="EARLY",
                estimated_days=None,
                last_check_date=datetime.now(),
                days_in_list=0,
                
                # Psikolojik filtreler
                psychological_risk=psych.get('psychological_risk', False),
                previously_failed=psych.get('previously_failed', False),
                high_volatility_risk=psych.get('high_volatility_risk', False),
                news_dependent=psych.get('news_dependent', False),
                manipulation_history=psych.get('manipulation_history', False),
            )
            
            session.add(entry)
            session.flush()  # ID'yi almak için
            
            # Audit Log
            self._log_audit(
                entry.id, 
                "CREATE", 
                new_val=f"{symbol} added", 
                desc="Initial add to watchlist",
                session=session
            )
            
            # İlk snapshot oluştur
            snapshot = self._create_snapshot_from_scan(entry.id, scan_result)
            session.add(snapshot)
            
            session.commit()
            
            logger.info(f"✅ {symbol} watchlist'e eklendi (ID: {entry.id})")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Database error: {e}")
            session.rollback()
            return False
    
    def _create_snapshot_from_scan(
        self, 
        entry_id: int, 
        scan_result: Dict
    ) -> WatchlistSnapshot:
        """
        Tarama sonucundan kapsamlı snapshot oluştur (V2.0)
        
        Args:
            entry_id: WatchlistEntry ID
            scan_result: Tarama sonuç dictionary
        
        Returns:
            WatchlistSnapshot objesi
        """
        current_price = scan_result.get('current_price', 0.0)
        stop_loss = scan_result.get('stop')
        target1 = scan_result.get('target1')
        target2 = scan_result.get('target2')
        
        # R/R hesapla
        rr_ratio = None
        risk_percent = None
        if current_price and stop_loss and stop_loss < current_price:
            risk = current_price - stop_loss
            risk_percent = (risk / current_price) * 100
            if target1 and target1 > current_price:
                reward = target1 - current_price
                rr_ratio = reward / risk if risk > 0 else 0
        
        # Mesafe hesapla
        distance_to_stop = None
        distance_to_t1 = None
        distance_to_t2 = None
        if current_price > 0:
            if stop_loss:
                distance_to_stop = ((current_price - stop_loss) / current_price) * 100
            if target1:
                distance_to_t1 = ((target1 - current_price) / current_price) * 100
            if target2:
                distance_to_t2 = ((target2 - current_price) / current_price) * 100
        
        # ATR percent
        atr = scan_result.get('atr')
        atr_percent = (atr / current_price * 100) if atr and current_price > 0 else None
        
        # Risk metrics
        risk_metrics = scan_result.get('risk_metrics', {}) or {}
        quality_metrics = scan_result.get('quality_metrics', {}) or {}
        rs_data = scan_result.get('rs_data', {}) or {}
        squeeze_data = scan_result.get('squeeze_data', {}) or {}
        confirmation_data = scan_result.get('confirmation_data', {}) or {}
        ml_prediction = scan_result.get('ml_prediction', {}) or {}
        entry_recommendation = scan_result.get('entry_recommendation', {}) or {}
        tv_signals = scan_result.get('tv_signal_details', {}) or {}
        
        snapshot = WatchlistSnapshot(
            watchlist_entry_id=entry_id,
            snapshot_date=datetime.now(),
            
            # Fiyat
            price=current_price,
            entry_price=current_price if current_price > 0 else scan_result.get('entry'),
            trigger_price=scan_result.get('trigger_price'),
            stop_loss=stop_loss,
            target1=target1,
            target2=target2,
            target3=scan_result.get('target3'),
            
            # R/R
            rr_ratio=rr_ratio,
            risk_percent=risk_percent,
            
            # Trend
            main_trend=scan_result.get('main_trend'),
            trend_strength=scan_result.get('trend_strength'),
            ma_alignment=scan_result.get('ma_alignment'),
            setup_type=scan_result.get('setup_type', scan_result.get('signal_type')),
            structure_type=scan_result.get('structure_type'),
            
            # Temel indikatörler
            rsi=scan_result.get('rsi') if scan_result.get('rsi') is not None else scan_result.get('RSI'),
            rsi_trend=scan_result.get('rsi_trend'),
            macd=scan_result.get('macd') if scan_result.get('macd') is not None else scan_result.get('MACD'),
            macd_signal=scan_result.get('macd_signal'),
            macd_histogram=scan_result.get('macd_histogram'),
            adx=scan_result.get('adx') if scan_result.get('adx') is not None else scan_result.get('ADX'),
            plus_di=scan_result.get('plus_di'),
            minus_di=scan_result.get('minus_di'),
            
            # Hacim
            volume=scan_result.get('volume'),
            volume_avg=scan_result.get('volume_avg'),
            volume_ratio=scan_result.get('volume_ratio'),
            rvol=scan_result.get('rvol') if scan_result.get('rvol') is not None else scan_result.get('RVOL'),
            volume_confirms_price=scan_result.get('volume_confirms_price'),
            
            # Volatilite
            atr=atr,
            atr_percent=atr_percent,
            volatility_annualized=risk_metrics.get('volatility_annualized'),
            volatility_status=scan_result.get('volatility_status'),
            squeeze_status=squeeze_data.get('status'),
            
            # Performans
            rs_rating=rs_data.get('rs_rating', scan_result.get('rs_rating')),
            rs_score=rs_data.get('rs_score'),
            alpha=rs_data.get('alpha'),
            beta=scan_result.get('beta'),
            sharpe_ratio=risk_metrics.get('sharpe_ratio', scan_result.get('sharpe')),
            efficiency_ratio=quality_metrics.get('efficiency_ratio', scan_result.get('swing_efficiency')),
            
            # Gelişmiş
            divergence_info=scan_result.get('divergence_desc'),
            tv_signal=scan_result.get('tv_signal'),
            tv_buy_count=tv_signals.get('buy'),
            tv_sell_count=tv_signals.get('sell'),
            tv_neutral_count=tv_signals.get('neutral'),
            
            # ML
            ml_quality=ml_prediction.get('prediction', scan_result.get('ml_quality')),
            ml_confidence=ml_prediction.get('probability'),
            confirmation_count=confirmation_data.get('confirmation_count'),
            confirmation_required=confirmation_data.get('required_confirmations'),
            confirmation_confidence=confirmation_data.get('confidence'),
            
            # Mevcut
            trend_score=scan_result.get('trend_score'),
            swing_efficiency=scan_result.get('swing_efficiency'),
            market_regime=scan_result.get('market_regime'),
            signal_type=scan_result.get('signal_type', 'UNKNOWN'),
            signal_strength=scan_result.get('signal_strength'),
            confidence=scan_result.get('confidence', 0.5),
            confirmations_count=scan_result.get('confirmations', 0),
            
            # Entry timing
            entry_recommendation=entry_recommendation.get('recommendation'),
            entry_confidence=entry_recommendation.get('overall_confidence'),
            optimal_entry_price=entry_recommendation.get('entry_info', {}).get('entry_price') if entry_recommendation.get('entry_info') else None,
            
            # Mesafeler
            distance_to_stop_pct=distance_to_stop,
            distance_to_target1_pct=distance_to_t1,
            distance_to_target2_pct=distance_to_t2,
            daily_change_pct=scan_result.get('daily_change_pct'),
        )
        
        return snapshot
    
    def remove_from_watchlist(self, symbol: str, exchange: str = None, archive_reason: str = None) -> bool:
        """
        Hisseyi watchlist'ten çıkar (arşivleme ile)
        
        Args:
            symbol: Sembol adı
            exchange: Borsa (None = tüm exchange'lerdeki)
            archive_reason: Arşivleme nedeni
        
        Returns:
            True = başarılı, False = bulunamadı
        """
        try:
            session = self._get_session()
            
            query = session.query(WatchlistEntry).filter_by(symbol=symbol, is_active=True)
            if exchange:
                query = query.filter_by(exchange=exchange)
            
            entry = query.first()
            
            if not entry:
                logger.warning(f"⚠️ {symbol} watchlist'te bulunamadı")
                return False
            
            # Arşivle (soft delete yerine arşiv bilgisi ekle)
            old_status = entry.status_label
            entry.is_active = False
            entry.archived_date = datetime.now()
            entry.archive_reason = archive_reason or "Manual removal"
            entry.status_label = "PASSIVE"
            
            # Audit Log
            self._log_audit(
                entry.id, 
                "ARCHIVE", 
                old_val=old_status,
                new_val="PASSIVE", 
                desc=f"Reason: {entry.archive_reason}",
                session=session
            )
            
            session.commit()
            
            logger.info(f"✅ {symbol} watchlist'ten çıkarıldı (Neden: {archive_reason})")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Database error: {e}")
            session.rollback()
            return False
    
    def get_active_watchlist(self, status_filter: str = None) -> List[Dict]:
        """
        Aktif watchlist'i getir (son snapshot bilgileriyle)
        
        Args:
            status_filter: Durum filtresi (ACTIVE, WAIT, ALARM, PASSIVE)
        
        Returns:
            List of dictionaries
        """
        try:
            session = self._get_session()
            
            query = session.query(WatchlistEntry).filter_by(is_active=True)
            
            if status_filter:
                query = query.filter_by(status_label=status_filter)
            
            entries = query.all()
            
            result = []
            for entry in entries:
                # Son snapshot
                latest_snapshot = entry.snapshots[-1] if entry.snapshots else None
                # İlk snapshot
                first_snapshot = entry.snapshots[0] if entry.snapshots else None
                
                # Aktif alarm sayısı
                active_alerts = len([a for a in entry.alerts if a.is_active])
                
                # Gün sayısı güncelle
                days = (datetime.now() - entry.added_date).days
                
                result.append({
                    'id': entry.id,
                    'symbol': entry.symbol,
                    'exchange': entry.exchange,
                    'added_date': entry.added_date,
                    'notes': entry.notes,
                    'snapshots_count': len(entry.snapshots),
                    
                    # Kimlik
                    'sector': entry.sector,
                    'sub_sector': entry.sub_sector,
                    'index_membership': entry.index_membership,
                    'float_ratio': entry.float_ratio,
                    'avg_daily_volume': entry.avg_daily_volume,
                    'liquidity_score': entry.liquidity_score,
                    'market_cap': entry.market_cap,
                    
                    # Durum
                    'status_label': entry.status_label,
                    'status_emoji': entry.status_emoji,
                    'setup_status': entry.setup_status,
                    'estimated_days': entry.estimated_days,
                    'last_check_date': entry.last_check_date,
                    'days_in_list': days,
                    
                    # Psikolojik
                    'psychological_risk': entry.psychological_risk,
                    'previously_failed': entry.previously_failed,
                    'high_volatility_risk': entry.high_volatility_risk,
                    'news_dependent': entry.news_dependent,
                    'manipulation_history': entry.manipulation_history,
                    
                    # İşlem geçmişi
                    'total_trades': entry.total_trades,
                    'winning_trades': entry.winning_trades,
                    'losing_trades': entry.losing_trades,
                    
                    # Alarmlar
                    'active_alerts': active_alerts,
                    
                    # Snapshots
                    'latest_snapshot': self._snapshot_to_dict(latest_snapshot) if latest_snapshot else None,
                    'first_snapshot': self._snapshot_to_dict(first_snapshot) if first_snapshot else None,
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Database error: {e}")
            return []
    
    def create_snapshot(self, symbol: str, exchange: str, scan_result: Dict) -> bool:
        """
        Belirtilen sembol için yeni snapshot oluştur
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
            scan_result: Güncel tarama sonucu
        
        Returns:
            True = başarılı, False = hata
        """
        try:
            session = self._get_session()
            
            # Entry bul
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                logger.warning(f"⚠️ {symbol} watchlist'te bulunamadı")
                return False
            
            # Yeni snapshot
            snapshot = self._create_snapshot_from_scan(entry.id, scan_result)
            session.add(snapshot)
            
            # Son kontrol tarihini güncelle
            entry.last_check_date = datetime.now()
            entry.days_in_list = (datetime.now() - entry.added_date).days
            
            # Risk skorunu güncelle (V3.0)
            if 'risk_score' in scan_result:
                entry.risk_score = scan_result.get('risk_score')
            
            session.commit()
            
            logger.info(f"✅ {symbol} için yeni snapshot oluşturuldu")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Database error: {e}")
            session.rollback()
            return False
    
    # =========================================================================
    # DURUM ETİKETLERİ
    # =========================================================================
    
    def update_status_label(self, symbol: str, exchange: str, new_status: str) -> bool:
        """
        Sembolün durum etiketini güncelle
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
            new_status: Yeni durum (ACTIVE, WAIT, ALARM, PASSIVE)
        
        Returns:
            True = başarılı
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                return False
            
            old_status = entry.status_label
            entry.status_label = new_status
            entry.last_check_date = datetime.now()
            
            # Audit Log
            self._log_audit(
                entry.id, 
                "STATUS_CHANGE", 
                old_val=old_status,
                new_val=new_status, 
                desc="Manual status update",
                session=session
            )
            
            session.commit()
            
            logger.info(f"✅ {symbol} durumu güncellendi: {new_status}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Status update error: {e}")
            session.rollback()
            return False
    
    def update_setup_status(self, symbol: str, exchange: str, setup_status: str, estimated_days: int = None) -> bool:
        """
        Setup durumunu güncelle
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
            setup_status: READY, APPROACHING, EARLY, EXPIRED
            estimated_days: Tahmini gün sayısı
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                return False
            
            old_setup = entry.setup_status
            entry.setup_status = setup_status
            if estimated_days is not None:
                entry.estimated_days = estimated_days
            entry.last_check_date = datetime.now()
            
            # Audit Log
            self._log_audit(
                entry.id, 
                "SETUP_UPDATE", 
                old_val=old_setup,
                new_val=setup_status, 
                desc=f"Est. Days: {estimated_days}",
                session=session
            )
            
            session.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Setup status update error: {e}")
            session.rollback()
            return False
    
    # =========================================================================
    # ALARM SİSTEMİ
    # =========================================================================
    
    def create_alert(
        self,
        symbol: str,
        exchange: str,
        alert_type: str,
        trigger_value: float,
        condition: str = "ABOVE",
        description: str = None
    ) -> bool:
        """
        Yeni alarm oluştur
        
        Args:
            symbol: Sembol
            exchange: Borsa
            alert_type: PRICE_ABOVE, PRICE_BELOW, VOLUME_SPIKE, RSI_OVERSOLD, etc.
            trigger_value: Tetik değeri
            condition: ABOVE, BELOW, CROSS_UP, CROSS_DOWN
            description: Açıklama
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                logger.warning(f"⚠️ {symbol} bulunamadı")
                return False
            
            alert = WatchlistAlert(
                watchlist_entry_id=entry.id,
                created_date=datetime.now(),
                alert_type=alert_type,
                trigger_value=trigger_value,
                condition=condition,
                description=description or f"{alert_type} @ {trigger_value}",
                is_active=True,
                triggered=False
            )
            
            session.add(alert)
            
            # Entry durumunu ALARM olarak güncelle
            entry.status_label = "ALARM"
            
            session.commit()
            
            logger.info(f"✅ {symbol} için alarm oluşturuldu: {alert_type} @ {trigger_value}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Alert creation error: {e}")
            session.rollback()
            return False
    
    def get_active_alerts(self, symbol: str = None) -> List[Dict]:
        """
        Aktif alarmları getir
        
        Args:
            symbol: Belirli sembol (None = tümü)
        """
        try:
            session = self._get_session()
            
            query = session.query(WatchlistAlert).filter_by(is_active=True, triggered=False)
            
            if symbol:
                # Sembol'e göre filtrele
                entry = session.query(WatchlistEntry).filter_by(symbol=symbol, is_active=True).first()
                if entry:
                    query = query.filter_by(watchlist_entry_id=entry.id)
            
            alerts = query.all()
            
            result = []
            for alert in alerts:
                result.append({
                    'id': alert.id,
                    'symbol': alert.entry.symbol,
                    'exchange': alert.entry.exchange,
                    'alert_type': alert.alert_type,
                    'trigger_value': alert.trigger_value,
                    'condition': alert.condition,
                    'description': alert.description,
                    'created_date': alert.created_date,
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Get alerts error: {e}")
            return []
    
    def check_alerts(self, current_data: Dict[str, Dict]) -> List[Dict]:
        """
        Tüm aktif alarmları kontrol et
        
        Args:
            current_data: {'SYMBOL': {'price': x, 'rsi': y, 'volume': z, ...}, ...}
        
        Returns:
            Tetiklenen alarmların listesi
        """
        triggered = []
        
        try:
            session = self._get_session()
            
            active_alerts = session.query(WatchlistAlert).filter_by(
                is_active=True, 
                triggered=False
            ).all()
            
            for alert in active_alerts:
                symbol = alert.entry.symbol
                
                if symbol not in current_data:
                    continue
                
                data = current_data[symbol]
                is_triggered = False
                triggered_value = None
                
                # Alarm tipine göre kontrol
                if alert.alert_type == "PRICE_ABOVE":
                    if data.get('price', 0) >= alert.trigger_value:
                        is_triggered = True
                        triggered_value = data['price']
                        
                elif alert.alert_type == "PRICE_BELOW":
                    if data.get('price', 0) <= alert.trigger_value:
                        is_triggered = True
                        triggered_value = data['price']
                        
                elif alert.alert_type == "VOLUME_SPIKE":
                    if data.get('volume_ratio', 0) >= alert.trigger_value:
                        is_triggered = True
                        triggered_value = data['volume_ratio']
                        
                elif alert.alert_type == "RSI_OVERSOLD":
                    if data.get('rsi', 100) <= alert.trigger_value:
                        is_triggered = True
                        triggered_value = data['rsi']
                        
                elif alert.alert_type == "RSI_OVERBOUGHT":
                    if data.get('rsi', 0) >= alert.trigger_value:
                        is_triggered = True
                        triggered_value = data['rsi']
                        
                elif alert.alert_type == "STOP_PROXIMITY":
                    # Stop'a yakınlık kontrolü
                    price = data.get('price', 0)
                    stop = data.get('stop_loss', 0)
                    if price > 0 and stop > 0:
                        distance_pct = ((price - stop) / price) * 100
                        if distance_pct <= alert.trigger_value:
                            is_triggered = True
                            triggered_value = distance_pct
                            
                elif alert.alert_type == "TARGET_PROXIMITY":
                    # Hedefe yakınlık kontrolü
                    price = data.get('price', 0)
                    target = data.get('target1', 0)
                    if price > 0 and target > price:
                        distance_pct = ((target - price) / price) * 100
                        if distance_pct <= alert.trigger_value:
                            is_triggered = True
                            triggered_value = distance_pct
                
                if is_triggered:
                    alert.triggered = True
                    alert.triggered_date = datetime.now()
                    alert.triggered_value = triggered_value
                    
                    triggered.append({
                        'symbol': symbol,
                        'exchange': alert.entry.exchange,
                        'alert_type': alert.alert_type,
                        'trigger_value': alert.trigger_value,
                        'triggered_value': triggered_value,
                        'description': alert.description,
                    })
            
            session.commit()
            
            if triggered:
                logger.info(f"🔔 {len(triggered)} alarm tetiklendi!")
            
            return triggered
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Check alerts error: {e}")
            return []
    
    def delete_alert(self, alert_id: int) -> bool:
        """Alarmı sil"""
        try:
            session = self._get_session()
            
            alert = session.query(WatchlistAlert).filter_by(id=alert_id).first()
            if alert:
                session.delete(alert)
                session.commit()
                return True
            return False
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Delete alert error: {e}")
            return False
    
    # =========================================================================
    # ARŞİV VE OTOMATİK TEMİZLİK
    # =========================================================================
    
    def get_archived_entries(self, days: int = 30) -> List[Dict]:
        """
        Arşivlenmiş kayıtları getir
        
        Args:
            days: Son N gün (0 = tümü)
        """
        try:
            session = self._get_session()
            
            query = session.query(WatchlistEntry).filter_by(is_active=False)
            
            if days > 0:
                cutoff = datetime.now() - timedelta(days=days)
                query = query.filter(WatchlistEntry.archived_date >= cutoff)
            
            entries = query.order_by(WatchlistEntry.archived_date.desc()).all()
            
            result = []
            for entry in entries:
                latest = entry.snapshots[-1] if entry.snapshots else None
                
                result.append({
                    'id': entry.id,
                    'symbol': entry.symbol,
                    'exchange': entry.exchange,
                    'added_date': entry.added_date,
                    'archived_date': entry.archived_date,
                    'archive_reason': entry.archive_reason,
                    'days_in_list': entry.days_in_list,
                    'final_price': latest.price if latest else None,
                    'final_rr': latest.rr_ratio if latest else None,
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Get archived error: {e}")
            return []
    
    def auto_cleanup(self, current_data: Dict[str, Dict] = None) -> Dict:
        """
        Otomatik temizleme kurallarını uygula
        
        Kurallar:
        1. Trend bozulduysa (main_trend = DOWN)
        2. Stop seviyesi çalıştıysa (price <= stop_loss)
        3. Setup süresi uzadıysa (>14 gün, hareket yok)
        
        Returns:
            {'cleaned': int, 'reasons': {'trend_broken': X, 'stop_hit': Y, ...}}
        """
        result = {'cleaned': 0, 'reasons': {}}
        
        try:
            session = self._get_session()
            
            entries = session.query(WatchlistEntry).filter_by(is_active=True).all()
            
            for entry in entries:
                remove_reason = None
                
                # Son snapshot
                latest = entry.snapshots[-1] if entry.snapshots else None
                
                if latest:
                    # Current data varsa kullan, yoksa snapshot'taki fiyatı kullan
                    current_price = latest.price
                    if current_data and entry.symbol in current_data:
                        current_price = current_data[entry.symbol].get('price', latest.price)
                    
                    # Kural 1: Stop hit
                    if latest.stop_loss and current_price <= latest.stop_loss:
                        remove_reason = "Stop seviyesi çalıştı"
                    
                    # Kural 2: Trend bozuldu
                    elif latest.main_trend == "DOWN":
                        remove_reason = "Trend bozuldu"
                
                # Kural 3: Süre aşımı (14 gün)
                days = (datetime.now() - entry.added_date).days
                if days > 14 and entry.setup_status in ["EARLY", "APPROACHING"]:
                    remove_reason = "Setup süresi doldu"
                
                if remove_reason:
                    entry.is_active = False
                    entry.archived_date = datetime.now()
                    entry.archive_reason = remove_reason
                    entry.status_label = "PASSIVE"
                    
                    # Audit Log (V3.0)
                    self._log_audit(
                        entry.id,
                        "AUTO_CLEANUP",
                        old_val="ACTIVE",
                        new_val="PASSIVE",
                        desc=f"Auto cleanup: {remove_reason}",
                        context="Auto-Cleanup",
                        session=session
                    )
                    
                    result['cleaned'] += 1
                    result['reasons'][remove_reason] = result['reasons'].get(remove_reason, 0) + 1
                    
                    logger.info(f"🧹 {entry.symbol} arşivlendi: {remove_reason}")
            
            session.commit()
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Auto cleanup error: {e}")
            return result
    
    # =========================================================================
    # YARDIMCI METODLAR
    # =========================================================================
    
    def _snapshot_to_dict(self, snapshot: WatchlistSnapshot) -> Dict:
        """Snapshot'ı dictionary'ye çevir (V2.0 - genişletilmiş)"""
        if not snapshot:
            return {}
            
        return {
            'id': snapshot.id,
            'date': snapshot.snapshot_date,
            
            # Fiyat
            'price': snapshot.price,
            'entry_price': snapshot.entry_price,
            'trigger_price': snapshot.trigger_price,
            'stop_loss': snapshot.stop_loss,
            'target1': snapshot.target1,
            'target2': snapshot.target2,
            'target3': snapshot.target3,
            'rr_ratio': snapshot.rr_ratio,
            'risk_percent': snapshot.risk_percent,
            
            # Trend
            'main_trend': snapshot.main_trend,
            'trend_strength': snapshot.trend_strength,
            'ma_alignment': snapshot.ma_alignment,
            'setup_type': snapshot.setup_type,
            'structure_type': snapshot.structure_type,
            
            # İndikatörler
            'rsi': snapshot.rsi,
            'rsi_trend': snapshot.rsi_trend,
            'macd': snapshot.macd,
            'macd_signal': snapshot.macd_signal,
            'macd_histogram': snapshot.macd_histogram,
            'adx': snapshot.adx,
            'plus_di': snapshot.plus_di,
            'minus_di': snapshot.minus_di,
            
            # Hacim
            'volume': snapshot.volume,
            'volume_avg': snapshot.volume_avg,
            'volume_ratio': snapshot.volume_ratio,
            'rvol': snapshot.rvol,
            'volume_confirms_price': snapshot.volume_confirms_price,
            
            # Volatilite
            'atr': snapshot.atr,
            'atr_percent': snapshot.atr_percent,
            'volatility_annualized': snapshot.volatility_annualized,
            'volatility_status': snapshot.volatility_status,
            'squeeze_status': snapshot.squeeze_status,
            
            # Performans
            'rs_rating': snapshot.rs_rating,
            'rs_score': snapshot.rs_score,
            'alpha': snapshot.alpha,
            'beta': snapshot.beta,
            'sharpe_ratio': snapshot.sharpe_ratio,
            'efficiency_ratio': snapshot.efficiency_ratio,
            
            # Gelişmiş
            'divergence_info': snapshot.divergence_info,
            'tv_signal': snapshot.tv_signal,
            'tv_buy_count': snapshot.tv_buy_count,
            'tv_sell_count': snapshot.tv_sell_count,
            'tv_neutral_count': snapshot.tv_neutral_count,
            
            # ML
            'ml_quality': snapshot.ml_quality,
            'ml_confidence': snapshot.ml_confidence,
            'confirmation_count': snapshot.confirmation_count,
            'confirmation_required': snapshot.confirmation_required,
            'confirmation_confidence': snapshot.confirmation_confidence,
            
            # Mevcut
            'trend_score': snapshot.trend_score,
            'swing_efficiency': snapshot.swing_efficiency,
            'market_regime': snapshot.market_regime,
            'signal_type': snapshot.signal_type,
            'signal_strength': snapshot.signal_strength,
            'confidence': snapshot.confidence,
            'confirmations_count': snapshot.confirmations_count,
            
            # Entry
            'entry_recommendation': snapshot.entry_recommendation,
            'entry_confidence': snapshot.entry_confidence,
            'optimal_entry_price': snapshot.optimal_entry_price,
            
            # Mesafeler
            'distance_to_stop_pct': snapshot.distance_to_stop_pct,
            'distance_to_target1_pct': snapshot.distance_to_target1_pct,
            'distance_to_target2_pct': snapshot.distance_to_target2_pct,
            'daily_change_pct': snapshot.daily_change_pct,
        }
    
    def get_watchlist_history(
        self, 
        symbol: str, 
        exchange: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Sembolün geçmiş snapshot'larını getir
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
            days: Kaç gün geriye (0 = tüm geçmiş)
        
        Returns:
            List of snapshot dictionaries
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                return []
            
            snapshots = entry.snapshots
            
            # Son N gün filtresi (opsiyonel)
            if days > 0:
                cutoff_date = datetime.now() - timedelta(days=days)
                snapshots = [s for s in snapshots if s.snapshot_date >= cutoff_date]
            
            return [self._snapshot_to_dict(s) for s in snapshots]
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Database error: {e}")
            return []
    
    def close(self):
        """Database bağlantısını kapat"""
        if self.session:
            self.session.close()
            self.session = None

    def add_multiple_to_watchlist(
        self,
        items: List[Dict],
    ) -> Dict:
        """
        Birden fazla hisseyi watchlist'e ekle (toplu ekleme)
        
        Args:
            items: [{'symbol': 'X', 'exchange': 'BIST', 'scan_result': {...}, 'notes': ''}, ...]
        
        Returns:
            {'added': int, 'skipped': int, 'failed': int, 'details': [...]}
        """
        result = {
            'added': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        for item in items:
            symbol = item.get('symbol', '')
            exchange = item.get('exchange', 'BIST')
            scan_result = item.get('scan_result', {})
            notes = item.get('notes', '')
            identity_info = item.get('identity_info', {})
            psychological_flags = item.get('psychological_flags', {})
            
            if not symbol:
                result['failed'] += 1
                result['details'].append({'symbol': 'EMPTY', 'status': 'failed', 'reason': 'Empty symbol'})
                continue
            
            try:
                success = self.add_to_watchlist(
                    symbol, exchange, scan_result, notes,
                    identity_info, psychological_flags
                )
                if success:
                    result['added'] += 1
                    result['details'].append({'symbol': symbol, 'status': 'added'})
                else:
                    result['skipped'] += 1
                    result['details'].append({'symbol': symbol, 'status': 'skipped', 'reason': 'Already exists'})
            except Exception as e:
                result['failed'] += 1
                result['details'].append({'symbol': symbol, 'status': 'failed', 'reason': str(e)})
                logger.error(f"❌ Error adding {symbol}: {e}")
        
        logger.info(f"✅ Bulk add complete: {result['added']} added, {result['skipped']} skipped, {result['failed']} failed")
        return result

    def refresh_all_snapshots(self, scan_results: Dict[str, Dict]) -> Dict:
        """
        Tüm aktif watchlist için yeni snapshot oluştur
        
        Args:
            scan_results: {'SYMBOL': scan_result_dict, ...} formatında güncel tarama sonuçları
        
        Returns:
            {'refreshed': int, 'failed': int, 'not_found': int}
        """
        result = {
            'refreshed': 0,
            'failed': 0,
            'not_found': 0
        }
        
        watchlist = self.get_active_watchlist()
        
        for entry in watchlist:
            symbol = entry['symbol']
            exchange = entry['exchange']
            
            # Tarama sonuçlarında bu sembol var mı?
            if symbol in scan_results:
                scan_result = scan_results[symbol]
                try:
                    success = self.create_snapshot(symbol, exchange, scan_result)
                    if success:
                        result['refreshed'] += 1
                    else:
                        result['failed'] += 1
                except Exception as e:
                    result['failed'] += 1
                    logger.error(f"❌ Error refreshing {symbol}: {e}")
            else:
                result['not_found'] += 1
                logger.debug(f"⚠️ {symbol} not in scan results, skipping")
        
        logger.info(f"✅ Refresh complete: {result['refreshed']} refreshed, {result['failed']} failed, {result['not_found']} not found")
        return result

    def get_entry_with_all_snapshots(self, symbol: str, exchange: str) -> Optional[Dict]:
        """
        Sembolün tüm snapshot geçmişini al (karşılaştırma için)
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
        
        Returns:
            Entry + tüm snapshot'lar veya None
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                return None
            
            return {
                'id': entry.id,
                'symbol': entry.symbol,
                'exchange': entry.exchange,
                'added_date': entry.added_date,
                'notes': entry.notes,
                'status_label': entry.status_label,
                'setup_status': entry.setup_status,
                'psychological_risk': entry.psychological_risk,
                'snapshots': [self._snapshot_to_dict(s) for s in entry.snapshots]
            }
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Database error: {e}")
            return None
    
    def update_psychological_flags(
        self, 
        symbol: str, 
        exchange: str,
        flags: Dict
    ) -> bool:
        """
        Psikolojik risk bayraklarını güncelle
        
        Args:
            symbol: Sembol
            exchange: Borsa
            flags: {'previously_failed': True, 'high_volatility_risk': True, ...}
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                return False
            
            if 'previously_failed' in flags:
                entry.previously_failed = flags['previously_failed']
            if 'high_volatility_risk' in flags:
                entry.high_volatility_risk = flags['high_volatility_risk']
            if 'news_dependent' in flags:
                entry.news_dependent = flags['news_dependent']
            if 'manipulation_history' in flags:
                entry.manipulation_history = flags['manipulation_history']
            
            # Herhangi bir risk varsa psychological_risk'i True yap
            entry.psychological_risk = any([
                entry.previously_failed,
                entry.high_volatility_risk,
                entry.news_dependent,
                entry.manipulation_history
            ])
            
            # Audit Log (V3.0)
            changed_flags = [k for k, v in flags.items() if v]
            self._log_audit(
                entry.id,
                "PSYCH_FLAG_UPDATE",
                new_val=str(changed_flags) if changed_flags else "cleared",
                desc=f"Psychological flags updated: {', '.join(changed_flags) if changed_flags else 'all cleared'}",
                session=session
            )
            
            session.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Update psychological flags error: {e}")
            session.rollback()
            return False
    
    def update_trade_history(
        self,
        symbol: str,
        exchange: str,
        is_winner: bool
    ) -> bool:
        """
        İşlem geçmişini güncelle
        
        Args:
            symbol: Sembol
            exchange: Borsa
            is_winner: Kazanan işlem mi
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                return False
            
            entry.total_trades += 1
            if is_winner:
                entry.winning_trades += 1
            else:
                entry.losing_trades += 1
                # Kaybedince previously_failed'ı True yap
                entry.previously_failed = True
                entry.psychological_risk = True
            
            session.commit()
            
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Update trade history error: {e}")
            session.rollback()
            return False

    # =========================================================================
    # KURUMSAL İŞLEM YÖNETİMİ (V3.0)
    # =========================================================================
    
    def add_trade_execution(
        self,
        symbol: str, 
        exchange: str,
        side: str, # BUY, SELL
        quantity: float,
        price: float,
        fees: float = 0.0,
        order_type: str = "MARKET",
        notes: str = None
    ) -> bool:
        """
        Yeni işlem kaydı ekle (Trade Execution)
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                return False
            
            execution = TradeExecution(
                watchlist_entry_id=entry.id,
                execution_date=datetime.now(),
                side=side,
                quantity=quantity,
                price=price,
                fees=fees,
                order_type=order_type,
                notes=notes
            )
            session.add(execution)
            
            # İstatistikleri güncelle (Basit sayaçlar için)
            entry.total_trades += 1
            if side == "SELL":
                # Basit logic: Eğer fiyat > son alış fiyatı ise kazanç?
                # Bu çok basit, ilerde FIFO hesaplaması eklenebilir.
                pass 
                
            self._log_audit(
                entry.id, 
                "TRADE_EXEC", 
                new_val=f"{side} {quantity} @ {price}", 
                desc=f"Fees: {fees}",
                session=session
            )
            
            session.commit()
            logger.info(f"✅ İşlem eklendi: {symbol} {side}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Add trade error: {e}")
            session.rollback()
            return False

    def update_trade_journal(
        self,
        symbol: str,
        exchange: str,
        journal_data: Dict
    ) -> bool:
        """
        İşlem günlüğünü güncelle (Qualitative Data)
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange
            ).first() # Aktif veya pasif olabilir
            
            if not entry:
                return False
            
            journal = entry.journal
            if not journal:
                journal = TradeJournal(watchlist_entry_id=entry.id)
                session.add(journal)
            
            # Alanları güncelle
            if 'entry_reason' in journal_data: journal.entry_reason = journal_data['entry_reason']
            if 'setup_quality' in journal_data: journal.setup_quality = journal_data['setup_quality']
            if 'emotion_entry' in journal_data: journal.emotion_entry = journal_data['emotion_entry']
            if 'exit_reason' in journal_data: journal.exit_reason = journal_data['exit_reason']
            if 'emotion_exit' in journal_data: journal.emotion_exit = journal_data['emotion_exit']
            if 'lessons_learned' in journal_data: journal.lessons_learned = journal_data['lessons_learned']
            if 'mistakes_made' in journal_data: journal.mistakes_made = journal_data['mistakes_made']
            
            self._log_audit(
                entry.id, 
                "JOURNAL_UPDATE", 
                desc="Updated trade journal details",
                session=session
            )
            
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Update journal error: {e}")
            session.rollback()
            return False

    # =========================================================================
    # QUERY / ACCESSOR METHODS (V3.0)
    # =========================================================================

    def get_audit_history(
        self,
        symbol: str,
        exchange: str,
        days: int = 30,
        action_filter: str = None
    ) -> List[Dict]:
        """
        Denetim günlüğünü getir
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
            days: Son N gün (0 = tümü)
            action_filter: Belirli aksiyon tipi filtresi (CREATE, STATUS_CHANGE, vb.)
        
        Returns:
            List of audit log dicts, en yeniden en eskiye
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange
            ).first()
            
            if not entry:
                return []
            
            query = session.query(WatchlistAuditLog).filter_by(
                watchlist_entry_id=entry.id
            )
            
            if days > 0:
                cutoff = datetime.now() - timedelta(days=days)
                query = query.filter(WatchlistAuditLog.timestamp >= cutoff)
            
            if action_filter:
                query = query.filter_by(action_type=action_filter)
            
            audits = query.order_by(WatchlistAuditLog.timestamp.desc()).all()
            
            return [{
                'id': a.id,
                'timestamp': a.timestamp,
                'action_type': a.action_type,
                'old_value': a.old_value,
                'new_value': a.new_value,
                'user_context': a.user_context,
                'description': a.description,
            } for a in audits]
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Get audit history error: {e}")
            return []

    def get_trade_executions(
        self,
        symbol: str,
        exchange: str
    ) -> List[Dict]:
        """
        İşlem kayıtlarını getir
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
        
        Returns:
            List of trade execution dicts
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange
            ).first()
            
            if not entry:
                return []
            
            trades = session.query(TradeExecution).filter_by(
                watchlist_entry_id=entry.id
            ).order_by(TradeExecution.execution_date.desc()).all()
            
            return [{
                'id': t.id,
                'execution_date': t.execution_date,
                'side': t.side,
                'quantity': t.quantity,
                'price': t.price,
                'fees': t.fees,
                'order_type': t.order_type,
                'notes': t.notes,
                'total_cost': t.quantity * t.price + t.fees,
            } for t in trades]
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Get trade executions error: {e}")
            return []

    def get_trade_journal(
        self,
        symbol: str,
        exchange: str
    ) -> Optional[Dict]:
        """
        İşlem günlüğünü getir
        
        Args:
            symbol: Sembol adı
            exchange: Borsa
        
        Returns:
            Journal dict veya None
        """
        try:
            session = self._get_session()
            
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol,
                exchange=exchange
            ).first()
            
            if not entry or not entry.journal:
                return None
            
            j = entry.journal
            return {
                'id': j.id,
                'entry_reason': j.entry_reason,
                'setup_quality': j.setup_quality,
                'emotion_entry': j.emotion_entry,
                'exit_reason': j.exit_reason,
                'emotion_exit': j.emotion_exit,
                'lessons_learned': j.lessons_learned,
                'mistakes_made': j.mistakes_made,
                'screenshot_path': j.screenshot_path,
            }
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Get trade journal error: {e}")
            return None

    def record_sector_performance(
        self,
        sector_data: List[Dict]
    ) -> bool:
        """
        Günlük sektör performanslarını kaydet
        
        Args:
            sector_data: [{
                'sector': 'Bankacılık',
                'avg_change_pct': 1.5,
                'top_gainer': 'GARAN', 'top_gainer_pct': 3.2,
                'top_loser': 'ISCTR', 'top_loser_pct': -0.5,
                'stock_count': 12, 'bullish_count': 8, 'bearish_count': 3, 'neutral_count': 1,
                'sector_volume': 500000000, 'momentum_score': 65.0
            }, ...]
        
        Returns:
            True = başarılı
        """
        try:
            session = self._get_session()
            now = datetime.now()
            
            for data in sector_data:
                record = SectorPerformanceHistory(
                    record_date=now,
                    sector=data.get('sector', 'Unknown'),
                    avg_change_pct=data.get('avg_change_pct'),
                    top_gainer=data.get('top_gainer'),
                    top_gainer_pct=data.get('top_gainer_pct'),
                    top_loser=data.get('top_loser'),
                    top_loser_pct=data.get('top_loser_pct'),
                    stock_count=data.get('stock_count', 0),
                    bullish_count=data.get('bullish_count', 0),
                    bearish_count=data.get('bearish_count', 0),
                    neutral_count=data.get('neutral_count', 0),
                    sector_volume=data.get('sector_volume'),
                    momentum_score=data.get('momentum_score'),
                )
                session.add(record)
            
            session.commit()
            logger.info(f"✅ {len(sector_data)} sektör performansı kaydedildi")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Record sector performance error: {e}")
            session.rollback()
            return False

    def get_sector_rotation_history(
        self,
        days: int = 30,
        sector: str = None
    ) -> List[Dict]:
        """
        Sektör rotasyon tarihçesini getir
        
        Args:
            days: Son N gün (0 = tümü)
            sector: Belirli sektör (None = tümü)
        
        Returns:
            List of sector performance dicts, tarihe göre sıralı
        """
        try:
            session = self._get_session()
            
            query = session.query(SectorPerformanceHistory)
            
            if days > 0:
                cutoff = datetime.now() - timedelta(days=days)
                query = query.filter(SectorPerformanceHistory.record_date >= cutoff)
            
            if sector:
                query = query.filter_by(sector=sector)
            
            records = query.order_by(
                SectorPerformanceHistory.record_date.desc(),
                SectorPerformanceHistory.avg_change_pct.desc()
            ).all()
            
            return [{
                'id': r.id,
                'record_date': r.record_date,
                'sector': r.sector,
                'avg_change_pct': r.avg_change_pct,
                'top_gainer': r.top_gainer,
                'top_gainer_pct': r.top_gainer_pct,
                'top_loser': r.top_loser,
                'top_loser_pct': r.top_loser_pct,
                'stock_count': r.stock_count,
                'bullish_count': r.bullish_count,
                'bearish_count': r.bearish_count,
                'neutral_count': r.neutral_count,
                'sector_volume': r.sector_volume,
                'momentum_score': r.momentum_score,
            } for r in records]
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Get sector rotation error: {e}")
            return []

    def get_portfolio_summary(self) -> Dict:
        """
        Portföy özet istatistiklerini getir
        
        Returns:
            {
                'total_active': int,
                'total_archived': int,
                'status_distribution': {'ACTIVE': n, 'WAIT': n, ...},
                'sector_distribution': {'Bankacılık': n, ...},
                'trade_stats': {'total': n, 'wins': n, 'losses': n, 'win_rate': float},
                'avg_days_in_list': float,
                'risk_flags': {'psychological_risk': n, 'high_volatility': n, ...},
            }
        """
        try:
            session = self._get_session()
            
            # Active entries
            active_entries = session.query(WatchlistEntry).filter_by(is_active=True).all()
            archived_count = session.query(WatchlistEntry).filter_by(is_active=False).count()
            
            # Status distribution
            status_dist = {}
            sector_dist = {}
            total_trades = 0
            total_wins = 0
            total_losses = 0
            total_days = 0
            risk_flags = {
                'psychological_risk': 0,
                'high_volatility': 0,
                'news_dependent': 0,
                'manipulation_history': 0,
                'previously_failed': 0
            }
            
            for entry in active_entries:
                # Status
                status = entry.status_label or 'UNKNOWN'
                status_dist[status] = status_dist.get(status, 0) + 1
                
                # Sector
                sector = entry.sector or 'Bilinmiyor'
                sector_dist[sector] = sector_dist.get(sector, 0) + 1
                
                # Trades
                total_trades += entry.total_trades or 0
                total_wins += entry.winning_trades or 0
                total_losses += entry.losing_trades or 0
                
                # Days
                days = (datetime.now() - entry.added_date).days
                total_days += days
                
                # Risk flags
                if entry.psychological_risk: risk_flags['psychological_risk'] += 1
                if entry.high_volatility_risk: risk_flags['high_volatility'] += 1
                if entry.news_dependent: risk_flags['news_dependent'] += 1
                if entry.manipulation_history: risk_flags['manipulation_history'] += 1
                if entry.previously_failed: risk_flags['previously_failed'] += 1
            
            active_count = len(active_entries)
            avg_days = total_days / active_count if active_count > 0 else 0
            win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'total_active': active_count,
                'total_archived': archived_count,
                'status_distribution': status_dist,
                'sector_distribution': sector_dist,
                'trade_stats': {
                    'total': total_trades,
                    'wins': total_wins,
                    'losses': total_losses,
                    'win_rate': round(win_rate, 1)
                },
                'avg_days_in_list': round(avg_days, 1),
                'risk_flags': risk_flags,
            }
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Get portfolio summary error: {e}")
            return {}

    # =========================================================================
    # RISK & ANALYTICS INTEGRATION (V3.0 Phase 2)
    # =========================================================================

    def update_risk_scores(self, data_handler_config: Dict = None) -> int:
        """
        Aktif hisselerin risk skorlarını güncelle
        
        Args:
            data_handler_config: DataHandler yapılandırması
        
        Returns:
            Güncellenen hisse sayısı
        """
        try:
            from scanner.data_handler import DataHandler
            
            session = self._get_session()
            active_entries = session.query(WatchlistEntry).filter_by(is_active=True).all()
            
            if not active_entries:
                return 0
                
            rm = RiskManager()
            handler = DataHandler(data_handler_config or {})
            updated_count = 0
            
            for entry in active_entries:
                try:
                    # 120 günlük veri çek (~6 ay)
                    df = handler.get_daily_data(entry.symbol, entry.exchange, n_bars=120)
                    
                    if df is not None and len(df) > 30:
                        # Market verisi şimdilik dummy veya cache'den alınabilir
                        # İleride BIST100 endeks hacmi vb. eklenebilir
                        risk_data = rm.calculate_stock_risk_score(df)
                        
                        entry.risk_score = risk_data.get('risk_score')
                        
                        # High risk uyarısı varsa audit'e ekle
                        if risk_data.get('risk_label') in ['HIGH', 'CRITICAL']:
                            entry.psychological_risk = True
                        
                        updated_count += 1
                except Exception as e:
                    logger.error(f"❌ Risk score update error for {entry.symbol}: {e}")
                    continue
            
            if updated_count > 0:
                session.commit()
                logger.info(f"✅ {updated_count} hissenin risk skoru güncellendi")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"❌ Batch risk update error: {e}")
            return 0

    def get_risk_analysis(self, symbol: str, exchange: str) -> Dict:
        """
        Tekil hisse risk analizi detayı
        
        Returns:
            RiskManager.calculate_stock_risk_score çıktısı
        """
        try:
            session = self._get_session()
            entry = session.query(WatchlistEntry).filter_by(
                symbol=symbol, 
                exchange=exchange,
                is_active=True
            ).first()
            
            if not entry:
                return {}
            
            # Veriyi çekip anlık hesapla
            from scanner.data_handler import DataHandler
            # Config'i nereden alacağız? Varsayılan parametreler:
            handler = DataHandler({}) 
            
            df = handler.get_daily_data(symbol, exchange, n_bars=120)
            if df is not None:
                rm = RiskManager()
                return rm.calculate_stock_risk_score(df)
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Get risk analysis error: {e}")
            return {}
