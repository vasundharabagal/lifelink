import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { getAllProtocols, getProtocol } from '../features/protocols/lib/protocolRegistry';
import { ProtocolViewer } from '../features/protocols/components/ProtocolViewer';
import { PROTOCOL_DISCLAIMER } from '../lib/strings';

describe('Protocols Feature & Offline Guidance', () => {
  it('statically loads all 7 emergency protocols', () => {
    const all = getAllProtocols();
    expect(all).toHaveLength(7);

    const ids = all.map((p) => p.id);
    expect(ids).toContain('PROT_BURNS');
    expect(ids).toContain('PROT_CHOKING');
    expect(ids).toContain('PROT_GENERAL');
    expect(ids).toContain('PROT_SEIZURE');
    expect(ids).toContain('PROT_SEVERE_BLEEDING');
    expect(ids).toContain('PROT_TRAUMA_FALL');
    expect(ids).toContain('PROT_UNRESPONSIVE');
  });

  it('retrieves specific protocol by ID with all required fields', () => {
    const cpr = getProtocol('PROT_UNRESPONSIVE');
    expect(cpr.id).toBe('PROT_UNRESPONSIVE');
    expect(cpr.title).toContain('Unresponsive');
    expect(cpr.steps.length).toBeGreaterThan(0);
    expect(cpr.do_not.length).toBeGreaterThan(0);
    expect(cpr.call_emergency_first).toBe(true);
  });

  it('renders step instructions, icons, DO NOT warning box, and disclaimer', () => {
    render(
      <MemoryRouter>
        <ProtocolViewer initialProtocolId="PROT_UNRESPONSIVE" />
      </MemoryRouter>
    );

    // Title
    expect(screen.getByRole('heading', { name: /Unresponsive Person/i })).toBeInTheDocument();

    // Steps
    expect(screen.getByText(/Call 112 immediately/i)).toBeInTheDocument();
    expect(screen.getByText(/Deliver hard and fast chest compressions/i)).toBeInTheDocument();

    // DO NOT Box
    const doNotBox = document.getElementById('protocol-do-not-box');
    expect(doNotBox).toBeInTheDocument();
    expect(screen.getByText(/Critical Contraindications \(DO NOT\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Do not leave the person unattended/i)).toBeInTheDocument();

    // Disclaimer
    expect(screen.getByText(PROTOCOL_DISCLAIMER)).toBeInTheDocument();
  });

  it('switches displayed protocol when clicking tabs or drawer item', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <ProtocolViewer
          initialProtocolId="PROT_UNRESPONSIVE"
          relatedProtocolIds={['PROT_SEVERE_BLEEDING']}
        />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: /Unresponsive Person/i })).toBeInTheDocument();

    // Click secondary tab (Severe Bleeding)
    const bleedingTab = screen.getByRole('tab', { name: /Bleeding/i });
    await user.click(bleedingTab);

    expect(screen.getByRole('heading', { name: /Severe External Bleeding/i })).toBeInTheDocument();
    expect(screen.getByText(/Apply firm, continuous direct pressure/i)).toBeInTheDocument();

    // Open drawer
    const drawerBtn = document.getElementById('open-protocols-drawer-btn') as HTMLButtonElement;
    await user.click(drawerBtn);

    const drawer = document.getElementById('protocol-drawer');
    expect(drawer).toBeInTheDocument();

    // Select Choking protocol in drawer
    const chokingOption = document.getElementById('drawer-protocol-PROT_CHOKING') as HTMLButtonElement;
    await user.click(chokingOption);

    expect(screen.getByRole('heading', { name: /Choking/i })).toBeInTheDocument();
  });
});
