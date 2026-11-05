"""校园二手交易平台主文件"""
import os
import time
import uuid
from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from routers_1.user import user
from routers_1.products import products
from routers_1.announcements import announcements
from routers_1.orders import order
from routers_1.reports import report
from routers_1.chat import chat
from admin.routerd_a.admins import admin
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from admin.routerd_a.users import admin_user
from admin.routerd_a.products import admin_product
from admin.routerd_a.orders import admin_order
from admin.routerd_a.overview import admin_overview
from admin.routerd_a.reports import admin_reports
from admin.routerd_a.announcements import admin_announcement
from tools_1.lifespan import lifespan
from tools_1.logger import configure_uvicorn_logging, get_logger


logger = get_logger(__name__, "python")
configure_uvicorn_logging("python")


app = FastAPI(lifespan=lifespan)




@app.middleware("http")
async def add_security_headers(request, call_next):
    """为 API 响应补充基础安全响应头。"""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "请求处理失败 request_id=%s method=%s path=%s client=%s",
            request_id,
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown"
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000
    log_method = logger.warning if response.status_code >= 400 else logger.info
    log_method(
        "HTTP请求 request_id=%s method=%s path=%s status=%s duration_ms=%.1f client=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request.client.host if request.client else "unknown"
    )

    response.headers.setdefault("X-Request-ID", request_id)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault(
        "Referrer-Policy",
        "strict-origin-when-cross-origin"
    )
    return response

"""添加中间件"""
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "https://chuhlblog.top,"
        "https://www.chuhlblog.top,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware, # type: ignore[arg-type]
    allow_origins=allowed_origins,
    # 本项目使用 Authorization 头携带 token 而不是 Cookie,
    # 因此不能与 allow_origins=["*"] 组合开启 allow_credentials,
    # 否则浏览器会直接拒绝该跨域响应
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""挂载管理员后台界面"""
ADMIN_STATIC = (
    Path(__file__).resolve().parent
    / "admin"
    / "static"
)
IMAGE_STATIC = (
    Path(__file__).resolve().parent
    / "image_server"
    / "images"
)
IMAGE_STATIC.mkdir(parents=True, exist_ok=True)

@app.get("/admin", include_in_schema=False)
async def admin_redirect():
    return RedirectResponse("/admin/login.html")
app.mount("/admin",StaticFiles(directory=str(ADMIN_STATIC),html=True),name="admin_static")
app.mount("/images",StaticFiles(directory=str(IMAGE_STATIC)),name="image_static")



"""添加路由"""
app.include_router(user)
app.include_router(products)
app.include_router(announcements)
app.include_router(order)
app.include_router(report)
app.include_router(chat)
app.include_router(admin)
app.include_router(admin_user)
app.include_router(admin_product)
app.include_router(admin_order)
app.include_router(admin_overview)
app.include_router(admin_reports)
app.include_router(admin_announcement)




if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8000,
        access_log=False,
        log_config=None
    )
