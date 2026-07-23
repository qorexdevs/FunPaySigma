from unittest import TestCase
from unittest.mock import Mock, patch

from Utils.telegram_proxy import (
    check_telegram_proxy,
    mask_telegram_proxy,
    normalize_telegram_proxy,
    telegram_proxy_mapping,
)


class TelegramProxyTests(TestCase):
    def test_normalizes_proxy_and_escapes_credentials(self):
        proxy = normalize_telegram_proxy("socks5h://user@mail:p@ss@127.0.0.1:1080")

        self.assertEqual(proxy, "socks5h://user%40mail:p%40ss@127.0.0.1:1080")
        self.assertEqual(telegram_proxy_mapping(proxy), {"http": proxy, "https": proxy})

    def test_masks_password(self):
        masked = mask_telegram_proxy("http://user:secret@127.0.0.1:8080")

        self.assertEqual(masked, "http://user:••••@127.0.0.1:8080")
        self.assertNotIn("secret", masked)

    @patch("Utils.telegram_proxy.requests.get", side_effect=RuntimeError("123456:SECRET"))
    def test_connection_errors_do_not_expose_token(self, _):
        success, details = check_telegram_proxy(
            "http://user:password@127.0.0.1:8080", "123456:SECRET"
        )

        self.assertFalse(success)
        self.assertNotIn("123456:SECRET", details)
        self.assertNotIn("password", details)

    @patch("Utils.telegram_proxy.requests.get")
    def test_checks_bot_api_through_proxy(self, request_get):
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {"ok": True, "result": {"username": "sigma_test_bot"}}
        request_get.return_value = response

        success, details = check_telegram_proxy(
            "socks5://127.0.0.1:1080", "123456:TEST_TOKEN"
        )

        self.assertTrue(success)
        self.assertEqual(details, "@sigma_test_bot")
        self.assertEqual(
            request_get.call_args.kwargs["proxies"],
            {
                "http": "socks5://127.0.0.1:1080",
                "https": "socks5://127.0.0.1:1080",
            },
        )
