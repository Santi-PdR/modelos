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
        System.out.println("OK: clamped monotonic Cinema Scope transition");
    }
}
