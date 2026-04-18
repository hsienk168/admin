from unittest.mock import patch, MagicMock
from monitor.notifier import TelegramNotifier

@patch("monitor.notifier.requests.post")
def test_send_volatility_alert(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="test_token", chat_id="123")
    result = notifier.send_volatility_alert(
        symbol="BTCUSDT",
        price=100000.0,
        change_pct=5.2,
        std_devs=2.3
    )
    assert result is True
    args = mock_post.call_args
    assert "BTCUSDT" in args.kwargs["json"]["text"]

@patch("monitor.notifier.requests.post")
def test_send_funding_rate_alert(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="test_token", chat_id="123")
    result = notifier.send_funding_rate_alert(symbol="ETHUSDT", funding_rate=-0.015)
    assert result is True

@patch("monitor.notifier.requests.post")
def test_send_tracking_report(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="test_token", chat_id="123")
    result = notifier.send_tracking_report(symbol="BTCUSDT", price=101000.0, change_pct=1.2, report_count=3)
    assert result is True

@patch("monitor.notifier.requests.post")
def test_send_noop(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    notifier = TelegramNotifier(bot_token="test_token", chat_id="123")
    result = notifier.send_noop()
    assert result is True
