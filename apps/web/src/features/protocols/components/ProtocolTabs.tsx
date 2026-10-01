import { BookOpen } from 'lucide-react';
import { getProtocol } from '../lib/protocolRegistry';

interface ProtocolTabsProps {
  activeProtocolId: string;
  onSelectTab: (protocolId: string) => void;
  onOpenDrawer: () => void;
  additionalProtocolIds?: string[];
}

export function ProtocolTabs({
  activeProtocolId,
  onSelectTab,
  onOpenDrawer,
  additionalProtocolIds = [],
}: ProtocolTabsProps) {
  // Combine active protocol with any additional ones (deduplicated)
  const tabIds = Array.from(new Set([activeProtocolId, ...additionalProtocolIds]));

  return (
    <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none" role="tablist">
      {tabIds.map((id) => {
        const prot = getProtocol(id);
        const isActive = id === activeProtocolId;
        return (
          <button
            key={id}
            id={`protocol-tab-${id}`}
            role="tab"
            aria-selected={isActive}
            onClick={() => onSelectTab(id)}
            className={`
              px-3.5 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all border
              ${
                isActive
                  ? 'bg-slate-900 border-slate-900 text-white shadow-sm'
                  : 'bg-white border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50'
              }
            `}
          >
            {prot.title.split('/')[0].trim()}
          </button>
        );
      })}

      <button
        id="open-protocols-drawer-btn"
        type="button"
        onClick={onOpenDrawer}
        className="px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center gap-1 transition-colors"
        aria-label="View all first aid protocols"
      >
        <BookOpen className="w-3.5 h-3.5" />
        <span>+ All Protocols</span>
      </button>
    </div>
  );
}
