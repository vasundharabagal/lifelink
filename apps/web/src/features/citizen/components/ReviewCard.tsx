import { useEffect, useState } from 'react';
import { AlertOctagon, AlertTriangle, Info, MapPin, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { useSosDraft } from '../../../context/SosDraftContext';
import { api, ApiError } from '../../../lib/api';
import { formatAccuracy } from '../../../lib/geolocation';
import {
  TRIAGE_DISCLAIMER,
  PRIVACY_GUARANTEE,
  GPS_FALLBACK_BADGE,
  ACCURACY_UNAVAILABLE,
} from '../../../lib/strings';

export interface TriageResult {
  emergency_type: string;
  observed_conditions: string[];
  red_flags: string[];
  protocol_id: string;
  required_skills: Array<{ skill: string; min_level: number }>;
  priority: 'P1' | 'P2' | 'P3' | string;
  ambulance_required: boolean;
  confidence: number;
  source: string;
  evidence: Array<{ condition: string; from_source: string; span?: string }>;
  rules_version: string;
  disclaimer_key: string;
}

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

const PROTOCOL_NAMES: Record<string, string> = {
  PROT_UNRESPONSIVE: 'Unresponsive Person / Cardiac Arrest',
  PROT_SEVERE_BLEEDING: 'Severe Bleeding Control',
  PROT_CHOKING: 'Choking / Airway Obstruction',
  PROT_BURNS: 'Burn Care & Thermal Injuries',
  PROT_SEIZURE: 'Seizure Management',
  PROT_TRAUMA_FALL: 'Trauma & Fall Response',
  PROT_GENERAL: 'General Medical Emergency',
};

interface ReviewCardProps {
  onTriageLoaded?: (result: TriageResult) => void;
}

export function ReviewCard({ onTriageLoaded }: ReviewCardProps) {
  const { draft } = useSosDraft();
  const [triage, setTriage] = useState<TriageResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchPreview() {
      setLoading(true);
      setPreviewError(null);

      const quickType = draft.emergencyType
        ? QUICK_TYPE_MAP[draft.emergencyType] || draft.emergencyType.toUpperCase()
        : null;

      const payload = {
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
      };

      try {
        const res = await api.post<TriageResult>('/api/v1/triage/preview', payload);
        if (isMounted) {
          setTriage(res);
          onTriageLoaded?.(res);
        }
      } catch (err) {
        if (isMounted) {
          // If offline or mock fallback in test without endpoint
          const errMsg =
            err instanceof ApiError ? err.detail : 'Unable to connect to triage preview service';
          setPreviewError(errMsg);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    fetchPreview();
  }, [
    draft.emergencyType,
    draft.unresponsive,
    draft.breathingNormally,
    draft.severeBleeding,
    draft.description,
    onTriageLoaded,
  ]);

  const accuracyText =
    draft.accuracy_m !== null
      ? `${formatAccuracy(draft.accuracy_m)} GPS accuracy`
      : ACCURACY_UNAVAILABLE;

  const priority = triage?.priority || 'P2';
  const isP1 = priority === 'P1';
  const isP2 = priority === 'P2';

  const protocolTitle = triage?.protocol_id
    ? PROTOCOL_NAMES[triage.protocol_id] || triage.protocol_id
    : 'General First Aid Response';

  return (
    <div className="flex flex-col gap-4">
      {/* Priority Banner */}
      <div
        id="triage-priority-banner"
        className={`rounded-2xl border p-4 flex items-start gap-3 transition-colors ${
          isP1
            ? 'bg-red-50 border-red-200 text-red-900'
            : isP2
            ? 'bg-amber-50 border-amber-200 text-amber-900'
            : 'bg-blue-50 border-blue-200 text-blue-900'
        }`}
      >
        {isP1 ? (
          <AlertOctagon className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
        ) : isP2 ? (
          <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
        ) : (
          <Info className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" />
        )}
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <span className="text-base font-bold tracking-tight">
              {loading
                ? 'Evaluating Priority…'
                : isP1
                ? 'Priority 1 — Immediate Emergency'
                : isP2
                ? 'Priority 2 — Urgent Emergency'
                : 'Priority 3 — Standard Response'}
            </span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full uppercase bg-white/70 border border-current">
              {priority}
            </span>
          </div>
          {triage?.ambulance_required && (
            <p className="text-xs font-semibold mt-1 text-red-700">
              Dual-track response: Professional ambulance dispatch initiated with volunteer network.
            </p>
          )}
        </div>
      </div>

      {/* Conditions & Protocol Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
          Detected Conditions & Guidance
        </h3>

        {/* Conditions Tags */}
        <div id="triage-conditions" className="flex flex-wrap gap-1.5">
          {triage?.observed_conditions && triage.observed_conditions.length > 0 ? (
            triage.observed_conditions.map((cond) => (
              <span
                key={cond}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-100 text-slate-800 border border-slate-300"
              >
                <CheckCircle2 className="w-3 h-3 text-slate-600" />
                {cond}
              </span>
            ))
          ) : (
            <span className="text-xs text-slate-500 italic">
              {loading ? 'Analyzing conditions…' : 'General community response'}
            </span>
          )}
        </div>

        {/* Protocol Assignment */}
        <div className="pt-2 border-t border-slate-100">
          <p className="text-xs text-slate-500 font-medium">Assigned Clinical Protocol</p>
          <p id="triage-protocol-title" className="text-sm font-bold text-slate-900 mt-0.5">
            {protocolTitle}
          </p>
        </div>

        {/* Disclaimer */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-600">
          <p id="triage-disclaimer">{TRIAGE_DISCLAIMER}</p>
        </div>
      </div>

      {/* Location Verification Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Verified Location
          </h3>
          <span
            id="location-accuracy-badge"
            className="text-xs font-medium text-slate-600"
          >
            {accuracyText}
          </span>
        </div>

        {/* Explicit fallback badge when isFallbackLocation is true */}
        {draft.isFallbackLocation && (
          <div
            id="review-fallback-badge"
            role="alert"
            className="flex items-center gap-2 bg-amber-50 border border-amber-300 text-amber-800 rounded-xl px-3 py-2 text-xs font-semibold"
          >
            <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
            {GPS_FALLBACK_BADGE}
          </div>
        )}

        <div className="flex items-start gap-2.5">
          <MapPin className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            {draft.landmark ? (
              <p className="font-semibold text-slate-900">{draft.landmark}</p>
            ) : (
              <p className="font-semibold text-slate-800">
                GPS: {draft.lat.toFixed(4)}, {draft.lng.toFixed(4)}
              </p>
            )}
          </div>
        </div>

        {/* Privacy badge */}
        <div
          id="review-privacy-badge"
          className="flex items-center gap-2 pt-2 border-t border-slate-100 text-xs text-slate-600 font-medium"
        >
          <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{PRIVACY_GUARANTEE}</span>
        </div>
      </div>

      {previewError && (
        <div className="text-xs text-slate-500 text-center">
          Preview offline — emergency dispatch will evaluate deterministically upon send.
        </div>
      )}
    </div>
  );
}
