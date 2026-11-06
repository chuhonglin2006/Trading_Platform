from pathlib import Path
import logging
import logging.handlers
import os
import sys
import time
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from tools_1.logger import configure_uvicorn_logging, get_logger
except ModuleNotFoundError as exc:
    if exc.name not in {"tools_1", "tools_1.logger"}:
        raise

    LOG_DIR = BACKEND_DIR / "Log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _image_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "Image.log",
        maxBytes=20 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    _image_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )

    for _uvicorn_logger_name in ("uvicorn", "uvicorn.error"):
        _uvicorn_logger = logging.getLogger(_uvicorn_logger_name)
        _uvicorn_logger.setLevel(logging.INFO)
        _uvicorn_logger.propagate = False
        _uvicorn_logger.handlers = [_image_handler]

    _access_logger = logging.getLogger("uvicorn.access")
    _access_logger.handlers = []
    _access_logger.propagate = False
    _access_logger.disabled = True

    def configure_uvicorn_logging(category: str = "image") -> None:
        return

    def get_logger(module_name: str, category: str = "image"):
        fallback_logger = logging.getLogger(
            f"backend.{category}.{module_name}"
        )
        fallback_logger.setLevel(logging.INFO)
        fallback_logger.propagate = False
        if _image_handler not in fallback_logger.handlers:
            fallback_logger.addHandler(_image_handler)
        return fallback_logger


logger = get_logger(__name__, "image")
configure_uvicorn_logging("image")


# 图片保存目录
IMAGE_DIR = BASE_DIR / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# 最大图片大小：10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# 允许的图片格式
ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# 服务器监听地址
HOST = os.getenv(
    "IMAGE_SERVER_HOST",
    "0.0.0.0"
)

# 图片服务器端口
PORT = int(
    os.getenv(
        "IMAGE_SERVER_PORT",
        "8001"
    )
)

PUBLIC_BASE_URL = os.getenv(
    "IMAGE_SERVER_PUBLIC_URL"
).rstrip("/")


app = FastAPI(
    title="校园二手交易平台图片服务器",
    description="校园二手交易平台商品图片上传与管理服务",
    version="1.0.0",
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_image_server_request(request, call_next):
    """记录图片服务器请求和异常。"""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "图片服务器请求失败 request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000
    log_method = logger.warning if response.status_code >= 400 else logger.info
    log_method(
        "图片服务器请求 request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms
    )
    response.headers.setdefault("X-Request-ID", request_id)
    return response

# 静态图片目录


app.mount(
    "/images",
    StaticFiles(directory=str(IMAGE_DIR)),
    name="images",
)

# 工具函数


def get_product_dir(product_id: int) -> Path:
    """
    获取商品对应的图片目录。

    例如：

    product_id = 8

    返回：

    images/8/
    """

    product_dir = IMAGE_DIR / str(product_id)

    product_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    return product_dir


def build_image_url(
    product_id: int,
    filename: str
) -> str:
    """
    生成图片公网访问地址。
    """

    return (
        f"{PUBLIC_BASE_URL}"
        f"/images/{product_id}/{filename}"
    )



# 健康检查


@app.get("/health")
async def health():
    """
    图片服务器健康检查。
    """

    return {
        "code": 200,
        "message": "图片服务器运行正常",
        "data": {
            "host": HOST,
            "port": PORT,
            "image_dir": str(IMAGE_DIR),
            "public_base_url": PUBLIC_BASE_URL,
        }
    }



# 上传图片


@app.post("/api/images/upload")
async def upload_image(
    product_id: int,
    file: UploadFile = File(...)
):
    """
    上传商品图片。

    注意：

    product_id 是 Query 参数。

    正确请求：

    POST
    /api/images/upload?product_id=8

    multipart/form-data:
        file = 图片文件
    """


    # 检查商品 ID


    if product_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="商品ID无效"
        )


    # 检查文件名


    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="文件名不能为空"
        )


    # 获取扩展名


    suffix = Path(
        file.filename
    ).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="只允许上传 JPG、JPEG、PNG、WEBP 图片"
        )


    # 读取文件


    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=400,
            detail="图片文件为空"
        )


    # 检查文件大小


    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="图片大小不能超过10MB"
        )


    # 获取商品图片目录


    product_dir = get_product_dir(product_id)

    # 生成随机文件名
    # 不直接使用用户上传的文件名，
    # 防止特殊字符、中文文件名、文件覆盖等问题。

    filename = (
        f"{uuid.uuid4().hex}"
        f"{suffix}"
    )

    save_path = product_dir / filename

    # 保存图片


    try:
        save_path.write_bytes(data)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"图片保存失败: {str(e)}"
        )


    # 生成公网图片 URL

    image_url = build_image_url(
        product_id,
        filename
    )

    return {
        "code": 200,
        "message": "图片上传成功",
        "data": {
            "filename": filename,
            "image_url": image_url,
            "product_id": product_id,
            "size": len(data),
        },
    }


