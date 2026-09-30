import { useCallback } from 'react';
import { usePolling } from './lib/usePolling';
import { DiagnosticsCard, HealthData } from './components/DiagnosticsCard';
import { ReconnectionBanner } from './components/ReconnectionBanner';
import { PhoneCall, ShieldCheck } from 'lucide-react';

export default function App() {
  const fetchHealth = useCallback(async (signal: AbortSignal): Promise<HealthData> => {
    const res = await fetch('/api/v1/health', { signal });
    if (!res.ok) {
      throw new Error(`Health check returned status ${res.status}`);
    }
    return res.json();
  }, []);

  const { data, latencyMs, pollCount, error, isReconnecting, refetch } = usePolling<HealthData>(
    fetchHealth,
    { intervalMs: 2000, backgroundIntervalMs: 5000 }
  );

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-between antialiased">
      {/* Non-blocking top reconnection banner (D-06) */}
      <ReconnectionBanner isReconnecting={isReconnecting} />

      {/* Main Body */}
      <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8">
        {/* Safety Header Callout */}
        <div className="w-full max-w-xl mb-4 flex items-center justify-between bg-white/80 backdrop-blur px-4 py-2.5 rounded-2xl border border-slate-200 text-xs">
          <div className="flex items-center space-x-2 text-slate-700">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span className="font-semibold">Dual-Track Emergency Network</span>
          </div>
          <a
            href="tel:112"
            className="inline-flex items-center space-x-1.5 px-3 py-1 bg-red-600 text-white rounded-lg font-bold hover:bg-red-700 transition-colors shadow-sm"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>Call 112</span>
          </a>
        </div>

        {/* Diagnostics Card (D-05) */}
        <DiagnosticsCard
          data={data}
          latencyMs={latencyMs}
          pollCount={pollCount}
          error={error}
          isReconnecting={isReconnecting}
          onRefresh={refetch}
        />
      </div>

      {/* Persistent Footer */}
      <footer className="py-4 text-center text-xs text-slate-500 border-t border-slate-200 bg-white/50">
        LIFELINK Emergency Dispatch Coordinator &copy; 2026 &bull; Strict Light-Theme WCAG AA Design System
      </footer>
    </div>
  );
}
