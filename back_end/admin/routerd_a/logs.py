"""管理员日志查看接口"""

from datetime import datetime
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from admin.curd_a.admins import get_supper_admin_info


admin_logs = APIRouter()



BASE_DIR = Path(__file__).resolve().parents[2]

# 日志目录
LOG_DIR = BASE_DIR / "Log"

# 单次最多读取的日志行数
MAX_LINES = 5000


@admin_logs.get("/api/admin/logs")
async def get_log_files(
    current_admin: dict = Depends(get_supper_admin_info),
) -> dict[str, Any]:
    """
    获取所有日志文件

    仅超级管理员可以访问
    """

    if not LOG_DIR.exists():
        return {
            "code": 200,
            "message": "日志目录为空",
            "data": []
        }

    files = []

    for file_path in LOG_DIR.iterdir():
        # 只允许普通文件
        if not file_path.is_file():
            continue

        # 这里只展示 .log 文件
        if file_path.suffix.lower() != ".log":
            continue

        stat = file_path.stat()

        files.append({
            "name": file_path.name,
            "size": stat.st_size,
            "modified_at": datetime.fromtimestamp(
                stat.st_mtime
            ).isoformat()
        })

    # 按最后修改时间倒序
    files.sort(
        key=lambda item: item["modified_at"],
        reverse=True
    )

    return {
        "code": 200,
        "message": "获取日志文件成功",
        "data": files
    }


@admin_logs.get("/api/admin/logs/content")
async def get_log_content(
    filename: str = Query(..., min_length=1),
    lines: int = Query(
        1000,
        ge=1,
        le=MAX_LINES
    ),
    current_admin: dict = Depends(get_supper_admin_info),
) -> dict[str, Any]:
    """
    查看指定日志文件内容

    仅超级管理员可以访问
    """

    # 禁止路径穿越
    #
    # 防止用户传：
    # ../../keys.env
    # ../../../../etc/passwd
    safe_name = Path(filename).name

    # 如果处理后的名称不一致，说明尝试访问其他目录
    if safe_name != filename:
        raise HTTPException(
            status_code=400,
            detail="非法日志文件名"
        )

    file_path = LOG_DIR / safe_name

    # 再次确保真实路径仍然位于 Log 目录内
    try:
        resolved_log_dir = LOG_DIR.resolve()
        resolved_file_path = file_path.resolve()

        resolved_file_path.relative_to(
            resolved_log_dir
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="非法文件路径"
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="日志文件不存在"
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="目标不是文件"
        )

    # 只允许查看 .log
    if file_path.suffix.lower() != ".log":
        raise HTTPException(
            status_code=403,
            detail="只允许查看日志文件"
        )

    try:
        # 使用 utf-8，遇到异常字符不让接口崩溃
        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as file:
            all_lines = file.readlines()

    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"读取日志失败：{exc}"
        )


    content_lines = all_lines[-lines:]

    stat = file_path.stat()

    return {
        "code": 200,
        "message": "获取日志内容成功",
        "data": {
            "name": file_path.name,
            "size": stat.st_size,
            "modified_at": datetime.fromtimestamp(
                stat.st_mtime
            ).isoformat(),
            "total_lines": len(all_lines),
            "show_lines": len(content_lines),
            "content": "".join(content_lines)
        }
    }