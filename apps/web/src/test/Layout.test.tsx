import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Call112Button } from '../components/layout/Call112Button';
import { OfflineBanner } from '../components/layout/OfflineBanner';

// Mock AuthContext before importing Header
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    authError: null,
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { Header } from '../components/layout/Header';

describe('Call112Button', () => {
  it('renders with href="tel:112"', () => {
    render(
      <MemoryRouter>
        <Call112Button />
      </MemoryRouter>
    );
    const link = screen.getByRole('link', { name: /call 112/i });
    expect(link).toHaveAttribute('href', 'tel:112');
  });

  it('displays Call 112 Emergency label', () => {
    render(
      <MemoryRouter>
        <Call112Button />
      </MemoryRouter>
    );
    expect(screen.getByText('Call 112 Emergency')).toBeInTheDocument();
  });

  it('displays device-dependency subtitle', () => {
    render(
      <MemoryRouter>
        <Call112Button />
      </MemoryRouter>
    );
    expect(
      screen.getByText('Official national emergency service · Works offline')
    ).toBeInTheDocument();
  });

  it('has id="call-112-button"', () => {
    render(
      <MemoryRouter>
        <Call112Button />
      </MemoryRouter>
    );
    expect(document.getElementById('call-112-button')).toBeInTheDocument();
  });
});

describe('OfflineBanner', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'onLine', { writable: true, value: true });
  });

  it('does not render when online', () => {
    render(<OfflineBanner />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('renders when offline event is fired', () => {
    render(<OfflineBanner />);
    fireEvent(window, new Event('offline'));
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Offline mode/i)).toBeInTheDocument();
  });

  it('shows id="offline-banner" when offline', () => {
    Object.defineProperty(navigator, 'onLine', { writable: true, value: false });
    render(<OfflineBanner />);
    expect(document.getElementById('offline-banner')).toBeInTheDocument();
  });
});

describe('Header', () => {
  it('renders LIFELINK brand text', () => {
    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>
    );
    expect(screen.getByText('LIFELINK')).toBeInTheDocument();
  });

  it('does not show DEMO pill when not demo mode', () => {
    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>
    );
    expect(screen.queryByText('DEMO')).not.toBeInTheDocument();
  });
});
