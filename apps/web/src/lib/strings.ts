/**
 * Centralized UI copywriting strings for LIFELINK citizen SOS interface.
 * All user-facing text must come from this registry for consistency and safety compliance.
 */

// Non-network emergency control — device/environment dependent
export const CALL_112_LABEL = 'Call 112 Emergency';
export const CALL_112_SUBTITLE = 'Official national emergency service · Works offline';
// SAFETY: Never modify to claim a call was placed — device dialer dependency only

// Offline state messaging
export const OFFLINE_BANNER =
  'Offline mode — Cellular/Wi-Fi disconnected. Emergency calls work via 112. First-aid protocols available below.';

// Triage and clinical safety disclaimers
export const TRIAGE_DISCLAIMER =
  'Automated decision-support classification. Not a medical diagnosis.';

export const PROTOCOL_DISCLAIMER =
  'Demo clinical guidance — unreviewed for clinical use. Call 112 for official dispatch.';

// Location and privacy
export const PRIVACY_GUARANTEE =
  'Privacy-gated: Exact location revealed only to accepted responder.';

// GPS fallback — must be visually explicit, never implies real GPS
export const GPS_FALLBACK_BADGE = 'Demo location used — GPS unavailable';
export const ACCURACY_UNAVAILABLE = 'Accuracy unavailable';

// SOS flow
export const SOS_BUTTON_ARIA =
  'Emergency SOS button. Press and hold for 1.5 seconds to trigger emergency request.';
export const SOS_CONFIRM_TITLE = 'Send Emergency Request?';
export const SOS_CONFIRM_GUIDED = 'Add Details / Guided Triage';
export const SOS_CONFIRM_FAST = 'Send Now (Instant Fast Dispatch)';
export const SOS_CONFIRM_CANCEL = 'Cancel';

// Duplicate incident
export const DUPLICATE_TITLE = 'Nearby Emergency Detected';
export const DUPLICATE_JOIN = 'Join Existing Incident';
export const DUPLICATE_SEPARATE = 'Report as Separate Incident';

// Cancellation reasons
export const CANCEL_FALSE_ALARM = 'False alarm / accidental trigger';
export const CANCEL_RESOLVED = 'Patient recovered / help not needed';
export const CANCEL_CALLED_112 = 'Called 112 instead';
export const CANCEL_OTHER = 'Other reason';
