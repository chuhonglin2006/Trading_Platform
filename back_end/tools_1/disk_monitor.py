""" 定期检查磁盘剩余空间 """
import asyncio
import os
import shutil
import socket
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tools_1.email import send_email
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / "keys.env")

GB = 1024 ** 3

ALERT_EMAIL = os.getenv("ALERT_EMAIL", "").strip()
ALERT_THRESHOLD = float(os.getenv("DISK_ALERT_GB", "5")) * GB
CHECK_INTERVAL = int(os.getenv("DISK_CHECK_INTERVAL", "600"))
REPEAT_SECONDS = int(float(os.getenv("DISK_ALERT_REPEAT_HOURS", "24")) * 3600)

# 回升到 阈值 + 1GB 以上才算恢复
RECOVER_MARGIN = 1 * GB

# Redis 不可用时的进程内兜底状态
_local_sent: dict[str, float] = {}
_local_active: set[str] = set()


def _watch_paths() -> list[Path]:
    """要检查的目录：图片目录、后端目录再加上自定义目录。"""
    paths = [BACKEND_DIR / "image_data" / "images", BACKEND_DIR]
    extra = os.getenv("DISK_CHECK_PATHS", "")
    paths += [Path(item.strip()) for item in extra.split(",") if item.strip()]
    return paths


def _collect_disks() -> dict[str, tuple[Path, int, int, int]]:
    """
    返回 {设备标识: (目录, 总容量, 已用, 剩余)}。
    同一块磁盘上的多个目录只检查一次。
    """
    disks: dict[str, tuple[Path, int, int, int]] = {}

    for path in _watch_paths():
        try:
            device = str(os.stat(path).st_dev)
            total, used, free = shutil.disk_usage(path)
        except OSError:
            logger.warning("磁盘检查跳过，目录不可访问：%s", path)
            continue

        disks.setdefault(device, (path, total, used, free))

    return disks


def _alert_key(device: str) -> str:
    return f"disk:alert:{device}"      # 提醒节流：有效期内不重复发


def _active_key(device: str) -> str:
    return f"disk:active:{device}"     # 标记 正处于空间不足状态 用于发恢复通知


async def _claim_alert(redis, device: str) -> bool:
    """抢到发送权才返回 True"""
    try:
        return bool(
            await redis.set(
                _alert_key(device), "1", nx=True, ex=REPEAT_SECONDS
            )
        )
    except Exception:
        logger.exception("磁盘提醒节流读取 Redis 失败，改用进程内记录")
        now = time.monotonic()
        last = _local_sent.get(device)
        if last is not None and now - last < REPEAT_SECONDS:
            return False
        _local_sent[device] = now
        return True


async def _release_alert(redis, device: str) -> None:
    """邮件发送失败时释放发送权 下一轮检查会重试。"""
    _local_sent.pop(device, None)
    try:
        await redis.delete(_alert_key(device))
    except Exception:
        logger.exception("释放磁盘提醒节流标记失败")


async def _mark_active(redis, device: str) -> None:
    try:
        await redis.set(_active_key(device), "1")
    except Exception:
        _local_active.add(device)


async def _take_active(redis, device: str) -> bool:
    """
    取走 空间不足 标记；之前确实处于不足状态才返回 True。
    同时清掉节流标记，这样空间再次不足时可以立刻重新提醒。
    """
    try:
        was_active = bool(await redis.delete(_active_key(device)))
        await redis.delete(_alert_key(device))
    except Exception:
        was_active = False

    if device in _local_active:
        _local_active.discard(device)
        was_active = True

    _local_sent.pop(device, None)
    return was_active


def _fmt(size: float) -> str:
    return f"{size / GB:.2f} GB"


def _build_alert(path: Path, total: int, used: int, free: int) -> tuple[str, str]:
    subject = f"磁盘空间不足 剩余 {_fmt(free)}"
    content = (
        "校园二手交易平台服务器磁盘空间不足，请尽快处理。\n\n"
        f"服务器：{socket.gethostname()}\n"
        f"检查目录：{path}\n"
        f"总容量：{_fmt(total)}\n"
        f"已使用：{_fmt(used)}（{used / total:.0%}）\n"
        f"剩余：{_fmt(free)}（提醒阈值：{_fmt(ALERT_THRESHOLD)}）\n"
        f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n\n"

    )
    return subject, content


def _build_recovery(path: Path, total: int, free: int) -> tuple[str, str]:
    subject = f"磁盘空间已恢复 剩余 {_fmt(free)}"
    content = (
        "校园二手交易平台服务器磁盘空间已恢复。\n\n"
        f"服务器：{socket.gethostname()}\n"
        f"检查目录：{path}\n"
        f"总容量：{_fmt(total)}\n"
        f"剩余：{_fmt(free)}\n"
        f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}"
    )
    return subject, content


async def check_disks(redis) -> None:
    """检查一次所有磁盘，按需发送提醒或恢复邮件。"""
    disks = await asyncio.to_thread(_collect_disks)

    for device, (path, total, used, free) in disks.items():
        if free < ALERT_THRESHOLD:
            if not await _claim_alert(redis, device):
                continue

            subject, content = _build_alert(path, total, used, free)
            try:
                # send_email 是同步函数，放进线程避免阻塞事件循环
                await asyncio.to_thread(
                    send_email, ALERT_EMAIL, content, subject
                )
            except Exception:
                logger.exception("磁盘空间提醒邮件发送失败，下一轮重试")
                await _release_alert(redis, device)
            else:
                await _mark_active(redis, device)
                logger.warning(
                    "磁盘空间不足，已发送提醒邮件 path=%s free=%s",
                    path,
                    _fmt(free),
                )

        elif free >= ALERT_THRESHOLD + RECOVER_MARGIN:
            if not await _take_active(redis, device):
                continue

            subject, content = _build_recovery(path, total, free)
            try:
                await asyncio.to_thread(
                    send_email, ALERT_EMAIL, content, subject
                )
            except Exception:
                logger.exception("磁盘空间恢复通知邮件发送失败")
            else:
                logger.info(
                    "磁盘空间已恢复，已发送通知 path=%s free=%s",
                    path,
                    _fmt(free),
                )


async def disk_monitor_loop(redis) -> None:
    """后台任务：定时检查磁盘剩余空间。"""
    if not ALERT_EMAIL:
        logger.warning("未配置 ALERT_EMAIL，磁盘空间监控已关闭")
        return

    logger.info(
        "磁盘空间监控已启动 threshold=%s interval=%ss",
        _fmt(ALERT_THRESHOLD),
        CHECK_INTERVAL,
    )

    while True:
        try:
            await check_disks(redis)
        except Exception:
            logger.exception("磁盘空间检查失败")
        await asyncio.sleep(CHECK_INTERVAL)