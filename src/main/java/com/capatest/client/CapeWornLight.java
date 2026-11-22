package com.capatest.client;

import com.capatest.item.CapeState;

/** Per-wearer cosmetic clock, shared by the two equipment renderers. */
final class CapeWornLight {
    record Frame(CapeState.Glow glow, CapeNocturne.Gains halo) {}

    private final CapeTint tint = new CapeTint();
    private final CapeNocturne exposure = new CapeNocturne();
    private Frame frame;
    private int tick;
    private float partial;

    Frame sample(CapeState mode, int block, int sky, float daylight, int age, float fraction, int wearerId,
                 CapeResponse.SpeedWake wake) {
        float offset = Float.isFinite(fraction) ? Math.max(0, Math.min(1, fraction)) : 0;
        // Replays at the same or an earlier fraction are not a new pose or
        // light sample. Don't let an extra pass rewind a transition.
        if (frame != null && tick == age && offset <= partial) return frame;
        tick = age;
        partial = offset;
        double seconds = (age + (double) offset) / 20;
        frame = new Frame(tint.sample(mode, seconds), exposure.sample(block, sky, daylight, seconds, wearerId, wake));
        return frame;
    }
}
