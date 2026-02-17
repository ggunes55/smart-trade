# -*- coding: utf-8 -*-
"""
Watchlist Database Models - SQLAlchemy ORM
SQLite tabanlı watchlist veri modelleri

V2.0: Profesyonel Swing Trade Takip Sistemi
- Genişletilmiş WatchlistEntry (kimlik, likidite, psikolojik filtreler)
- Genişletilmiş WatchlistSnapshot (trend, setup, tam teknik veriler)
- Yeni WatchlistAlert modeli (fiyat/indikatör alarmları)
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, 
    String, Text, create_engine, Index, Enum, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
import enum

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================================
# ENUM TYPES
# ============================================================================

class StatusLabel(enum.Enum):
    """Watchlist durum etiketleri"""
    ACTIVE = "🟢 Aktif"
    WAIT = "🟡 Bekle"
    ALARM = "🔵 Alarm Bekliyor"
    PASSIVE = "🔴 Pasif"


class SetupStatus(enum.Enum):
    """Setup hazırlık durumu"""
    READY = "Hazır"
    APPROACHING = "Yaklaşıyor"
    EARLY = "Erken"
    EXPIRED = "Süresi Doldu"


class TrendDirection(enum.Enum):
    """Ana trend yönü"""
    UP = "↑ Yükseliş"
    SIDEWAYS = "→ Yatay"
    DOWN = "↓ Düşüş"


class AlertType(enum.Enum):
    """Alarm türleri"""
    PRICE_ABOVE = "Fiyat Üstü"
    PRICE_BELOW = "Fiyat Altı"
    VOLUME_SPIKE = "Hacim Patlaması"
    RSI_OVERSOLD = "RSI Aşırı Satım"
    RSI_OVERBOUGHT = "RSI Aşırı Alım"
    MACD_CROSS_UP = "MACD Yukarı Kesişim"
    MACD_CROSS_DOWN = "MACD Aşağı Kesişim"
    STOP_PROXIMITY = "Stop Yakınlığı"
    TARGET_PROXIMITY = "Hedef Yakınlığı"


# ============================================================================
# WATCHLIST ENTRY - Ana Kayıt
# ============================================================================

class WatchlistEntry(Base):
    """
    Watchlist Ana Kayıt (V2.0)
    Her hisse için bir entry - kimlik, filtre ve psikolojik bilgiler içerir
    """
    __tablename__ = 'watchlist_entries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(10), nullable=False)  # BIST, NASDAQ, NYSE, CRYPTO
    added_date = Column(DateTime, nullable=False, default=datetime.now)
    notes = Column(Text, nullable=True)  # Kullanıcı notları
    is_active = Column(Boolean, default=True, nullable=False)
    
    # ===== YENİ: Kimlik & Piyasa Bilgileri =====
    sector = Column(String(50), nullable=True)  # Sektör
    sub_sector = Column(String(50), nullable=True)  # Alt sektör
    index_membership = Column(String(20), nullable=True)  # BIST100, BIST30, Other
    float_ratio = Column(Float, nullable=True)  # Serbest dolaşım oranı (%)
    avg_daily_volume = Column(Float, nullable=True)  # Ortalama günlük hacim (20-30 gün)
    liquidity_score = Column(Float, nullable=True)  # Hesaplanan likidite skoru (0-100)
    market_cap = Column(Float, nullable=True)  # Piyasa değeri
    
    # ===== YENİ: Durum & Zamanlama =====
    status_label = Column(String(20), default="ACTIVE")  # ACTIVE, WAIT, ALARM, PASSIVE
    setup_status = Column(String(20), default="EARLY")  # READY, APPROACHING, EARLY, EXPIRED
    estimated_days = Column(Integer, nullable=True)  # Tahmini tetik süresi (gün)
    last_check_date = Column(DateTime, nullable=True)  # Son manuel kontrol
    days_in_list = Column(Integer, default=0)  # Listede kaç gün
    
    # ===== YENİ: Psikolojik Filtreler =====
    psychological_risk = Column(Boolean, default=False)  # Psikolojik risk işareti
    previously_failed = Column(Boolean, default=False)  # Daha önce bu hissede zarar edildi mi
    high_volatility_risk = Column(Boolean, default=False)  # Aşırı volatil mi
    news_dependent = Column(Boolean, default=False)  # Haber bağımlı mı
    manipulation_history = Column(Boolean, default=False)  # Manipülasyon geçmişi var mı
    
    # ===== YENİ: İşlem Geçmişi =====
    total_trades = Column(Integer, default=0)  # Bu hissedeki toplam işlem sayısı
    winning_trades = Column(Integer, default=0)  # Kazanan işlem sayısı
    losing_trades = Column(Integer, default=0)  # Kaybeden işlem sayısı
    
    # ===== YENİ: Arşiv Bilgisi =====
    archived_date = Column(DateTime, nullable=True)  # Arşivlenme tarihi
    archive_reason = Column(String(200), nullable=True)  # Arşivleme nedeni
    
    # ===== YENİ: Risk Skoru (V3.0 Phase 2) =====
    risk_score = Column(Float, nullable=True)  # Bileşik risk skoru (0-100)
    
    # İlişkiler
    snapshots = relationship(
        'WatchlistSnapshot',
        back_populates='entry',
        cascade='all, delete-orphan',
        order_by='WatchlistSnapshot.snapshot_date'
    )
    
    alerts = relationship(
        'WatchlistAlert',
        back_populates='entry',
        cascade='all, delete-orphan'
    )
    
    # İndeksler
    __table_args__ = (
        Index('idx_symbol_active', 'symbol', 'is_active'),
        Index('idx_exchange', 'exchange'),
        Index('idx_status', 'status_label'),
        Index('idx_setup_status', 'setup_status'),
    )
    
    def __repr__(self):
        return f"<WatchlistEntry(symbol='{self.symbol}', exchange='{self.exchange}', status='{self.status_label}')>"
    
    @property
    def status_emoji(self) -> str:
        """Durum etiketini emoji ile döndür"""
        status_map = {
            "ACTIVE": "🟢",
            "WAIT": "🟡", 
            "ALARM": "🔵",
            "PASSIVE": "🔴"
        }
        return status_map.get(self.status_label, "⚪")


# ============================================================================
# WATCHLIST SNAPSHOT - Anlık Görüntü
# ============================================================================

class WatchlistSnapshot(Base):
    """
    Watchlist Snapshot (V2.0) - Belirli bir zamandaki tüm analiz değerleri
    Her snapshot bir fotoğraf gibi, o andaki tüm metrikleri saklar
    """
    __tablename__ = 'watchlist_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    watchlist_entry_id = Column(Integer, ForeignKey('watchlist_entries.id'), nullable=False)
    snapshot_date = Column(DateTime, nullable=False, default=datetime.now)
    
    # ===== Fiyat Bilgileri =====
    price = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=True)  # Önerilen giriş
    trigger_price = Column(Float, nullable=True)  # YENİ: Tetik seviyesi
    stop_loss = Column(Float, nullable=True)
    target1 = Column(Float, nullable=True)
    target2 = Column(Float, nullable=True)
    target3 = Column(Float, nullable=True)
    
    # ===== YENİ: Risk/Reward =====
    rr_ratio = Column(Float, nullable=True)  # Risk/Reward oranı
    risk_percent = Column(Float, nullable=True)  # Risk yüzdesi
    
    # ===== YENİ: Trend & Yapı =====
    main_trend = Column(String(20), nullable=True)  # UP, SIDEWAYS, DOWN
    trend_strength = Column(String(20), nullable=True)  # STRONG, MEDIUM, WEAK
    ma_alignment = Column(String(50), nullable=True)  # EMA20>EMA50>EMA200
    setup_type = Column(String(30), nullable=True)  # BREAKOUT, PULLBACK, CONSOLIDATION, etc.
    structure_type = Column(String(30), nullable=True)  # YENİ: Konsolidasyon, Pullback, vb.
    
    # ===== Temel Teknik İndikatörler =====
    rsi = Column(Float, nullable=True)
    rsi_trend = Column(String(20), nullable=True)  # YENİ: Yükselen/Düşen
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)  # YENİ
    macd_histogram = Column(Float, nullable=True)  # YENİ
    adx = Column(Float, nullable=True)
    plus_di = Column(Float, nullable=True)  # YENİ
    minus_di = Column(Float, nullable=True)  # YENİ
    
    # ===== YENİ: Hacim Analizi =====
    volume = Column(Float, nullable=True)
    volume_avg = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)  # Mevcut/Ortalama
    rvol = Column(Float, nullable=True)  # Relative Volume
    volume_confirms_price = Column(Boolean, nullable=True)  # Hacim fiyatı teyit ediyor mu
    
    # ===== YENİ: Volatilite & ATR =====
    atr = Column(Float, nullable=True)
    atr_percent = Column(Float, nullable=True)  # ATR / Fiyat * 100
    volatility_annualized = Column(Float, nullable=True)
    volatility_status = Column(String(20), nullable=True)  # HIGH, NORMAL, LOW
    squeeze_status = Column(String(30), nullable=True)  # YENİ: Squeeze durumu
    
    # ===== YENİ: Performans Metrikleri =====
    rs_rating = Column(Float, nullable=True)  # Relative Strength Rating (0-100)
    rs_score = Column(Float, nullable=True)  # RS Score
    alpha = Column(Float, nullable=True)  # Alpha vs benchmark
    beta = Column(Float, nullable=True)  # YENİ: Beta
    sharpe_ratio = Column(Float, nullable=True)
    efficiency_ratio = Column(Float, nullable=True)  # Swing efficiency
    
    # ===== YENİ: Gelişmiş Analiz =====
    divergence_info = Column(String(100), nullable=True)  # Divergence açıklaması
    tv_signal = Column(String(20), nullable=True)  # TradingView sinyali
    tv_buy_count = Column(Integer, nullable=True)
    tv_sell_count = Column(Integer, nullable=True)
    tv_neutral_count = Column(Integer, nullable=True)
    
    # ===== YENİ: ML & Confirmation =====
    ml_quality = Column(String(30), nullable=True)  # HIGH_QUALITY, MEDIUM, LOW
    ml_confidence = Column(Float, nullable=True)  # ML güven skoru
    confirmation_count = Column(Integer, nullable=True)
    confirmation_required = Column(Integer, nullable=True)
    confirmation_confidence = Column(Float, nullable=True)
    
    # ===== Mevcut Alanlar (Güncellendi) =====
    trend_score = Column(Float, nullable=True)
    swing_efficiency = Column(Float, nullable=True)
    market_regime = Column(String(20), nullable=True)
    
    # Sinyal bilgisi
    signal_type = Column(String(20), nullable=True)  # BREAKOUT, PULLBACK, REVERSAL
    signal_strength = Column(String(20), nullable=True)  # YENİ: Güçlü/Orta/Zayıf
    confidence = Column(Float, nullable=True)  # ML confidence (0-1)
    confirmations_count = Column(Integer, default=0)  # Kaç doğrulama var
    
    # ===== YENİ: Entry Timing =====
    entry_recommendation = Column(String(30), nullable=True)  # ENTER_NOW, WAIT, etc.
    entry_confidence = Column(Float, nullable=True)
    optimal_entry_price = Column(Float, nullable=True)
    
    # ===== YENİ: Durum Değerlendirmesi =====
    distance_to_stop_pct = Column(Float, nullable=True)  # Stop'a uzaklık (%)
    distance_to_target1_pct = Column(Float, nullable=True)  # Hedef1'e uzaklık (%)
    distance_to_target2_pct = Column(Float, nullable=True)  # Hedef2'ye uzaklık (%)
    daily_change_pct = Column(Float, nullable=True)  # Günlük değişim (%)
    
    # İlişki
    entry = relationship('WatchlistEntry', back_populates='snapshots')
    
    # İndeksler
    __table_args__ = (
        Index('idx_entry_date', 'watchlist_entry_id', 'snapshot_date'),
        Index('idx_snapshot_date', 'snapshot_date'),
    )
    
    def __repr__(self):
        return f"<WatchlistSnapshot(entry_id={self.watchlist_entry_id}, date='{self.snapshot_date}', price={self.price})>"


# ============================================================================
# WATCHLIST ALERT - Alarm Sistemi
# ============================================================================

class WatchlistAlert(Base):
    """
    Watchlist Alert (YENİ V2.0) - Fiyat ve indikatör alarmları
    """
    __tablename__ = 'watchlist_alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    watchlist_entry_id = Column(Integer, ForeignKey('watchlist_entries.id'), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.now)
    
    # Alarm Tanımı
    alert_type = Column(String(30), nullable=False)  # AlertType enum değeri
    trigger_value = Column(Float, nullable=True)  # Tetik değeri (fiyat, RSI seviyesi vb.)
    condition = Column(String(20), nullable=True)  # ABOVE, BELOW, CROSS_UP, CROSS_DOWN
    description = Column(String(200), nullable=True)  # Alarm açıklaması
    
    # Durum
    is_active = Column(Boolean, default=True, nullable=False)
    triggered = Column(Boolean, default=False, nullable=False)
    triggered_date = Column(DateTime, nullable=True)
    triggered_value = Column(Float, nullable=True)  # Tetiklendiğindeki değer
    
    # Bildirim
    notification_sent = Column(Boolean, default=False)
    notification_date = Column(DateTime, nullable=True)
    
    # İlişki
    entry = relationship('WatchlistEntry', back_populates='alerts')
    
    # İndeksler
    __table_args__ = (
        Index('idx_alert_active', 'is_active'),
        Index('idx_alert_entry', 'watchlist_entry_id'),
        Index('idx_alert_type', 'alert_type'),
    )
    
    def __repr__(self):
        return f"<WatchlistAlert(entry_id={self.watchlist_entry_id}, type='{self.alert_type}', active={self.is_active})>"


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db(db_path: str = 'watchlist.db') -> tuple[Session, any]:
    """
    Database'i başlat ve session döndür
    
    Args:
        db_path: SQLite database dosya yolu
    
    Returns:
        (session, engine) tuple
    """
    logger.info(f"📊 Initializing watchlist database: {db_path}")
    
    # Engine oluştur
    engine = create_engine(
        f'sqlite:///{db_path}',
        echo=False,  # SQL query loglarını kapatıyoruz
        connect_args={'check_same_thread': False}  # Multi-thread support
    )
    
    # WAL modunu etkinleştir (daha iyi concurrency için)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.commit()
        logger.info("✅ SQLite WAL mode enabled")
    
    # Tabloları oluştur (yeni sütunlar otomatik eklenir)
    Base.metadata.create_all(engine)
    logger.info("✅ Database tables created/verified")
    
    # Session factory
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    return session, engine


# ============================================================================
# INSTITUTIONAL MODULES (V3.0)
# ============================================================================

class WatchlistAuditLog(Base):
    """
    Watchlist Audit Log (V3.0) - Denetim İzi
    Her türlü değişikliğin kaydını tutar
    """
    __tablename__ = 'watchlist_audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    watchlist_entry_id = Column(Integer, ForeignKey('watchlist_entries.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    
    action_type = Column(String(50), nullable=False) # CREATE, UPDATE, DELETE, STATUS_CHANGE
    old_value = Column(Text, nullable=True) # JSON or string
    new_value = Column(Text, nullable=True) # JSON or string
    user_context = Column(String(50), default="Manual") # Manual, Auto-Cleanup, System
    description = Column(String(255), nullable=True)
    
    # İlişki
    entry = relationship('WatchlistEntry', back_populates='audit_logs')
    
    __table_args__ = (
        Index('idx_audit_entry', 'watchlist_entry_id'),
        Index('idx_audit_time', 'timestamp'),
    )

class TradeExecution(Base):
    """
    Trade Execution (V3.0) - İşlem Kaydı
    Alım/Satım emirlerinin detayları
    """
    __tablename__ = 'trade_executions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    watchlist_entry_id = Column(Integer, ForeignKey('watchlist_entries.id'), nullable=False)
    execution_date = Column(DateTime, nullable=False, default=datetime.now)
    
    side = Column(String(10), nullable=False) # BUY, SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    order_type = Column(String(20), default="MARKET") # MARKET, LIMIT, STOP
    notes = Column(Text, nullable=True)
    
    # İlişki
    entry = relationship('WatchlistEntry', back_populates='executions')

class TradeJournal(Base):
    """
    Trade Journal (V3.0) - Detaylı İşlem Günlüğü
    Niteliksel veriler (Duygu, Strateji, Dersler)
    """
    __tablename__ = 'trade_journals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    watchlist_entry_id = Column(Integer, ForeignKey('watchlist_entries.id'), nullable=False)
    
    # Giriş Analizi
    entry_reason = Column(Text, nullable=True)
    setup_quality = Column(Integer, nullable=True) # 1-10
    emotion_entry = Column(String(50), nullable=True) # CONFIDENT, FOMO, HESITANT
    
    # Çıkış Analizi
    exit_reason = Column(Text, nullable=True)
    emotion_exit = Column(String(50), nullable=True) # SATISFIED, PANIC, GREED
    
    # Sonuç
    lessons_learned = Column(Text, nullable=True)
    mistakes_made = Column(Text, nullable=True)
    screenshot_path = Column(String(255), nullable=True)
    
    # İlişki
    entry = relationship('WatchlistEntry', back_populates='journal')

class SectorPerformanceHistory(Base):
    """
    Sektör Performans Tarihçesi (V3.0) - Sektör Rotasyonu Takibi
    Günlük sektör performanslarını kaydeder
    """
    __tablename__ = 'sector_performance_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    record_date = Column(DateTime, nullable=False, default=datetime.now)
    sector = Column(String(50), nullable=False)
    
    # Performans Metrikleri
    avg_change_pct = Column(Float, nullable=True)  # Sektör ortalama değişim %
    top_gainer = Column(String(20), nullable=True)  # En çok yükselen hisse
    top_gainer_pct = Column(Float, nullable=True)
    top_loser = Column(String(20), nullable=True)  # En çok düşen hisse
    top_loser_pct = Column(Float, nullable=True)
    
    # Sektör İstatistikleri
    stock_count = Column(Integer, default=0)  # Sektördeki hisse sayısı
    bullish_count = Column(Integer, default=0)  # Yükselen hisse sayısı
    bearish_count = Column(Integer, default=0)  # Düşen hisse sayısı
    neutral_count = Column(Integer, default=0)  # Yatay hisse sayısı
    
    # Hacim & Momentum
    sector_volume = Column(Float, nullable=True)  # Toplam sektör hacmi
    momentum_score = Column(Float, nullable=True)  # Sektör momentum puanı (-100 to +100)
    
    __table_args__ = (
        Index('idx_sector_date', 'sector', 'record_date'),
        Index('idx_sector_name', 'sector'),
    )
    
    def __repr__(self):
        return f"<SectorPerformance(sector='{self.sector}', date='{self.record_date}', avg={self.avg_change_pct}%)>"


# Update WatchlistEntry relationships
WatchlistEntry.audit_logs = relationship('WatchlistAuditLog', back_populates='entry', cascade='all, delete-orphan')
WatchlistEntry.executions = relationship('TradeExecution', back_populates='entry', cascade='all, delete-orphan')
WatchlistEntry.journal = relationship('TradeJournal', back_populates='entry', uselist=False, cascade='all, delete-orphan')


def migrate_database(db_path: str = 'watchlist.db') -> bool:
    """
    Mevcut veritabanını yeni şemaya migrate et (V3.0 Updates)
    """
    import sqlite3
    
    try:
        logger.info(f"🔄 Migrating database: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Mevcut sütunları al
        cursor.execute("PRAGMA table_info(watchlist_entries)")
        existing_entry_cols = {row[1] for row in cursor.fetchall()}
        
        cursor.execute("PRAGMA table_info(watchlist_snapshots)")
        existing_snapshot_cols = {row[1] for row in cursor.fetchall()}
        
        # WatchlistEntry için yeni sütunlar (V2.0)
        entry_new_cols = [
            ("sector", "TEXT"),
            ("sub_sector", "TEXT"),
            ("index_membership", "TEXT"),
            ("float_ratio", "REAL"),
            ("avg_daily_volume", "REAL"),
            ("liquidity_score", "REAL"),
            ("market_cap", "REAL"),
            ("status_label", "TEXT DEFAULT 'ACTIVE'"),
            ("setup_status", "TEXT DEFAULT 'EARLY'"),
            ("estimated_days", "INTEGER"),
            ("last_check_date", "DATETIME"),
            ("days_in_list", "INTEGER DEFAULT 0"),
            ("psychological_risk", "INTEGER DEFAULT 0"),
            ("previously_failed", "INTEGER DEFAULT 0"),
            ("high_volatility_risk", "INTEGER DEFAULT 0"),
            ("news_dependent", "INTEGER DEFAULT 0"),
            ("manipulation_history", "INTEGER DEFAULT 0"),
            ("total_trades", "INTEGER DEFAULT 0"),
            ("winning_trades", "INTEGER DEFAULT 0"),
            ("losing_trades", "INTEGER DEFAULT 0"),
            ("archived_date", "DATETIME"),
            ("archive_reason", "TEXT"),
            ("risk_score", "REAL"),
        ]
        
        # WatchlistSnapshot için yeni sütunlar (V2.0 + Eksik Olanlar)
        snapshot_new_cols = [
            ("entry_price", "REAL"),
            ("trigger_price", "REAL"),
            ("stop_loss", "REAL"),
            ("target1", "REAL"),
            ("target2", "REAL"),
            ("target3", "REAL"),
            ("rr_ratio", "REAL"),
            ("risk_percent", "REAL"),
            ("main_trend", "TEXT"),
            ("trend_strength", "TEXT"),
            ("ma_alignment", "TEXT"),
            ("setup_type", "TEXT"),
            ("structure_type", "TEXT"),
            ("rsi", "REAL"),
            ("rsi_trend", "TEXT"),
            ("macd", "REAL"),
            ("macd_signal", "REAL"),
            ("macd_histogram", "REAL"),
            ("adx", "REAL"),
            ("plus_di", "REAL"),
            ("minus_di", "REAL"),
            ("volume", "REAL"),
            ("volume_avg", "REAL"),
            ("volume_ratio", "REAL"),
            ("rvol", "REAL"),
            ("volume_confirms_price", "INTEGER"),
            ("atr", "REAL"),
            ("atr_percent", "REAL"),
            ("volatility_annualized", "REAL"),
            ("volatility_status", "TEXT"),
            ("squeeze_status", "TEXT"),
            ("rs_rating", "REAL"),
            ("rs_score", "REAL"),
            ("alpha", "REAL"),
            ("beta", "REAL"),
            ("sharpe_ratio", "REAL"),
            ("efficiency_ratio", "REAL"),
            ("divergence_info", "TEXT"),
            ("tv_signal", "TEXT"),
            ("tv_buy_count", "INTEGER"),
            ("tv_sell_count", "INTEGER"),
            ("tv_neutral_count", "INTEGER"),
            ("ml_quality", "TEXT"),
            ("ml_confidence", "REAL"),
            ("confirmation_count", "INTEGER"),
            ("confirmation_required", "INTEGER"),
            ("confirmation_confidence", "REAL"),
            ("trend_score", "REAL"),
            ("swing_efficiency", "REAL"),
            ("market_regime", "TEXT"),
            ("signal_type", "TEXT"),
            ("signal_strength", "TEXT"),
            ("confidence", "REAL"),
            ("confirmations_count", "INTEGER"),
            ("entry_recommendation", "TEXT"),
            ("entry_confidence", "REAL"),
            ("optimal_entry_price", "REAL"),
            ("distance_to_stop_pct", "REAL"),
            ("distance_to_target1_pct", "REAL"),
            ("distance_to_target2_pct", "REAL"),
            ("daily_change_pct", "REAL"),
        ]
        
        # Entry sütunlarını ekle
        added_count = 0
        for col_name, col_type in entry_new_cols:
            if col_name not in existing_entry_cols:
                try:
                    cursor.execute(f"ALTER TABLE watchlist_entries ADD COLUMN {col_name} {col_type}")
                    logger.info(f"  ➕ Added column: watchlist_entries.{col_name}")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        logger.warning(f"  ⚠️ Could not add {col_name}: {e}")
        
        # Snapshot sütunlarını ekle
        for col_name, col_type in snapshot_new_cols:
            if col_name not in existing_snapshot_cols:
                try:
                    cursor.execute(f"ALTER TABLE watchlist_snapshots ADD COLUMN {col_name} {col_type}")
                    logger.info(f"  ➕ Added column: watchlist_snapshots.{col_name}")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        logger.warning(f"  ⚠️ Could not add {col_name}: {e}")
        
        # Alerts tablosunu oluştur (yoksa)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_entry_id INTEGER NOT NULL,
                created_date DATETIME NOT NULL,
                alert_type TEXT NOT NULL,
                trigger_value REAL,
                condition TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                triggered INTEGER DEFAULT 0,
                triggered_date DATETIME,
                triggered_value REAL,
                notification_sent INTEGER DEFAULT 0,
                notification_date DATETIME,
                FOREIGN KEY (watchlist_entry_id) REFERENCES watchlist_entries(id)
            )
        """)
        
        # V3.0 TABLOLARI - Audit Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_entry_id INTEGER NOT NULL,
                timestamp DATETIME NOT NULL,
                action_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                user_context TEXT DEFAULT 'Manual',
                description TEXT,
                FOREIGN KEY (watchlist_entry_id) REFERENCES watchlist_entries(id)
            )
        """)
        
        # V3.0 TABLOLARI - Trade Execution
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_entry_id INTEGER NOT NULL,
                execution_date DATETIME NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                fees REAL DEFAULT 0,
                order_type TEXT DEFAULT 'MARKET',
                notes TEXT,
                FOREIGN KEY (watchlist_entry_id) REFERENCES watchlist_entries(id)
            )
        """)
        
        # V3.0 TABLOLARI - Trade Journal
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_journals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_entry_id INTEGER NOT NULL,
                entry_reason TEXT,
                setup_quality INTEGER,
                emotion_entry TEXT,
                exit_reason TEXT,
                emotion_exit TEXT,
                lessons_learned TEXT,
                mistakes_made TEXT,
                screenshot_path TEXT,
                FOREIGN KEY (watchlist_entry_id) REFERENCES watchlist_entries(id)
            )
        """)
        
        # V3.0 TABLOLARI - Sector Performance History
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sector_performance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date DATETIME NOT NULL,
                sector TEXT NOT NULL,
                avg_change_pct REAL,
                top_gainer TEXT,
                top_gainer_pct REAL,
                top_loser TEXT,
                top_loser_pct REAL,
                stock_count INTEGER DEFAULT 0,
                bullish_count INTEGER DEFAULT 0,
                bearish_count INTEGER DEFAULT 0,
                neutral_count INTEGER DEFAULT 0,
                sector_volume REAL,
                momentum_score REAL
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Database migration completed: {added_count} columns added, V3.0 tables verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def get_session(db_path: str = 'watchlist.db') -> Session:
    """
    Yeni bir database session döndür
    Otomatik migration yapar
    
    Args:
        db_path: SQLite database dosya yolu
    
    Returns:
        Session objesi
    """
    # Önce migration yap
    migrate_database(db_path)
    
    engine = create_engine(
        f'sqlite:///{db_path}',
        echo=False,
        connect_args={'check_same_thread': False}
    )
    
    # WAL modunu etkinleştir
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.commit()
    
    # Yeni tabloları oluştur
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
