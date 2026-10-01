import protBurns from '../../../../../../shared/protocols/PROT_BURNS.json';
import protChoking from '../../../../../../shared/protocols/PROT_CHOKING.json';
import protGeneral from '../../../../../../shared/protocols/PROT_GENERAL.json';
import protSeizure from '../../../../../../shared/protocols/PROT_SEIZURE.json';
import protSevereBleeding from '../../../../../../shared/protocols/PROT_SEVERE_BLEEDING.json';
import protTraumaFall from '../../../../../../shared/protocols/PROT_TRAUMA_FALL.json';
import protUnresponsive from '../../../../../../shared/protocols/PROT_UNRESPONSIVE.json';

export interface ProtocolStep {
  n: number;
  text_key: string;
  icon: string;
}

export interface Protocol {
  id: string;
  version: string;
  title: string;
  applies_to: string[];
  status: string;
  source_citation: string;
  reviewed_by?: string | null;
  reviewed_on?: string | null;
  call_emergency_first: boolean;
  steps: ProtocolStep[];
  do_not: string[];
  disclaimer_key: string;
}

export const PROTOCOL_REGISTRY: Record<string, Protocol> = {
  PROT_BURNS: protBurns as Protocol,
  PROT_CHOKING: protChoking as Protocol,
  PROT_GENERAL: protGeneral as Protocol,
  PROT_SEIZURE: protSeizure as Protocol,
  PROT_SEVERE_BLEEDING: protSevereBleeding as Protocol,
  PROT_TRAUMA_FALL: protTraumaFall as Protocol,
  PROT_UNRESPONSIVE: protUnresponsive as Protocol,
};

export function getAllProtocols(): Protocol[] {
  return Object.values(PROTOCOL_REGISTRY);
}

export function getProtocol(id?: string | null): Protocol {
  if (!id) return PROTOCOL_REGISTRY.PROT_GENERAL;
  return PROTOCOL_REGISTRY[id] || PROTOCOL_REGISTRY.PROT_GENERAL;
}
