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
        double[] shots = {40, 95, 170, 230, 300, 365};
        if (SceneCurve.shot(-1, shots) != 40 || SceneCurve.shot(200, shots) != 365 || SceneCurve.shot(400, shots) != 365)
            throw new AssertionError("shot endpoints");
        for (int i = 1; i < 2000; i++) {
            double a = SceneCurve.shot(i / 10.0, shots);
            double b = SceneCurve.shot((i + 1) / 10.0, shots);
            if (b < a || b - a > 1) throw new AssertionError("unstable shot interpolation");
        }
        System.out.println("OK: clamped transition and bounded impact envelope");
    }
}
