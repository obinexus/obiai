import type { ObservationIn } from '../lib/types';
import type { HandRaiseEvent } from './handRaiseClassifier';

/** Structured events only — never frames. */
export function observationFromHandRaise(event: HandRaiseEvent): ObservationIn {
  return {
    modality: 'vision',
    event_type: 'participant_raised_hand',
    value: true,
    confidence: Math.round(event.confidence * 100) / 100,
    source: 'browser_hand_classifier',
  };
}
