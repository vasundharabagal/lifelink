import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SosButton } from '../features/citizen/components/SosButton';

// Mock requestAnimationFrame for deterministic timing
let rafCallbacks: FrameRequestCallback[] = [];
const mockRaf = vi.fn((cb: FrameRequestCallback) => {
  rafCallbacks.push(cb);
  return rafCallbacks.length;
});
const mockCancelRaf = vi.fn((id: number) => {
  rafCallbacks = rafCallbacks.filter((_, i) => i !== id - 1);
});

// Mock performance.now for controlled timing
let mockTime = 0;
const mockPerformanceNow = vi.fn(() => mockTime);

vi.mock('../context/SosDraftContext', () => ({
  useSosDraft: () => ({
    draft: {
      lat: 19.076, lng: 72.8777, accuracy_m: null, isFallbackLocation: true,
      idempotencyKey: 'test-key',
    },
    updateDraft: vi.fn(),
    purgeDraft: vi.fn(),
    geoLoading: false,
    geoError: null,
  }),
  SosDraftProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../lib/api', () => ({
  api: { post: vi.fn() },
  ApiError: class ApiError extends Error { constructor(public status: number, public detail: string) { super(detail); } },
}));

describe('SosButton', () => {
  beforeEach(() => {
    mockTime = 0;
    rafCallbacks = [];
    vi.stubGlobal('requestAnimationFrame', mockRaf);
    vi.stubGlobal('cancelAnimationFrame', mockCancelRaf);
    vi.stubGlobal('performance', { now: mockPerformanceNow });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders with correct aria-label and id', () => {
    const onTriggered = vi.fn();
    render(<SosButton onTriggered={onTriggered} />);
    const btn = document.getElementById('sos-button');
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveAttribute('aria-label', expect.stringContaining('Press and hold'));
  });

  it('does NOT trigger when released before 1500ms', async () => {
    const onTriggered = vi.fn();
    render(<SosButton onTriggered={onTriggered} />);
    const btn = screen.getByRole('button');

    fireEvent.mouseDown(btn);
    // Advance only 500ms — not enough
    mockTime = 500;
    act(() => { rafCallbacks.forEach(cb => cb(500)); rafCallbacks = []; });
    fireEvent.mouseUp(btn);

    expect(onTriggered).not.toHaveBeenCalled();
  });

  it('triggers onTriggered after continuous 1500ms hold', async () => {
    const onTriggered = vi.fn();
    render(<SosButton onTriggered={onTriggered} />);
    const btn = screen.getByRole('button');

    fireEvent.mouseDown(btn);
    // Run RAF frames until 1500ms threshold
    let t = 0;
    while (t < 1500 && onTriggered.mock.calls.length === 0) {
      t += 100;
      mockTime = t;
      const cbs = [...rafCallbacks];
      rafCallbacks = [];
      act(() => { cbs.forEach(cb => cb(t)); });
    }

    await waitFor(() => {
      expect(onTriggered).toHaveBeenCalledTimes(1);
    });
  });

  it('shows SOS label', () => {
    const onTriggered = vi.fn();
    render(<SosButton onTriggered={onTriggered} />);
    expect(screen.getByText('SOS')).toBeInTheDocument();
  });
});

describe('SosConfirmSheet', () => {
  it('renders confirm sheet title and both action buttons', async () => {
    const { SosConfirmSheet } = await import('../features/citizen/components/SosConfirmSheet');
    const onClose = vi.fn();

    render(
      <MemoryRouter>
        <SosConfirmSheet onClose={onClose} />
      </MemoryRouter>
    );

    expect(screen.getByText('Send Emergency Request?')).toBeInTheDocument();
    expect(screen.getByText(/Add Details/i)).toBeInTheDocument();
    expect(screen.getByText(/Send Now/i)).toBeInTheDocument();
  });

  it('renders countdown bar with id="sos-countdown-bar"', async () => {
    const { SosConfirmSheet } = await import('../features/citizen/components/SosConfirmSheet');
    render(
      <MemoryRouter>
        <SosConfirmSheet onClose={vi.fn()} />
      </MemoryRouter>
    );
    expect(document.getElementById('sos-countdown-bar')).toBeInTheDocument();
  });
});
