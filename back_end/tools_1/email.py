"""邮件发送模块"""
import os
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, status

from tools_1.logger import get_logger

logger = get_logger(__name__, "python")


key_env_path = (Path(__file__).resolve().parent.parent / "keys.env")
load_dotenv(key_env_path)
EMAIL_HOST = os.getenv("EMAIL_HOST","smtp.qq.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS","hbkj_market@qq.com")
EMAIL_AUTH_CODE = os.getenv("EMAIL_AUTH_CODE","")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL","3198753913@qq.com")


def send_email(user_email: str,content: str,subject: str = "二手交易网站") -> None:
    """
    发送邮件。
    :param user_email: 收件人邮箱
    :param content: 邮件正文
    :param subject: 邮件主题
    """
    msg = MIMEText(content,"plain","utf-8")
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = user_email
    try:
        with smtplib.SMTP_SSL(EMAIL_HOST,EMAIL_PORT,timeout=15) as smtp:
            smtp.login(EMAIL_ADDRESS,EMAIL_AUTH_CODE)
            smtp.sendmail(EMAIL_ADDRESS,[user_email],msg.as_string())
    except Exception:
        logger.exception(
            "邮件发送失败 host=%s port=%s",
            EMAIL_HOST,
            EMAIL_PORT
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送失败,请稍后重试"
        )

def send_cancel_notification(user_email: str,info: dict) -> None:
    """
    向订单另一方发送取消通知。
    卖家取消 -> 通知买家
    买家取消 -> 通知卖家
    """
    if info["cancel_role"] == "seller":
        subject = "订单取消通知：卖家已取消订单"
        content = (
            f"您好，{info['username']}：\n\n"
            f"您购买的商品「{info['product_name']}」"
            f"已被卖家取消订单。\n\n"
            f"订单编号：{info['order_no']}\n"
            f"取消时间：{info['cancel_time']}\n\n"
            "您可以登录校园二手交易平台查看订单详情。\n\n"
            "二手交易网站")
    elif info["cancel_role"] == "buyer":
        subject = "订单取消通知：买家已取消订单"
        content = (
            f"您好，{info['username']}：\n\n"
            f"买家已取消商品「{info['product_name']}」"
            f"的订单。\n\n"
            f"订单编号：{info['order_no']}\n"
            f"取消时间：{info['cancel_time']}\n\n"
            "商品已恢复上架，其他用户可以继续购买。\n\n"
            "二手交易网站")
    else:
        logger.error(
            "未知的订单取消身份：%s",
            info.get("cancel_role"))
        return
    try:
        send_email(
            user_email=user_email,
            content=content,
            subject=subject)
    except Exception:
        logger.exception(
            "订单取消通知发送失败，订单号：%s",
            info.get("order_no")
        )

def send_new_order_notification(user_email: str,info: dict) -> None:
    """
    买家拍下商品后，向卖家发送邮件通知。
    """
    subject = "新订单通知：您的商品已被拍下"
    content = (
        f"您好，{info['seller_username']}：\n\n"
        f"您发布的商品「{info['product_name']}」"
        f"已被买家拍下。\n\n"
        f"订单编号：{info['order_no']}\n"
        f"成交价格：¥{info['price']}\n"
        f"下单时间：{info['created_at']}\n\n"
        "请及时登录二手交易网站，"
        "查看订单详情并与买家协商交易。\n\n"
        "二手交易网站")
    try:
        send_email(
            user_email=user_email,
            content=content,
            subject=subject)
        logger.info(
            "新订单邮件已提交给 SMTP 服务器，订单号：%s",
            info["order_no"])
    except Exception:
        logger.exception(
            "新订单邮件发送失败，订单号：%s",
            info.get("order_no"))
