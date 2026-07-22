/** TypeScript mirrors of the backend Pydantic models and WS event envelopes. */

export type TruthState = 'YES' | 'NO' | 'MAYBE';

export type Modality = 'vision' | 'chat' | 'system';

export interface Observation {
  observation_id: string;
  session_id: string;
  modality: Modality;
  event_type: string;
  value: boolean | number | string;
  confidence: number;
  source: string;
  timestamp: string;
}

export interface ObservationIn {
  modality: Modality;
  event_type: string;
  value: boolean | number | string;
  confidence: number;
  source: string;
}

export interface Provenance {
  module: string;
  version: string;
}

/** A speech-recognition result. Recognition runs client-side (Web Speech
 * API); only recognized text ever crosses the wire, never audio. */
export interface TranscriptSegment {
  text: string;
  start_ms: number;
  end_ms: number;
  confidence: number;
  final: boolean;
}

export interface Evidence {
  evidence_id: string;
  proposition: string;
  value: boolean;
  confidence: number;
  source_observation_id: string | null;
  provenance: Provenance;
}

export interface BiasReport {
  protected_paths: string[][];
  parity_gap: number | null;
  passed: boolean;
  notes: string[];
}

export interface SafetyAudit {
  passed: boolean;
  policy_flags: string[];
}

export interface Action {
  name: string;
  parameters: Record<string, unknown>;
  rationale: string;
}

export interface UModelProfile {
  model_id: string;
  version: string;
  display_name: string;
  training_state: string;
  artifact_name: string;
  loaded_from: string | null;
  data_manifest_ref: string;
  source_count: number;
  concept_count: number;
  separation_contract: string[];
}

/** Status of the trained (LoRA-adapter) UAI model, from GET /model/status.
 * Separate from UModelProfile above, which describes the rule-based seeded
 * UAgenticModel, not the trained language model. */
export interface UAIModelStatus {
  artifact_root?: string;
  current_run_id: string | null;
  current_status: string | null;
  loaded_run_id: string | null;
  loaded: boolean;
  loaded_device?: string | null;
  max_new_tokens?: number;
}

export interface Decision {
  decision_id: string;
  session_id: string;
  proposition: string;
  probability: number;
  uncertainty: number;
  state: TruthState;
  evidence: Evidence[];
  ontological_concepts: string[];
  semantic_path: string[];
  bias_audit: BiasReport;
  safety_audit: SafetyAudit;
  action: Action | null;
  explanation: string[];
  created_at: string;
}

// --- WebSocket events -------------------------------------------------------

export type ClientEvent =
  | { type: 'session.start' }
  | { type: 'session.end' }
  | { type: 'chat.message'; text: string }
  | { type: 'observation.submit'; observation: ObservationIn }
  | { type: 'clarification.answer'; decision_id: string; answer: string }
  | { type: 'transcript.partial'; segment: TranscriptSegment }
  | { type: 'transcript.final'; segment: TranscriptSegment };

export type ServerEvent =
  | { type: 'session.ready'; session_id: string }
  | { type: 'observation.created'; observation: Observation }
  | { type: 'reasoning.started'; observation_id: string }
  | { type: 'decision.created'; decision: Decision }
  | {
      type: 'agent.thinking';
      message: string;
      model_run_id: string | null;
    }
  | {
      type: 'agent.message';
      text: string;
      /** Which layer produced `text`: 'governance_pipeline', 'trained_uai',
       * 'seeded_uagentic', 'transcript_confidence_guard', or 'static_greeting'.
       * Never 'trained_uai' unless adapter_loaded is also true. */
      response_source: string;
      adapter_loaded: boolean;
      model_run_id: string | null;
    }
  | {
      type: 'audit.created';
      decision_id: string;
      bias_audit: BiasReport;
      safety_audit: SafetyAudit;
    }
  | { type: 'transcript.partial'; segment: TranscriptSegment }
  | { type: 'transcript.final'; segment: TranscriptSegment }
  | { type: 'error'; message: string; code: string };

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

/** Visible assistant states — always rendered as text, never colour alone. */
export type UState =
  | 'idle'
  | 'requesting_permission'
  | 'connecting'
  | 'listening'
  | 'observing'
  | 'reasoning'
  | 'thinking'
  | 'speaking'
  | 'waiting_clarification'
  | 'disconnected'
  | 'error';

export const U_STATE_LABELS: Record<UState, string> = {
  idle: 'Idle',
  requesting_permission: 'Requesting permission',
  connecting: 'Connecting',
  listening: 'Listening',
  observing: 'Observing',
  reasoning: 'Reasoning',
  thinking: 'Thinking',
  speaking: 'Speaking',
  waiting_clarification: 'Waiting for clarification',
  disconnected: 'Disconnected',
  error: 'Error',
};
