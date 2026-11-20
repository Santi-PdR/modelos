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
    private static final int SAFETY_TIMEOUT = 212;
    private static boolean active;
    private static net.minecraft.client.CameraType previousCamera;
    private static int age, impactAge = 4;
    private static int impactDirection;
    private static double progress, previous;
    private KatanaScene() { }

    public static void start() {
        if (!KatanaClientConfig.ULTIMATE_FRAME.get()) return;
        Minecraft mc = Minecraft.getInstance();
        if (!active && mc.player != null) {
            previousCamera = mc.options.getCameraType();
            mc.options.setCameraType(net.minecraft.client.CameraType.THIRD_PERSON_BACK);
        }
        active = true; age = 0; impactAge = 4;
    }
    public static void stop() {
        Minecraft mc = Minecraft.getInstance();
        if (previousCamera != null && mc.options.getCameraType() == net.minecraft.client.CameraType.THIRD_PERSON_BACK)
            mc.options.setCameraType(previousCamera);
        previousCamera = null;
        active = false; impactAge = 4;
    }
    public static void impact(boolean second, boolean leftHanded) {
        if (active && KatanaClientConfig.ULTIMATE_FRAME.get()) {
            impactAge = 0;
            impactDirection = (second ^ leftHanded) ? -1 : 1;
        }
    }
    private static void reset() { stop(); age = 0; impactAge = 4; progress = previous = 0; }

    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || !KatanaClientConfig.ULTIMATE_FRAME.get()) { reset(); return; }
        if (mc.isPaused()) return;
        previous = progress;
        if (impactAge < 4) impactAge++;
        if (active && ++age >= SAFETY_TIMEOUT) stop();
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
        // Brief additional zoom on each server-confirmed stroke; no screen shake or flash.
        double impulse = SceneCurve.impactEnvelope(impactAge + Minecraft.getInstance().getFrameTime());
        double zoom = KatanaClientConfig.ZOOM_FRACTION.get() * strength * (1.0 + 0.35 * impulse);
        event.setFOV(event.getFOV() * (1.0 - zoom));
    }
    @SubscribeEvent public static void camera(ViewportEvent.ComputeCameraAngles event) {
        if (!canRender()) return;
        float partial = (float) event.getPartialTick();
        double pulse = SceneCurve.impactEnvelope(impactAge + partial);
        double tilt = KatanaClientConfig.CAMERA_ROLL.get() * strength(partial) * pulse * impactDirection;
        // Visual roll only: it does not alter the player's aim, movement or perspective.
        event.setRoll(event.getRoll() + (float) tilt);
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
