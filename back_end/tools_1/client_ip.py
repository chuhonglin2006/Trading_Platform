"""获取客户端 IP 的唯一入口
真实 IP 的还原由 uvicorn 的 proxy-headers 机制完成（：
只有当连接直接来自受信任的反向代理 Nginx 时，uvicorn 才会读取 X-Forwarded-For
并改写 request.client；来自其他地址的请求即使带了转发头，也会被忽略，无法伪造。
所以这里不再自己读取任何请求头，只读取 request.client.host 并做格式规范化。
项目里所有需要客户端 IP 的地方（限流、登录失败计数、验证码、访问日志、浏览量、归属地）
都必须通过 get_client_ip() 获取，不要直接用 request.client.host，也不要自己读请求头。
"""

import ipaddress

from fastapi import Request


def _normalize_ip(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None

    if text.startswith("[") and "]" in text:
        text = text[1:text.index("]")]

    # IPv6 作用域标识，例如 fe80::1%eth0
    if "%" in text:
        text = text.split("%", 1)[0]

    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return None

    # ::ffff:1.2.3.4 统一成 1.2.3.4，
    # 避免同一个用户因为 IPv4 / IPv6 映射写法不同，被当成两个 IP
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    return str(ip)


def get_client_ip(request: Request) -> str:
    """返回客户端 IP；取不到时返回 "unknown"。"""
    return _normalize_ip(request.client.host if request.client else None) or "unknown"