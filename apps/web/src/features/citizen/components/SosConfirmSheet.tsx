import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, AlertTriangle, ChevronRight, Zap } from 'lucide-react';
import { useSosDraft } from '../../../context/SosDraftContext';
import { api, ApiError } from '../../../lib/api';
import {
  SOS_CONFIRM_TITLE,
  SOS_CONFIRM_GUIDED,
  SOS_CONFIRM_FAST,
  SOS_CONFIRM_CANCEL,
} from '../../../lib/strings';
import { Button } from '../../../components/ui/Button';

interface SosConfirmSheetProps {
  onClose: () => void;
}

const AUTO_CANCEL_SECONDS = 10;

/**
 * Bottom action sheet shown after 1.5s SOS button trigger.
 *
 * SAFETY CONTRACT (D-04, User Correction 4):
 * "Send Now (Instant Fast Dispatch)" MUST issue POST /api/v1/emergencies
 * entering the full backend safety pipeline:
 *   Create emergency → deterministic triage → Phase 4 eligibility → scoring → dispatch
 * It must NEVER directly dispatch a nearby responder client-side.
 */
export function SosConfirmSheet({ onClose }: SosConfirmSheetProps) {
  const { draft, purgeDraft } = useSosDraft();
  const navigate = useNavigate();
  const [secondsLeft, setSecondsLeft] = useState(AUTO_CANCEL_SECONDS);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 10-second auto-cancel countdown
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          onClose();
          return 0;
        }
        return s - 1;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [onClose]);

  const stopCountdown = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
  }, []);

  const handleGuided = useCallback(() => {
    stopCountdown();
    onClose();
    navigate('/sos/type');
  }, [navigate, onClose, stopCountdown]);

  /**
   * Fast Dispatch path — strictly calls backend safety pipeline.
   * POST /api/v1/emergencies → triage → eligibility → scoring → dispatch
   */
  const handleFastDispatch = useCallback(async () => {
    stopCountdown();
    setIsSending(true);
    setSendError(null);

    try {
      const payload = {
        lat: draft.lat,
        lng: draft.lng,
        accuracy_m: draft.accuracy_m,
        is_fallback_location: draft.isFallbackLocation,
        emergency_type: draft.emergencyType,
        description: draft.description || null,
      };

      const result = await api.post<{ id: string }>(
        '/api/v1/emergencies',
        payload,
        { 'Idempotency-Key': draft.idempotencyKey }
      );

      purgeDraft();
      navigate(`/emergency/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Duplicate incident — router will handle via error state
        navigate('/sos/duplicate', { state: { error: err.detail } });
        return;
      }
      const msg = err instanceof ApiError ? err.detail : 'Failed to send emergency request. Please call 112.';
      setSendError(msg);
      setIsSending(false);
    }
  }, [draft, navigate, purgeDraft, stopCountdown]);

  const progressPercent = ((AUTO_CANCEL_SECONDS - secondsLeft) / AUTO_CANCEL_SECONDS) * 100;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 backdrop-blur-sm">
      <div
        id="sos-confirm-sheet"
        className="w-full max-w-md bg-white rounded-t-3xl shadow-2xl pb-8"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sos-confirm-title"
      >
        {/* Auto-cancel progress bar */}
        <div className="h-1.5 bg-slate-100 rounded-t-3xl overflow-hidden">
          <div
            id="sos-countdown-bar"
            className="h-full bg-red-600 transition-all duration-1000 linear"
            style={{ width: `${progressPercent}%` }}
            aria-label={`Auto-cancelling in ${secondsLeft} seconds`}
          />
        </div>

        <div className="px-5 pt-4">
          {/* Header */}
          <div className="flex items-start justify-between mb-1">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600" aria-hidden="true" />
              <h2 id="sos-confirm-title" className="text-lg font-black text-slate-900">
                {SOS_CONFIRM_TITLE}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="min-h-[36px] min-w-[36px] flex items-center justify-center rounded-full hover:bg-slate-100 transition-colors"
              aria-label="Cancel emergency request"
            >
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>

          <p className="text-sm text-slate-500 mb-4">
            Auto-cancelling in <strong>{secondsLeft}s</strong> if no action taken.
          </p>

          {/* Error */}
          {sendError && (
            <div role="alert" className="mb-3 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm">
              {sendError}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col gap-3">
            {/* Guided triage */}
            <Button
              id="sos-guided-btn"
              variant="secondary"
              size="lg"
              onClick={handleGuided}
              className="w-full justify-between"
            >
              <span>{SOS_CONFIRM_GUIDED}</span>
              <ChevronRight className="w-4 h-4 ml-1" aria-hidden="true" />
            </Button>

            {/* Fast dispatch — must go through backend pipeline */}
            <Button
              id="sos-fast-dispatch-btn"
              variant="emergency"
              size="lg"
              onClick={handleFastDispatch}
              isLoading={isSending}
              className="w-full justify-between"
            >
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4" aria-hidden="true" />
                <span>{SOS_CONFIRM_FAST}</span>
              </div>
            </Button>

            {/* Cancel */}
            <Button
              id="sos-cancel-btn"
              variant="ghost"
              size="md"
              onClick={onClose}
              className="w-full text-slate-500"
            >
              {SOS_CONFIRM_CANCEL}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
