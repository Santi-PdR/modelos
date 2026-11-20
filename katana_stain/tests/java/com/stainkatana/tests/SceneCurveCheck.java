package com.stainkatana.tests;

import com.stainkatana.katana.client.SceneCurve;

public final class SceneCurveCheck {
    public static void main(String[] args) {
        if (SceneCurve.ease(-1) != 0 || SceneCurve.ease(2) != 1 || SceneCurve.ease(.5) != .5)
            throw new AssertionError("curve endpoints or clamp");
        double last = -1;
        for (int i = 0; i <= 1000; i++) {
            double v = SceneCurve.ease(i / 1000.0);
            if (v < last || v < 0 || v > 1) throw new AssertionError("non-monotonic curve");
            last = v;
        }
        if (SceneCurve.impactEnvelope(-1) != 0 || SceneCurve.impactEnvelope(0) != 0
                || SceneCurve.impactEnvelope(1) != 1 || SceneCurve.impactEnvelope(4) != 0
                || SceneCurve.impactEnvelope(Double.NaN) != 0) throw new AssertionError("impact envelope");
        for (int i = 0; i <= 400; i++) {
            double v = SceneCurve.impactEnvelope(i / 100.0);
            if (v < 0 || v > 1) throw new AssertionError("impact envelope range");
        }
        System.out.println("OK: clamped transition and bounded impact envelope");
    }
}
