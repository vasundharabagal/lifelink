import { useState } from 'react';
import { X, Search, BookOpen, ChevronRight } from 'lucide-react';
import { getAllProtocols, Protocol } from '../lib/protocolRegistry';

interface ProtocolDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectProtocol: (protocolId: string) => void;
  currentProtocolId?: string;
}

export function ProtocolDrawer({
  isOpen,
  onClose,
  onSelectProtocol,
  currentProtocolId,
}: ProtocolDrawerProps) {
  const [search, setSearch] = useState('');
  const allProtocols = getAllProtocols();

  if (!isOpen) return null;

  const filtered = allProtocols.filter(
    (p) =>
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      p.id.toLowerCase().includes(search.toLowerCase()) ||
      p.applies_to.some((a) => a.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-labelledby="protocol-drawer-title"
    >
      <div
        id="protocol-drawer"
        className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-200"
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-slate-700" />
            <h2 id="protocol-drawer-title" className="text-base font-bold text-slate-900">
              First Aid Protocols
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            aria-label="Close protocols drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Input */}
        <div className="p-4 border-b border-slate-100">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search guidance (CPR, bleeding, choking)…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-xl text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
          </div>
        </div>

        {/* Protocol List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {filtered.map((prot: Protocol) => {
            const isSelected = prot.id === currentProtocolId;
            return (
              <button
                key={prot.id}
                id={`drawer-protocol-${prot.id}`}
                onClick={() => {
                  onSelectProtocol(prot.id);
                  onClose();
                }}
                className={`
                  w-full text-left p-3.5 rounded-2xl border transition-all flex items-center justify-between
                  ${
                    isSelected
                      ? 'border-slate-900 bg-slate-50 ring-1 ring-slate-900'
                      : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                  }
                `}
              >
                <div>
                  <p className="text-sm font-bold text-slate-900">{prot.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {prot.steps.length} steps · {prot.source_citation.split(';')[0]}
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0 ml-2" />
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 text-center">
          100% offline available · No network connection required
        </div>
      </div>
    </div>
  );
}
