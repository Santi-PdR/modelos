package com.capatest.client;

import com.capatest.item.CapeState;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.cache.object.GeoBone;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;

/** Seek the numeric, periodic rotations in the active worn animation resource. */
final class CapeWornClips {
    private final GeoBone[] bones;
    private final Clip[] clips = new Clip[CapeWornMotion.MODES.length];
    private final float[] pose;

    private record Clip(double length, Curve[] rotations) {}

    CapeWornClips(ResourceLocation resource, List<GeoBone> parts) throws IOException {
        bones = parts.toArray(GeoBone[]::new);
        pose = new float[bones.length * 3];
        JsonObject library;
        try (var reader = Minecraft.getInstance().getResourceManager().openAsReader(resource)) {
            library = object(JsonParser.parseReader(reader).getAsJsonObject().get("animations"));
        }
        for (CapeState mode : CapeWornMotion.MODES) {
            var clip = object(library.get(mode.clip()));
            double length = number(clip.get("animation_length")) * 20;
            if (!(length > 0) || !clip.has("loop") || !clip.get("loop").isJsonPrimitive()
                    || !clip.getAsJsonPrimitive("loop").isBoolean() || !clip.get("loop").getAsBoolean())
                throw unsupported();
            var channels = object(clip.get("bones"));
            var rotations = new Curve[bones.length];
            for (int i = 0; i < bones.length; ++i) {
                String name = bones[i].getName();
                if (!channels.has(name)) continue;
                var track = object(channels.get(name));
                if (track.size() != 1) throw unsupported();
                rotations[i] = Curve.read(object(track.get("rotation")), length);
            }
            clips[mode.ordinal()] = new Clip(length, rotations);
        }
    }

    void apply(CapeWornMotion motion) {
        Arrays.fill(pose, 0);
        for (CapeState mode : CapeWornMotion.MODES) {
            double weight = motion.weight(mode);
            if (weight <= 0) continue;
            Clip clip = clips[mode.ordinal()];
            double tick = motion.phase(mode, clip.length()) * clip.length();
            for (int i = 0, n = 0; i < bones.length; i++, n += 3) {
                Curve r = clip.rotations()[i];
                if (r != null) r.add(tick, weight, pose, n);
            }
        }
        // Always write from the bind pose. No addition to a bone left over
        // from the previous wearer, render pass, or earlier in this frame.
        for (int i = 0, n = 0; i < bones.length; i++, n += 3) {
            GeoBone b = bones[i];
            var base = b.getInitialSnapshot();
            b.updateRotation(base.getRotX() + pose[n], base.getRotY() + pose[n+1], base.getRotZ() + pose[n+2]);
        }
    }

    private record Curve(double[] ticks, float[] values) {
        static Curve read(JsonObject keys, double duration) {
            int size = keys.size();
            if (size < 2) throw unsupported();
            var times = new double[size];
            var values = new float[3 * size];
            int i = 0;
            for (var entry : keys.entrySet()) {
                double t = Double.parseDouble(entry.getKey()) * 20;
                if (!Double.isFinite(t) || (i == 0 ? t != 0 : t <= times[i - 1])) throw unsupported();
                times[i] = t;
                var key = object(entry.getValue());
                if (!key.has("easing") || !"linear".equals(key.get("easing").getAsString())
                        || !key.has("vector") || !(key.get("vector") instanceof JsonArray v) || v.size() != 3)
                    throw unsupported();
                // Same coordinate convention as GeckoLib's numeric keys.
                for (int axis = 0; axis < 3; ++axis)
                    values[3 * i + axis] = (float) Math.toRadians((axis == 2 ? 1 : -1) * number(v.get(axis)));
                i++;
            }
            if (Math.abs(times[size-1] - duration) > 1e-8) throw unsupported();
            for (int axis = 0; axis < 3; ++axis)
                if (values[axis] != values[3*(size-1)+axis]) throw unsupported();
            return new Curve(times, values);
        }

        void add(double tick, double weight, float[] pose, int base) {
            int right = Arrays.binarySearch(ticks, tick);
            double f = 0;
            if (right < 0) {
                right = Math.min(ticks.length - 1, -right - 1);
                f = (ticks[right] - tick) / (ticks[right] - ticks[right-1]);
            }
            int left = f == 0 ? right : right - 1;
            for (int a = 0; a < 3; ++a) {
                float end = values[right * 3 + a];
                pose[base+a] += (float) ((end + (values[left*3+a] - end) * f) * weight);
            }
        }
    }

    private static JsonObject object(JsonElement element) {
        if (element instanceof JsonObject obj) return obj;
        throw unsupported();
    }

    private static double number(JsonElement element) {
        if (element != null && element.isJsonPrimitive() && element.getAsJsonPrimitive().isNumber()) {
            double n = element.getAsDouble();
            if (Double.isFinite(n)) return n;
        }
        throw unsupported();
    }

    private static IllegalArgumentException unsupported() {
        return new IllegalArgumentException("Expected periodic numeric rotations in the worn clip");
    }
}
