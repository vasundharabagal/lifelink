import { Link } from 'react-router-dom';
import { ArrowLeft, BookOpen } from 'lucide-react';
import { ProtocolViewer } from '../components/ProtocolViewer';
import { Call112Button } from '../../../components/layout/Call112Button';

export function ProtocolsPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col pb-36">
      <div className="bg-white border-b border-slate-200 px-4 py-3 sticky top-0 z-30 flex items-center justify-between">
        <Link
          to="/"
          className="flex items-center gap-1.5 text-sm font-semibold text-slate-700 hover:text-slate-900 min-h-[44px] px-2 -ml-2 rounded-lg"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Home</span>
        </Link>
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-slate-800" />
          <h1 className="text-sm font-bold text-slate-900">First Aid Protocols</h1>
        </div>
        <div className="w-12" />
      </div>

      <div className="max-w-md mx-auto w-full px-4 pt-4 flex flex-col gap-4">
        <ProtocolViewer initialProtocolId="PROT_UNRESPONSIVE" />
      </div>

      <Call112Button />
    </div>
  );
}
