import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Send, AlertCircle, Edit3 } from 'lucide-react';
import { useSosDraft } from '../../../context/SosDraftContext';
import { api, ApiError } from '../../../lib/api';
import { ReviewCard } from '../components/ReviewCard';
import { DuplicateModal, DuplicateData } from '../components/DuplicateModal';
import { Button } from '../../../components/ui/Button';
import { Call112Button } from '../../../components/layout/Call112Button';

const QUICK_TYPE_MAP: Record<string, string> = {
  bleeding: 'BLEEDING',
  unresponsive: 'UNRESPONSIVE',
  accident: 'TRAUMA_FALL',
  choking: 'CHOKING',
  burn: 'BURNS',
  seizure: 'SEIZURE',
  chest_pain: 'CHEST_PAIN',
  other: 'OTHER',
};

export function SosReviewPage() {
  const navigate = useNavigate();
  const { draft, purgeDraft } = useSosDraft();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [duplicateData, setDuplicateData] = useState<DuplicateData | null>(null);
  const [isDuplicateOpen, setIsDuplicateOpen] = useState(false);

  const handleSubmit = async (forceCreate = false) => {
    setIsSubmitting(true);
    setErrorMessage(null);

    const quickType = draft.emergencyType
      ? QUICK_TYPE_MAP[draft.emergencyType] || draft.emergencyType.toUpperCase()
      : null;

    const payload = {
      lat: draft.lat,
      lng: draft.lng,
      location_accuracy_m: draft.accuracy_m ?? 10.0,
      location_hint: draft.landmark ? draft.landmark.trim() : null,
      patient_is_reporter: draft.victim === 'me',
      consent_share_medical: false,
      triage_input: {
        quick_type: quickType,
        answers: {
          awake:
            draft.unresponsive === true
              ? 'yes'
              : draft.unresponsive === false
              ? 'no'
              : 'not_sure',
          breathing:
            draft.breathingNormally === true
              ? 'yes'
              : draft.breathingNormally === false
              ? 'no'
              : 'not_sure',
          severe_bleeding:
            draft.severeBleeding === true
              ? 'yes'
              : draft.severeBleeding === false
              ? 'no'
              : 'not_sure',
        },
        description: draft.description ? draft.description.trim() : null,
      },
      force_create: forceCreate,
    };

    try {
      const res = await api.post<{ id: string }>(
        '/api/v1/emergencies',
        payload,
        { 'Idempotency-Key': draft.idempotencyKey }
      );

      purgeDraft();
      navigate(`/emergency/${res.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        try {
          const detail = typeof err.detail === 'string' ? JSON.parse(err.detail) : err.detail;
          setDuplicateData({
            existing_emergency_id: detail.existing_emergency_id,
            distance_m: detail.distance_m ?? 50,
            priority: detail.priority,
            created_at: detail.created_at,
          });
        } catch {
          setDuplicateData({
            existing_emergency_id: 'existing-id',
            distance_m: 50,
          });
        }
        setIsDuplicateOpen(true);
      } else {
        const msg =
          err instanceof ApiError
            ? err.detail
            : 'Failed to submit emergency request. Please call 112.';
        setErrorMessage(msg);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleJoinExisting = () => {
    if (!duplicateData) return;
    setIsDuplicateOpen(false);
    purgeDraft();
    navigate(`/emergency/${duplicateData.existing_emergency_id}?mode=observer`);
  };

  const handleForceCreate = () => {
    setIsDuplicateOpen(false);
    handleSubmit(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col pb-36">
      {/* Top Bar */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 sticky top-0 z-30 flex items-center justify-between">
        <button
          onClick={() => navigate('/sos/details')}
          className="flex items-center gap-1.5 text-sm font-semibold text-slate-700 hover:text-slate-900 min-h-[44px] px-2 -ml-2 rounded-lg"
          aria-label="Back to scene details"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
          Step 4 of 4: Review & Dispatch
        </span>
        <Link
          to="/sos/type"
          className="flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900"
        >
          <Edit3 className="w-3.5 h-3.5" />
          <span>Edit</span>
        </Link>
      </div>

      <div className="max-w-md mx-auto w-full px-4 pt-4 flex flex-col gap-5">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            Review Request
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Confirm details. Volunteers and ambulance are dispatched upon submission.
          </p>
        </div>

        {errorMessage && (
          <div
            role="alert"
            className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-2xl p-4 text-sm font-medium"
          >
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">Submission Failed</p>
              <p className="text-xs mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Review Card */}
        <ReviewCard />

        {/* Primary CTA */}
        <div className="pt-2">
          <Button
            id="submit-sos-btn"
            variant="emergency"
            size="lg"
            onClick={() => handleSubmit(false)}
            isLoading={isSubmitting}
            className="w-full justify-center text-lg py-4 shadow-xl active:scale-[0.98]"
          >
            <Send className="w-5 h-5 mr-2" />
            <span>Send Emergency Request Now</span>
          </Button>
          <p className="text-center text-xs text-slate-500 mt-2">
            Deterministic triage · Dual-track dispatch · Strict audit logging
          </p>
        </div>
      </div>

      {/* 409 Conflict Duplicate Modal */}
      <DuplicateModal
        isOpen={isDuplicateOpen}
        duplicateData={duplicateData}
        onJoinExisting={handleJoinExisting}
        onForceCreate={handleForceCreate}
        onCancel={() => setIsDuplicateOpen(false)}
        isSubmitting={isSubmitting}
      />

      <Call112Button />
    </div>
  );
}