# 获取商品图片列表

@app.get("/api/images/{product_id}")
async def get_product_images(
    product_id: int
):
    """
    获取某个商品的全部图片。

    例如：

    GET /api/images/8
    """

    if product_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="商品ID无效"
        )

    product_dir = IMAGE_DIR / str(product_id)

    # 商品没有图片目录
    if not product_dir.exists():
        return {
            "code": 200,
            "message": "获取商品图片成功",
            "data": []
        }

    images = []

    # 遍历图片


    for path in sorted(product_dir.iterdir()):

        # 只处理文件
        if not path.is_file():
            continue

        # 过滤非图片文件
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        images.append({
            "filename": path.name,
            "image_url": build_image_url(
                product_id,
                path.name
            ),
        })

    return {
        "code": 200,
        "message": "获取商品图片成功",
        "data": images
    }



# 删除单张图片


@app.delete("/api/images/{product_id}/{filename}")
async def delete_image(
    product_id: int,
    filename: str
):
    """
    删除某个商品的一张图片。

    例如：

    DELETE
    /api/images/8/xxxxxxxx.png
    """

    if product_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="商品ID无效"
        )


    # 防止路径穿越

    if Path(filename).name != filename:
        raise HTTPException(
            status_code=400,
            detail="非法文件名"
        )

    # 检查扩展名


    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="非法图片格式"
        )


    # 图片路径


    file_path = (
        IMAGE_DIR
        / str(product_id)
        / filename
    )

    # 检查文件


    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="图片不存在"
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="目标不是图片文件"
        )


    # 删除


    try:
        file_path.unlink()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"图片删除失败: {str(e)}"
        )


    # 如果商品目录已经空了，就删除目录


    product_dir = IMAGE_DIR / str(product_id)

    if product_dir.exists():

        try:
            remaining_files = list(
                product_dir.iterdir()
            )

            if not remaining_files:
                product_dir.rmdir()

        except OSError:
            pass

    return {
        "code": 200,
        "message": "图片删除成功",
        "data": None
    }



# 删除商品全部图片


@app.delete("/api/images/product/{product_id}")
async def delete_product_images(
    product_id: int
):
    """
    删除某个商品的全部图片。

    例如：

    DELETE
    /api/images/product/8
    """

    if product_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="商品ID无效"
        )

    product_dir = IMAGE_DIR / str(product_id)


    # 如果目录不存在


    if not product_dir.exists():
        return {
            "code": 200,
            "message": "商品图片删除成功",
            "data": None
        }

    # 删除目录里的文件


    try:

        for path in product_dir.iterdir():

            if path.is_file():
                path.unlink()

            elif path.is_dir():
                # 理论上不应该出现子目录
                # 如果出现则不处理，避免误删其他内容
                pass

        # 删除空目录
        try:
            product_dir.rmdir()
        except OSError:
            pass

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"商品图片删除失败: {str(e)}"
        )

    return {
        "code": 200,
        "message": "商品图片删除成功",
        "data": None
    }



# 根路径

@app.get("/")
async def root():
    """
    图片服务器根路径。
    """

    return {
        "code": 200,
        "message": "校园二手交易平台图片服务器",
        "data": {
            "status": "running",
            "public_base_url": PUBLIC_BASE_URL,
            "upload_api": "/api/images/upload",
            "health_api": "/health",
        }
    }


# 启动

if __name__ == "__main__":
    import uvicorn

    logger.info(
        "校园二手交易平台图片服务器已启动 host=%s port=%s",
        HOST,
        PORT
    )

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False,
        access_log=False,
        log_config=None
    )
