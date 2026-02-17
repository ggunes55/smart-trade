# -*- coding: utf-8 -*-
"""
Notification Manager - Real-time Bildirimler
In-app toasts, desktop notifications, Telegram, Email
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationManager:
    """Real-time bildirimler yönetimi"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.email_enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
        
        self.notification_callbacks = []
    
    def register_callback(self, callback):
        """Bildirim callback'i kaydet"""
        self.notification_callbacks.append(callback)
    
    def send_signal_notification(self, symbol: str, action: str, 
                                confidence: float, price: float = None):
        """Sinyal bildirimi gönder"""
        try:
            confidence_pct = confidence * 100
            
            message = f"🎯 {symbol} {action} Sinyali\nGüven: %{confidence_pct:.0f}"
            if price:
                message += f"\nFiyat: ₺{price:.2f}"
            
            # In-app toast
            self._show_toast(
                title=f"{symbol} {action}",
                message=message,
                level='success',
                duration=5000
            )
            
            # Desktop notification
            self._show_desktop_notification(
                title="Swing Trade - Sinyal",
                message=f"{symbol} {action} sinyali (%{confidence_pct:.0f} güven)"
            )
            
            # Telegram
            if self.telegram_token:
                self._send_telegram(
                    f"🎯 *{symbol}* {action}\n"
                    f"Güven: {confidence_pct:.0f}%\n"
                    f"Fiyat: ₺{price:.2f}" if price else ""
                )
            
            logger.info(f"✅ Sinyal bildirimi gönderildi: {symbol} {action}")
        
        except Exception as e:
            logger.error(f"Sinyal bildirimi hatası: {e}")
    
    def send_risk_alert(self, message: str, portfolio_state: dict = None):
        """Risk uyarısı gönder"""
        try:
            # In-app toast
            self._show_toast(
                title="⚠️ Risk Uyarısı",
                message=message,
                level='warning',
                duration=7000
            )
            
            # Desktop notification
            self._show_desktop_notification(
                title="Swing Trade - Risk Uyarısı",
                message=message
            )
            
            # Telegram
            if self.telegram_token:
                self._send_telegram(f"⚠️ *Risk Uyarısı*\n{message}")
            
            logger.warning(f"⚠️ Risk uyarısı: {message}")
        
        except Exception as e:
            logger.error(f"Risk uyarısı hatası: {e}")
    
    def send_connection_alert(self, connected: bool):
        """Bağlantı durumu bildirimi"""
        try:
            if connected:
                message = "✅ WebSocket bağlantısı kuruldu"
                level = 'success'
                title = "Bağlantı Başarılı"
            else:
                message = "❌ WebSocket bağlantısı kesildi"
                level = 'error'
                title = "Bağlantı Başarısız"
            
            self._show_toast(
                title=title,
                message=message,
                level=level,
                duration=3000
            )
            
            logger.info(f"🔌 Bağlantı: {message}")
        
        except Exception as e:
            logger.error(f"Bağlantı bildirimi hatası: {e}")
    
    def send_error_notification(self, error_msg: str, context: str = ""):
        """Hata bildirimi gönder"""
        try:
            full_message = f"{context}\n{error_msg}" if context else error_msg
            
            self._show_toast(
                title="❌ Hata Oluştu",
                message=full_message,
                level='error',
                duration=5000
            )
            
            self._show_desktop_notification(
                title="Swing Trade - Hata",
                message=error_msg
            )
            
            if self.telegram_token:
                self._send_telegram(f"❌ *Hata*\n{error_msg}")
            
            logger.error(f"❌ Hata: {error_msg}")
        
        except Exception as e:
            logger.error(f"Hata bildirimi hatası: {e}")
    
    def _show_toast(self, title: str, message: str, level: str = 'info', 
                   duration: int = 3000):
        """In-app toast göster"""
        try:
            notification_data = {
                'type': 'toast',
                'title': title,
                'message': message,
                'level': level,  # info, success, warning, error
                'duration': duration
            }
            
            # Tüm callback'leri çağır
            for callback in self.notification_callbacks:
                try:
                    callback(notification_data)
                except Exception as e:
                    logger.error(f"Toast callback hatası: {e}")
        
        except Exception as e:
            logger.error(f"Toast gösterme hatası: {e}")
    
    def _show_desktop_notification(self, title: str, message: str):
        """İşletim sistemi bildirimini göster"""
        try:
            # Windows: win10toast kullanılabilir
            # Linux: notify-send
            # macOS: osascript
            
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    title=title,
                    msg=message,
                    duration=5,
                    threaded=True
                )
            except ImportError:
                logger.debug("win10toast modülü yüklü değil, desktop notification atlanıyor")
        
        except Exception as e:
            logger.debug(f"Desktop notification hatası: {e}")
    
    def _send_telegram(self, message: str):
        """Telegram'a mesaj gönder"""
        try:
            if not self.telegram_token or not self.telegram_chat_id:
                logger.debug("Telegram token veya chat ID yapılandırılmadı")
                return
            
            import requests
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                logger.debug("✅ Telegram mesajı gönderildi")
            else:
                logger.warning(f"Telegram mesajı gönderilemedi: {response.status_code}")
        
        except Exception as e:
            logger.debug(f"Telegram gönderme hatası: {e}")
    
    def _send_email(self, subject: str, body: str, recipient: Optional[str] = None):
        """Email gönder"""
        try:
            if not self.email_enabled:
                return
            
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            sender_email = os.getenv('EMAIL_SENDER')
            sender_password = os.getenv('EMAIL_PASSWORD')
            recipient = recipient or os.getenv('EMAIL_RECIPIENT')
            
            if not all([sender_email, sender_password, recipient]):
                logger.debug("Email konfigürasyonu eksik")
                return
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # SMTP bağlantısı
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            logger.debug("✅ Email gönderildi")
        
        except Exception as e:
            logger.debug(f"Email gönderme hatası: {e}")
