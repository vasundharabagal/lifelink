import { Activity, Database, Server, Clock, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';

export interface HealthData {
  status: string;
  db: string;
  version: string;
  demo_mode: boolean;
  timestamp: string;
  environment: string;
}

export interface DiagnosticsCardProps {
  data: HealthData | null;
  latencyMs: number | null;
  pollCount: number;
  error: Error | null;
  isReconnecting: boolean;
  onRefresh?: () => void;
}

export function DiagnosticsCard({
  data,
  latencyMs,
  pollCount,
  error,
  isReconnecting,
  onRefresh,
}: DiagnosticsCardProps) {
  const isApiOk = !error && data?.status === 'ok';
  const isDbOk = !error && data?.db === 'ok';

  return (
    <div className="w-full max-w-xl bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="p-6 sm:p-8 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 rounded-2xl bg-red-600 text-white flex items-center justify-center font-bold text-xl shadow-sm shadow-red-200">
            LL
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              LIFELINK Walking Skeleton
            </h1>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              Phase 0 Deployment Spike & Health Monitor
            </p>
          </div>
        </div>

        <button
          onClick={onRefresh}
          className="p-2.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 min-h-[44px] min-w-[44px] flex items-center justify-center"
          title="Force immediate poll"
          aria-label="Force immediate health poll"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Primary Status Matrix */}
      <div className="p-6 sm:p-8 space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* API Status Pill */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Server className="w-5 h-5 text-slate-500" />
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">FastAPI Service</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5">
                  {isApiOk ? 'Operational' : isReconnecting ? 'Reconnecting' : 'Unreachable'}
                </p>
              </div>
            </div>
            {isApiOk ? (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> OK
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800">
                <AlertCircle className="w-3.5 h-3.5 mr-1" /> Error
              </span>
            )}
          </div>

          {/* Database Connectivity Pill */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Database className="w-5 h-5 text-slate-500" />
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">PostgreSQL DB</p>
                <p className="text-sm font-bold text-slate-900 mt-0.5">
                  {isDbOk ? 'Connected' : 'Unavailable'}
                </p>
              </div>
            </div>
            {isDbOk ? (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> SELECT 1
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800">
                <AlertCircle className="w-3.5 h-3.5 mr-1" /> Offline
              </span>
            )}
          </div>
        </div>

        {/* Diagnostic Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
          <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-100">
            <span className="text-xs text-slate-500 font-medium">Roundtrip Latency</span>
            <div className="mt-1 flex items-baseline space-x-1">
              <span className="text-lg font-bold text-slate-900">
                {latencyMs !== null ? `${latencyMs}` : '—'}
              </span>
              <span className="text-xs font-semibold text-slate-500">ms</span>
            </div>
          </div>

          <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-100">
            <span className="text-xs text-slate-500 font-medium">Poll Counter</span>
            <div className="mt-1 flex items-baseline space-x-1">
              <span className="text-lg font-bold text-slate-900">{pollCount}</span>
              <span className="text-xs font-semibold text-slate-500">ticks</span>
            </div>
          </div>

          <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-100 col-span-2 sm:col-span-1">
            <span className="text-xs text-slate-500 font-medium">Runtime Env</span>
            <div className="mt-1">
              <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-slate-200/80 text-slate-800 capitalize">
                {data?.environment || 'detecting...'}
              </span>
            </div>
          </div>
        </div>

        {/* Server Metadata Bar */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>Server Time (UTC):</span>
            <span className="font-mono font-medium text-slate-800">
              {data?.timestamp ? new Date(data.timestamp).toUTCString() : 'Awaiting heartbeat...'}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            <span>Cadence: 2 s (active) / 5 s (bg)</span>
          </div>
        </div>
      </div>

      {/* Footer Banner */}
      <div className="px-6 py-4 bg-slate-50/50 border-t border-slate-100 text-center">
        <p className="text-xs text-slate-500">
          Emergency response systems run beside national 112 services.
          See <a href="#adr" className="text-red-600 font-semibold hover:underline">ADR-001</a> for deployment benchmarks.
        </p>
      </div>
    </div>
  );
}
