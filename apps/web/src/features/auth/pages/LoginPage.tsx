import { useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, Activity, Zap } from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';
import { Button } from '../../../components/ui/Button';

const DEMO_CREDENTIALS = [
  { label: 'Demo Citizen', email: 'citizen.maya@demo.lifelink.invalid', password: 'demopass' },
  { label: 'Demo Responder', email: 'asha.nurse@demo.lifelink.invalid', password: 'demopass' },
];

export function LoginPage() {
  const { login, authError, isLoading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      try {
        await login(email, password);
        navigate('/');
      } catch {
        // Error displayed via authError
      }
    },
    [login, email, password, navigate]
  );

  const fillDemo = useCallback((creds: { email: string; password: string }) => {
    setEmail(creds.email);
    setPassword(creds.password);
  }, []);

  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-4 bg-slate-50 pb-20">
      <div className="w-full max-w-sm">
        {/* Brand lockup */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 text-red-600 mb-2">
            <Activity className="w-7 h-7" />
            <span className="text-2xl font-extrabold tracking-tight">LIFELINK</span>
          </div>
          <p className="text-sm text-slate-500">Emergency coordination network</p>
        </div>

        {/* Error alert */}
        {authError && (
          <div
            id="login-error-banner"
            role="alert"
            className="mb-4 flex gap-2 items-start bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm"
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{authError}</span>
          </div>
        )}

        {/* Login card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h1 className="text-lg font-bold text-slate-900 mb-4">Sign in</h1>

          <form onSubmit={handleSubmit} noValidate>
            <div className="space-y-4">
              <div>
                <label htmlFor="login-email" className="block text-sm font-medium text-slate-700 mb-1">
                  Email address
                </label>
                <input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="
                    w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm
                    bg-white text-slate-900 placeholder-slate-400
                    focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent
                    transition-colors
                  "
                  placeholder="your@email.com"
                />
              </div>

              <div>
                <label htmlFor="login-password" className="block text-sm font-medium text-slate-700 mb-1">
                  Password
                </label>
                <input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="
                    w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm
                    bg-white text-slate-900 placeholder-slate-400
                    focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent
                    transition-colors
                  "
                  placeholder="••••••••"
                />
              </div>

              <Button
                type="submit"
                variant="primary"
                isLoading={isLoading}
                disabled={!email || !password}
                className="w-full"
              >
                Sign in
              </Button>
            </div>
          </form>

          <div className="mt-4 pt-4 border-t border-slate-100">
            <p className="text-xs text-slate-500 mb-2 flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-500" />
              Quick-fill demo credentials:
            </p>
            <div className="flex gap-2 flex-wrap">
              {DEMO_CREDENTIALS.map((creds) => (
                <button
                  key={creds.email}
                  type="button"
                  onClick={() => fillDemo(creds)}
                  className="
                    text-xs px-2.5 py-1.5 bg-amber-50 border border-amber-200
                    text-amber-800 rounded-lg font-medium hover:bg-amber-100
                    transition-colors min-h-[32px]
                  "
                >
                  {creds.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-sm text-slate-500 mt-4">
          No account?{' '}
          <Link to="/register" className="text-slate-900 font-semibold hover:underline">
            Register
          </Link>
        </p>
      </div>
    </main>
  );
}
