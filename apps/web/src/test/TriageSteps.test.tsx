import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

// Draft mock with controlled state
const mockDraft = {
  emergencyType: null as string | null,
  victim: 'someone_else' as 'me' | 'someone_else',
  unresponsive: null as boolean | null,
  breathingNormally: null as boolean | null,
  severeBleeding: null as boolean | null,
  description: '',
  lat: 19.076, lng: 72.8777, accuracy_m: null, isFallbackLocation: true,
  landmark: '', idempotencyKey: 'test-key',
};

const mockUpdateDraft = vi.fn((partial: Partial<typeof mockDraft>) => {
  Object.assign(mockDraft, partial);
});

vi.mock('../context/SosDraftContext', () => ({
  useSosDraft: () => ({
    draft: mockDraft,
    updateDraft: mockUpdateDraft,
    purgeDraft: vi.fn(),
    geoLoading: false,
    geoError: null,
  }),
  SosDraftProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { QuickTypeGrid } from '../features/citizen/components/QuickTypeGrid';
import { TriageQuestions } from '../features/citizen/components/TriageQuestions';

describe('QuickTypeGrid', () => {
  it('renders all 8 emergency chips', () => {
    const onContinue = vi.fn();
    const onSkip = vi.fn();
    render(
      <MemoryRouter>
        <QuickTypeGrid onContinue={onContinue} onSkip={onSkip} />
      </MemoryRouter>
    );
    expect(screen.getByText('Bleeding')).toBeInTheDocument();
    expect(screen.getByText('Not responding')).toBeInTheDocument();
    expect(screen.getByText('Chest Pain')).toBeInTheDocument();
    expect(screen.getByText('Other Emergency')).toBeInTheDocument();
  });

  it('renders who-needs-help victim selector', () => {
    render(
      <MemoryRouter>
        <QuickTypeGrid onContinue={vi.fn()} onSkip={vi.fn()} />
      </MemoryRouter>
    );
    expect(screen.getByText('Me')).toBeInTheDocument();
    expect(screen.getByText('Someone else')).toBeInTheDocument();
  });

  it('selecting a chip calls updateDraft with emergencyType', async () => {
    const user = userEvent.setup();
    mockUpdateDraft.mockClear();
    render(
      <MemoryRouter>
        <QuickTypeGrid onContinue={vi.fn()} onSkip={vi.fn()} />
      </MemoryRouter>
    );
    await user.click(screen.getByText('Bleeding'));
    expect(mockUpdateDraft).toHaveBeenCalledWith(expect.objectContaining({ emergencyType: 'bleeding' }));
  });

  it('skip button calls onSkip', async () => {
    const user = userEvent.setup();
    const onSkip = vi.fn();
    render(
      <MemoryRouter>
        <QuickTypeGrid onContinue={vi.fn()} onSkip={onSkip} />
      </MemoryRouter>
    );
    await user.click(screen.getByText('Skip'));
    expect(onSkip).toHaveBeenCalled();
  });

  it('all chips meet min-h-[56px] touch target', () => {
    render(
      <MemoryRouter>
        <QuickTypeGrid onContinue={vi.fn()} onSkip={vi.fn()} />
      </MemoryRouter>
    );
    const chestPainChip = document.getElementById('chip-chest_pain');
    expect(chestPainChip).toHaveClass('min-h-[56px]');
  });
});

describe('TriageQuestions', () => {
  it('renders all 3 question cards', () => {
    render(
      <MemoryRouter>
        <TriageQuestions />
      </MemoryRouter>
    );
    expect(screen.getByText(/awake and responding/i)).toBeInTheDocument();
    expect(screen.getByText(/breathing normally/i)).toBeInTheDocument();
    expect(screen.getByText(/severe.*bleeding/i)).toBeInTheDocument();
  });

  it('each question has Yes, No, Not sure options', () => {
    render(
      <MemoryRouter>
        <TriageQuestions />
      </MemoryRouter>
    );
    expect(screen.getAllByText('Yes')).toHaveLength(3);
    expect(screen.getAllByText('No')).toHaveLength(3);
    expect(screen.getAllByText('Not sure')).toHaveLength(3);
  });

  it('clicking Yes on first question calls updateDraft', async () => {
    const user = userEvent.setup();
    mockUpdateDraft.mockClear();
    render(
      <MemoryRouter>
        <TriageQuestions />
      </MemoryRouter>
    );
    await user.click(screen.getAllByText('Yes')[0]);
    expect(mockUpdateDraft).toHaveBeenCalled();
  });
});
