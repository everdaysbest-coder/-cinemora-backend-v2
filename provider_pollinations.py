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
    """يستدعي Pollinations بشكل متزامن ويرجع الفيديو مباشرة (بدون job/polling)."""
    pollinations_model = VIDEO_MODEL_MAP.get(model, "wan")
    width, height = (1280, 720) if aspect_ratio != "9:16" else (720, 1280)
    params = {
        "model": pollinations_model,
        "width": width,
        "height": height,
        "nologo": "true",
    }
    url = f"{IMAGE_BASE}/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"

    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.get(url)
        r.raise_for_status()
        video_bytes = r.content

    b64 = base64.b64encode(video_bytes).decode("utf-8")
    return {"video_base64": f"data:video/mp4;base64,{b64}"}

