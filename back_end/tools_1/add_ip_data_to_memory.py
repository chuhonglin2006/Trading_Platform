"""将 IPv4 离线地区库加载到内存并提供查询。"""

from pathlib import Path
import sys

from ip2region import searcher, util

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tools_1.logger import get_logger


logger = get_logger(__name__, "python")

IP_DATA_PATH = (
    BACKEND_DIR
    / "ip_data"
    / "ip2region_v4.xdb"
)

_ip_region_searcher: searcher.Searcher | None = None


def init_ip_region_searcher() -> None:
    """首次启动时读取 XDB，后续查询全部走内存。"""
    global _ip_region_searcher

    if _ip_region_searcher is not None:
        return

    if not IP_DATA_PATH.is_file():
        raise FileNotFoundError(
            f"IP2Region 数据库不存在: {IP_DATA_PATH}"
        )

    buffer = util.load_content_from_file(str(IP_DATA_PATH))
    _ip_region_searcher = searcher.new_with_buffer(
        util.IPv4,
        buffer,
    )
    logger.info(
        "IP2Region数据库已加载到内存 path=%s size=%sbytes",
        IP_DATA_PATH,
        len(buffer),
    )


def search_ip_region(ip: str) -> str:
    """查询 IPv4 原始地区信息；未初始化、IPv6 或查询失败时返回空串。"""
    if _ip_region_searcher is None:
        return ""

    try:
        return _ip_region_searcher.search(ip)
    except ValueError:
        return ""


if __name__ == "__main__":
    init_ip_region_searcher()
    print(f"IP2Region 内存加载成功: {IP_DATA_PATH}")
