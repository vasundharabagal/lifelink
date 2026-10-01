import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { DuplicateModal } from '../features/citizen/components/DuplicateModal';
import { CancelModal } from '../features/citizen/components/CancelModal';
import { api } from '../lib/api';
import {
  DUPLICATE_TITLE,
  DUPLICATE_JOIN,
  DUPLICATE_SEPARATE,
  CANCEL_FALSE_ALARM,
} from '../lib/strings';

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

describe('EmergencyModals', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('DuplicateModal (409 Conflict Resolution)', () => {
    const mockDuplicateData = {
      existing_emergency_id: 'emg-existing-uuid-9999',
      distance_m: 65.4,
      priority: 'P1',
    };

    it('renders duplicate incident details and distance', () => {
      render(
        <DuplicateModal
          isOpen={true}
          duplicateData={mockDuplicateData}
          onJoinExisting={vi.fn()}
          onForceCreate={vi.fn()}
          onCancel={vi.fn()}
        />
      );

      expect(screen.getByText(DUPLICATE_TITLE)).toBeInTheDocument();
      expect(screen.getByText(/65m/)).toBeInTheDocument();
      expect(screen.getByText(DUPLICATE_JOIN)).toBeInTheDocument();
      expect(screen.getByText(DUPLICATE_SEPARATE)).toBeInTheDocument();
    });

    it('invokes onJoinExisting when Join button is clicked', async () => {
      const user = userEvent.setup();
      const onJoin = vi.fn();

      render(
        <DuplicateModal
          isOpen={true}
          duplicateData={mockDuplicateData}
          onJoinExisting={onJoin}
          onForceCreate={vi.fn()}
          onCancel={vi.fn()}
        />
      );

      const joinBtn = screen.getByRole('button', { name: new RegExp(DUPLICATE_JOIN, 'i') });
      await user.click(joinBtn);
      expect(onJoin).toHaveBeenCalledTimes(1);
    });

    it('invokes onForceCreate when Report as Separate button is clicked', async () => {
      const user = userEvent.setup();
      const onForce = vi.fn();

      render(
        <DuplicateModal
          isOpen={true}
          duplicateData={mockDuplicateData}
          onJoinExisting={vi.fn()}
          onForceCreate={onForce}
          onCancel={vi.fn()}
        />
      );

      const forceBtn = screen.getByRole('button', { name: new RegExp(DUPLICATE_SEPARATE, 'i') });
      await user.click(forceBtn);
      expect(onForce).toHaveBeenCalledTimes(1);
    });
  });

  describe('CancelModal (Two-Step Reason Gating)', () => {
    it('disables Confirm Cancellation button until a reason is selected', async () => {
      render(
        <MemoryRouter>
          <CancelModal
            isOpen={true}
            emergencyId="emg-test-123"
            onClose={vi.fn()}
          />
        </MemoryRouter>
      );

      const confirmBtn = screen.getByRole('button', { name: /Confirm Cancellation/i });
      expect(confirmBtn).toBeDisabled();
    });

    it('enables confirm button after selecting a reason and submits cancellation', async () => {
      const user = userEvent.setup();
      vi.mocked(api.post).mockResolvedValue({ status: 'CANCELLED' });

      render(
        <MemoryRouter initialEntries={['/emergency/emg-test-123']}>
          <Routes>
            <Route
              path="/emergency/:id"
              element={
                <CancelModal
                  isOpen={true}
                  emergencyId="emg-test-123"
                  onClose={vi.fn()}
                />
              }
            />
            <Route path="/sos" element={<div>SOS Home</div>} />
          </Routes>
        </MemoryRouter>
      );

      const confirmBtn = screen.getByRole('button', { name: /Confirm Cancellation/i });
      expect(confirmBtn).toBeDisabled();

      // Click reason chip
      const reasonBtn = screen.getByText(CANCEL_FALSE_ALARM);
      await user.click(reasonBtn);

      expect(confirmBtn).not.toBeDisabled();

      // Click confirm
      await user.click(confirmBtn);

      await waitFor(() => {
        expect(api.post).toHaveBeenCalledWith(
          '/api/v1/emergencies/emg-test-123/cancel',
          { reason: 'false_alarm' }
        );
      });
    });
  });
});
