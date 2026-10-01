import { clsx } from 'clsx';
import { useSosDraft } from '../../../context/SosDraftContext';

type TriState = boolean | null;

const QUESTIONS = [
  {
    id: 'unresponsive' as const,
    label: 'Is the person awake and responding?',
    field: 'unresponsive' as const,
    // true = awake/yes, false = not awake/no, null = not sure
  },
  {
    id: 'breathingNormally' as const,
    label: 'Is the person breathing normally?',
    field: 'breathingNormally' as const,
  },
  {
    id: 'severeBleeding' as const,
    label: 'Is there severe, uncontrolled bleeding?',
    field: 'severeBleeding' as const,
  },
] as const;

const OPTIONS: Array<{ label: string; value: TriState }> = [
  { label: 'Yes', value: true },
  { label: 'No', value: false },
  { label: 'Not sure', value: null },
];

/**
 * 3 tri-state triage question cards for the citizen SOS flow.
 * All fields are optional — citizen can skip to avoid panic.
 */
export function TriageQuestions() {
  const { draft, updateDraft } = useSosDraft();

  const handleAnswer = (field: keyof typeof draft, value: TriState) => {
    updateDraft({ [field]: value });
  };

  return (
    <div className="flex flex-col gap-4">
      {QUESTIONS.map(({ id, label, field }) => {
        const current = draft[field] as TriState;
        return (
          <div
            key={id}
            className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm"
          >
            <p className="text-sm font-semibold text-slate-900 mb-3">{label}</p>
            <div
              className="flex gap-2"
              role="group"
              aria-label={label}
              id={`triage-${id}`}
            >
              {OPTIONS.map(({ label: optLabel, value }) => {
                const isSelected =
                  current === value ||
                  // null matches "Not sure"
                  (current === null && value === null && current !== undefined);
                const actuallySelected = draft[field] === value;

                return (
                  <button
                    key={optLabel}
                    id={`triage-${id}-${optLabel.toLowerCase().replace(' ', '-')}`}
                    type="button"
                    onClick={() => handleAnswer(field, value)}
                    aria-pressed={actuallySelected}
                    className={clsx(
                      'flex-1 min-h-[48px] rounded-xl border font-semibold text-sm transition-colors',
                      actuallySelected
                        ? value === false
                          ? 'bg-red-600 border-red-600 text-white'
                          : value === true
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'bg-amber-500 border-amber-500 text-white'
                        : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                    )}
                  >
                    {optLabel}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
