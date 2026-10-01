import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { api } from '../lib/api';
import {
  TRIAGE_DISCLAIMER,
  PRIVACY_GUARANTEE,
  GPS_FALLBACK_BADGE,
  ACCURACY_UNAVAILABLE,
} from '../lib/strings';

// Mock API
vi.mock('../lib/api', () => ({
  api: {
    post: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    detail: any;
    constructor(status: number, detail: any) {
      super(typeof detail === 'string' ? detail : JSON.stringify(detail));
      this.status = status;
      this.detail = detail;
    }
  },
}));

const mockPurgeDraft = vi.fn();
const mockUpdateDraft = vi.fn();

const defaultDraft = {
  emergencyType: 'bleeding',
  victim: 'me' as const,
  unresponsive: true,
  breathingNormally: true,
  severeBleeding: true,
  description: 'Cut on arm with severe bleeding',
  lat: 19.076,
  lng: 72.8777,
  accuracy_m: 20 as number | null,
  isFallbackLocation: false,
  landmark: 'Gate 4, Ground Floor',
  idempotencyKey: 'review-uuid-1234',
};

let currentDraft = { ...defaultDraft };

vi.mock('../context/SosDraftContext', () => ({
  useSosDraft: vi.fn(() => ({
    draft: currentDraft,
    updateDraft: mockUpdateDraft,
    purgeDraft: mockPurgeDraft,
    resetDraft: vi.fn(),
    geoLoading: false,
    geoError: null,
  })),
  SosDraftProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { ReviewCard } from '../features/citizen/components/ReviewCard';
import { SosReviewPage } from '../features/citizen/pages/SosReviewPage';

describe('ReviewCard & SosReviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentDraft = { ...defaultDraft };
    vi.mocked(api.post).mockResolvedValue({
      emergency_type: 'BLEEDING',
      observed_conditions: ['SEVERE_BLEEDING'],
      red_flags: [],
      protocol_id: 'PROT_SEVERE_BLEEDING',
      required_skills: [{ skill: 'bleeding_control', min_level: 1 }],
      priority: 'P1',
      ambulance_required: true,
      confidence: 1.0,
      source: 'rules',
      evidence: [],
      rules_version: '1.0.0',
      disclaimer_key: 'decision_support_not_diagnosis',
    });
  });

  it('calls POST /api/v1/triage/preview with draft answers on mount', async () => {
    render(
      <MemoryRouter>
        <ReviewCard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/v1/triage/preview',
        expect.objectContaining({
          quick_type: 'BLEEDING',
          answers: {
            awake: 'yes',
            breathing: 'yes',
            severe_bleeding: 'yes',
          },
          description: 'Cut on arm with severe bleeding',
        })
      );
    });
  });

  it('renders priority banner, condition tags, and privacy guarantee', async () => {
    render(
      <MemoryRouter>
        <ReviewCard />
      </MemoryRouter>
    );

    // Wait for preview response to populate
    await waitFor(() => {
      expect(screen.getByText(/Priority 1 — Immediate Emergency/i)).toBeInTheDocument();
    });

    expect(screen.getByText('SEVERE_BLEEDING')).toBeInTheDocument();
    expect(screen.getByText(/Severe Bleeding Control/i)).toBeInTheDocument();
    expect(screen.getByText(TRIAGE_DISCLAIMER)).toBeInTheDocument();
    expect(screen.getByText(PRIVACY_GUARANTEE)).toBeInTheDocument();
    expect(screen.getByText(/±20m GPS accuracy/i)).toBeInTheDocument();
  });

  it('displays "Accuracy unavailable" when accuracy_m is null', async () => {
    currentDraft = {
      ...defaultDraft,
      accuracy_m: null,
    };

    render(
      <MemoryRouter>
        <ReviewCard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(ACCURACY_UNAVAILABLE)).toBeInTheDocument();
    });
  });

  it('renders explicit fallback badge when isFallbackLocation is true', async () => {
    currentDraft = {
      ...defaultDraft,
      isFallbackLocation: true,
    };

    render(
      <MemoryRouter>
        <ReviewCard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(GPS_FALLBACK_BADGE)).toBeInTheDocument();
    });
  });

  it('submits emergency request with Idempotency-Key and purges draft on success', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post)
      .mockResolvedValueOnce({
        // Preview response
        emergency_type: 'BLEEDING',
        observed_conditions: ['SEVERE_BLEEDING'],
        red_flags: [],
        protocol_id: 'PROT_SEVERE_BLEEDING',
        required_skills: [{ skill: 'bleeding_control', min_level: 1 }],
        priority: 'P1',
        ambulance_required: true,
        confidence: 1.0,
        source: 'rules',
        evidence: [],
        rules_version: '1.0.0',
        disclaimer_key: 'decision_support_not_diagnosis',
      })
      .mockResolvedValueOnce({
        // Emergency create response
        id: 'emg-new-789',
      });

    render(
      <MemoryRouter initialEntries={['/sos/review']}>
        <Routes>
          <Route path="/sos/review" element={<SosReviewPage />} />
          <Route path="/emergency/:id" element={<div>Emergency Live View</div>} />
        </Routes>
      </MemoryRouter>
    );

    const submitBtn = document.getElementById('submit-sos-btn') as HTMLButtonElement;
    expect(submitBtn).toBeInTheDocument();

    await user.click(submitBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/api/v1/emergencies',
        expect.objectContaining({
          lat: 19.076,
          lng: 72.8777,
          patient_is_reporter: true,
          location_hint: 'Gate 4, Ground Floor',
          force_create: false,
        }),
        { 'Idempotency-Key': 'review-uuid-1234' }
      );
    });

    expect(mockPurgeDraft).toHaveBeenCalled();
  });
});
