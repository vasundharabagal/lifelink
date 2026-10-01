import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Header } from './components/layout/Header';
import { OfflineBanner } from './components/layout/OfflineBanner';
import { Call112Button } from './components/layout/Call112Button';
import { LoginPage } from './features/auth/pages/LoginPage';
import { RegisterPage } from './features/auth/pages/RegisterPage';
import { SosHomePage } from './features/citizen/pages/SosHomePage';
import { SosTypePage } from './features/citizen/pages/SosTypePage';
import { SosQuestionsPage } from './features/citizen/pages/SosQuestionsPage';
import { SosDetailsPage } from './features/citizen/pages/SosDetailsPage';
import { SosReviewPage } from './features/citizen/pages/SosReviewPage';
import { LiveEmergencyPlaceholder } from './features/citizen/pages/LiveEmergencyPlaceholder';
import { ProtocolsPage } from './features/protocols/pages/ProtocolsPage';
import { DiagnosticsCard, HealthData } from './components/DiagnosticsCard';
import { ReconnectionBanner } from './components/ReconnectionBanner';
import { usePolling } from './lib/usePolling';
import { useCallback } from 'react';
import { ShieldCheck } from 'lucide-react';

function DashboardPage() {
  const fetchHealth = useCallback(async (signal: AbortSignal): Promise<HealthData> => {
    const res = await fetch('/api/v1/health', { signal });
    if (!res.ok) throw new Error(`Health check returned status ${res.status}`);
    return res.json();
  }, []);

  const { data, latencyMs, pollCount, error, isReconnecting, refetch } = usePolling<HealthData>(
    fetchHealth,
    { intervalMs: 2000, backgroundIntervalMs: 5000 }
  );

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8 pb-24">
      <ReconnectionBanner isReconnecting={isReconnecting} />
      {/* Safety Header Callout */}
      <div className="w-full max-w-xl mb-4 flex items-center justify-between bg-white/80 backdrop-blur px-4 py-2.5 rounded-2xl border border-slate-200 text-xs">
        <div className="flex items-center space-x-2 text-slate-700">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span className="font-semibold">Dual-Track Emergency Network</span>
        </div>
      </div>
      <DiagnosticsCard
        data={data}
        latencyMs={latencyMs}
        pollCount={pollCount}
        error={error}
        isReconnecting={isReconnecting}
        onRefresh={refetch}
      />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        {/* App shell */}
        <div className="min-h-screen bg-slate-100 flex flex-col antialiased">
          <Header />
          <OfflineBanner />

          <main className="flex-1 flex flex-col">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              {/* SOS flow routes */}
              <Route path="/sos" element={<SosHomePage />} />
              <Route path="/sos/type" element={<SosTypePage />} />
              <Route path="/sos/questions" element={<SosQuestionsPage />} />
              <Route path="/sos/details" element={<SosDetailsPage />} />
              <Route path="/sos/review" element={<SosReviewPage />} />
              <Route path="/emergency/:id" element={<LiveEmergencyPlaceholder />} />
              <Route path="/protocols" element={<ProtocolsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          {/* Persistent footer */}
          <footer className="py-4 text-center text-xs text-slate-500 border-t border-slate-200 bg-white/50 pb-24">
            LIFELINK Emergency Dispatch Coordinator &copy; 2026 &bull; Strict Light-Theme WCAG AA Design System
          </footer>

          {/* Non-network emergency control — always present */}
          <Call112Button />
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}
