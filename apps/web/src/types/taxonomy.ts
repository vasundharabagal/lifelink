/**
 * TypeScript domain type declarations for LIFELINK.
 * Grounded in canonical shared/taxonomy.json.
 */
import taxonomy from '../../../../shared/taxonomy.json';

export type EmergencyTypeCode = (typeof taxonomy.emergency_types)[number]['code'];

export type ConditionCode = (typeof taxonomy.conditions)[number]['code'];

export type SkillCode = (typeof taxonomy.skills)[number]['code'];

export type ResponderCategory = (typeof taxonomy.responder_categories)[number];

export type SkillLevel = 1 | 2 | 3;

export type ResponderReadiness = 'available' | 'off_duty' | 'busy';

export type CredentialStatus =
  | 'pending'
  | 'verified'
  | 'rejected'
  | 'expired'
  | 'suspended';

export type AmbulanceUnitType = 'basic' | 'advanced';

export type AmbulanceUnitStatus = 'available' | 'busy' | 'offline';

export type Priority = 'P1_CRITICAL' | 'P2_SERIOUS' | 'P3_STABLE';

export type EmergencyStatus =
  | 'CREATED'
  | 'TRIAGED'
  | 'DISPATCHING'
  | 'IN_PROGRESS'
  | 'HANDED_OVER'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'NO_COVERAGE_CLOSED';

export type TrackStatus =
  | 'NOT_STARTED'
  | 'SEARCHING'
  | 'OFFERED'
  | 'ASSIGNED'
  | 'ON_SCENE'
  | 'DONE'
  | 'UNAVAILABLE'
  | 'CANCELLED';

export type OfferStatus =
  | 'OFFERED'
  | 'ACCEPTED'
  | 'ARRIVED'
  | 'COMPLETED'
  | 'DECLINED'
  | 'EXPIRED'
  | 'CANCELLED';

export type AuditOutcome = 'allow' | 'deny';

export type TargetKind = 'responder' | 'ambulance';

export type TrackKind = 'community' | 'professional';

export interface EmergencyTypeDefinition {
  code: EmergencyTypeCode;
  label: string;
  description: string;
}

export interface ConditionDefinition {
  code: ConditionCode;
  label: string;
  red_flag: boolean;
}

export interface SkillDefinition {
  code: SkillCode;
  name: string;
  levels: {
    '1': string;
    '2': string;
    '3': string;
  };
}

export interface ProtocolRequirement {
  skill: SkillCode;
  min_level: SkillLevel;
}

export interface TaxonomySchema {
  version: string;
  emergency_types: EmergencyTypeDefinition[];
  conditions: ConditionDefinition[];
  skills: SkillDefinition[];
  responder_categories: ResponderCategory[];
  protocol_skill_requirements: Record<string, ProtocolRequirement[]>;
}

export { taxonomy };
