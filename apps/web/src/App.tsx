
export default function App() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-slate-50 text-slate-900">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center space-y-6">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-50 text-red-600 border border-red-100 font-bold text-2xl">
          LL
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            LIFELINK Walking Skeleton
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Emergency Response Coordination Layer
          </p>
        </div>
        <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-left space-y-2 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-slate-500 font-medium">Core Stack:</span>
            <span className="font-semibold text-slate-800">React 19 + FastAPI</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500 font-medium">Platform:</span>
            <span className="font-semibold text-slate-800">Vercel Serverless</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500 font-medium">Status:</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
              Scaffolded
            </span>
          </div>
        </div>
      </div>
    </main>
  );
}
