import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { Activity, Radio, XCircle, ArrowLeft } from 'lucide-react';
import { api } from '../../../lib/api';
import { ProtocolViewer } from '../../protocols/components/ProtocolViewer';
import { CancelModal } from '../components/CancelModal';
import { Call112Button } from '../../../components/layout/Call112Button';

interface EmergencyData {
  id: string;
  status: string;
  priority: string;
  created_at: string;
  protocol_id?: string;
  lat: number;
  lng: number;
}

/**
 * Placeholder view for active emergency (/emergency/:id).
 * Bridges Phase 6 to Phase 8 live tracking while delivering immediate offline first-aid protocols,
 * status feedback, Call 112 access, and emergency cancellation.
 */
export function LiveEmergencyPlaceholder() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const isObserver = searchParams.get('mode') === 'observer';

  const [emergency, setEmergency] = useState<EmergencyData | null>(null);
  const [isCancelOpen, setIsCancelOpen] = useState(false);

  useEffect(() => {
    if (!id) return;
    api
      .get<EmergencyData>(`/api/v1/emergencies/${id}`)
      .then((data) => setEmergency(data))
      .catch(() => {
        // Fallback placeholder data if backend offline or mocked
        setEmergency({
          id,
          status: 'SEARCHING_RESPONDERS',
          priority: 'P1',
          created_at: new Date().toISOString(),
          protocol_id: 'PROT_UNRESPONSIVE',
          lat: 19.076,
          lng: 72.8777,
        });
      });
  }, [id]);

  const shortId = id ? id.slice(0, 8) : 'active';
  const statusLabel = emergency?.status?.replace(/_/g, ' ') || 'SEARCHING RESPONDERS';
  const priority = emergency?.priority || 'P1';

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col pb-36">
      {/* Top Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 sticky top-0 z-30 flex items-center justify-between">
        <Link
          to="/sos"
          className="flex items-center gap-1.5 text-sm font-semibold text-slate-700 hover:text-slate-900 min-h-[44px] px-2 -ml-2 rounded-lg"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Home</span>
        </Link>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-pulse" />
          <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
            Incident #{shortId}
          </span>
        </div>
        {!isObserver && (
          <button
            id="open-cancel-modal-btn"
            onClick={() => setIsCancelOpen(true)}
            className="flex items-center gap-1 text-xs font-bold text-red-600 hover:text-red-700"
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>Cancel</span>
          </button>
        )}
      </div>

      <div className="max-w-md mx-auto w-full px-4 pt-4 flex flex-col gap-4">
        {/* Status Card */}
        <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio className="w-4 h-4 text-red-600 animate-pulse" />
              <span className="text-xs font-black uppercase tracking-wider text-red-600">
                {statusLabel}
              </span>
            </div>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full uppercase bg-red-50 text-red-800 border border-red-200">
              {priority}
            </span>
          </div>

          <div>
            <h1 className="text-xl font-black text-slate-900">
              Emergency Response Active
            </h1>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              We are contacting nearby verified responders and official ambulance services. Immediate guidance is provided below while help is en route.
            </p>
          </div>

          {isObserver && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-2.5 text-xs text-blue-900 font-medium">
              You joined this incident in observer mode to avoid responder fragmentation.
            </div>
          )}
        </div>

        {/* First Aid Protocol Guidance Viewer */}
        <div>
          <div className="flex items-center gap-2 mb-2 px-1">
            <Activity className="w-4 h-4 text-slate-700" />
            <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Immediate Patient Care Guidance
            </h2>
          </div>
          <ProtocolViewer initialProtocolId={emergency?.protocol_id || 'PROT_UNRESPONSIVE'} />
        </div>
      </div>

      {/* Cancellation Modal */}
      {id && (
        <CancelModal
          isOpen={isCancelOpen}
          emergencyId={id}
          onClose={() => setIsCancelOpen(false)}
        />
      )}

      <Call112Button />
    </div>
  );
}
