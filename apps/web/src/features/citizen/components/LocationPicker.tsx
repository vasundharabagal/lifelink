import { useEffect, useRef } from 'react';
import { MapPin, LocateFixed } from 'lucide-react';
import { useSosDraft } from '../../../context/SosDraftContext';
import { formatAccuracy, requestCurrentPosition, DEMO_CENTER_LAT, DEMO_CENTER_LNG } from '../../../lib/geolocation';
import { GPS_FALLBACK_BADGE, ACCURACY_UNAVAILABLE } from '../../../lib/strings';

declare global {
  interface Window {
    L: typeof import('leaflet');
  }
}

/**
 * Stacked Leaflet mini-map with draggable pin and explicit GPS fallback badge.
 *
 * SAFETY INVARIANTS:
 * - When isFallbackLocation === true, prominently show GPS_FALLBACK_BADGE (amber)
 *   — never implies user's real GPS location
 * - Accuracy displays only real browser-provided value (±{n}m) or "Accuracy unavailable"
 */
export function LocationPicker() {
  const { draft, updateDraft, geoLoading, geoError } = useSosDraft();
  const mapRef = useRef<import('leaflet').Map | null>(null);
  const markerRef = useRef<import('leaflet').Marker | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Dynamically import leaflet to keep test bundle clean
    let isMounted = true;
    let map: import('leaflet').Map | null = null;

    import('leaflet').then((L) => {
      if (!isMounted || !containerRef.current) return;
      if (mapRef.current) return; // Already initialized

      // Fix default icon paths for Vite
      delete (L.Icon.Default.prototype as Record<string, unknown>)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });

      map = L.map(containerRef.current, {
        zoomControl: true,
        attributionControl: false,
      }).setView([draft.lat, draft.lng], 16);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
      }).addTo(map);

      const marker = L.marker([draft.lat, draft.lng], { draggable: true }).addTo(map);
      marker.on('dragend', () => {
        const pos = marker.getLatLng();
        updateDraft({ lat: pos.lat, lng: pos.lng });
      });

      markerRef.current = marker;
      mapRef.current = map;
    });

    return () => {
      isMounted = false;
      if (map) {
        map.remove();
        mapRef.current = null;
        markerRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only mount once

  // Update marker position when draft coords change externally
  useEffect(() => {
    if (markerRef.current && mapRef.current) {
      markerRef.current.setLatLng([draft.lat, draft.lng]);
      mapRef.current.setView([draft.lat, draft.lng], mapRef.current.getZoom());
    }
  }, [draft.lat, draft.lng]);

  const recenter = () => {
    requestCurrentPosition()
      .then((pos) => {
        updateDraft({
          lat: pos.lat,
          lng: pos.lng,
          accuracy_m: pos.accuracy_m,
          isFallbackLocation: false,
        });
      })
      .catch(() => {
        updateDraft({
          lat: DEMO_CENTER_LAT,
          lng: DEMO_CENTER_LNG,
          accuracy_m: null,
          isFallbackLocation: true,
        });
      });
  };

  const accuracyText = draft.accuracy_m !== null ? formatAccuracy(draft.accuracy_m) : ACCURACY_UNAVAILABLE;

  return (
    <div className="flex flex-col gap-3">
      {/* Fallback location badge — mandatory when isFallbackLocation */}
      {draft.isFallbackLocation && (
        <div
          id="location-fallback-badge"
          role="alert"
          className="flex items-center gap-2 bg-amber-50 border border-amber-300 text-amber-800 rounded-xl px-3 py-2 text-xs font-semibold"
        >
          <MapPin className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
          {GPS_FALLBACK_BADGE}
        </div>
      )}

      {/* Mini-map */}
      <div className="relative rounded-xl overflow-hidden border border-slate-200 shadow-sm h-48">
        <div
          id="location-map"
          ref={containerRef}
          className="w-full h-full"
          aria-label="Draggable emergency location map"
        />

        {/* Loading overlay */}
        {geoLoading && (
          <div className="absolute inset-0 bg-white/70 flex items-center justify-center text-xs text-slate-500">
            Getting location…
          </div>
        )}

        {/* Re-center button */}
        <button
          id="recenter-btn"
          type="button"
          onClick={recenter}
          className="absolute top-2 right-2 z-[1000] bg-white border border-slate-200 shadow rounded-lg p-1.5 hover:bg-slate-50 transition-colors min-h-[32px] min-w-[32px] flex items-center justify-center"
          aria-label="Re-center to my GPS location"
        >
          <LocateFixed className="w-4 h-4 text-slate-700" aria-hidden="true" />
        </button>
      </div>

      {/* Accuracy display */}
      <div id="location-accuracy-display" className="text-xs text-slate-600 font-medium">
        {geoLoading ? 'Getting GPS accuracy…' : accuracyText}
        {geoError && !draft.isFallbackLocation && (
          <span className="text-amber-600 ml-1">({geoError})</span>
        )}
      </div>

      {/* Landmark input */}
      <div>
        <label htmlFor="landmark-input" className="block text-xs font-semibold text-slate-700 mb-1">
          Landmark / access details
        </label>
        <input
          id="landmark-input"
          type="text"
          value={draft.landmark}
          onChange={(e) => updateDraft({ landmark: e.target.value })}
          placeholder="Gate 2, 3rd floor, blue door…"
          className="
            w-full min-h-[44px] px-3 py-2 border border-slate-300 rounded-lg text-sm
            bg-white text-slate-900 placeholder-slate-400
            focus:outline-none focus:ring-2 focus:ring-slate-900 focus:border-transparent
          "
        />
      </div>
    </div>
  );
}
