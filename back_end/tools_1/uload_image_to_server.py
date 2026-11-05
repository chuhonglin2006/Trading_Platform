"""上传图片到图片服务器"""

import httpx
from fastapi import UploadFile
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")


# 图片服务器只允许后端服务器内部访问
IMAGE_SERVER = "http://127.0.0.1:8001"


def normalize_image_url(image_url: str | None) -> str | None:
    """
    将图片服务器返回的完整 URL 统一转换成前端使用的 /images/xxx 路径。

    例如：

    http://120.26.37.94:8001/images/14/xxx.jpg
    ->
    /images/14/xxx.jpg

    http://127.0.0.1:8001/images/14/xxx.jpg
    ->
    /images/14/xxx.jpg

    /images/14/xxx.jpg
    ->
    /images/14/xxx.jpg
    """

    if not image_url:
        return None

    # 已经是相对路径
    if image_url.startswith("/images/"):
        return image_url

    marker = "/images/"

    if marker in image_url:
        return image_url[image_url.index(marker):]

    return image_url


async def upload_image(product_id: int, file: UploadFile) -> dict:
    """
    上传商品图片到图片服务器。

    图片服务器接口要求：
        POST /api/images/upload?product_id=xxx

    注意：
        product_id 是 query 参数，不是 form-data。
    """

    # 读取上传文件
    file_data = await file.read()

    files = {
        "file": (
            file.filename,
            file_data,
            file.content_type
        )
    }

    async with httpx.AsyncClient(timeout=30) as client:

        response = await client.post(
            f"{IMAGE_SERVER}/api/images/upload",
            params={
                "product_id": product_id
            },
            files=files
        )

    # 调试输出
    if response.status_code != 200:
        logger.error(
            "图片上传失败 product_id=%s status=%s response=%s",
            product_id,
            response.status_code,
            response.text[:1000]
        )

    response.raise_for_status()

    result = response.json()
    logger.info(
        "图片上传成功 product_id=%s filename=%s",
        product_id,
        file.filename
    )

    # 统一图片 URL
    if (
        isinstance(result, dict)
        and isinstance(result.get("data"), dict)
        and result["data"].get("image_url")
    ):
        result["data"]["image_url"] = normalize_image_url(
            result["data"]["image_url"]
        )

    return result


async def delete_image(product_id: int, file_name: str) -> dict:
    """
    删除商品图片。
    """

    url = f"{IMAGE_SERVER}/api/images/{product_id}/{file_name}"

    async with httpx.AsyncClient(timeout=30) as client:

        response = await client.delete(url)

    response.raise_for_status()
    logger.info(
        "图片删除成功 product_id=%s filename=%s",
        product_id,
        file_name
    )

    return response.json()


def get_image_filename(image_url: str) -> str:
    """
    从图片 URL 中获取文件名。

    支持：

    /images/14/abc.jpg

    http://120.26.37.94/images/14/abc.jpg

    http://120.26.37.94/images/14/abc.jpg?name=abc.jpg
    """

    parsed = urlparse(image_url)

    params = parse_qs(parsed.query)

    if "name" in params:
        return Path(
            unquote(params["name"][0])
        ).name

    return Path(
        unquote(parsed.path)
    ).name
