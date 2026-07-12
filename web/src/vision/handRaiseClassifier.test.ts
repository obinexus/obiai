import { describe, expect, it } from 'vitest';

import {
  DEFAULT_HAND_RAISE_CONFIG,
  HandFrame,
  HandLandmark,
  HandRaiseClassifier,
  isRaisedPose,
} from './handRaiseClassifier';

/** Synthetic 21-landmark hand. Fingertips [4,8,12,16,20] get `tipY`. */
function hand(wristY: number, tipY: number, score = 0.95, raisedTips = 5): HandFrame {
  const landmarks: HandLandmark[] = Array.from({ length: 21 }, () => ({ x: 0.5, y: 0.6 }));
  landmarks[0] = { x: 0.5, y: wristY };
  const tips = [4, 8, 12, 16, 20];
  tips.forEach((tip, i) => {
    landmarks[tip] = { x: 0.5, y: i < raisedTips ? tipY : wristY + 0.05 };
  });
  return { landmarks, score };
}

const RAISED = () => hand(0.9, 0.2);
const LOWERED = () => hand(0.3, 0.9); // fingertips below wrist

describe('isRaisedPose', () => {
  it('detects wrist below fingertip majority', () => {
    expect(isRaisedPose(RAISED().landmarks, 3)).toBe(true);
    expect(isRaisedPose(LOWERED().landmarks, 3)).toBe(false);
  });

  it('respects the majority threshold', () => {
    const twoTips = hand(0.9, 0.2, 0.95, 2);
    expect(isRaisedPose(twoTips.landmarks, 3)).toBe(false);
    const threeTips = hand(0.9, 0.2, 0.95, 3);
    expect(isRaisedPose(threeTips.landmarks, 3)).toBe(true);
  });
});

describe('HandRaiseClassifier', () => {
  it('emits only after the sustain window', () => {
    const classifier = new HandRaiseClassifier();
    expect(classifier.update(RAISED(), 0).event).toBeNull();
    expect(classifier.update(RAISED(), 300).event).toBeNull();
    const tick = classifier.update(RAISED(), 600);
    expect(tick.event).not.toBeNull();
    expect(tick.event?.confidence).toBeCloseTo(0.95, 5);
  });

  it('a dropped pose resets the sustain timer', () => {
    const classifier = new HandRaiseClassifier();
    classifier.update(RAISED(), 0);
    classifier.update(LOWERED(), 300); // reset
    classifier.update(RAISED(), 400);
    expect(classifier.update(RAISED(), 700).event).toBeNull(); // only 300ms sustained
    expect(classifier.update(RAISED(), 950).event).not.toBeNull();
  });

  it('a lost hand resets the sustain timer and reports tracking inactive', () => {
    const classifier = new HandRaiseClassifier();
    classifier.update(RAISED(), 0);
    const lost = classifier.update(null, 300);
    expect(lost.trackingActive).toBe(false);
    classifier.update(RAISED(), 400);
    expect(classifier.update(RAISED(), 800).event).toBeNull();
  });

  it('low confidence never emits', () => {
    const classifier = new HandRaiseClassifier();
    const weak = hand(0.9, 0.2, 0.5);
    classifier.update(weak, 0);
    classifier.update(weak, 400);
    const tick = classifier.update(weak, 900);
    expect(tick.raisedNow).toBe(false);
    expect(tick.event).toBeNull();
  });

  it('cooldown gates re-emission, then re-arms', () => {
    const classifier = new HandRaiseClassifier();
    classifier.update(RAISED(), 0);
    expect(classifier.update(RAISED(), 600).event).not.toBeNull();

    // Sustained again immediately: still inside the 4000ms cooldown.
    classifier.update(RAISED(), 700);
    expect(classifier.update(RAISED(), 1400).event).toBeNull();
    expect(classifier.update(RAISED(), 4500).event).toBeNull(); // sustain reset each denied tick? no:
    // cooldown ended at 4600; the ongoing sustain started at 700, so the next
    // update past the cooldown emits.
    const tick = classifier.update(RAISED(), 4700);
    expect(tick.event).not.toBeNull();
  });

  it('averages confidence across the sustained raise', () => {
    const classifier = new HandRaiseClassifier();
    classifier.update(hand(0.9, 0.2, 0.8), 0);
    classifier.update(hand(0.9, 0.2, 0.9), 300);
    const tick = classifier.update(hand(0.9, 0.2, 1.0), 600);
    expect(tick.event?.confidence).toBeCloseTo(0.9, 5);
  });

  it('default config matches the backend allowlist expectations', () => {
    expect(DEFAULT_HAND_RAISE_CONFIG.sustainMs).toBe(500);
    expect(DEFAULT_HAND_RAISE_CONFIG.minConfidence).toBe(0.8);
    expect(DEFAULT_HAND_RAISE_CONFIG.cooldownMs).toBe(4000);
  });
});
