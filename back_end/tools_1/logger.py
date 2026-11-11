"""按类别写入 Log 目录的统一日志配置。"""

from logging import Formatter, Logger, getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "Log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILES = {
    "python": "Python.log",
    "redis": "Redis.log",
    "mysql": "MySQL.log",
    "image": "Image.log",
}

FORMATTER = Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_handlers: dict[str, RotatingFileHandler] = {}


def _get_handler(category: str) -> RotatingFileHandler:
    """按需创建分类 Handler，避免不同进程占用无关日志文件。"""
    if category not in LOG_FILES:
        raise ValueError(f"未知日志分类: {category}")

    handler = _handlers.get(category)
    if handler is not None:
        return handler

    handler = RotatingFileHandler(
        LOG_DIR / LOG_FILES[category],
        maxBytes=20 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    handler.setLevel("DEBUG")
    handler.setFormatter(FORMATTER)
    _handlers[category] = handler
    return handler


def get_logger(module_name: str, category: str = "python") -> Logger:
    """获取指定分类的模块日志器。"""
    logger = getLogger(f"backend.{category}.{module_name}")
    logger.setLevel("INFO")
    logger.propagate = False

    handler = _get_handler(category)
    if handler not in logger.handlers:
        logger.addHandler(handler)

    return logger


def configure_uvicorn_logging(category: str = "python") -> None:
    """将 Uvicorn 日志写入指定分类，访问日志由 HTTP 中间件记录。"""
    category_handler = _get_handler(category)

    for name in ("uvicorn", "uvicorn.error"):
        logger = getLogger(name)
        logger.setLevel("INFO")
        logger.propagate = False
        logger.handlers = [category_handler]

    access_logger = getLogger("uvicorn.access")
    access_logger.handlers = []
    access_logger.propagate = False
    access_logger.disabled = True
