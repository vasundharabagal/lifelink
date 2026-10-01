import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import {
  DEMO_CENTER_LAT,
  DEMO_CENTER_LNG,
  requestCurrentPosition,
} from '../lib/geolocation';

const STORAGE_KEY = 'lifelink_sos_draft';

function generateIdempotencyKey(): string {
  return crypto.randomUUID();
}

export interface SosDraft {
  emergencyType: string | null;
  victim: 'me' | 'someone_else';
  unresponsive: boolean | null;
  breathingNormally: boolean | null;
  severeBleeding: boolean | null;
  description: string;
  lat: number;
  lng: number;
  accuracy_m: number | null;
  isFallbackLocation: boolean;
  landmark: string;
  idempotencyKey: string;
}

const DEFAULT_DRAFT: SosDraft = {
  emergencyType: null,
  victim: 'someone_else',
  unresponsive: null,
  breathingNormally: null,
  severeBleeding: null,
  description: '',
  lat: DEMO_CENTER_LAT,
  lng: DEMO_CENTER_LNG,
  accuracy_m: null,
  isFallbackLocation: true,
  landmark: '',
  idempotencyKey: generateIdempotencyKey(),
};

function loadDraft(): SosDraft {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<SosDraft>;
      return { ...DEFAULT_DRAFT, ...parsed };
    }
  } catch {
    // ignore
  }
  return { ...DEFAULT_DRAFT, idempotencyKey: generateIdempotencyKey() };
}

function saveDraft(draft: SosDraft): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // ignore quota errors
  }
}

interface SosDraftContextValue {
  draft: SosDraft;
  geoLoading: boolean;
  geoError: string | null;
  updateDraft: (partial: Partial<SosDraft>) => void;
  resetDraft: () => void;
  purgeDraft: () => void;
}

const SosDraftContext = createContext<SosDraftContextValue | null>(null);

export function useSosDraft(): SosDraftContextValue {
  const ctx = useContext(SosDraftContext);
  if (!ctx) throw new Error('useSosDraft must be used inside SosDraftProvider');
  return ctx;
}

export function SosDraftProvider({ children }: { children: React.ReactNode }) {
  const [draft, setDraft] = useState<SosDraft>(loadDraft);
  const [geoLoading, setGeoLoading] = useState(true);
  const [geoError, setGeoError] = useState<string | null>(null);
  const initialized = useRef(false);

  // Pre-warm geolocation on mount
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    requestCurrentPosition()
      .then((pos) => {
        setDraft((prev) => {
          const next: SosDraft = {
            ...prev,
            lat: pos.lat,
            lng: pos.lng,
            accuracy_m: pos.accuracy_m,
            isFallbackLocation: false,
          };
          saveDraft(next);
          return next;
        });
        setGeoError(null);
      })
      .catch((err: Error | GeolocationPositionError) => {
        const msg =
          'code' in err && err.code === 1
            ? 'GPS permission denied. Using demo location.'
            : 'GPS unavailable. Using demo location.';
        setGeoError(msg);
        // isFallbackLocation stays true from DEFAULT_DRAFT
      })
      .finally(() => {
        setGeoLoading(false);
      });
  }, []);

  const updateDraft = useCallback((partial: Partial<SosDraft>) => {
    setDraft((prev) => {
      const next = { ...prev, ...partial };
      saveDraft(next);
      return next;
    });
  }, []);

  const resetDraft = useCallback(() => {
    const fresh: SosDraft = {
      ...DEFAULT_DRAFT,
      lat: draft.lat,
      lng: draft.lng,
      accuracy_m: draft.accuracy_m,
      isFallbackLocation: draft.isFallbackLocation,
      idempotencyKey: generateIdempotencyKey(),
    };
    saveDraft(fresh);
    setDraft(fresh);
  }, [draft]);

  const purgeDraft = useCallback(() => {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    setDraft({ ...DEFAULT_DRAFT, idempotencyKey: generateIdempotencyKey() });
  }, []);

  return (
    <SosDraftContext.Provider
      value={{ draft, geoLoading, geoError, updateDraft, resetDraft, purgeDraft }}
    >
      {children}
    </SosDraftContext.Provider>
  );
}
