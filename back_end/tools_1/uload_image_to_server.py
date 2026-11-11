"""商品图片工具"""

from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from tools_1.image_storage import delete_image, upload_image  # noqa: F401


def normalize_image_url(image_url: str | None) -> str | None:
    """
    将图片 URL 统一转换成前端使用的 /images/xxx 路径
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


def get_image_filename(image_url: str) -> str:
    """
    从图片 URL 中获取文件名。
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