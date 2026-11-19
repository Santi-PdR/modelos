package com.capatest.client;

import com.capatest.item.CapeState;

/** Crossfade RGB from the currently visible colour, without changing coverage. */
public final class CapeTint {
    private static final double BLEND_SECONDS = 0.18;

    private CapeState target;
    private CapeState.Glow from;
    private double changedAt;
    private double last = Double.NaN;

    public CapeState.Glow sample(CapeState mode, double seconds) {
        double dt = seconds - last;
        last = seconds;
        if (target == null || !Double.isFinite(dt) || dt < 0 || dt > .5) {
            target = mode;
            from = null;
        } else if (target != mode) {
            // When interrupted, continue from the running mix, not from an old preset.
            from = at(seconds);
            target = mode;
            changedAt = seconds;
        }
        return at(seconds);
    }

    private CapeState.Glow at(double seconds) {
        CapeState.Glow to = target.glow(seconds);
        if (from == null) return to;
        double t = (seconds - changedAt) / BLEND_SECONDS;
        if (t >= 1) {
            from = null;
            return to;
        }
        float f = (float) (t * t * (3 - 2 * t));
        return new CapeState.Glow(from.red() + f * (to.red() - from.red()),
                from.green() + f * (to.green() - from.green()),
                from.blue() + f * (to.blue() - from.blue()));
    }
}
