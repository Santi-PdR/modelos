package com.stainkatana.katana.client;

import com.stainkatana.katana.KatanaParticles;
import net.minecraft.client.Minecraft;

/** Server-authoritative impact location; angles are used by the particle renderer, not as velocity. */
public final class KatanaVisuals {
    private KatanaVisuals() { }
    public static void spawn(int entityId, double x, double y, double z, float yaw, int style, boolean leftHanded) {
        var level = Minecraft.getInstance().level;
        if (level == null || style < 0 || style > 5 || !Double.isFinite(x) || !Double.isFinite(y)
                || !Double.isFinite(z) || !Float.isFinite(yaw)) return;
        if (style == 5) {
            DaggerVisuals.spawn(entityId, x, y, z);
            return;
        }
        if (style == 4) {
            if (Minecraft.getInstance().player != null && Minecraft.getInstance().player.getId() == entityId)
                KatanaHud.bloodFlash();
            return;
        }
        if ((style == 1 || style == 3) && Minecraft.getInstance().player != null
                && Minecraft.getInstance().player.getId() == entityId) KatanaScene.impact(style == 3, leftHanded);
        if (style == 0 || style == 3) {
            // The follow-up is the opposite Better Combat stroke. Turn the textured
            // plane 180 degrees for that stroke, and invert again for left-handers.
            float visualYaw = yaw + ((style == 3) ^ leftHanded ? 180F : 0F);
            // Tilt the world-oriented plane toward the viewer: at zero pitch it
            // becomes nearly invisible when viewed from behind at eye level.
            level.addParticle(KatanaParticles.SLASH.get(), x, y, z, visualYaw, 55, 0);
        } else if (style == 1) {
            // First stroke of the ultimate, angled across the body.
            level.addParticle(KatanaParticles.PULSE.get(), x, y, z, yaw, 90, leftHanded ? -25 : 25);
        } else {
            // Paralysis feedback around the marked target.
            level.addParticle(KatanaParticles.PULSE.get(), x, y, z, yaw, 90, 0);
        }
    }
}
