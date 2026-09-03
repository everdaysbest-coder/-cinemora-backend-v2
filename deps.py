"""Dependencies مشتركة (مثل معرفة المستخدم الحالي) بمعزل عن الراوترات
لتفادي circular imports بين auth.py و referral.py وغيرهما."""
import os
from datetime import datetime, timezone

from fastapi import Request

from db import sessions_col, users_col

SESSION_COOKIE_NAME = os.environ.get("SESSION_COOKIE_NAME", "cinemora_session")
OWNER_BYPASS_TOKEN = os.environ.get("OWNER_BYPASS_TOKEN", "")


def is_owner_bypass(request: Request) -> bool:
    """يسمح لك (المالك) بتجاوز كل الحدود والقيود عبر رابط فيه
    ?owner_token=<القيمة نفسها بمتغير البيئة OWNER_BYPASS_TOKEN>.
    لا يُفعَّل إطلاقًا إذا لم يُضبط المتغير (آمن افتراضيًا)."""
    return bool(OWNER_BYPASS_TOKEN) and request.query_params.get("owner_token") == OWNER_BYPASS_TOKEN


async def get_current_user(request: Request):
    """يرجّع بيانات المستخدم الحالي (dict) من كوكي الجلسة، أو None إذا زائر."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    session = await sessions_col.find_one({"session_token": token})
    if not session:
        return None
    if session["expires_at"] < datetime.now(timezone.utc).isoformat():
        return None
    user = await users_col.find_one({"_id": session["user_id"]})
    if user and user.get("banned"):
        return None  # حساب محظور — يُعامل كأنه غير مسجّل دخول بأي نقطة نهاية
    return user
