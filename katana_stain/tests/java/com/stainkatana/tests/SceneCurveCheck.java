package com.stainkatana.tests;

import com.stainkatana.katana.client.SceneCurve;
import com.stainkatana.katana.client.FxCurve;
import com.stainkatana.katana.client.GestureCurve;

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
        if (SceneCurve.shot(0, 30, shots) != 40 || SceneCurve.shot(30, 30, shots) != 365
                || SceneCurve.shot(15, 30, new double[]{0, 10, 20}) != 10)
            throw new AssertionError("short finisher timing");
        try { SceneCurve.shot(0, 0, shots); throw new AssertionError("invalid duration accepted"); }
        catch (IllegalArgumentException expected) { }
        for (int i = 1; i < 2000; i++) {
            double a = SceneCurve.shot(i / 10.0, shots);
            double b = SceneCurve.shot((i + 1) / 10.0, shots);
            if (b < a || b - a > 1) throw new AssertionError("unstable shot interpolation");
        }
        if (FxCurve.size(0) != .82F || FxCurve.size(1) != 1F
                || FxCurve.opacity(0) != 1F || FxCurve.opacity(1) != 0F)
            throw new AssertionError("FX curve endpoints");
        float previousSize = 0, previousOpacity = 1;
        for (int i = 0; i <= 1000; i++) {
            float phase = i / 1000F, size = FxCurve.size(phase), opacity = FxCurve.opacity(phase);
            if (!Float.isFinite(size) || !Float.isFinite(opacity) || size < previousSize
                    || opacity > previousOpacity || size < .82F || size > 1F || opacity < 0 || opacity > 1)
                throw new AssertionError("FX envelope must stay bounded and monotonic");
            previousSize = size; previousOpacity = opacity;
        }
        if (!Float.isFinite(FxCurve.size(Float.NaN)) || !Float.isFinite(FxCurve.opacity(Float.NaN)))
            throw new AssertionError("FX curve nonfinite input");
        if (GestureCurve.contact(-1) != 0F || GestureCurve.contact(3) != 0F
                || GestureCurve.contact(12) != 1F || GestureCurve.contact(38) != 1F
                || GestureCurve.contact(52) != 0F || GestureCurve.contact(100) != 0F)
            throw new AssertionError("Blood gesture contact boundaries");
        float previousContact = 0F;
        for (int t = 0; t <= 60; t++) {
            float value = GestureCurve.contact(t);
            if (value < 0F || value > 1F || (t <= 12 && value < previousContact)
                    || (t >= 38 && value > previousContact))
                throw new AssertionError("Blood gesture contact envelope");
            previousContact = value;
        }
        if (GestureCurve.contact(Float.NaN) != 0F || GestureCurve.contact(Float.POSITIVE_INFINITY) != 0F)
            throw new AssertionError("Blood gesture nonfinite input");
        previousContact = 0F;
        for (int i = 0; i <= 6000; i++) {
            float t = i / 100F, value = GestureCurve.contact(t);
            if (!Float.isFinite(value) || value < 0F || value > 1F
                    || (t <= 12F && value < previousContact) || (t >= 38F && value > previousContact)
                    || Math.abs(value - previousContact) > .01F)
                throw new AssertionError("Blood gesture fractional interpolation");
            previousContact = value;
        }
        if (!(GestureCurve.contact(5.5F) > GestureCurve.contact(5F)
                && GestureCurve.contact(5.5F) < GestureCurve.contact(6F)))
            throw new AssertionError("Blood gesture must interpolate between ticks");
        System.out.println("OK: clamped transition, impact, FX and blood gesture envelopes");
    }
}
