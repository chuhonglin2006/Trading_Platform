"""校园二手交易平台主文件"""
import os
import time
import uuid
from pathlib import Path
from admin.routerd_a.logs import admin_logs
import uvicorn
from admin.routerd_a.admins import admin
from admin.routerd_a.announcements import admin_announcement
from admin.routerd_a.orders import admin_order
from admin.routerd_a.overview import admin_overview
from admin.routerd_a.products import admin_product
from admin.routerd_a.reports import admin_reports
from admin.routerd_a.system import admin_system
from admin.routerd_a.users import admin_user
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from routers_1.announcements import announcements
from routers_1.chat import chat
from routers_1.orders import order
from routers_1.products import products
from routers_1.reports import report
from routers_1.user import user
from tools_1.client_ip import get_client_ip
from tools_1.image_storage import IMAGE_DIR
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
            get_client_ip(request)
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
        get_client_ip(request)
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
        "http://localhost,"
        "https://localhost,"
        "capacitor://localhost,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,# type: ignore[arg-type]
    allow_origins=allowed_origins,
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

@app.get("/admin", include_in_schema=False)
async def admin_redirect():
    return RedirectResponse("/admin/login.html")
app.mount("/admin",StaticFiles(directory=str(ADMIN_STATIC),html=True),name="admin_static")
app.mount("/images",StaticFiles(directory=str(IMAGE_DIR)),name="image_static")


DOWNLOAD_DIR = Path(__file__).resolve().parent / "app_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)
app.mount("/downloads", StaticFiles(directory=str(DOWNLOAD_DIR)), name="app_downloads")



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
app.include_router(admin_system)
app.include_router(admin_logs)




if __name__ == '__main__':
    uvicorn.run(app,
        host="127.0.0.1",
        port=8000,
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
        access_log=False,
        log_config=None
    )