package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.CombatTuning;
import com.stainkatana.katana.KatanaClientConfig;
import com.stainkatana.katana.KatanaKeys;
import com.stainkatana.katana.StainKatanaItem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.network.chat.Component;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Presentation only: server snapshots are the authority for cooldowns. */
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
    @SubscribeEvent public static void render(RenderGuiEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null || mc.screen != null || mc.options.hideGui) return;
        GuiGraphics g = event.getGuiGraphics();
        if (flashTicks > 0 && KatanaClientConfig.BLOOD_FLASH.get()) {
            int alpha = Math.min(64, flashTicks * 6);
            g.fill(0, 0, g.guiWidth(), g.guiHeight(), (alpha << 24) | 0x00950018);
        }
        if (!KatanaClientConfig.SHOW_HUD.get() || !(mc.player.getMainHandItem().getItem() instanceof StainKatanaItem)) return;
        // Compact separated ability plates leave more of the world visible.
        int w = 104;
        boolean top = KatanaClientConfig.HUD_POSITION.get() == KatanaClientConfig.HudPosition.TOP_CENTER;
        int x = top ? Math.max(5, (g.guiWidth() - w) / 2) : Math.max(5, g.guiWidth() - w - 8);
        int y = top ? 12 : Math.max(8, (g.guiHeight() - 69) / 2);
        String[] labels = {"stainkatana.hud.paralysis", "stainkatana.hud.slash", "stainkatana.hud.ultimate"};
        for (int i = 0; i < 3; i++) {
            int row = y + i * 23;
            boolean finisherReady = i == 0 && synced && charges >= 2;
            boolean ready = synced && (remaining[i] == 0 || finisherReady);
            int accent = ready ? 0xFFE46C73 : 0xFF85454D;
            g.fill(x + 2, row + 2, x + w, row + 21, 0xD20D0A0E);
            g.fill(x, row, x + 21, row + 21, 0xDD1C1115);
            g.fill(x, row, x + 2, row + 21, accent);
            g.fill(x + 2, row, x + 21, row + 1, 0xFF6C343B);
            g.fill(x + 2, row + 20, x + 21, row + 21, 0xFF452229);
            // Fine red edge and a clipped corner give each plate definition
            // without relying on bright color alone to signal availability.
            g.fill(x + 21, row + 19, x + w - 4, row + 20, 0xFF35252B);
            g.fill(x + w - 4, row + 17, x + w - 2, row + 18, accent);
            String key = KatanaKeys.get(i).getTranslatedKeyMessage().getString();
            key = mc.font.plainSubstrByWidth(key, 16);
            g.drawCenteredString(mc.font, key, x + 11, row + 6, 0xFFF2DFD8);
            String labelKey = finisherReady ? "stainkatana.hud.finisher" : labels[i];
            String label = mc.font.plainSubstrByWidth(Component.translatable(labelKey).getString(), 52);
            g.drawString(mc.font, label, x + 26, row + 3, ready ? 0xFFF0D7CF : 0xFFAF9692, false);
            String time = synced ? (!finisherReady && remaining[i] > 0 ? Integer.toString((remaining[i] + 19) / 20) + "s" : "") : "--";
            g.drawString(mc.font, time, x + w - 5 - mc.font.width(time), row + 3, 0xFFE6A0A2, false);
            int barX = x + 26, barWidth = w - 32;
            g.fill(barX, row + 15, barX + barWidth, row + 17, 0xFF392329);
            int fill = finisherReady ? barWidth : synced ? barWidth - (int)Math.ceil((double)remaining[i] * barWidth / CombatTuning.cooldown(i)) : 0;
            if (fill > 0) g.fill(barX, row + 15, barX + fill, row + 17, accent);
            if (i == 0) {
                for (int blood = 0; blood < 2; blood++) {
                    int sx = x + w - 16 + blood * 6;
                    int color = synced && charges > blood ? 0xFFFF6A72 : 0xFF60343A;
                    g.fill(sx + 1, row + 10, sx + 3, row + 11, color);
                    g.fill(sx, row + 11, sx + 4, row + 13, color);
                }
            }
        }
    }
}
