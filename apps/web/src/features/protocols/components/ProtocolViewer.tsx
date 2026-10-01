import { useState } from 'react';
import {
  Phone,
  UserCheck,
  ArrowDown,
  Activity,
  RotateCw,
  Zap,
  Droplets,
  AlertTriangle,
  Flame,
  Wind,
  Shield,
} from 'lucide-react';
import { getProtocol } from '../lib/protocolRegistry';
import { ProtocolTabs } from './ProtocolTabs';
import { ProtocolDrawer } from './ProtocolDrawer';
import { PROTOCOL_DISCLAIMER } from '../../../lib/strings';

interface ProtocolViewerProps {
  initialProtocolId?: string;
  relatedProtocolIds?: string[];
}

function getStepIcon(iconName: string) {
  switch (iconName) {
    case 'phone':
      return <Phone className="w-4 h-4 text-red-600" />;
    case 'user-check':
      return <UserCheck className="w-4 h-4 text-emerald-600" />;
    case 'arrow-down':
      return <ArrowDown className="w-4 h-4 text-blue-600" />;
    case 'activity':
      return <Activity className="w-4 h-4 text-red-600" />;
    case 'repeat':
      return <RotateCw className="w-4 h-4 text-amber-600" />;
    case 'zap':
      return <Zap className="w-4 h-4 text-yellow-600" />;
    case 'droplets':
      return <Droplets className="w-4 h-4 text-red-600" />;
    case 'flame':
      return <Flame className="w-4 h-4 text-orange-600" />;
    case 'wind':
      return <Wind className="w-4 h-4 text-teal-600" />;
    case 'shield':
      return <Shield className="w-4 h-4 text-indigo-600" />;
    default:
      return <Activity className="w-4 h-4 text-slate-600" />;
  }
}

/**
 * Offline-first clinical first-aid protocol guidance viewer (D-09, D-11, D-12, UI-SPEC §5.9).
 * Renders statically bundled JSON guidance with zero network reliance.
 */
export function ProtocolViewer({
  initialProtocolId = 'PROT_UNRESPONSIVE',
  relatedProtocolIds = [],
}: ProtocolViewerProps) {
  const [activeProtocolId, setActiveProtocolId] = useState(initialProtocolId);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const protocol = getProtocol(activeProtocolId);

  return (
    <div className="flex flex-col gap-4">
      {/* Condition Tabs */}
      <ProtocolTabs
        activeProtocolId={activeProtocolId}
        onSelectTab={setActiveProtocolId}
        onOpenDrawer={() => setIsDrawerOpen(true)}
        additionalProtocolIds={relatedProtocolIds}
      />

      {/* Main Guidance Card */}
      <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm space-y-5">
        {/* Header */}
        <div className="border-b border-slate-100 pb-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Clinical Protocol ({protocol.id})
            </span>
            {protocol.call_emergency_first && (
              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
                <AlertTriangle className="w-3 h-3" />
                Call 112 First
              </span>
            )}
          </div>
          <h2 id="protocol-title" className="text-xl font-black text-slate-900 mt-1 leading-snug">
            {protocol.title}
          </h2>
        </div>

        {/* Step-by-Step Instructions */}
        <div className="space-y-3.5" id="protocol-steps">
          {protocol.steps.map((step) => (
            <div
              key={step.n}
              className="flex items-start gap-3.5 bg-slate-50 border border-slate-100 rounded-2xl p-3.5"
            >
              <div className="w-7 h-7 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs flex-shrink-0 mt-0.5">
                {step.n}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="p-1 rounded-md bg-white border border-slate-200">
                    {getStepIcon(step.icon)}
                  </span>
                  <span className="text-xs font-semibold text-slate-500">
                    Step {step.n}
                  </span>
                </div>
                <p className="text-sm font-semibold text-slate-900 leading-snug">
                  {step.text_key}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* High-Visibility DO NOT Warning Box */}
        {protocol.do_not && protocol.do_not.length > 0 && (
          <div
            id="protocol-do-not-box"
            role="alert"
            className="bg-red-50 border-l-4 border-red-600 p-4 rounded-r-2xl space-y-2"
          >
            <div className="flex items-center gap-2 text-red-900">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <h3 className="text-xs font-black uppercase tracking-wider">
                Critical Contraindications (DO NOT)
              </h3>
            </div>
            <ul className="list-disc list-inside space-y-1 text-xs text-red-950 font-medium leading-relaxed">
              {protocol.do_not.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Source Citation & Safety Disclaimer */}
        <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 space-y-1">
          <p className="font-medium text-slate-600">
            Source: <span className="italic">{protocol.source_citation}</span>
          </p>
          <p id="protocol-disclaimer" className="text-slate-400">
            {PROTOCOL_DISCLAIMER}
          </p>
        </div>
      </div>

      {/* Slide-over Drawer */}
      <ProtocolDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onSelectProtocol={setActiveProtocolId}
        currentProtocolId={activeProtocolId}
      />
    </div>
  );
}
