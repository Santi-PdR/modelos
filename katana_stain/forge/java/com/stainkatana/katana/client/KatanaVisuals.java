package com.stainkatana.katana.client;

import com.stainkatana.katana.KatanaParticles;
import com.stainkatana.katana.KatanaVisualStyle;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;

/** Server-authoritative impact location; particles never decide damage. */
public final class KatanaVisuals {
    private KatanaVisuals() { }
    public static void spawn(int entityId, double x, double y, double z, float yaw, int style, boolean leftHanded) {
        var mc = Minecraft.getInstance();
        var level = mc.level;
        if (level == null || !KatanaVisualStyle.valid(style) || !Double.isFinite(x) || !Double.isFinite(y)
                || !Double.isFinite(z) || !Float.isFinite(yaw)) return;
        if (style == KatanaVisualStyle.DAGGER) {
            DaggerVisuals.spawn(entityId, x, y, z);
            return;
        }
        boolean localCaster = mc.player != null && mc.player.getId() == entityId;
        if (style == KatanaVisualStyle.BLOOD_FLASH) {
            if (localCaster) KatanaHud.bloodFlash();
            return;
        }
        if (localCaster && (style == KatanaVisualStyle.ULTIMATE_CUT || style == KatanaVisualStyle.ULTIMATE_CROSS
                || style == KatanaVisualStyle.ULTIMATE_FINAL || style == KatanaVisualStyle.FINISHER
                || style == KatanaVisualStyle.SCENE_FOCUS)) {
            if (style == KatanaVisualStyle.SCENE_FOCUS) KatanaScene.focus(x, y, z);
            else KatanaScene.impact(style == KatanaVisualStyle.ULTIMATE_CROSS, leftHanded, x, y, z);
        }
        // Focus is a camera cue, not a premature hit effect.
        if (style == KatanaVisualStyle.SCENE_FOCUS) return;
        float sign = leftHanded ? -1 : 1;
        if (style == KatanaVisualStyle.SWING || style == KatanaVisualStyle.ULTIMATE_CROSS) {
            float visualYaw = yaw + ((style == KatanaVisualStyle.ULTIMATE_CROSS) ^ leftHanded ? 180F : 0F);
            level.addParticle(KatanaParticles.SLASH.get(), x, y, z, visualYaw, 55, 0);
            level.addParticle(KatanaParticles.PULSE.get(), x, y, z, visualYaw, 75, sign * 20);
        } else if (style == KatanaVisualStyle.ULTIMATE_CUT || style == KatanaVisualStyle.ULTIMATE_FINAL) {
            level.addParticle(KatanaParticles.SLASH.get(), x, y, z, yaw, 55, -sign * 30);
            level.addParticle(KatanaParticles.PULSE.get(), x, y, z, yaw, 90, sign * 25);
            if (style == KatanaVisualStyle.ULTIMATE_FINAL) {
                level.addParticle(KatanaParticles.SLASH.get(), x, y, z, yaw + 180, 70, sign * 35);
                level.addParticle(KatanaParticles.RING.get(), x, y - .65, z, yaw, 0, 0);
                sparks(level, x, y, z, yaw, 8);
            }
        } else if (style == KatanaVisualStyle.BLOOD_BIND) {
            // An expanding, grounded ring and a vertical glyph distinguish a bind
            // from an ordinary cut, using credited Better Combat Particle frames.
            level.addParticle(KatanaParticles.RING.get(), x, y - .65, z, yaw, 0, 0);
            level.addParticle(KatanaParticles.PULSE.get(), x, y, z, yaw, 90, 0);
            sparks(level, x, y, z, yaw, 5);
        } else if (style == KatanaVisualStyle.FINISHER) {
            level.addParticle(KatanaParticles.SLASH.get(), x, y, z, yaw, 65, sign * 35);
            level.addParticle(KatanaParticles.PULSE.get(), x, y, z, yaw + 180, 80, -sign * 30);
            level.addParticle(KatanaParticles.RING.get(), x, y, z, yaw, 70, sign * 15);
            sparks(level, x, y, z, yaw, 8);
        } else if (style == KatanaVisualStyle.HIT) {
            sparks(level, x, y, z, yaw, 3);
        }
    }

    /** Bounded client-only radial burst using the existing credited blood sprite. */
    private static void sparks(ClientLevel level, double x, double y, double z, float yaw, int count) {
        for (int i = 0; i < count; i++) {
            double a = Math.toRadians(yaw) + Math.PI * 2 * i / count;
            double vx = Math.cos(a) * .065, vz = Math.sin(a) * .065;
            level.addParticle(KatanaParticles.SHARD.get(), x + vx, y, z + vz, vx, .035 + .012 * (i % 3), vz);
        }
    }
}
