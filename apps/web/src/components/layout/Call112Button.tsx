import { Phone } from 'lucide-react';
import { CALL_112_LABEL, CALL_112_SUBTITLE } from '../../lib/strings';

/**
 * Persistent non-network "Call 112" emergency control.
 *
 * SAFETY INVARIANTS (DO NOT MODIFY WITHOUT REVIEW):
 * - Renders as <a href="tel:112"> — triggers device OS dialer, not a network call
 * - Device/environment dependent: requires OS telephony capability
 * - Application MUST NEVER claim or imply a call was placed or connected
 * - This control works offline (tel: URI is resolved by OS, not network)
 * - Must remain visible on all citizen emergency screens
 */
export function Call112Button() {
  return (
    <a
      href="tel:112"
      id="call-112-button"
      role="link"
      aria-label="Call 112 — official national emergency service. Opens device dialer."
      className="
        fixed bottom-4 left-4 right-4 max-w-md mx-auto z-40
        min-h-[52px] bg-red-600 hover:bg-red-700 active:bg-red-800
        text-white font-bold rounded-xl shadow-lg
        flex flex-col items-center justify-center px-4 py-2 text-center
        transition-transform active:scale-95 select-none
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-red-600
      "
    >
      <div className="flex items-center gap-2">
        <Phone className="w-5 h-5" aria-hidden="true" />
        <span className="text-base font-bold">{CALL_112_LABEL}</span>
      </div>
      <span className="text-xs font-normal text-red-100 mt-0.5">{CALL_112_SUBTITLE}</span>
    </a>
  );
}
