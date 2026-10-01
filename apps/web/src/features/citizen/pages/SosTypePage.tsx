import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { QuickTypeGrid } from '../components/QuickTypeGrid';
import { Call112Button } from '../../../components/layout/Call112Button';
import { SosDraftProvider } from '../../../context/SosDraftContext';

export function SosTypePage() {
  const navigate = useNavigate();

  return (
    <SosDraftProvider>
      <div className="flex flex-col min-h-screen bg-slate-50 pb-28">
        {/* Step header */}
        <div className="sticky top-14 z-20 bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate('/sos')}
            className="min-h-[40px] min-w-[40px] flex items-center justify-center rounded-full hover:bg-slate-100 transition-colors"
            aria-label="Back to SOS button"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600" />
          </button>
          <div>
            <p className="text-xs text-slate-500 font-medium">Step 1 of 4</p>
            <h1 className="text-base font-bold text-slate-900">Emergency Type</h1>
          </div>
        </div>

        <div className="flex-1 px-4 py-5 max-w-md mx-auto w-full">
          <QuickTypeGrid
            onContinue={() => navigate('/sos/questions')}
            onSkip={() => navigate('/sos/questions')}
          />
        </div>

        <Call112Button />
      </div>
    </SosDraftProvider>
  );
}
