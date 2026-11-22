package com.capatest.client;

import com.capatest.item.CapeState;

/** Per-wearer cosmetic clock, shared by the two equipment renderers. */
final class CapeWornLight {
    /** hem is the same as halo unless this frame is asked for the lower-hem echo. */
    record Frame(CapeState.Glow glow, CapeNocturne.Gains halo, CapeNocturne.Gains hem,
                 double seconds, double dusk) {}

    private final CapeTint tint = new CapeTint();
    private final CapeNocturne exposure = new CapeNocturne();
    private Frame frame;
    private int tick;
    private float partial;

    Frame sample(CapeState mode, int block, int sky, float daylight, int age, float fraction, int wearerId,
                 CapeResponse.SpeedWake wake) {
        return sample(mode, block, sky, daylight, age, fraction, wearerId, wake, 0);
    }

    Frame sample(CapeState mode, int block, int sky, float daylight, int age, float fraction, int wearerId,
                 CapeResponse.SpeedWake wake, double heat) {
        float offset = Float.isFinite(fraction) ? Math.max(0, Math.min(1, fraction)) : 0;
        // Replays at the same or an earlier fraction are not a new pose or
        // light sample. Don't let an extra pass rewind a transition.
        if (frame == null || tick != age || offset > partial) {
            tick = age;
            partial = offset;
            double seconds = (age + (double) offset) / 20;
            var halo = exposure.sample(block, sky, daylight, seconds, wearerId, wake);
            // Keep the cached frame free of the impulse: a second pass in the
            // same tick must not rewind either clock, but may ask for the hem.
            frame = new Frame(tint.sample(mode, seconds), halo, halo, seconds, exposure.dusk());
        }
        if (!(heat > 0) || frame.dusk() == 0) return frame;
        return new Frame(frame.glow(), frame.halo(),
                CapeNocturne.hemGains(frame.dusk(), frame.halo(), frame.seconds(), wearerId, heat),
                frame.seconds(), frame.dusk());
    }
}
