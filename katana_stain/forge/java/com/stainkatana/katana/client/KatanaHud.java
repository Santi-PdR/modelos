package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.CombatTuning;
import com.stainkatana.katana.KatanaClientConfig;
import com.stainkatana.katana.KatanaKeys;
import com.stainkatana.katana.StainKatanaItem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Compact crimson sigils instead of plates: one small ring per ability, a sweeping
 * arc for the cooldown, and two blood droplets for the Z meter. Presentation only;
 * the server snapshots remain the authority on cooldowns and charges.
 */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaHud {
    private static final int[] remaining = new int[3];
    private static ClientLevel level;
    private static boolean synced;
    private static int flashTicks, charges;
    private KatanaHud() { }

    public static void update(int z, int x, int c, int bloodCharges) {
        level = Minecraft.getInstance().level;
        int[] values = {z, x, c};
        for (int i = 0; i < 3; i++) remaining[i] = Math.max(0, Math.min(CombatTuning.cooldown(i), values[i]));
        charges = Math.min(2, Math.max(0, bloodCharges));
        synced = level != null;
    }

    public static void bloodFlash() { if (KatanaClientConfig.BLOOD_FLASH.get()) flashTicks = 12; }

    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level != level || mc.player == null) {
            level = mc.level; synced = false; flashTicks = 0; charges = 0;
            for (int i = 0; i < 3; i++) remaining[i] = 0;
        }
        if (mc.level == null || mc.isPaused()) return;
        if (flashTicks > 0) flashTicks--;
        for (int i = 0; i < 3; i++) if (remaining[i] > 0) remaining[i]--;
    }

    private static void disc(GuiGraphics g, int cx, int cy, double radius, int color) {
        for (int dy = (int) -Math.ceil(radius); dy <= (int) Math.ceil(radius); dy++) {
            double half = Math.sqrt(Math.max(0.0, radius * radius - (double) dy * dy));
            int left = (int) Math.floor(cx - half);
            int right = (int) Math.ceil(cx + half);
            if (right >= left) g.fill(left, cy + dy, right + 1, cy + dy + 1, color);
        }
    }

    /** Two-pixel-thick arc band drawn as a stepped polyline of 1px cells. */
    private static void arc(GuiGraphics g, int cx, int cy, double radius, double fromAngle, double sweep, int color) {
        int steps = Math.max(12, (int) (Math.abs(sweep) * radius / 1.1));
        for (int pass = 0; pass < 2; pass++) {
            double r = radius - pass;
            for (int i = 0; i <= steps; i++) {
                double angle = fromAngle + sweep * (i / (double) steps);
                int px = (int) Math.floor(cx + r * Math.cos(angle));
                int py = (int) Math.floor(cy + r * Math.sin(angle));
                g.fill(px, py, px + 1, py + 1, color);
            }
        }
    }

    private static void droplet(GuiGraphics g, int x, int y, int color) {
        g.fill(x + 1, y, x + 3, y + 1, color);
        g.fill(x, y + 1, x + 4, y + 3, color);
        g.fill(x + 1, y + 3, x + 3, y + 4, color);
    }

    @SubscribeEvent public static void render(RenderGuiEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null || mc.screen != null || mc.options.hideGui) return;
        GuiGraphics g = event.getGuiGraphics();
        if (flashTicks > 0 && KatanaClientConfig.BLOOD_FLASH.get()) {
            int alpha = Math.min(64, flashTicks * 6);
            g.fill(0, 0, g.guiWidth(), g.guiHeight(), (alpha << 24) | 0x00950018);
        }
        if (!KatanaClientConfig.SHOW_HUD.get() || !(mc.player.getMainHandItem().getItem() instanceof StainKatanaItem)) return;
        boolean top = KatanaClientConfig.HUD_POSITION.get() == KatanaClientConfig.HudPosition.TOP_CENTER;
        double radius = 8.0;
        int spacing = 27, pitch = 26;
        float pulse = (float) (0.62 + 0.38 * Math.sin(System.currentTimeMillis() / 260.0));
        for (int i = 0; i < 3; i++) {
            int cx, cy;
            if (top) { cx = g.guiWidth() / 2 + (i - 1) * spacing; cy = 18; }
            else { cx = g.guiWidth() - 17; cy = g.guiHeight() / 2 - pitch + i * pitch; }
            int total = CombatTuning.cooldown(i);
            boolean finisherReady = i == 0 && synced && charges >= 2;
            boolean ready = synced && (remaining[i] == 0 || finisherReady);
            double fraction = synced ? 1.0 - (double) remaining[i] / total : 0.0;
            // Soft shadow, dark glass body, then the track ring.
            disc(g, cx + 1, cy + 1, radius + 1.5, 0x66000000);
            disc(g, cx, cy, radius, 0xC0151218);
            disc(g, cx, cy - 1, radius - 2.5, 0x8A211B22);
            arc(g, cx, cy, radius, -Math.PI / 2, Math.PI * 2, 0xFF453943);
            if (finisherReady) {
                int gold = (int) (140 + 115 * pulse);
                arc(g, cx, cy, radius, -Math.PI / 2, Math.PI * 2, (gold << 24) | 0xC79A3D);
                arc(g, cx, cy, radius + 2.5, -Math.PI / 2, Math.PI * 2, (int) (90 * pulse) << 24 | 0xC79A3D);
            } else if (ready) {
                arc(g, cx, cy, radius, -Math.PI / 2, Math.PI * 2, 0xFFD85A64);
                arc(g, cx, cy, radius + 2.5, -Math.PI / 2, Math.PI * 2, 0x3EDD5F6B);
            } else if (fraction > 0.02) {
                arc(g, cx, cy, radius, -Math.PI / 2, Math.PI * 2 * fraction, 0xFFD85A64);
            }
            String key = KatanaKeys.get(i).getTranslatedKeyMessage().getString();
            key = mc.font.plainSubstrByWidth(key, 12);
            int letterColor = ready || finisherReady ? 0xFFF6E7E4 : 0xFF8E7E7C;
            g.drawCenteredString(mc.font, key, cx, cy - 4, letterColor);
            if (i == 0) {
                for (int blood = 0; blood < 2; blood++) {
                    int dx = cx - 5 + blood * 6;
                    int fill = synced && charges > blood ? 0xFFE35A62 : 0xFF4A3A41;
                    droplet(g, dx, cy + 11, fill);
                }
            }
        }
    }
}
