import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { TriageQuestions } from '../components/TriageQuestions';
import { Call112Button } from '../../../components/layout/Call112Button';
import { Button } from '../../../components/ui/Button';
import { SosDraftProvider } from '../../../context/SosDraftContext';
import { TRIAGE_DISCLAIMER } from '../../../lib/strings';
import { AlertCircle } from 'lucide-react';

export function SosQuestionsPage() {
  const navigate = useNavigate();

  return (
    <SosDraftProvider>
      <div className="flex flex-col min-h-screen bg-slate-50 pb-28">
        {/* Step header */}
        <div className="sticky top-14 z-20 bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate('/sos/type')}
            className="min-h-[40px] min-w-[40px] flex items-center justify-center rounded-full hover:bg-slate-100 transition-colors"
            aria-label="Back to emergency type"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600" />
          </button>
          <div>
            <p className="text-xs text-slate-500 font-medium">Step 2 of 4</p>
            <h1 className="text-base font-bold text-slate-900">Immediate Assessment</h1>
          </div>
        </div>

        <div className="flex-1 px-4 py-5 max-w-md mx-auto w-full">
          {/* Triage disclaimer */}
          <div className="flex items-start gap-2 mb-4 text-xs text-slate-500">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <span>{TRIAGE_DISCLAIMER}</span>
          </div>

          <TriageQuestions />

          <div className="mt-6 flex flex-col gap-2">
            <Button
              id="questions-continue-btn"
              variant="primary"
              size="lg"
              onClick={() => navigate('/sos/details')}
              className="w-full"
            >
              Continue to Scene Details
            </Button>
            <button
              id="questions-skip-btn"
              type="button"
              onClick={() => navigate('/sos/details')}
              className="w-full min-h-[44px] text-slate-500 font-medium text-sm hover:text-slate-700 transition-colors"
            >
              Skip questions
            </button>
          </div>
        </div>

        <Call112Button />
      </div>
    </SosDraftProvider>
  );
}
