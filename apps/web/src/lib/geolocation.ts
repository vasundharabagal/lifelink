/**
 * Geolocation utility for LIFELINK citizen SOS flow.
 *
 * SAFETY INVARIANTS:
 * - isFallback: true MUST trigger a visually explicit "Demo location used — GPS unavailable" badge in UI
 * - Accuracy displays ±{n}m only when browser provides real GPS/network fix; otherwise "Accuracy unavailable"
 * - DEMO_CENTER coordinates are NEVER implied to be the user's real location
 */

export const DEMO_CENTER_LAT = Number(import.meta.env.VITE_DEMO_CENTER_LAT) || 19.076;
export const DEMO_CENTER_LNG = Number(import.meta.env.VITE_DEMO_CENTER_LNG) || 72.8777;

export interface GeoLocationState {
  lat: number;
  lng: number;
  accuracy_m: number | null;
  isFallback: boolean;
  isLoading: boolean;
  error: string | null;
}

export const INITIAL_GEO_STATE: GeoLocationState = {
  lat: DEMO_CENTER_LAT,
  lng: DEMO_CENTER_LNG,
  accuracy_m: null,
  isFallback: true,
  isLoading: true,
  error: null,
};

/** Formats accuracy for display. Returns "±{n}m" or "Accuracy unavailable" */
export function formatAccuracy(accuracy_m: number | null): string {
  if (accuracy_m === null) return 'Accuracy unavailable';
  return `±${Math.round(accuracy_m)}m`;
}

export interface GeoPositionResult {
  lat: number;
  lng: number;
  accuracy_m: number;
}

/**
 * Request a single geolocation fix.
 * On success: real coordinates with accuracy from browser.
 * On error: throws GeolocationPositionError for caller to fall back to DEMO_CENTER.
 */
export function requestCurrentPosition(): Promise<GeoPositionResult> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation API not available in this browser or environment.'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy_m: pos.coords.accuracy,
        });
      },
      (err) => {
        reject(err);
      },
      {
        timeout: 8000,
        maximumAge: 30000,
        enableHighAccuracy: true,
      }
    );
  });
}
