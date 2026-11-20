package com.stainkatana.katana.client;

import com.stainkatana.katana.KatanaParticles;
import net.minecraft.client.Minecraft;

/** Server-authoritative impact location; angles are used by the particle renderer, not as velocity. */
public final class KatanaVisuals {
    private KatanaVisuals() { }
    public static void spawn(double x, double y, double z, float yaw, int style) {
        var level = Minecraft.getInstance().level;
        if (level == null || style < 0 || style > 2 || !Double.isFinite(x) || !Double.isFinite(y)
                || !Double.isFinite(z) || !Float.isFinite(yaw)) return;
        if (style == 0) {
            // Horizontal cut, silver with a subtle crimson edge.
            level.addParticle(KatanaParticles.SLASH.get(), x, y, z, yaw, 0, 0);
        } else if (style == 1) {
            // First stroke of the ultimate, angled across the body.
            level.addParticle(KatanaParticles.PULSE.get(), x, y, z, yaw, 62, 18);
        } else {
            // Paralysis feedback around the marked target.
            level.addParticle(KatanaParticles.PULSE.get(), x, y, z, yaw, 90, 0);
        }
    }
}
