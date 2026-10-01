import { useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, Activity } from 'lucide-react';
import { useAuth, UserRole } from '../../../context/AuthContext';
import { Button } from '../../../components/ui/Button';

export function RegisterPage() {
  const { register, authError, isLoading } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('citizen');

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      try {
        await register({ email, password, full_name: fullName, role });
        navigate('/');
      } catch {
        // Error displayed via authError
      }
    },
    [register, email, password, fullName, role, navigate]
  );

  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-4 bg-slate-50 pb-20">
      <div className="w-full max-w-sm">
        {/* Brand lockup */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 text-red-600 mb-2">
            <Activity className="w-7 h-7" />
            <span className="text-2xl font-extrabold tracking-tight">LIFELINK</span>
          </div>
          <p className="text-sm text-slate-500">Create your emergency network account</p>
        </div>

        {/* Error alert */}
        {authError && (
          <div
            id="register-error-banner"
            role="alert"
            className="mb-4 flex gap-2 items-start bg-red-50 border border-red-200 text-red-700 rounded-xl p-3 text-sm"
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{authError}</span>
          </div>
        )}

        {/* Register card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
          <h1 className="text-lg font-bold text-slate-900 mb-4">Create account</h1>

          <form onSubmit={handleSubmit} noValidate>
            <div className="space-y-4">
              <div>
                <label htmlFor="register-name" className="block text-sm font-medium text-slate-700 mb-1">
                  Full name
                </label>
                <input
                  id="register-name"
                  type="text"
                  autoComplete="name"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="
                    w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm
                    bg-white text-slate-900 placeholder-slate-400
                    focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent
                    transition-colors
                  "
                  placeholder="Your full name"
                />
              </div>

              <div>
                <label htmlFor="register-email" className="block text-sm font-medium text-slate-700 mb-1">
                  Email address
                </label>
                <input
                  id="register-email"
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
                <label htmlFor="register-password" className="block text-sm font-medium text-slate-700 mb-1">
                  Password
                </label>
                <input
                  id="register-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="
                    w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm
                    bg-white text-slate-900 placeholder-slate-400
                    focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent
                    transition-colors
                  "
                  placeholder="Choose a strong password"
                />
              </div>

              <div>
                <label htmlFor="register-role" className="block text-sm font-medium text-slate-700 mb-1">
                  I am registering as a
                </label>
                <select
                  id="register-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as UserRole)}
                  className="
                    w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm
                    bg-white text-slate-900
                    focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent
                    transition-colors cursor-pointer
                  "
                >
                  <option value="citizen">Citizen (emergency help-seeker)</option>
                  <option value="responder">First Responder (trained volunteer)</option>
                </select>
              </div>

              <Button
                type="submit"
                variant="primary"
                isLoading={isLoading}
                disabled={!email || !password || !fullName}
                className="w-full"
              >
                Create account
              </Button>
            </div>
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-slate-900 font-semibold hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
