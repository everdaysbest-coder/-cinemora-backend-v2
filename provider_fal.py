"""
مزوّد fal.ai
=============
يستخدم fal.ai queue API الموثّق:
    POST https://queue.fal.run/{model_id}          (Authorization: Key <FAL_KEY>)
        -> {request_id, status_url, response_url, ...}
    GET  {status_url}                                -> {status: IN_QUEUE|IN_PROGRESS|COMPLETED, ...}
    GET  {response_url}                               -> نتيجة النموذج النهائية (تحتوي رابط فيديو)
"""

import os

import httpx

FAL_KEY = os.environ.get("FAL_KEY", "")
FAL_BASE = "https://queue.fal.run"


async def generate_image(prompt: str) -> dict:
    """صور عالية الجودة عبر fal.ai (مدفوعة، رخيصة جدًا ~$0.03/صورة)."""
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY غير مضبوط في .env")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://fal.run/fal-ai/flux-2-pro",
            headers=_headers(),
            json={"prompt": prompt},
        )
        if r.status_code >= 400:
            raise RuntimeError(f"fal.ai [{r.status_code}] {r.text[:500]}")
        data = r.json()

    images = data.get("images") or []
    if not images:
        raise RuntimeError(f"fal.ai لم يرجع أي صورة: {data}")
    return {"image_url": images[0].get("url")}

FAL_MODEL_MAP = {
    "sora-2_short": "fal-ai/kling-video/v3/standard/text-to-video",
    "sora-2_long": "fal-ai/longcat-video/text-to-video/720p",
}


def _headers():
    return {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}


async def submit_video_job(prompt: str, duration: int, aspect_ratio: str, model: str) -> dict:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY غير مضبوط في .env")
    fal_model = FAL_MODEL_MAP.get(model, model)
    duration = max(1, min(60, duration))

    if duration <= 15:
        fal_model = FAL_MODEL_MAP["sora-2_short"]
        payload = {
            "prompt": prompt,
            "duration": str(max(3, duration)),
            "aspect_ratio": aspect_ratio if aspect_ratio in ("16:9", "9:16", "1:1") else "16:9",
            "generate_audio": False,  # نوفّر التكلفة: البوت يحرق صوته الخاص أصلاً (gTTS) لاحقًا
        }
    else:
        fal_model = FAL_MODEL_MAP["sora-2_long"]
        payload = {"prompt": prompt, "num_frames": duration * 30}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{FAL_BASE}/{fal_model}",
            headers=_headers(),
            json=payload,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"fal.ai [{r.status_code}] {r.text[:500]}")
        data = r.json()

    return {
        "job_id": data.get("request_id"),
        "status": "queued",
        "_status_url": data.get("status_url"),
        "_response_url": data.get("response_url"),
    }


async def get_video_job(job_id: str, status_url: str, response_url: str) -> dict:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY غير مضبوط في .env")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(status_url, headers=_headers())
        r.raise_for_status()
        status_data = r.json()
        fal_status = status_data.get("status", "IN_QUEUE")

        if fal_status in ("FAILED", "ERROR", "CANCELLED"):
            error_detail = status_data.get("error") or status_data.get("logs") or fal_status
            return {"job_id": job_id, "status": "failed", "error": str(error_detail)[:300]}

        if fal_status != "COMPLETED":
            return {"job_id": job_id, "status": _map_status(fal_status)}

        rr = await client.get(response_url, headers=_headers())
        if rr.status_code >= 400:
            return {"job_id": job_id, "status": "failed", "error": f"fal.ai response error {rr.status_code}: {rr.text[:300]}"}
        result = rr.json()

    video_url = None
    video_field = result.get("video")
    if isinstance(video_field, dict):
        video_url = video_field.get("url")
    elif isinstance(video_field, str):
        video_url = video_field

    return {"job_id": job_id, "status": "completed", "video_url": video_url, "raw": result}


def _map_status(fal_status: str) -> str:
    return {
        "IN_QUEUE": "queued",
        "IN_PROGRESS": "processing",
        "COMPLETED": "completed",
    }.get(fal_status, "processing")
