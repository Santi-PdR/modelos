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

/** Client-only framing: target tracking and orbit never change server aim or damage. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaScene {
    private static final int TRANSITION_TICKS = 4;
    private static final int SAFETY_TIMEOUT = 212;
    private static boolean active;
    private static net.minecraft.client.CameraType previousCamera;
    private static net.minecraft.world.phys.Vec3 focus, cameraPosition;
    private static boolean cameraUnavailable, cameraApplied;
    private static java.lang.reflect.Method positionMethod, rotationMethod;
    private static int age, impactAge = 4;
    private static int impactDirection;
    private static float initialYaw;
    private static final double[] ORBIT = {40, 95, 170, 230, 300, 365};
    private static final double[] DISTANCE = {5.0, 3.4, 4.2, 3.2, 5.0, 3.6};
    private static final double[] HEIGHT = {2.0, .9, 2.1, .8, 2.8, 1.3};
    private static double progress, previous;
    private KatanaScene() { }

    public static void start() {
        if (!KatanaClientConfig.ULTIMATE_FRAME.get()) return;
        Minecraft mc = Minecraft.getInstance();
        if (!active && mc.player != null) {
            previousCamera = mc.options.getCameraType();
            mc.options.setCameraType(net.minecraft.client.CameraType.THIRD_PERSON_BACK);
        }
        initialYaw = mc.player == null ? 0 : mc.player.getYRot();
        active = true; age = 0; impactAge = 4; focus = null; cameraPosition = null; cameraApplied = false;
    }
    public static void stop() {
        Minecraft mc = Minecraft.getInstance();
        if (previousCamera != null && mc.options.getCameraType() == net.minecraft.client.CameraType.THIRD_PERSON_BACK)
            mc.options.setCameraType(previousCamera);
        previousCamera = null;
        active = false; impactAge = 4; focus = null; cameraPosition = null;
    }
    public static boolean cameraApplied() { return cameraApplied; }
    public static void impact(boolean second, boolean leftHanded, double x, double y, double z) {
        if (active && KatanaClientConfig.ULTIMATE_FRAME.get()) {
            impactAge = 0;
            focus = new net.minecraft.world.phys.Vec3(x, y, z);
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
        event.setRoll(event.getRoll() + (float) tilt);
        if (!active || focus == null || cameraUnavailable) return;
        Minecraft mc = Minecraft.getInstance();
        // Original orbit around the midpoint, with a wall raycast to avoid filming through terrain.
        var player = mc.player;
        var caster = player.getPosition(partial).add(0, 1.1, 0);
        var center = caster.lerp(focus, .55);
        double time = age + partial;
        double angle = Math.toRadians(initialYaw + SceneCurve.shot(time, ORBIT));
        double distance = SceneCurve.shot(time, DISTANCE);
        double height = SceneCurve.shot(time, HEIGHT);
        var desired = center.add(Math.sin(angle) * distance, height, -Math.cos(angle) * distance);
        var trace = mc.level.clip(new net.minecraft.world.level.ClipContext(center, desired,
                net.minecraft.world.level.ClipContext.Block.COLLIDER,
                net.minecraft.world.level.ClipContext.Fluid.NONE, player));
        if (trace.getType() != net.minecraft.world.phys.HitResult.Type.MISS)
            desired = trace.getLocation().lerp(center, .12);
        if (cameraPosition == null) cameraPosition = event.getCamera().getPosition();
        // Exponential smoothing measured in game ticks, not rendered frames: the
        // shot behaves consistently at both low and high frame rates.
        double frameTicks = Math.max(0, Math.min(3, mc.getDeltaFrameTime()));
        double blend = 1.0 - Math.pow(1.0 - .36 * strength(partial), frameTicks);
        cameraPosition = cameraPosition.lerp(desired, blend);
        var interpolatedTrace = mc.level.clip(new net.minecraft.world.level.ClipContext(center, cameraPosition,
                net.minecraft.world.level.ClipContext.Block.COLLIDER,
                net.minecraft.world.level.ClipContext.Fluid.NONE, player));
        if (interpolatedTrace.getType() != net.minecraft.world.phys.HitResult.Type.MISS)
            cameraPosition = interpolatedTrace.getLocation().lerp(center, .12);
        var delta = center.subtract(cameraPosition);
        float yaw = (float)Math.toDegrees(Math.atan2(-delta.x, delta.z));
        float pitch = (float)-Math.toDegrees(Math.atan2(delta.y, Math.sqrt(delta.x * delta.x + delta.z * delta.z)));
        try {
            if (positionMethod == null) {
                positionMethod = net.minecraftforge.fml.util.ObfuscationReflectionHelper.findMethod(net.minecraft.client.Camera.class,
                        "m_90584_", double.class, double.class, double.class);
                rotationMethod = net.minecraftforge.fml.util.ObfuscationReflectionHelper.findMethod(net.minecraft.client.Camera.class,
                        "m_90572_", float.class, float.class);
            }
            positionMethod.invoke(event.getCamera(), cameraPosition.x, cameraPosition.y, cameraPosition.z);
            rotationMethod.invoke(event.getCamera(), yaw, pitch);
            event.setYaw(yaw); event.setPitch(pitch);
            cameraApplied = true;
        } catch (ReflectiveOperationException | RuntimeException failure) {
            cameraUnavailable = true;
            com.mojang.logging.LogUtils.getLogger().warn("Katana cinematic camera unavailable; keeping normal framing", failure);
        }
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
