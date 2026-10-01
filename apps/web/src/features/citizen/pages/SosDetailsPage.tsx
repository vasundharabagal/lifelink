import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { LocationPicker } from '../components/LocationPicker';
import { Call112Button } from '../../../components/layout/Call112Button';
import { Button } from '../../../components/ui/Button';
import { SosDraftProvider, useSosDraft } from '../../../context/SosDraftContext';

function SosDetailsContent() {
  const navigate = useNavigate();
  const { draft, updateDraft } = useSosDraft();
  const remaining = 500 - draft.description.length;

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 pb-28">
      {/* Step header */}
      <div className="sticky top-14 z-20 bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate('/sos/questions')}
          className="min-h-[40px] min-w-[40px] flex items-center justify-center rounded-full hover:bg-slate-100 transition-colors"
          aria-label="Back to triage questions"
        >
          <ArrowLeft className="w-5 h-5 text-slate-600" />
        </button>
        <div>
          <p className="text-xs text-slate-500 font-medium">Step 3 of 4</p>
          <h1 className="text-base font-bold text-slate-900">Scene Details</h1>
        </div>
      </div>

      <div className="flex-1 px-4 py-5 max-w-md mx-auto w-full space-y-5">
        {/* Description textarea */}
        <div>
          <label htmlFor="description-input" className="block text-sm font-semibold text-slate-700 mb-1">
            Describe the situation <span className="text-slate-400 font-normal">(optional)</span>
          </label>
          <textarea
            id="description-input"
            value={draft.description}
            onChange={(e) => {
              if (e.target.value.length <= 500) {
                updateDraft({ description: e.target.value });
              }
            }}
            rows={4}
            placeholder="What's happening? Any relevant details for the responder…"
            className="
              w-full px-3 py-2 border border-slate-300 rounded-xl text-sm
              bg-white text-slate-900 placeholder-slate-400 resize-none
              focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent
            "
          />
          <p
            id="description-char-counter"
            className={`text-right text-xs mt-1 ${remaining < 50 ? 'text-amber-600' : 'text-slate-400'}`}
          >
            {remaining} characters remaining
          </p>
        </div>

        {/* Location picker */}
        <div>
          <p className="text-sm font-semibold text-slate-700 mb-2">Confirm your location</p>
          <LocationPicker />
        </div>

        <Button
          id="details-continue-btn"
          variant="primary"
          size="lg"
          onClick={() => navigate('/sos/review')}
          className="w-full"
        >
          Continue to Review
        </Button>
      </div>

      <Call112Button />
    </div>
  );
}

export function SosDetailsPage() {
  return (
    <SosDraftProvider>
      <SosDetailsContent />
    </SosDraftProvider>
  );
}
