from __future__ import annotations

from urllib.parse import quote, unquote

import requests


def _parse_proxy(proxy: str) -> tuple[str, str, str, str, str]:
    if "://" in proxy:
        scheme, rest = proxy.split("://", 1)
    else:
        scheme, rest = "http", proxy
    scheme = scheme.lower()

    try:
        if "@" in rest:
            credentials, address = rest.rsplit("@", 1)
            login, password = credentials.split(":", 1)
        else:
            login, password = "", ""
            address = rest
        host, port = address.rsplit(":", 1)
    except ValueError as error:
        raise ValueError(
            "прокси должен иметь формат scheme://login:password@ip:port или ip:port"
        ) from error

    host_parts = host.split(".")
    if len(host_parts) != 4 or not all(
            part.isdigit() and 0 <= int(part) < 256 for part in host_parts
    ):
        raise ValueError("неправильный IPv4-адрес")
    if not port.isdigit() or not 0 < int(port) <= 65535:
        raise ValueError("неправильный порт")
    if scheme not in ("http", "https", "socks5", "socks5h"):
        raise ValueError("схема должна быть http, https, socks5 или socks5h")
    return scheme, login, password, host, port


def normalize_telegram_proxy(proxy: str | None) -> str:
    """Проверяет и нормализует URL Telegram-прокси."""
    if not proxy or not proxy.strip():
        return ""

    scheme, login, password, host, port = _parse_proxy(proxy.strip())
    auth = ""
    if login and password:
        auth = f"{quote(unquote(login), safe='')}:{quote(unquote(password), safe='')}@"
    return f"{scheme}://{auth}{host}:{port}"


def telegram_proxy_mapping(proxy: str | None) -> dict[str, str] | None:
    normalized = normalize_telegram_proxy(proxy)
    if not normalized:
        return None
    return {"http": normalized, "https": normalized}


def mask_telegram_proxy(proxy: str | None) -> str:
    if not proxy:
        return "—"
    scheme, login, _, host, port = _parse_proxy(proxy)
    auth = f"{unquote(login)}:••••@" if login else ""
    return f"{scheme}://{auth}{host}:{port}"


def check_telegram_proxy(proxy: str, token: str, timeout: int = 15) -> tuple[bool, str]:
    """Проверяет доступ к Telegram Bot API через конкретный прокси."""
    try:
        normalized = normalize_telegram_proxy(proxy)
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            proxies=telegram_proxy_mapping(normalized),
            timeout=timeout,
            headers={"User-Agent": "FunPaySigma-telegram-proxy-check"},
        )
        payload = response.json()
        if response.ok and payload.get("ok"):
            username = payload.get("result", {}).get("username") or "Telegram bot"
            return True, f"@{username}"
        description = str(payload.get("description") or f"HTTP {response.status_code}")
        return False, description.replace(token, "***")
    except Exception as error:
        return False, f"{type(error).__name__}: соединение не установлено"
