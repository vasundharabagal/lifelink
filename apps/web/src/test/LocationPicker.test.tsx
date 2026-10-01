import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { GPS_FALLBACK_BADGE, ACCURACY_UNAVAILABLE } from '../lib/strings';

// Mock Leaflet to prevent jsdom DOM errors
vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => ({
      setView: vi.fn().mockReturnThis(),
      remove: vi.fn(),
      getZoom: vi.fn().mockReturnValue(16),
    })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    marker: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis(),
      on: vi.fn().mockReturnThis(),
      setLatLng: vi.fn(),
    })),
    Icon: {
      Default: {
        prototype: {},
        mergeOptions: vi.fn(),
      },
    },
  },
}));

const mockUpdateDraft = vi.fn();

const defaultDraftContext = {
  draft: {
    lat: 19.076,
    lng: 72.8777,
    accuracy_m: 35,
    isFallbackLocation: false,
    emergencyType: null,
    victim: 'someone_else' as const,
    unresponsive: null,
    breathingNormally: null,
    severeBleeding: null,
    description: '',
    landmark: '',
    idempotencyKey: 'test-key',
  },
  updateDraft: mockUpdateDraft,
  resetDraft: vi.fn(),
  purgeDraft: vi.fn(),
  geoLoading: false,
  geoError: null,
};

// Mock SosDraftContext
vi.mock('../context/SosDraftContext', () => ({
  useSosDraft: vi.fn(() => defaultDraftContext),
  SosDraftProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { LocationPicker } from '../features/citizen/components/LocationPicker';
import { useSosDraft } from '../context/SosDraftContext';

describe('LocationPicker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSosDraft).mockReturnValue(defaultDraftContext);
  });

  it('does NOT show fallback badge when real GPS is available', () => {
    render(
      <MemoryRouter>
        <LocationPicker />
      </MemoryRouter>
    );
    expect(screen.queryByText(GPS_FALLBACK_BADGE)).not.toBeInTheDocument();
  });

  it('shows amber fallback badge when isFallbackLocation is true', () => {
    vi.mocked(useSosDraft).mockReturnValue({
      draft: {
        lat: 19.076, lng: 72.8777, accuracy_m: null, isFallbackLocation: true,
        emergencyType: null, victim: 'someone_else', unresponsive: null,
        breathingNormally: null, severeBleeding: null, description: '', landmark: '',
        idempotencyKey: 'test-key',
      },
      updateDraft: mockUpdateDraft,
      resetDraft: vi.fn(),
      purgeDraft: vi.fn(),
      geoLoading: false,
      geoError: 'GPS permission denied. Using demo location.',
    });

    render(
      <MemoryRouter>
        <LocationPicker />
      </MemoryRouter>
    );

    const badge = document.getElementById('location-fallback-badge');
    expect(badge).toBeInTheDocument();
    expect(badge?.textContent).toContain(GPS_FALLBACK_BADGE);
  });

  it('displays real accuracy as ±{n}m when available', () => {
    render(
      <MemoryRouter>
        <LocationPicker />
      </MemoryRouter>
    );
    const accuracyEl = document.getElementById('location-accuracy-display');
    expect(accuracyEl?.textContent).toContain('±35m');
  });

  it('displays "Accuracy unavailable" when accuracy_m is null', () => {
    vi.mocked(useSosDraft).mockReturnValue({
      draft: {
        lat: 19.076, lng: 72.8777, accuracy_m: null, isFallbackLocation: false,
        emergencyType: null, victim: 'someone_else', unresponsive: null,
        breathingNormally: null, severeBleeding: null, description: '', landmark: '',
        idempotencyKey: 'test-key',
      },
      updateDraft: mockUpdateDraft,
      resetDraft: vi.fn(),
      purgeDraft: vi.fn(),
      geoLoading: false,
      geoError: null,
    });

    render(
      <MemoryRouter>
        <LocationPicker />
      </MemoryRouter>
    );

    const accuracyEl = document.getElementById('location-accuracy-display');
    expect(accuracyEl?.textContent).toContain(ACCURACY_UNAVAILABLE);
  });

  it('renders landmark input', () => {
    render(
      <MemoryRouter>
        <LocationPicker />
      </MemoryRouter>
    );
    expect(document.getElementById('landmark-input')).toBeInTheDocument();
  });

  it('renders recenter button', () => {
    render(
      <MemoryRouter>
        <LocationPicker />
      </MemoryRouter>
    );
    expect(document.getElementById('recenter-btn')).toBeInTheDocument();
  });
});
