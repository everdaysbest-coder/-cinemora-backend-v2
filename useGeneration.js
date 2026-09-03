// hooks/useGeneration.js
// ⚠️ ملف مُعاد بناؤه — لم يكن موجودًا في الأرشيف الأصلي رغم أن GenerateModal.jsx
// يستورده. يطابق العقد الحقيقي لـ lib/api.js (submitVideoJob/getVideoJob/generateImage/
// enhancePrompt) لكن التفاصيل الدقيقة (رسائل، حواف حالات) قد تختلف عن النسخة الأصلية.
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  generateImage as apiGenerateImage,
  submitVideoJob,
  getVideoJob,
  enhancePrompt as apiEnhancePrompt,
} from '../lib/api';
import {
  DEFAULT_VIDEO_PROVIDER,
  DEFAULT_VIDEO_MODEL,
  DEFAULT_VIDEO_DURATION,
  POLL_INTERVAL_MS,
} from '../lib/constants';

const DONE_STATUSES = new Set(['completed', 'done', 'success', 'succeeded', 'finished', 'ready']);
const FAILED_STATUSES = new Set(['failed', 'error', 'cancelled', 'canceled']);

export function useGeneration({ open, presetTitle, initialMode = 'image', defaultSuggestion = '' }) {
  const [mode, setMode] = useState(initialMode);
  const [prompt, setPrompt] = useState('');
  const [originalPrompt, setOriginalPrompt] = useState('');
  const [wasEnhanced, setWasEnhanced] = useState(false);
  const [enhancing, setEnhancing] = useState(false);

  const [provider, setProvider] = useState(DEFAULT_VIDEO_PROVIDER);
  const [model, setModel] = useState(DEFAULT_VIDEO_MODEL);
  const [duration, setDuration] = useState(DEFAULT_VIDEO_DURATION);
  const [aspect, setAspect] = useState('16:9');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [image, setImage] = useState(null);
  const [caption, setCaption] = useState('');
  const [videoUrl, setVideoUrl] = useState(null);
  const [job, setJob] = useState(null);
  const [saved, setSaved] = useState(false);

  const pollTimer = useRef(null);

  useEffect(() => {
    if (open) {
      setPrompt(presetTitle ? `${presetTitle} — ${defaultSuggestion}` : defaultSuggestion);
      setMode(initialMode);
      setError('');
      setSaved(false);
    }
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, presetTitle]);

  const enhanceWithClaude = useCallback(async () => {
    if (!prompt.trim()) return;
    setEnhancing(true);
    setError('');
    try {
      const { enhanced_prompt } = await apiEnhancePrompt(prompt, mode);
      setOriginalPrompt(prompt);
      setPrompt(enhanced_prompt);
      setWasEnhanced(true);
    } catch (e) {
      setError('Could not enhance prompt right now.');
    } finally {
      setEnhancing(false);
    }
  }, [prompt, mode]);

  const revertEnhance = useCallback(() => {
    if (originalPrompt) setPrompt(originalPrompt);
    setWasEnhanced(false);
  }, [originalPrompt]);

  const runImageGeneration = useCallback(async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError('');
    setImage(null);
    setSaved(false);
    try {
      const data = await apiGenerateImage(prompt);
      setImage(data.image_base64 || data.image_url);
      setCaption(prompt);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Image generation failed.');
    } finally {
      setLoading(false);
    }
  }, [prompt]);

  const runVideoGeneration = useCallback(async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError('');
    setVideoUrl(null);
    setSaved(false);
    setJob(null);

    try {
      const submitted = await submitVideoJob({
        prompt,
        duration,
        aspect_ratio: aspect,
        provider,
        model,
      });
      const jobId = submitted.job_id || submitted.id;
      setJob({ ...submitted, provider });

      let consecutiveFailures = 0;
      const poll = async () => {
        try {
          const current = await getVideoJob(jobId);
          consecutiveFailures = 0;
          setJob({ ...current, provider });
          const status = String(current.status || '').toLowerCase();

          if (DONE_STATUSES.has(status)) {
            setVideoUrl(current.video_url);
            setLoading(false);
            return;
          }
          if (FAILED_STATUSES.has(status)) {
            setError('Video generation failed. Try a different prompt or provider.');
            setLoading(false);
            return;
          }
          pollTimer.current = setTimeout(poll, POLL_INTERVAL_MS);
        } catch (e) {
          consecutiveFailures += 1;
          if (consecutiveFailures >= 5) {
            setError('Lost connection while checking video status. Please try again.');
            setLoading(false);
          } else {
            // انقطاع لحظي — نعيد المحاولة بدل ما نفشل فورًا
            pollTimer.current = setTimeout(poll, POLL_INTERVAL_MS);
          }
        }
      };
      pollTimer.current = setTimeout(poll, POLL_INTERVAL_MS);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Could not start video generation.');
      setLoading(false);
    }
  }, [prompt, duration, aspect, provider, model]);

  return {
    mode, setMode,
    prompt, setPrompt,
    wasEnhanced, enhancing, enhanceWithClaude, revertEnhance,
    provider, setProvider,
    model, setModel,
    duration, setDuration,
    aspect, setAspect,
    loading, error, setError,
    image, caption,
    videoUrl,
    job,
    saved, setSaved,
    runImageGeneration,
    runVideoGeneration,
  };
}
