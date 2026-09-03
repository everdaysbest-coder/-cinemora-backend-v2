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

VIDEO_MODEL_MAP = {
    "wan": "wan-fast",
    "seedance-2.0": "wan-fast",
    "veo": "wan-fast",
    "nova-reel": "nova-reel",
}


async def generate_image(prompt: str) -> dict:
    import random

    params = {"nologo": "true", "seed": random.randint(1, 2_000_000_000)}
    if POLLINATIONS_API_KEY:
        params["key"] = POLLINATIONS_API_KEY
    url = f"{IMAGE_BASE}/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        r = await client.get(url)
        content_type = r.headers.get("content-type", "")
        image_bytes = r.content

    if r.status_code != 200 or "image" not in content_type or len(image_bytes) < 1_000:
        preview = image_bytes[:400].decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Pollinations Image API خطأ (status: {r.status_code}, "
            f"content-type: {content_type or 'غير معروف'}, الحجم: {len(image_bytes)} بايت). "
            f"التفاصيل: {preview}"
        )

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return {"image_base64": f"data:image/jpeg;base64,{b64}"}


async def generate_video_sync(
    prompt: str, duration: int = 8, aspect_ratio: str = "16:9", model: str = "wan"
) -> dict:
    """يستدعي نقطة نهاية الفيديو المخصصة الأحدث لدى Pollinations."""
    pollinations_model = "wan-fast"
    duration = 5

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
