import requests
from typing import Optional

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def _send(self, text: str) -> bool:
        try:
            resp = requests.post(self.api_url, json={"chat_id": self.chat_id, "text": text}, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def send_volatility_alert(self, symbol: str, price: float, change_pct: float, std_devs: float) -> bool:
        text = (
            f"🚨 **波動警報**\n\n"
            f"幣種: {symbol}\n"
            f"現價: ${price:,.2f}\n"
            f"5分鐘變動: {change_pct:+.2f}%\n"
            f"偏離標準差: {std_devs:.1f}σ\n"
            f"原因: 波動超限"
        )
        return self._send(text)

    def send_funding_rate_alert(self, symbol: str, funding_rate: float) -> bool:
        text = (
            f"💸 **資金費率警報**\n\n"
            f"幣種: {symbol}\n"
            f"資金費率: {funding_rate * 100:.4f}%\n"
            f"原因: 負資金費率超限"
        )
        return self._send(text)

    def send_tracking_report(self, symbol: str, price: float, change_pct: float, report_count: int) -> bool:
        text = (
            f"📍 **追蹤回報** [{report_count}]\n\n"
            f"幣種: {symbol}\n"
            f"現價: ${price:,.2f}\n"
            f"相對於觸發時: {change_pct:+.2f}%"
        )
        return self._send(text)

    def send_noop(self):
        """空通知，用於測試連線"""
        return self._send("✅ Binance 監控系統已啟動")
