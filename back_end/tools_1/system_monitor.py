"""服务器状态采集：CPU、内存、带宽、磁盘、本服务进程、Redis、MySQL """
import asyncio
import math
import os
import platform
import shutil
import socket
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any

import psutil
from database_1.mysql_config import async_engine
from dotenv import load_dotenv
from sqlalchemy import text

from tools_1.logger import get_logger

logger = get_logger(__name__, "python")

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / "keys.env")

SAMPLE_INTERVAL = max(1, int(os.getenv("SYSTEM_SAMPLE_INTERVAL", "5")))
HISTORY_SECONDS = 3600
HISTORY_SIZE = HISTORY_SECONDS // SAMPLE_INTERVAL
MAX_CHART_POINTS = 240          # 返回给前端的最大点数，超过则等距抽稀
TOP_PROCESS_LIMIT = 5
TOP_PROCESS_CACHE_SECONDS = 10

try:
    BANDWIDTH_LIMIT_MBPS = float(os.getenv("NET_BANDWIDTH_MBPS", "0") or 0)
except ValueError:
    BANDWIDTH_LIMIT_MBPS = 0.0

# 统计流量时忽略的网卡：回环和 Docker 虚拟网卡（会把同一份流量重复统计一遍）
_SKIP_NIC_PREFIXES = ("docker", "veth", "br-", "virbr", "loopback")

_process = psutil.Process()
_cpu_count = psutil.cpu_count(logical=True) or 1

_history: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
_latest: dict[str, Any] = {}
_prev: dict[str, Any] = {}
_top_cache: dict[str, Any] = {"time": 0.0, "rows": []}


# ---------------------------------------------------------------- 采集函数

def _skip_nic(name: str) -> bool:
    lowered = name.lower()
    return lowered == "lo" or lowered.startswith(_SKIP_NIC_PREFIXES)


def _net_totals() -> dict[str, int]:
    """汇总所有真实网卡的累计流量。"""
    totals = {"rx": 0, "tx": 0, "rx_packets": 0, "tx_packets": 0}
    for name, counter in psutil.net_io_counters(pernic=True).items():
        if _skip_nic(name):
            continue
        totals["rx"] += counter.bytes_recv
        totals["tx"] += counter.bytes_sent
        totals["rx_packets"] += counter.packets_recv
        totals["tx_packets"] += counter.packets_sent
    return totals


def _disk_io_totals() -> dict[str, int] | None:
    try:
        counter = psutil.disk_io_counters()
    except Exception:
        return None
    if counter is None:
        return None
    return {"read": counter.read_bytes, "write": counter.write_bytes}


def _link_limit() -> tuple[float, str]:
    """带宽上限：优先用配置值，其次网卡速率，都没有则返回 0。"""
    if BANDWIDTH_LIMIT_MBPS > 0:
        return BANDWIDTH_LIMIT_MBPS, "configured"
    try:
        speeds = [
            stat.speed
            for name, stat in psutil.net_if_stats().items()
            if stat.isup and stat.speed > 0 and not _skip_nic(name)
        ]
    except Exception:
        speeds = []
    if speeds:
        return float(max(speeds)), "detected"
    return 0.0, "unknown"


def _rate(current: float, previous: float | None, seconds: float) -> float:
    if previous is None or seconds <= 0:
        return 0.0
    return max(0.0, (current - previous) / seconds)


def _prime() -> None:
    """psutil 的 cpu_percent 需要先调用一次建立基准。"""
    psutil.cpu_percent(interval=None)
    psutil.cpu_percent(interval=None, percpu=True)
    _process.cpu_percent(interval=None)
    _prev.update(
        time=time.time(),
        net=_net_totals(),
        disk=_disk_io_totals(),
    )


def _take_sample() -> dict[str, Any]:
    """采集一次，并更新速率基准。"""
    now = time.time()
    seconds = now - _prev.get("time", now)

    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
    memory = psutil.virtual_memory()

    net = _net_totals()
    prev_net = _prev.get("net") or {}
    rx_rate = _rate(net["rx"], prev_net.get("rx"), seconds)
    tx_rate = _rate(net["tx"], prev_net.get("tx"), seconds)

    disk = _disk_io_totals()
    prev_disk = _prev.get("disk")
    read_rate = write_rate = 0.0
    if disk and prev_disk:
        read_rate = _rate(disk["read"], prev_disk["read"], seconds)
        write_rate = _rate(disk["write"], prev_disk["write"], seconds)

    with _process.oneshot():
        # 单进程 CPU 以“单核 100%”计，除以核数后与整机百分比口径一致
        process_cpu = _process.cpu_percent(interval=None) / _cpu_count
        process_rss = _process.memory_info().rss

    _prev.update(time=now, net=net, disk=disk)

    sample = {
        "ts": int(now),
        "cpu": round(cpu_percent, 1),
        "mem": round(memory.percent, 1),
        "rx": round(rx_rate),
        "tx": round(tx_rate),
        "dr": round(read_rate),
        "dw": round(write_rate),
        "pc": round(process_cpu, 1),
        "pm": process_rss,
    }
    _latest.clear()
    _latest.update(
        sample=sample,
        cpu_cores=[round(value, 1) for value in cpu_cores],
        net=net,
    )
    return sample


