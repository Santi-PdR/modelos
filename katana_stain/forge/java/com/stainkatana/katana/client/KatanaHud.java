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
        int w = 82, x = Math.max(5, g.guiWidth() - w - 8), y = Math.max(8, g.guiHeight() / 2 - 32);
        // A restrained, layered burgundy panel with individual skill seals.
        g.fill(x + 2, y, x + w - 2, y + 2, 0xFF931D31);
        g.fill(x, y + 2, x + w, y + 65, 0xC6120D12);
        g.fill(x, y + 2, x + 1, y + 65, 0xFF671828);
        g.fill(x + w - 1, y + 2, x + w, y + 65, 0xFF671828);
        g.fill(x + 2, y + 65, x + w - 2, y + 66, 0xFF671828);
        for (int i = 0; i < 3; i++) {
            int row = y + 4 + i * 20;
            boolean ready = synced && remaining[i] == 0;
            g.fill(x + 3, row, x + 21, row + 17, ready ? 0xFF9E273B : 0xFF50202A);
            g.fill(x + 4, row + 1, x + 20, row + 16, 0xFF241019);
            g.fill(x + 5, row + 2, x + 19, row + 3, ready ? 0xFFE0757A : 0xFF8A343C);
            String key = KatanaKeys.get(i).getTranslatedKeyMessage().getString();
            key = mc.font.plainSubstrByWidth(key, 14);
            g.drawCenteredString(mc.font, key, x + 12, row + 5, 0xFFF2D6D6);
            if (i == 0) {
                for (int blood = 0; blood < 2; blood++) {
                    int sx = x + 25 + blood * 6;
                    g.fill(sx, row + 4, sx + 4, row + 9,
                            synced && charges > blood ? 0xFFE53A50 : 0xFF52202A);
                }
            }
            String time = synced ? (remaining[i] > 0 ? Integer.toString((remaining[i] + 19) / 20) + "s" : "OK") : "--";
            g.drawString(mc.font, time, x + w - 6 - mc.font.width(time), row + 2, ready ? 0xFFF3CBC2 : 0xFFE39A9E, false);
            int barX = x + 25, barWidth = w - 32;
            g.fill(barX, row + 13, barX + barWidth, row + 16, 0xFF3E1921);
            int fill = synced ? barWidth - (int)Math.ceil((double)remaining[i] * barWidth / CombatTuning.cooldown(i)) : 0;
            g.fill(barX, row + 13, barX + Math.max(0, fill), row + 15, ready ? 0xFFDA5964 : 0xFFA51C34);
        }
    }
}
