import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

const mockLogin = vi.fn();

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    authError: null,
    login: mockLogin,
    register: vi.fn(),
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { LoginPage } from '../features/auth/pages/LoginPage';

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders email and password inputs', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('submits login with email and password', async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue(undefined);

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
    await user.type(screen.getByLabelText(/password/i), 'testpassword');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'testpassword');
    });
  });

  it('renders quick-fill demo credential buttons', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    expect(screen.getByRole('button', { name: /demo citizen/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /demo responder/i })).toBeInTheDocument();
  });

  it('fills email on Demo Citizen click', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    await user.click(screen.getByRole('button', { name: /demo citizen/i }));
    expect((screen.getByLabelText(/email address/i) as HTMLInputElement).value).toBe(
      'citizen.maya@demo.lifelink.invalid'
    );
  });
});
