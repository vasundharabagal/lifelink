import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { SosButton } from '../components/SosButton';
import { SosConfirmSheet } from '../components/SosConfirmSheet';
import { Call112Button } from '../../../components/layout/Call112Button';
import { SosDraftProvider } from '../../../context/SosDraftContext';

/**
 * Citizen SOS home page — mounts the hold button and confirmation sheet.
 * Wrapped in SosDraftProvider to initialize geolocation pre-warming.
 */
export function SosHomePage() {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <SosDraftProvider>
      <div className="flex flex-col items-center min-h-screen bg-slate-50 pb-28 px-4">
        {/* Safety header */}
        <div className="w-full max-w-md mt-4 mb-6 flex items-center justify-between bg-white/80 backdrop-blur px-4 py-2.5 rounded-2xl border border-slate-200 text-xs">
          <div className="flex items-center space-x-2 text-slate-700">
            <ShieldCheck className="w-4 h-4 text-emerald-600" aria-hidden="true" />
            <span className="font-semibold">Citizen Emergency Request</span>
          </div>
        </div>

        {/* Hold instruction */}
        <div className="flex flex-col items-center mb-10 mt-6 text-center">
          <p className="text-sm text-slate-500 max-w-xs mb-8">
            Hold the button for 1.5 seconds to trigger an emergency request to the LIFELINK network.
          </p>

          <SosButton onTriggered={() => setShowConfirm(true)} />

          <p className="text-xs text-slate-400 mt-6 max-w-xs">
            Triggers community first-responder network. Also call 112 for official emergency services.
          </p>
        </div>

        {/* Confirm sheet overlay */}
        {showConfirm && (
          <SosConfirmSheet onClose={() => setShowConfirm(false)} />
        )}

        {/* Persistent non-network emergency control */}
        <Call112Button />
      </div>
    </SosDraftProvider>
  );
}
