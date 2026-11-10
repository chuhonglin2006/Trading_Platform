"""商品图片本地存储：与主服务同进程运行 """

import asyncio
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile, status
from tools_1.logger import get_logger


logger = get_logger(__name__, "image")


BACKEND_DIR = Path(__file__).resolve().parent.parent
IMAGE_DIR = BACKEND_DIR / "image_data" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# 单张图片上限 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _detect_extension(head: bytes) -> str | None:
    """根据文件头判断真实格式，不信任用户上传的文件名。"""
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


async def upload_image(product_id: int, file: UploadFile) -> dict:
    """
    保存商品图片。返回结构和原来的图片服务器保持一致，
    """
    if product_id <= 0:
        raise _bad_request("商品ID无效")

    # 最多只读 上限+1 字节，超大文件不会被整个读进内存
    data = await file.read(MAX_FILE_SIZE + 1)
    if not data:
        raise _bad_request("图片文件为空")
    if len(data) > MAX_FILE_SIZE:
        raise _bad_request("图片大小不能超过10MB")

    extension = _detect_extension(data[:16])
    if extension is None:
        raise _bad_request("只允许上传 JPG、PNG、WEBP 图片")

    filename = f"{uuid.uuid4().hex}{extension}"
    product_dir = IMAGE_DIR / str(product_id)

    def _write() -> None:
        product_dir.mkdir(parents=True, exist_ok=True)
        (product_dir / filename).write_bytes(data)

    try:
        # 磁盘写入放进线程，避免阻塞事件循环
        await asyncio.to_thread(_write)
    except OSError:
        logger.exception(
            "图片保存失败 product_id=%s filename=%s", product_id, filename
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="图片保存失败",
        )

    logger.info(
        "图片上传成功 product_id=%s filename=%s size=%s",
        product_id,
        filename,
        len(data),
    )
    return {
        "code": 200,
        "message": "图片上传成功",
        "data": {
            "filename": filename,
            "image_url": f"/images/{product_id}/{filename}",
            "product_id": product_id,
            "size": len(data),
        },
    }


async def delete_image(product_id: int, file_name: str) -> dict:
    """删除一张图片 文件已经不存在时视为成功"""
    if product_id <= 0:
        raise _bad_request("商品ID无效")
    # 防止路径穿越
    if not file_name or Path(file_name).name != file_name:
        raise _bad_request("非法文件名")
    if Path(file_name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise _bad_request("非法图片格式")

    product_dir = IMAGE_DIR / str(product_id)

    def _delete() -> None:
        (product_dir / file_name).unlink(missing_ok=True)
        # 商品目录空了就顺手删掉
        try:
            product_dir.rmdir()
        except OSError:
            pass

    try:
        await asyncio.to_thread(_delete)
    except OSError:
        logger.exception(
            "图片删除失败 product_id=%s filename=%s", product_id, file_name
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="图片删除失败",
        )

    logger.info("图片删除成功 product_id=%s filename=%s", product_id, file_name)
    return {"code": 200, "message": "图片删除成功", "data": None}