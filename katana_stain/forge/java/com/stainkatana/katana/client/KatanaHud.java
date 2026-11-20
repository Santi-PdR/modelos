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

/** Presentation only: server snapshots are the authority for cooldowns. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaHud {
    private static final int[] remaining = new int[3];
    private static ClientLevel level;
    private static boolean synced;
    private static int flashTicks;
    private KatanaHud() { }
    public static void update(int z, int x, int c) {
        level = Minecraft.getInstance().level;
        int[] values = {z, x, c};
        for (int i = 0; i < 3; i++) remaining[i] = Math.max(0, Math.min(CombatTuning.cooldown(i), values[i]));
        synced = level != null;
    }
    public static void bloodFlash() { if (KatanaClientConfig.BLOOD_FLASH.get()) flashTicks = 12; }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level != level || mc.player == null) {
            level = mc.level; synced = false; flashTicks = 0;
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
        int w = 70, x = Math.max(3, g.guiWidth() - w - 7), y = Math.max(8, g.guiHeight() / 2 - 24);
        for (int i = 0; i < 3; i++) {
            int row = y + i * 16;
            g.fill(x, row, x + w, row + 14, 0xC51B1014);
            g.fill(x, row, x + 2, row + 14, 0xFF9D1C2F);
            String key = KatanaKeys.get(i).getTranslatedKeyMessage().getString();
            key = mc.font.plainSubstrByWidth(key, 23);
            g.drawString(mc.font, key, x + 5, row + 3, 0xFFE4D9D8, false);
            String time = synced ? (remaining[i] > 0 ? Integer.toString((remaining[i] + 19) / 20) + "s" : "OK") : "--";
            g.drawString(mc.font, time, x + w - 4 - mc.font.width(time), row + 3, 0xFFFFB1B5, false);
            int usable = 30;
            int fill = synced ? usable - (int)Math.ceil((double)remaining[i] * usable / CombatTuning.cooldown(i)) : 0;
            g.fill(x + 28, row + 11, x + 28 + Math.max(0, fill), row + 13, 0xFFC32B40);
        }
    }
}