def _disk_paths() -> list[Path]:
    paths = [BACKEND_DIR / "image_data" / "images", BACKEND_DIR]
    extra = os.getenv("DISK_CHECK_PATHS", "")
    paths += [Path(item.strip()) for item in extra.split(",") if item.strip()]
    return paths


def _disk_usage() -> list[dict[str, Any]]:
    """各目录所在磁盘的使用情况，同一块磁盘只显示一次。"""
    seen: set[int] = set()
    rows: list[dict[str, Any]] = []
    for path in _disk_paths():
        try:
            device = os.stat(path).st_dev
            if device in seen:
                continue
            total, used, free = shutil.disk_usage(path)
        except OSError:
            continue
        seen.add(device)
        rows.append({
            "path": str(path),
            "total": total,
            "used": used,
            "free": free,
            "percent": round(used / total * 100, 1) if total else 0.0,
        })
    return rows


def _read_int(path: str) -> int | None:
    try:
        raw = Path(path).read_text().strip()
        return None if raw == "max" else int(raw)
    except (OSError, ValueError):
        return None


def _cgroup_limits() -> dict[str, Any]:
    """容器限额（Docker / K8s）。psutil 在容器里看到的是宿主机总量，需要另外读 cgroup。"""
    memory: dict[str, Any] | None = None
    for current, limit in (
        ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory.max"),
        (
            "/sys/fs/cgroup/memory/memory.usage_in_bytes",
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        ),
    ):
        used, cap = _read_int(current), _read_int(limit)
        # cgroup v1 没有限制时是一个极大的数
        if used is not None and cap and cap < (1 << 60):
            memory = {
                "used": used,
                "limit": cap,
                "percent": round(used / cap * 100, 1),
            }
            break

    cpu_cores: float | None = None
    try:
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if quota != "max":
            cpu_cores = round(int(quota) / int(period), 2)
    except (OSError, ValueError):
        pass

    return {"memory": memory, "cpu_cores": cpu_cores}


def _top_processes() -> list[dict[str, Any]]:
    """内存占用最高的几个进程，10 秒内重复请求直接用缓存。"""
    now = time.time()
    if now - _top_cache["time"] < TOP_PROCESS_CACHE_SECONDS:
        return _top_cache["rows"]

    rows: list[dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        info = proc.info
        memory_info = info.get("memory_info")
        if memory_info is None:
            continue
        rows.append({
            "pid": info["pid"],
            "name": info.get("name") or "?",
            "rss": memory_info.rss,
        })
    rows.sort(key=lambda row: row["rss"], reverse=True)
    rows = rows[:TOP_PROCESS_LIMIT]
    _top_cache.update(time=now, rows=rows)
    return rows


def _process_info(sample: dict[str, Any]) -> dict[str, Any]:
    with _process.oneshot():
        threads = _process.num_threads()
        created = _process.create_time()
    handles = None
    for attr in ("num_fds", "num_handles"):      # Linux / Windows
        getter = getattr(_process, attr, None)
        if getter:
            try:
                handles = getter()
            except Exception:
                handles = None
            break
    return {
        "pid": _process.pid,
        "rss": sample["pm"],
        "cpu_percent": sample["pc"],
        "threads": threads,
        "handles": handles,
        "uptime": max(0, time.time() - created),
        "top": _top_processes(),
    }


def _host_info() -> dict[str, Any]:
    try:
        load = [round(value, 2) for value in psutil.getloadavg()]
    except (AttributeError, OSError):
        load = None
    boot = psutil.boot_time()
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_physical": psutil.cpu_count(logical=False),
        "cpu_logical": _cpu_count,
        "boot_time": int(boot),
        "uptime": max(0, time.time() - boot),
        "load": load,
        "interval": SAMPLE_INTERVAL,
    }


async def _redis_status(redis) -> dict[str, Any]:
    try:
        info = await redis.info()
        keys = await redis.dbsize()
    except Exception:
        logger.exception("读取 Redis 状态失败")
        return {"available": False}

    hits = int(info.get("keyspace_hits", 0))
    misses = int(info.get("keyspace_misses", 0))
    lookups = hits + misses
    return {
        "available": True,
        "version": info.get("redis_version"),
        "uptime": info.get("uptime_in_seconds"),
        "used_memory": info.get("used_memory"),
        "peak_memory": info.get("used_memory_peak"),
        "max_memory": info.get("maxmemory") or None,   # 0 表示不限制
        "fragmentation": info.get("mem_fragmentation_ratio"),
        "clients": info.get("connected_clients"),
        "ops": info.get("instantaneous_ops_per_sec"),
        "keys": keys,
        "hit_rate": round(hits / lookups * 100, 1) if lookups else None,
        "evicted_keys": info.get("evicted_keys"),
        "expired_keys": info.get("expired_keys"),
    }


