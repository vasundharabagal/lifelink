import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, X, ShieldAlert } from 'lucide-react';
import { api, ApiError } from '../../../lib/api';
import { Button } from '../../../components/ui/Button';
import {
  CANCEL_FALSE_ALARM,
  CANCEL_RESOLVED,
  CANCEL_CALLED_112,
  CANCEL_OTHER,
} from '../../../lib/strings';

interface CancelModalProps {
  isOpen: boolean;
  emergencyId: string;
  onClose: () => void;
  onCancelled?: () => void;
}

const REASONS = [
  { id: 'false_alarm', label: CANCEL_FALSE_ALARM },
  { id: 'resolved_on_scene', label: CANCEL_RESOLVED },
  { id: 'called_112_instead', label: CANCEL_CALLED_112 },
  { id: 'other', label: CANCEL_OTHER },
] as const;

type ReasonId = (typeof REASONS)[number]['id'];

/**
 * Two-step confirmation modal for citizen emergency cancellation (D-16, UI-SPEC §5.8).
 * Mandatory reason chip selection ensures responders are not called off accidentally.
 */
export function CancelModal({
  isOpen,
  emergencyId,
  onClose,
  onCancelled,
}: CancelModalProps) {
  const navigate = useNavigate();
  const [selectedReason, setSelectedReason] = useState<ReasonId | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirmCancel = async () => {
    if (!selectedReason) return;
    setIsSubmitting(true);
    setError(null);

    try {
      await api.post(`/api/v1/emergencies/${emergencyId}/cancel`, {
        reason: selectedReason,
      });

      onCancelled?.();
      onClose();
      navigate('/sos', {
        state: { message: 'Emergency request has been cancelled.' },
      });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.detail
          : 'Failed to cancel emergency. Please call 112 if immediate assistance is still needed.';
      setError(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cancel-modal-title"
    >
      <div
        id="cancel-emergency-modal"
        className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150"
      >
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-red-600 flex-shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 id="cancel-modal-title" className="text-lg font-bold text-slate-900 leading-tight">
                Cancel Emergency Request?
              </h2>
              <p className="text-xs text-slate-500">Responders will stand down</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-slate-600 leading-relaxed">
          Please select a reason for cancellation. All standing offers to nearby volunteers and ambulance dispatch will be terminated.
        </p>

        {error && (
          <div
            role="alert"
            className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-xs font-semibold"
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Reason Selection Chips */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Reason for cancelling (Required)
          </label>
          <div className="flex flex-col gap-2" role="radiogroup" aria-label="Cancellation reason">
            {REASONS.map(({ id, label }) => {
              const isSelected = selectedReason === id;
              return (
                <button
                  key={id}
                  id={`cancel-reason-${id}`}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => setSelectedReason(id)}
                  className={`
                    w-full min-h-[48px] px-4 py-2.5 rounded-xl border text-left text-sm font-semibold transition-all
                    flex items-center justify-between
                    ${
                      isSelected
                        ? 'border-red-600 bg-red-50 text-red-900 ring-2 ring-red-600/30'
                        : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
                    }
                  `}
                >
                  <span>{label}</span>
                  <div
                    className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                      isSelected ? 'border-red-600 bg-red-600' : 'border-slate-300'
                    }`}
                  >
                    {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 pt-2">
          <Button
            id="confirm-cancel-btn"
            variant="emergency"
            size="lg"
            onClick={handleConfirmCancel}
            disabled={!selectedReason || isSubmitting}
            isLoading={isSubmitting}
            className="w-full justify-center"
          >
            Confirm Cancellation
          </Button>

          <Button
            id="keep-active-btn"
            variant="ghost"
            size="md"
            onClick={onClose}
            disabled={isSubmitting}
            className="w-full text-slate-600 hover:text-slate-900"
          >
            Keep Emergency Active
          </Button>
        </div>
      </div>
    </div>
  );
}
