export interface ReconnectionBannerProps {
  isReconnecting: boolean;
}

export function ReconnectionBanner({ isReconnecting }: ReconnectionBannerProps) {
  if (!isReconnecting) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-0 left-0 right-0 z-50 bg-amber-500 text-white px-4 py-2 text-center text-sm font-medium shadow-md flex items-center justify-center space-x-2 transition-transform duration-200"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
      </span>
      <span>
        Reconnecting to emergency dispatch service... preserving current screen state.
      </span>
    </div>
  );
}