async def _mysql_status() -> dict[str, Any]:
    names = (
        "Threads_connected",
        "Threads_running",
        "Uptime",
        "Max_used_connections",
        "Slow_queries",
        "Aborted_connects",
    )
    quoted = ",".join(f"'{name}'" for name in names)
    try:
        async with async_engine.connect() as connection:
            rows = await connection.execute(
                text(f"SHOW GLOBAL STATUS WHERE Variable_name IN ({quoted})")
            )
            status = {row[0]: row[1] for row in rows}
            version = await connection.scalar(text("SELECT VERSION()"))
            max_row = (
                await connection.execute(
                    text("SHOW VARIABLES LIKE 'max_connections'")
                )
            ).first()
    except Exception:
        logger.exception("读取 MySQL 状态失败")
        return {"available": False}

    def to_int(key: str) -> int | None:
        try:
            return int(status[key])
        except (KeyError, TypeError, ValueError):
            return None

    pool = async_engine.pool
    pool_info = None
    try:
        pool_info = {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except Exception:
        pass

    return {
        "available": True,
        "version": version,
        "uptime": to_int("Uptime"),
        "connections": to_int("Threads_connected"),
        "running": to_int("Threads_running"),
        "max_used": to_int("Max_used_connections"),
        "max_connections": int(max_row[1]) if max_row else None,
        "slow_queries": to_int("Slow_queries"),
        "aborted_connects": to_int("Aborted_connects"),
        "pool": pool_info,
    }


# ---------------------------------------------------------------- 对外接口

async def system_monitor_loop() -> None:
    """后台采样任务，在 lifespan 里启动。"""
    _prime()
    await asyncio.sleep(1)
    while True:
        try:
            _history.append(_take_sample())
        except Exception:
            logger.exception("服务器状态采样失败")
        await asyncio.sleep(SAMPLE_INTERVAL)


def _downsample(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(points) <= MAX_CHART_POINTS:
        return points
    step = math.ceil(len(points) / MAX_CHART_POINTS)
    # 从最新一点往回取，保证最新数据一定在结果里
    return points[::-1][::step][::-1]


async def get_system_status(redis, minutes: int) -> dict[str, Any]:
    """当前状态 + 最近 minutes 分钟的历史曲线。"""
    if not _latest:
        # 采样任务刚启动还没出数据时，临时采一次
        if not _prev:
            _prime()
        _history.append(_take_sample())

    sample = _latest["sample"]
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    limit_mbps, limit_source = _link_limit()
    limit_bytes = limit_mbps * 1_000_000 / 8

    def percent_of_limit(rate: float) -> float | None:
        if limit_bytes <= 0:
            return None
        return round(min(100.0, rate / limit_bytes * 100), 1)

    net = _latest["net"]
    cgroup = _cgroup_limits()
    try:
        frequency = psutil.cpu_freq()
    except Exception:
        frequency = None

    redis_info, mysql_info = await asyncio.gather(
        _redis_status(redis), _mysql_status()
    )

    cutoff = time.time() - minutes * 60
    history = _downsample([point for point in _history if point["ts"] >= cutoff])

    return {
        "current": {
            "time": sample["ts"],
            "host": _host_info(),
            "cpu": {
                "percent": sample["cpu"],
                "cores": _latest["cpu_cores"],
                "freq_mhz": round(frequency.current) if frequency else None,
                "limit_cores": cgroup["cpu_cores"],
            },
            "memory": {
                "total": memory.total,
                "used": memory.total - memory.available,
                "available": memory.available,
                "percent": round(memory.percent, 1),
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_percent": round(swap.percent, 1),
                "container": cgroup["memory"],
            },
            "network": {
                "rx_rate": sample["rx"],
                "tx_rate": sample["tx"],
                "rx_total": net["rx"],
                "tx_total": net["tx"],
                "rx_packets": net["rx_packets"],
                "tx_packets": net["tx_packets"],
                "limit_mbps": limit_mbps or None,
                "limit_source": limit_source,
                "rx_percent": percent_of_limit(sample["rx"]),
                "tx_percent": percent_of_limit(sample["tx"]),
            },
            "disk": {
                "partitions": _disk_usage(),
                "read_rate": sample["dr"],
                "write_rate": sample["dw"],
            },
            "process": _process_info(sample),
            "redis": redis_info,
            "mysql": mysql_info,
        },
        "history": history,
    }
