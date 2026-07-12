import { AgentActionPanel } from './components/AgentActionPanel';
import { BiasAuditPanel, SafetyAuditPanel } from './components/AuditPanels';
import { BeliefPanel } from './components/BeliefPanel';
import { EvidencePanel } from './components/EvidencePanel';
import { SemanticPathPanel } from './components/SemanticPathPanel';
import { TranscriptPanel } from './components/TranscriptPanel';
import { UHeader } from './components/UHeader';
import { VideoRoom } from './components/VideoRoom';
import { useAppStore } from './store';

export default function App() {
  const lastError = useAppStore((s) => s.lastError);

  return (
    <div className="app-shell">
      <UHeader />
      {lastError && (
        <div className="error-banner" role="alert">
          {lastError}
        </div>
      )}
      <main className="main-grid">
        <div className="column">
          <VideoRoom />
          <TranscriptPanel />
        </div>
        <div className="column">
          <BeliefPanel />
          <EvidencePanel />
          <SemanticPathPanel />
          <BiasAuditPanel />
          <SafetyAuditPanel />
          <AgentActionPanel />
        </div>
      </main>
    </div>
  );
}
