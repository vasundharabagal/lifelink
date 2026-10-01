import { AlertTriangle, Users, PlusCircle } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { DUPLICATE_TITLE, DUPLICATE_JOIN, DUPLICATE_SEPARATE } from '../../../lib/strings';

export interface DuplicateData {
  existing_emergency_id: string;
  distance_m: number;
  priority?: string;
  created_at?: string;
}

interface DuplicateModalProps {
  isOpen: boolean;
  duplicateData: DuplicateData | null;
  onJoinExisting: () => void;
  onForceCreate: () => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

/**
 * 409 Conflict resolution modal (D-13, D-14, UI-SPEC §5.7).
 * Prevents resource exhaustion from duplicate dispatches while allowing
 * citizens to explicitly force creation if reporting a distinct victim/incident.
 */
export function DuplicateModal({
  isOpen,
  duplicateData,
  onJoinExisting,
  onForceCreate,
  onCancel,
  isSubmitting = false,
}: DuplicateModalProps) {
  if (!isOpen || !duplicateData) return null;

  const distance = Math.round(duplicateData.distance_m);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="duplicate-dialog-title"
    >
      <div
        id="duplicate-modal"
        className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-150"
      >
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 text-amber-700">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h2 id="duplicate-dialog-title" className="text-lg font-bold text-slate-900 leading-tight">
              {DUPLICATE_TITLE}
            </h2>
            <p className="text-xs text-slate-500">Duplicate detection check</p>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-slate-600 leading-relaxed">
          An active emergency was reported <strong className="text-slate-900">{distance}m</strong> away.
          Are you reporting the same incident? Joining avoids fragmenting responders.
        </p>

        {/* Incident Summary Card */}
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 text-xs space-y-1">
          <p className="text-slate-500 font-medium">Existing Incident Details</p>
          <p className="font-semibold text-slate-800">
            ID: {duplicateData.existing_emergency_id.slice(0, 8)}…
          </p>
          {duplicateData.priority && (
            <p className="text-slate-700">
              Severity: <span className="font-bold">{duplicateData.priority}</span>
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2.5 pt-2">
          {/* Join Existing */}
          <Button
            id="join-existing-btn"
            variant="primary"
            size="lg"
            onClick={onJoinExisting}
            disabled={isSubmitting}
            className="w-full justify-center"
          >
            <Users className="w-4 h-4 mr-2" />
            <span>{DUPLICATE_JOIN}</span>
          </Button>

          {/* Report as Separate */}
          <Button
            id="force-create-btn"
            variant="secondary"
            size="lg"
            onClick={onForceCreate}
            isLoading={isSubmitting}
            className="w-full justify-center border-red-200 text-red-700 hover:bg-red-50 hover:border-red-300"
          >
            <PlusCircle className="w-4 h-4 mr-2 text-red-600" />
            <span>{DUPLICATE_SEPARATE}</span>
          </Button>

          {/* Dismiss / Cancel */}
          <Button
            id="duplicate-cancel-btn"
            variant="ghost"
            size="md"
            onClick={onCancel}
            disabled={isSubmitting}
            className="w-full text-slate-500"
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
