package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.core.animation.EasingType;
import software.bernie.geckolib.core.keyframe.Keyframe;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Read the authored rotations from GeckoLib's baked asset, but seek them explicitly. */
final class CapeWornClips {
    private final GeoBone[] bones;
    private final Clip[] clips = new Clip[CapeWornMotion.MODES.length];
    private final float[] pose;

    private record Rotation(Curve x, Curve y, Curve z) {}
    private record Clip(double length, Rotation[] rotations) {}

    CapeWornClips(CapaArmorModel model, CapaDeteriorerItem item, List<GeoBone> parts) {
        bones = parts.toArray(GeoBone[]::new);
        pose = new float[bones.length * 3];
        Map<String, Integer> index = new HashMap<>();
        for (int i = 0; i < bones.length; i++) index.put(bones[i].getName(), i);
        for (CapeState mode : CapeWornMotion.MODES) {
            var baked = model.getAnimation(item, mode.clip());
            if (baked == null || !(baked.length() > 0) || !Double.isFinite(baked.length()))
                throw new IllegalArgumentException("Invalid worn clip: " + mode.clip());
            var rotations = new Rotation[bones.length];
            for (var part : baked.boneAnimations()) {
                var i = index.get(part.boneName());
                if (i == null) continue;
                var keys = part.rotationKeyFrames();
                rotations[i] = new Rotation(Curve.of(keys.xKeyframes()), Curve.of(keys.yKeyframes()), Curve.of(keys.zKeyframes()));
            }
            clips[mode.ordinal()] = new Clip(baked.length(), rotations);
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
                Rotation r = clip.rotations()[i];
                if (r == null) continue;
                pose[n] += (float) (r.x().at(tick) * weight);
                pose[n + 1] += (float) (r.y().at(tick) * weight);
                pose[n + 2] += (float) (r.z().at(tick) * weight);
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

    private record Curve(double[] endTicks, float[] start, float[] end) {
        static Curve of(List<? extends Keyframe<?>> keys) {
            var times = new double[keys.size()];
            var start = new float[keys.size()];
            var end = new float[keys.size()];
            double time = 0;
            for (int i = 0; i < keys.size(); i++) {
                var key = keys.get(i);
                if (key.easingType() != EasingType.LINEAR || key.length() < 0
                        || !(key.startValue() instanceof com.eliotlash.mclib.math.Constant)
                        || !(key.endValue() instanceof com.eliotlash.mclib.math.Constant)) {
                    throw new IllegalArgumentException("The custom worn asset needs GeckoLib's default sampler");
                }
                times[i] = time += key.length();
                start[i] = (float) key.startValue().get();
                end[i] = (float) key.endValue().get();
            }
            return new Curve(times, start, end);
        }

        double at(double tick) {
            if (endTicks.length == 0) return 0;
            int i = Arrays.binarySearch(endTicks, tick);
            if (i >= 0) return end[i];
            i = -i - 1;
            if (i >= endTicks.length) return end[end.length - 1];
            double before = i == 0 ? 0 : endTicks[i - 1];
            return start[i] + (end[i] - start[i]) * (tick - before) / (endTicks[i] - before);
        }
    }
}
