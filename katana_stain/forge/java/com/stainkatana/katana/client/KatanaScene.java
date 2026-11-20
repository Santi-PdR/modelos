package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.KatanaClientConfig;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Short client-only framing for the confirmed ultimate, not a camera cutscene. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaScene {
    private static final int TRANSITION_TICKS = 4;
    private static final int SAFETY_TIMEOUT = 36;
    private static boolean active;
    private static int age;
    private static double progress, previous;
    private KatanaScene() { }

    public static void start() {
        if (!KatanaClientConfig.ULTIMATE_FRAME.get()) return;
        active = true; age = 0;
    }
    public static void stop() { active = false; }
    private static void reset() { active = false; age = 0; progress = previous = 0; }

    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || !KatanaClientConfig.ULTIMATE_FRAME.get()) { reset(); return; }
        if (mc.isPaused()) return;
        previous = progress;
        if (active && ++age >= SAFETY_TIMEOUT) active = false;
        progress = Math.max(0, Math.min(1, progress + (active ? 1.0 : -1.0) / TRANSITION_TICKS));
    }
    private static double strength(float partialTick) {
        double partial = Math.max(0, Math.min(1, partialTick));
        return SceneCurve.ease(previous + (progress - previous) * partial);
    }
    private static boolean canRender() {
        Minecraft mc = Minecraft.getInstance();
        return mc.level != null && mc.player != null && mc.screen == null
                && KatanaClientConfig.ULTIMATE_FRAME.get() && (active || progress > 0);
    }
    @SubscribeEvent public static void fov(ViewportEvent.ComputeFov event) {
        if (!canRender() || !event.usedConfiguredFov()) return;
        double strength = strength(Minecraft.getInstance().getFrameTime());
        event.setFOV(event.getFOV() * (1.0 - KatanaClientConfig.ZOOM_FRACTION.get() * strength));
    }
    @SubscribeEvent public static void render(RenderGuiEvent.Post event) {
        if (!canRender()) return;
        GuiGraphics graphics = event.getGuiGraphics();
        int w = graphics.guiWidth(), h = graphics.guiHeight();
        double eased = strength(event.getPartialTick());
        int bar = (int)Math.round(h * KatanaClientConfig.BAR_FRACTION.get() * eased);
        if (bar <= 0) return;
        // Adapted from Cinema Scope's animated letterbox, with a capped fractional height.
        graphics.fill(0, 0, w, bar, 0xFF000000);
        graphics.fill(0, h - bar, w, h, 0xFF000000);
    }
}
