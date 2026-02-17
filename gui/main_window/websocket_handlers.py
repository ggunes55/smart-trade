# -*- coding: utf-8 -*-
"""
WebSocket entegrasyonu için helper metodlar
main_window.py dosyasına eklenecek
"""

# ============================================================================
# WEBSOCKET VE REAL-TIME METODLAR (main_window.py'ye eklenecek)
# ============================================================================

def start_websocket(self):
    """Real-time veri akışını başlat"""
    try:
        symbols = self.symbols_tab.get_symbols()
        
        if not symbols:
            logging.warning("WebSocket için sembol seçilmedi")
            self.notification_manager.send_error_notification(
                "Lütfen en az bir sembol seçin",
                context="WebSocket başlatılmadı"
            )
            return
        
        # Önceki worker'ı durdur
        if self.ws_worker:
            self.stop_websocket()
        
        logging.info(f"🔌 WebSocket başlatılıyor: {len(symbols)} sembol...")
        
        # Worker oluştur
        self.ws_worker = WebSocketWorker(symbols, self.cfg)
        self.ws_thread = QThread()
        self.ws_worker.moveToThread(self.ws_thread)
        
        # Sinyalleri bağla
        self.ws_worker.price_updated.connect(self.on_ws_price_updated)
        self.ws_worker.signal_triggered.connect(self.on_ws_signal_triggered)
        self.ws_worker.portfolio_updated.connect(self.on_ws_portfolio_updated)
        self.ws_worker.error_occurred.connect(self.on_ws_error)
        self.ws_worker.connection_status.connect(self.on_ws_connection_status)
        
        # Thread'i başlat
        self.ws_thread.started.connect(self.ws_worker.run)
        self.ws_worker.finished.connect(self.ws_thread.quit)
        self.ws_worker.finished.connect(self.ws_worker.deleteLater)
        self.ws_thread.finished.connect(self.ws_thread.deleteLater)
        
        self.ws_thread.start()
        
        logging.info("✅ WebSocket başlatıldı")
    
    except Exception as e:
        logging.error(f"WebSocket başlatma hatası: {e}")
        self.notification_manager.send_error_notification(
            f"WebSocket başlatılamadı: {str(e)}"
        )


def stop_websocket(self):
    """Real-time veri akışını durdur"""
    try:
        if self.ws_worker:
            logging.info("🛑 WebSocket durduruluyor...")
            self.ws_worker.stop()
            
            if self.ws_thread:
                self.ws_thread.quit()
                self.ws_thread.wait(timeout=2000)
            
            self.ws_worker = None
            self.ws_thread = None
            
            logging.info("✅ WebSocket durduruldu")
    
    except Exception as e:
        logging.error(f"WebSocket durdurma hatası: {e}")


def on_ws_price_updated(self, symbol: str, price: float, change_pct: float):
    """Canlı fiyat güncellemesi"""
    try:
        # Price Ticker'ı güncelle
        if self.price_ticker:
            self.price_ticker.update_price(symbol, price, change_pct)
        
        # Watchlist'i güncelle
        if hasattr(self, 'watchlist_tab'):
            self.watchlist_tab.on_price_updated(symbol, price, change_pct)
        
        # Current chart'ı güncelle
        if self.chart_tab.current_symbol == symbol:
            import logging as log_module
            log_module.debug(f"Fiyat güncelleme: {symbol} ₺{price:.2f} ({change_pct:+.2f}%)")
    
    except Exception as e:
        logging.error(f"Fiyat güncelleme hatası: {e}")


def on_ws_signal_triggered(self, signal_data: dict):
    """Real-time sinyal tetiklendiğinde"""
    try:
        symbol = signal_data['symbol']
        action = signal_data['type']  # 'BUY', 'SELL'
        confidence = signal_data['confidence']
        price = signal_data['price']
        
        # Bildirim gönder
        self.notification_manager.send_signal_notification(
            symbol=symbol,
            action=action,
            confidence=confidence,
            price=price
        )
        
        # State manager'a kaydet
        self.state_manager.append_to_list('real_time_signals', signal_data)
        
        # Log
        logging.info(f"🎯 {action} Sinyali: {symbol} @ ₺{price:.2f} (Güven: {confidence:.0%})")
    
    except Exception as e:
        logging.error(f"Sinyal işleme hatası: {e}")


def on_ws_portfolio_updated(self, portfolio_state: dict):
    """Portfolio P&L gerçek zamanda güncellendi"""
    try:
        # State manager'a kaydet
        self.state_manager.set('portfolio_live_pnl', portfolio_state)
        
        # Portfolio tab'ı güncelle (varsa)
        if hasattr(self, 'portfolio_tab'):
            self.portfolio_tab.update_pnl(portfolio_state)
        
        # Risk uyarıları
        daily_loss_pct = portfolio_state.get('daily_loss_pct', 0)
        
        if daily_loss_pct < -5:  # -5% zarar
            self.notification_manager.send_risk_alert(
                f"Portfolio {daily_loss_pct:.2f}% zarar yaptı! "
                f"Risk limitini kontrol et.",
                portfolio_state=portfolio_state
            )
    
    except Exception as e:
        logging.error(f"Portfolio güncelleme hatası: {e}")


def on_ws_connection_status(self, connected: bool):
    """WebSocket bağlantı durumu değiştiğinde"""
    try:
        if self.price_ticker:
            self.price_ticker.set_connection_status(connected)
        
        self.notification_manager.send_connection_alert(connected)
        
        logging.info(f"🔌 WebSocket: {'Bağlı ✅' if connected else 'Bağlantı Yok ❌'}")
    
    except Exception as e:
        logging.error(f"Bağlantı durumu güncelleme hatası: {e}")


def on_ws_error(self, error_msg: str):
    """WebSocket hatası"""
    try:
        logging.error(f"WebSocket hatası: {error_msg}")
        self.notification_manager.send_error_notification(
            error_msg,
            context="WebSocket Hatası"
        )
    
    except Exception as e:
        logging.error(f"WebSocket hata işleme hatası: {e}")


def show_toast_notification(self, notification_data: dict):
    """Toast bildirimi göster"""
    try:
        from PyQt5.QtWidgets import QMessageBox, QApplication
        import time
        
        title = notification_data.get('title', 'Bildirim')
        message = notification_data.get('message', '')
        level = notification_data.get('level', 'info')  # info, success, warning, error
        duration = notification_data.get('duration', 3000)
        
        # Log
        emoji = {'info': 'ℹ️', 'success': '✅', 'warning': '⚠️', 'error': '❌'}.get(level, '📢')
        logging.info(f"{emoji} {title}: {message}")
        
        # Toast diyaloğu (opsiyonel - ileride widget oluşturulabilir)
        # QMessageBox kullanmak modal yapar, buradan kaçınmak daha iyi
        
    except Exception as e:
        logging.error(f"Toast gösterme hatası: {e}")
