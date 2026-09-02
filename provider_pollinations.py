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
# خرائط أسماء الموديلات اللي يستخدمها الفرونت اند (wan, seedance-2.0, veo, nova-reel)
# لأسماء موديلات Pollinations الفعلية المتاحة بدون "paid_only" (حسب /video/models)
VIDEO_MODEL_MAP = {
    "wan": "wan-fast",       # Wan 2.2 — الوحيد الحر من عائلة wan (5 ثواني، بدون صوت)
    "seedance-2.0": "wan-fast",
    "veo": "wan-fast",
    "nova-reel": "nova-reel",  # حر أيضًا، فيديو أطول (6-120 ثانية)
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
    """يستدعي نقطة نهاية الفيديو المخصصة الأحدث لدى Pollinations.

    الموديلات المجانية (بدون paid_only) عندها قيود مختلفة على المدة:
    - wan-fast: 5 ثواني بالضبط، مافي غيرها
    - nova-reel: من 6 لـ120 ثانية، بمضاعفات 6
    نختار تلقائيًا الأنسب حسب المدة المطلوبة من المستخدم.
    """
    if duration <= 5:
        pollinations_model = "wan-fast"
        duration = 5
    else:
        pollinations_model = "nova-reel"
        duration = max(6, min(120, round(duration / 6) * 6)) or 6

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

