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
import re
import urllib.parse

import httpx

IMAGE_BASE = os.environ.get("POLLINATIONS_IMAGE_BASE", "https://image.pollinations.ai/prompt")
VIDEO_BASE = os.environ.get("POLLINATIONS_VIDEO_BASE", "https://gen.pollinations.ai/video")
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


async def _translate_to_english_if_needed(prompt: str) -> str:
    """موديلات التوليد المجانية مدرّبة أساسًا بالإنجليزي — لو البرومبت فيه
    حروف غير لاتينية (عربي مثلاً)، نترجمه أولًا عبر MyMemory (خدمة ترجمة
    مجانية 100%، بدون مفتاح API). لو فشلت، نرجع البرومبت الأصلي كما هو."""
    if not re.search(r"[^\x00-\x7F]", prompt):
        return prompt
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.mymemory.translated.net/get",
                params={"q": prompt[:490], "langpair": "ar|en"},
            )
            r.raise_for_status()
            data = r.json()
        text = data.get("responseData", {}).get("translatedText", "").strip()
        return text or prompt
    except Exception:
        return prompt

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
    import random

    prompt = await _translate_to_english_if_needed(prompt)

    # ⚠️ الصور المجانية بـ Pollinations لا تحتاج مفتاح إطلاقًا — إرسال مفتاح
    # الفيديو (sk_...) هنا كان يسبب رفض صامت وإرجاع صورة افتراضية بدل الفعلية
    # model=flux لجودة أوضح، ودقة أعلى (1024x1024) بدل الافتراضي الصغير
    params = {
        "nologo": "true",
        "model": "flux",
        "width": 1024,
        "height": 1024,
        "seed": random.randint(1, 2_000_000_000),
    }
    url = f"{IMAGE_BASE}/{urllib.parse.quote(prompt)}?{urllib.parse.urlencode(params)}"

    headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
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
    """يستدعي نقطة نهاية الفيديو المخصصة الأحدث لدى Pollinations.

    ⚠️ الرصيد المجاني (Pollen) اللي تحصل عليه تلقائيًا بحساب Pollinations
    صغير جدًا (يكفي بضع مرات فقط). moديل wan-fast هو الأرخص (~0.01 Pollen
    بالثانية = 0.05 لفيديو 5 ثواني)، فنستخدمه دائمًا كافتراضي حتى ما يخلص
    رصيدك بسرعة. لفيديوهات أطول، لازم تشحن رصيد إضافي من
    https://enter.pollinations.ai
    """
    prompt = await _translate_to_english_if_needed(prompt)
    pollinations_model = "wan-fast"
    duration = 5  # المدة الوحيدة المدعومة لهذا الموديل

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

