"""
Price Alerts - Fiyat alarmları
"""


class PriceAlert:
    """
    Fiyat alarm sistemi
    - Fiyat seviyelerine alarm ekle
    - Otomatik tetiklenme
    """

    def __init__(self):
        self.alerts = []

    def add_alert(self, price: float, alert_type: str, message: str):
        """
        Fiyat alarmı ekle

        Args:
            price: Alarm fiyatı
            alert_type: 'above' veya 'below'
            message: Alarm mesajı
        """
        self.alerts.append(
            {"price": price, "type": alert_type, "message": message, "triggered": False}
        )

    def check_alerts(self, current_price: float) -> list:
        """
        Alarmları kontrol et

        Args:
            current_price: Güncel fiyat

        Returns:
            Tetiklenen alarmların listesi
        """
        triggered = []

        for alert in self.alerts:
            if alert["triggered"]:
                continue

            if alert["type"] == "above" and current_price >= alert["price"]:
                alert["triggered"] = True
                triggered.append(alert)
            elif alert["type"] == "below" and current_price <= alert["price"]:
                alert["triggered"] = True
                triggered.append(alert)

        return triggered

    def clear_alerts(self):
        """Tüm alarmları temizle"""
        self.alerts = []

    def remove_alert(self, price: float):
        """Belirli bir fiyat alarmını sil"""
        self.alerts = [a for a in self.alerts if a["price"] != price]

    def get_active_alerts(self) -> list:
        """Aktif (henüz tetiklenmemiş) alarmları döndür"""
        return [a for a in self.alerts if not a["triggered"]]

    def get_triggered_alerts(self) -> list:
        """Tetiklenmiş alarmları döndür"""
        return [a for a in self.alerts if a["triggered"]]
