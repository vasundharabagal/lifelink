import { clsx } from 'clsx';
import {
  Droplets, AlertCircle, Car, Wind, Flame, Activity, Heart, HelpCircle,
} from 'lucide-react';
import { useSosDraft } from '../../../context/SosDraftContext';

const CHIPS = [
  { id: 'bleeding', label: 'Bleeding', icon: Droplets },
  { id: 'unresponsive', label: 'Not responding', icon: AlertCircle },
  { id: 'accident', label: 'Accident / Fall', icon: Car },
  { id: 'choking', label: 'Choking', icon: Wind },
  { id: 'burn', label: 'Burn', icon: Flame },
  { id: 'seizure', label: 'Seizure', icon: Activity },
  { id: 'chest_pain', label: 'Chest Pain', icon: Heart },
  { id: 'other', label: 'Other Emergency', icon: HelpCircle },
] as const;

type Victim = 'me' | 'someone_else';

interface QuickTypeGridProps {
  onContinue: () => void;
  onSkip: () => void;
}

/**
 * Emergency type chip selector grid and victim selector.
 * Skippable — citizen is never forced to categorize in a panic.
 */
export function QuickTypeGrid({ onContinue, onSkip }: QuickTypeGridProps) {
  const { draft, updateDraft } = useSosDraft();

  const toggleChip = (id: string) => {
    updateDraft({ emergencyType: draft.emergencyType === id ? null : id });
  };

  const setVictim = (v: Victim) => updateDraft({ victim: v });

  return (
    <div className="flex flex-col gap-5">
      {/* Who needs help? */}
      <div>
        <p className="text-sm font-semibold text-slate-700 mb-2">Who needs help?</p>
        <div className="flex gap-2" role="group" aria-label="Who needs help">
          {(['me', 'someone_else'] as Victim[]).map((v) => (
            <button
              key={v}
              id={`victim-${v}`}
              type="button"
              onClick={() => setVictim(v)}
              className={clsx(
                'flex-1 min-h-[48px] rounded-xl border font-semibold text-sm transition-colors',
                draft.victim === v
                  ? 'bg-slate-900 border-slate-900 text-white'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              )}
              aria-pressed={draft.victim === v}
            >
              {v === 'me' ? 'Me' : 'Someone else'}
            </button>
          ))}
        </div>
      </div>

      {/* Emergency type chips */}
      <div>
        <p className="text-sm font-semibold text-slate-700 mb-2">Emergency type (optional)</p>
        <div className="grid grid-cols-2 gap-2">
          {CHIPS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`chip-${id}`}
              type="button"
              onClick={() => toggleChip(id)}
              className={clsx(
                'min-h-[56px] rounded-xl border px-3 py-2',
                'flex items-center gap-2.5 font-medium text-sm transition-colors text-left',
                draft.emergencyType === id
                  ? 'bg-red-600 border-red-600 text-white shadow-sm'
                  : 'bg-white border-slate-200 text-slate-800 hover:bg-slate-50 hover:border-slate-300'
              )}
              aria-pressed={draft.emergencyType === id}
            >
              <Icon
                className={clsx('w-4 h-4 flex-shrink-0', draft.emergencyType === id ? 'text-white' : 'text-red-500')}
                aria-hidden="true"
              />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 pt-1">
        <button
          id="quick-type-continue-btn"
          type="button"
          onClick={onContinue}
          className="w-full min-h-[52px] bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-800 transition-colors"
        >
          {draft.emergencyType ? 'Continue to Questions' : 'Skip to Questions'}
        </button>
        <button
          id="quick-type-skip-btn"
          type="button"
          onClick={onSkip}
          className="w-full min-h-[44px] text-slate-500 font-medium text-sm hover:text-slate-700 transition-colors"
        >
          Skip
        </button>
      </div>
    </div>
  );
}
