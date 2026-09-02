"""
مزوّد Pollinations (مجاني)
============================
الصور والفيديو كلاهما فعليًا عبر نفس نقطة النهاية:
    GET https://image.pollinations.ai/prompt/{prompt}?model=...&width=&height=
هذا موثّق رسميًا بمستودع pollinations/pollinations (APIDOCS.md).
موديلات الفيديو المتاحة: veo, seedance-pro, wan, wan-pro, p-video, nova-reel
"""

import base64
import os
import urllib.parse

import httpx

IMAGE_BASE = os.environ.get("POLLINATIONS_IMAGE_BASE", "https://image.pollinations.ai/prompt")
VIDEO_BASE = os.environ.get("POLLINATIONS_VIDEO_BASE", "https://gen.pollinations.ai/video")
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY", "")

# خرائط أسماء الموديلات اللي يستخدمها الفرونت اند (wan, seedance-2.0, veo, nova-reel)
# لأسماء موديلات Pollinations الفعلية
VIDEO_MODEL_MAP = {
    "wan": "wan",
    "seedance-2.0": "seedance-pro",
    "veo": "veo",
    "nova-reel": "nova-reel",
}


async def generate_image(prompt: str) -> dict:
    url = f"{IMAGE_BASE}/{urllib.parse.quote(prompt)}?nologo=true"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(url)
        r.raise_for_status()
        image_bytes = r.content
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return {"image_base64": f"data:image/jpeg;base64,{b64}"}


async def generate_video_sync(
    prompt: str, duration: int = 8, aspect_ratio: str = "16:9", model: str = "wan"
) -> dict:
    """يستدعي نقطة نهاية الفيديو المخصصة الأحدث لدى Pollinations."""
    pollinations_model = VIDEO_MODEL_MAP.get(model, "wan")
    params = {"model": pollinations_model, "duration": duration, "aspectRatio": aspect_ratio}
    if POLLINATIONS_API_KEY:
        params["key"] = POLLINATIONS_API_KEY
    url = f"{VIDEO_BASE}/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"

    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.get(url)
        content_type = r.headers.get("content-type", "")
        video_bytes = r.content

    if r.status_code != 200 or "video" not in content_type or len(video_bytes) < 10_000:
        preview = video_bytes[:400].decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Pollinations Video API خطأ (status: {r.status_code}, "
            f"content-type: {content_type or 'غير معروف'}, الحجم: {len(video_bytes)} بايت). "
            f"التفاصيل: {preview}"
        )

    b64 = base64.b64encode(video_bytes).decode("utf-8")
    return {"video_base64": f"data:video/mp4;base64,{b64}"}

