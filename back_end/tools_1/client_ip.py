"""从经过 Nginx 代理的请求中提取真实客户端 IP。"""

import ipaddress

from fastapi import Request


def _normalize_ip(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None

    # X-Forwarded-For 可能包含 "客户端, 代理1, 代理2"。
    text = text.split(",", 1)[0].strip()

    if text.startswith("[") and "]" in text:
        text = text[1:text.index("]")]
    elif text.count(":") == 1:
        host, port = text.rsplit(":", 1)
        if port.isdigit():
            text = host

    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return None


def get_client_ip(request: Request) -> str:
    """优先读取 Nginx 设置的转发头，最后回退到连接地址。"""
    for value in (
        request.headers.get("X-Forwarded-For"),
        request.headers.get("X-Real-IP"),
    ):
        ip = _normalize_ip(value)
        if ip:
            return ip

    return _normalize_ip(request.client.host if request.client else None) or "unknown"
