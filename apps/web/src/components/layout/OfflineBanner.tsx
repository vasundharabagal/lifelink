import { useEffect, useState } from 'react';
import { WifiOff } from 'lucide-react';
import { OFFLINE_BANNER } from '../../lib/strings';

/**
 * Offline detection banner for LIFELINK.
 * Shows high-visibility amber notice when device loses network connectivity.
 * Call 112 button and protocol guidance remain accessible regardless.
 */
export function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const handleOffline = () => setIsOffline(true);
    const handleOnline = () => setIsOffline(false);

    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);

    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
    };
  }, []);

  if (!isOffline) return null;

  return (
    <div
      id="offline-banner"
      role="alert"
      aria-live="assertive"
      className="
        bg-amber-600 text-white font-semibold text-sm
        px-4 py-2 flex items-center gap-2 shadow
        sticky top-14 z-30
      "
    >
      <WifiOff className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
      <span>{OFFLINE_BANNER}</span>
    </div>
  );
}
