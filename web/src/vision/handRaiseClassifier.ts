/**
 * Pure hand-raise classifier: a small state machine over per-frame hand
 * landmarks. No DOM, no MediaPipe — fully unit-testable.
 *
 * Rule (as specified):
 *  - hand landmarks detected;
 *  - the wrist sits below the majority of fingertip landmarks in screen
 *    coordinates (y grows downward, so tip.y < wrist.y);
 *  - the pose is sustained for at least `sustainMs`;
 *  - detection confidence >= `minConfidence`;
 *  - after emitting, a cooldown gates re-emission.
 */

export interface HandLandmark {
  x: number;
  y: number;
  z?: number;
}

export interface HandFrame {
  /** 21 normalized landmarks (MediaPipe Hands order; index 0 = wrist). */
  landmarks: HandLandmark[];
  /** Detection/handedness confidence in [0, 1]. */
  score: number;
}

export interface HandRaiseConfig {
  sustainMs: number;
  minConfidence: number;
  cooldownMs: number;
  /** How many of the five fingertips must sit above the wrist. */
  tipMajority: number;
}

export const DEFAULT_HAND_RAISE_CONFIG: HandRaiseConfig = {
  sustainMs: 500,
  minConfidence: 0.8,
  cooldownMs: 4000,
  tipMajority: 3,
};

export interface HandRaiseEvent {
  /** Mean detection confidence across the sustained raise. */
  confidence: number;
}

export interface ClassifierTick {
  trackingActive: boolean;
  raisedNow: boolean;
  confidence: number;
  sustainedMs: number;
  event: HandRaiseEvent | null;
}

const WRIST = 0;
const FINGERTIPS = [4, 8, 12, 16, 20];
const LANDMARK_COUNT = 21;

export function isRaisedPose(landmarks: HandLandmark[], tipMajority: number): boolean {
  if (landmarks.length < LANDMARK_COUNT) return false;
  const wristY = landmarks[WRIST].y;
  const tipsAboveWrist = FINGERTIPS.filter((tip) => landmarks[tip].y < wristY).length;
  return tipsAboveWrist >= tipMajority;
}

export class HandRaiseClassifier {
  private raiseStartMs: number | null = null;
  private lastEmitMs: number | null = null;
  private confidenceSum = 0;
  private confidenceCount = 0;

  constructor(private readonly config: HandRaiseConfig = DEFAULT_HAND_RAISE_CONFIG) {}

  update(frame: HandFrame | null, nowMs: number): ClassifierTick {
    if (frame === null || frame.landmarks.length < LANDMARK_COUNT) {
      this.resetSustain();
      return { trackingActive: false, raisedNow: false, confidence: 0, sustainedMs: 0, event: null };
    }

    const raisedPose = isRaisedPose(frame.landmarks, this.config.tipMajority);
    const confident = frame.score >= this.config.minConfidence;
    const raisedNow = raisedPose && confident;

    if (!raisedNow) {
      this.resetSustain();
      return {
        trackingActive: true,
        raisedNow: false,
        confidence: frame.score,
        sustainedMs: 0,
        event: null,
      };
    }

    if (this.raiseStartMs === null) {
      this.raiseStartMs = nowMs;
      this.confidenceSum = 0;
      this.confidenceCount = 0;
    }
    this.confidenceSum += frame.score;
    this.confidenceCount += 1;
    const sustainedMs = nowMs - this.raiseStartMs;

    const inCooldown =
      this.lastEmitMs !== null && nowMs - this.lastEmitMs < this.config.cooldownMs;

    let event: HandRaiseEvent | null = null;
    if (sustainedMs >= this.config.sustainMs && !inCooldown) {
      event = { confidence: this.confidenceSum / this.confidenceCount };
      this.lastEmitMs = nowMs;
      // Require a fresh sustained raise before the next emission.
      this.resetSustain();
    }

    return {
      trackingActive: true,
      raisedNow: true,
      confidence: frame.score,
      sustainedMs: event ? 0 : sustainedMs,
      event,
    };
  }

  private resetSustain(): void {
    this.raiseStartMs = null;
    this.confidenceSum = 0;
    this.confidenceCount = 0;
  }
}
