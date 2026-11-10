"""自建图片验证码：服务端生成随机字符图片，答案存 Redis，用户输入后校验。
1. 前端 GET /api/captcha  -> 返回 {captcha_id, image}
2. 用户看图输入字符，提交时带上 captcha_id 和 captcha_code
3. 后端 verify_image_captcha() 校验：答案取出即删除，每张图只能用一次
"""

import asyncio,base64,hmac,io,os,random,secrets,math
from fastapi import HTTPException, status
from PIL import Image, ImageDraw, ImageFont
from tools_1.logger import get_logger


logger = get_logger(__name__, "redis")

# 去掉容易混淆的字符
CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4
TTL_SECONDS = 120

WIDTH = 132
HEIGHT = 44

KEY_PREFIX = "imgcaptcha:"

# 字体：优先用 keys.env 里 CAPTCHA_FONT 指定的字体文件，其次常见系统字体，
# 最后用 Pillow 自带字
_FONT_CANDIDATES = [
    os.getenv("CAPTCHA_FONT", ""),
    "arialbd.ttf",
    "arial.ttf",
    "DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
]
_font_cache: dict[int, ImageFont.ImageFont] = {}


def _get_font(size: int):
    if size in _font_cache:
        return _font_cache[size]

    font = None
    for name in _FONT_CANDIDATES:
        if not name:
            continue
        try:
            font = ImageFont.truetype(name, size)
            break
        except OSError:
            continue

    if font is None:
        try:
            font = ImageFont.load_default(size=size)
        except TypeError:           # 老版本 Pillow，字号不可调
            font = ImageFont.load_default()

    _font_cache[size] = font
    return font


def _random_color(low: int, high: int) -> tuple[int, int, int]:
    return (
        random.randint(low, high),
        random.randint(low, high),
        random.randint(low, high),
    )


def _draw_char(char: str) -> Image.Image:
    """把单个字符画在透明小图上，随机字号并旋转。"""
    size = random.randint(28, 34)
    font = _get_font(size)
    color = _random_color(10, 110) + (255,)

    tile = Image.new("RGBA", (size + 16, size + 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tile)
    # stroke_width=1 让笔画更粗，字体较细时也看得清
    draw.text((8, 4), char, font=font, fill=color, stroke_width=1, stroke_fill=color)

    return tile.rotate(
        random.uniform(-18, 18),
        resample=Image.Resampling.BICUBIC,
        expand=True,
    )


def _warp(image: Image.Image) -> Image.Image:
    """按列做正弦波扭曲，增加机器识别难度。"""
    width, height = image.size
    out = Image.new("RGB", image.size, (255, 255, 255))
    amplitude = random.uniform(1.0, 2.2)
    period = random.uniform(28, 44)
    phase = random.uniform(0, math.tau)

    for x in range(width):
        shift = int(amplitude * math.sin(math.tau * x / period + phase))
        out.paste(image.crop((x, 0, x + 1, height)), (x, shift))

    return out


def generate_image(text: str) -> bytes:
    """根据文字生成 PNG 图片"""
    image = Image.new("RGB", (WIDTH, HEIGHT), _random_color(225, 250))
    draw = ImageDraw.Draw(image)

    # 背景干扰线（画在文字下面）
    for _ in range(3):
        draw.line(
            [
                (random.randint(0, WIDTH), random.randint(0, HEIGHT)),
                (random.randint(0, WIDTH), random.randint(0, HEIGHT)),
            ],
            fill=_random_color(150, 210),
            width=random.randint(1, 2),
        )

    # 逐个字符粘贴，位置有随机抖动
    step = (WIDTH - 20) / len(text)
    for index, char in enumerate(text):
        tile = _draw_char(char)
        x = int(8 + index * step + random.randint(-2, 3))
        y = int((HEIGHT - tile.height) / 2 + random.randint(-3, 3))
        image.paste(tile, (x, y), tile)

    # 前景干扰线和噪点（压在文字上面）
    draw = ImageDraw.Draw(image)
    for _ in range(2):
        draw.line(
            [
                (0, random.randint(5, HEIGHT - 5)),
                (WIDTH, random.randint(5, HEIGHT - 5)),
            ],
            fill=_random_color(60, 170),
            width=1,
        )
    for _ in range(50):
        draw.point(
            (random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1)),
            fill=_random_color(40, 200),
        )

    image = _warp(image)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def create_image_captcha(redis) -> dict:
    """生成一张验证码，答案存进 Redis，返回给前端 id 和图片。"""
    text = "".join(secrets.choice(CHARSET) for _ in range(CODE_LENGTH))
    captcha_id = secrets.token_urlsafe(16)

    # 画图是 CPU 计算，放进线程避免阻塞事件循环
    png = await asyncio.to_thread(generate_image, text)

    try:
        await redis.set(KEY_PREFIX + captcha_id, text, ex=TTL_SECONDS)
    except Exception:
        logger.exception("保存图片验证码失败")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="验证码服务暂时不可用，请稍后重试",
        )

    return {
        "captcha_id": captcha_id,
        "image": "data:image/png;base64," + base64.b64encode(png).decode("ascii"),
        "expires_in": TTL_SECONDS,
    }


async def verify_image_captcha(redis, captcha_id: str | None, answer: str | None) -> None:
    """
    校验图片验证码。通过则正常返回，不通过抛 HTTPException。
    答案取出即删除：每张图片只能校验一次，无论对错都作废，
    所以不能对同一张图反复猜；前端校验失败后必须刷新图片。
    Redis 异常时拒绝（fail-closed）。
    """
    if not captcha_id or not answer or len(captcha_id) > 64 or len(answer) > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入图片验证码",
        )

    key = KEY_PREFIX + captcha_id
    try:
        pipe = redis.pipeline(transaction=True)
        pipe.get(key)
        pipe.delete(key)
        saved, _ = await pipe.execute()
    except Exception:
        logger.exception("校验图片验证码失败")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="验证码服务暂时不可用，请稍后重试",
        )

    if saved is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片验证码已过期，请点击图片刷新",
        )

    # 不区分大小写；用 compare_digest 做常量时间比较
    if not hmac.compare_digest(
        str(saved).encode("utf-8"),
        answer.strip().upper().encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="图片验证码错误，请看新的图片重新输入",
        )