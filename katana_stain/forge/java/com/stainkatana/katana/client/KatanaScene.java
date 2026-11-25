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
    private static boolean finisher;
    // View-only impact feedback. The scene steers the camera during the
    // ultimate; these decay independently so the rim flash can outlive the
    // camera cut, like the cinematic letterbox fade-out.
    private static double shakeAge = 99, finalFlashAge = 99;
    private static boolean bigImpact;
    private static double shakePower;
    // Side-biased two-shots keep both actors readable; a full orbit frequently
    // put the victim directly in front of the attacker. Z has its own timing.
    private static final double[] C_ANGLE = {72, 92, 106, 78, 100, 88};
    private static final double[] C_DISTANCE = {4.6, 4.0, 4.5, 4.0, 4.6, 3.7};
    private static final double[] C_HEIGHT = {1.0, .65, .85, .55, 1.0, .6};
    private static final double[] Z_ANGLE = {70, 90, 105};
    private static final double[] Z_DISTANCE = {4.5, 3.5, 4.1};
    private static final double[] Z_HEIGHT = {.8, .55, .75};
    private static double progress, previous;
    private KatanaScene() { }

    public static void start(boolean shortFinisher) {
        if (!KatanaClientConfig.ULTIMATE_FRAME.get()) return;
        Minecraft mc = Minecraft.getInstance();
        if (!active && mc.player != null) {
            previousCamera = mc.options.getCameraType();
            mc.options.setCameraType(net.minecraft.client.CameraType.THIRD_PERSON_BACK);
        }
        initialYaw = mc.player == null ? 0 : mc.player.getYRot();
        finisher = shortFinisher;
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
    public static void focus(double x, double y, double z) {
        if (active && KatanaClientConfig.ULTIMATE_FRAME.get())
            focus = new net.minecraft.world.phys.Vec3(x, y, z);
    }
    /**
     * A server-confirmed stroke. {@code decisive} selects the big-impact feedback
     * (stronger FOV pulse, crimson rim flash). No text is ever shown on screen.
     */
    public static void impact(boolean second, boolean leftHanded, double x, double y, double z, boolean decisive) {
        if (active && KatanaClientConfig.ULTIMATE_FRAME.get()) {
            impactAge = 0;
            focus = new net.minecraft.world.phys.Vec3(x, y, z);
            impactDirection = (second ^ leftHanded) ? -1 : 1;
            bigImpact = decisive;
            shakeAge = 0;
            shakePower = bigImpact ? 1.0 : 0.45;
            if (bigImpact) finalFlashAge = 0;
        }
    }
    private static void reset() { stop(); age = 0; impactAge = 4; progress = previous = 0;
        shakeAge = finalFlashAge = 99; bigImpact = false; shakePower = 0; }

    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || !KatanaClientConfig.ULTIMATE_FRAME.get()) { reset(); return; }
        if (mc.isPaused()) return;
        previous = progress;
        if (impactAge < 4) impactAge++;
        if (shakeAge < 40) shakeAge++;
        if (finalFlashAge < 40) finalFlashAge++;
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
        // Brief additional zoom on each server-confirmed stroke (stronger on the
        // decisive execution); roll, shake and flash are applied elsewhere.
        double impulse = SceneCurve.impactEnvelope(impactAge + Minecraft.getInstance().getFrameTime()) * (bigImpact ? 1.8 : 1.0);
        double zoom = KatanaClientConfig.ZOOM_FRACTION.get() * strength * (1.0 + 0.35 * impulse);
        event.setFOV(event.getFOV() * (1.0 - zoom));
    }
    @SubscribeEvent public static void camera(ViewportEvent.ComputeCameraAngles event) {
        if (!canRender()) return;
        float partial = (float) event.getPartialTick();
        double pulse = SceneCurve.impactEnvelope(impactAge + partial);
        double tilt = KatanaClientConfig.CAMERA_ROLL.get() * strength(partial) * pulse * impactDirection;
        event.setRoll(event.getRoll() + (float) tilt);
        if (!active || focus == null || cameraUnavailable) {
            applyShake(event, partial);
            return;
        }
        Minecraft mc = Minecraft.getInstance();
        // Target-relative side framing: preserve the line between the two
        // actors even when the server relocates the caster for the next cut.
        // This is local presentation only and never changes aim or damage.
        var player = mc.player;
        var caster = player.getPosition(partial).add(0, 1.1, 0);
        var center = caster.lerp(focus, .5);
        var axis = caster.subtract(focus).multiply(1, 0, 1);
        double separation = axis.length();
        if (separation < .1) {
            double yaw = Math.toRadians(initialYaw);
            axis = new net.minecraft.world.phys.Vec3(Math.sin(yaw), 0, -Math.cos(yaw));
        } else axis = axis.scale(1 / separation);
        double time = age + partial;
        double duration = finisher ? 30 : 200;
        double angle = Math.toRadians(SceneCurve.shot(time, duration, finisher ? Z_ANGLE : C_ANGLE));
        double distance = SceneCurve.shot(time, duration, finisher ? Z_DISTANCE : C_DISTANCE)
                + Math.min(4.0, Math.max(0.0, separation - 2.0) * .5);
        double height = SceneCurve.shot(time, duration, finisher ? Z_HEIGHT : C_HEIGHT);
        var side = new net.minecraft.world.phys.Vec3(-axis.z, 0, axis.x);
        var desired = center.add(axis.scale(Math.cos(angle) * distance))
                .add(side.scale(Math.sin(angle) * distance)).add(0, height, 0);
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
        // The steering above sets absolute yaw/pitch; the shake rides on top.
        applyShake(event, partial);
    }

    /**
     * Additive view-only shake on strokes (half power on ordinary cuts, full on
     * the decisive execution). Decays within seven ticks and never affects aim.
     */
    private static void applyShake(ViewportEvent.ComputeCameraAngles event, float partial) {
        double t = shakeAge + partial;
        double shake = KatanaClientConfig.SCREEN_SHAKE.get() * shakePower;
        if (t < 7 && shake > 0) {
            double amp = shake * Math.pow(1.0 - t / 7.0, 2.0);
            event.setYaw(event.getYaw() + (float) (Math.sin(t * 3.1) * amp * 0.9));
            event.setPitch(event.getPitch() + (float) (Math.cos(t * 2.7 + 0.6) * amp * 0.75));
        }
    }
    /** Edge flash and title setup, drawn even when the scene has already handed the camera back. */
    private static boolean overlayAllowed() {
        Minecraft mc = Minecraft.getInstance();
        return mc.level != null && mc.player != null && mc.screen == null
                && KatanaClientConfig.ULTIMATE_FRAME.get();
    }

    @SubscribeEvent public static void render(RenderGuiEvent.Post event) {
        if (!overlayAllowed()) return;
        GuiGraphics graphics = event.getGuiGraphics();
        Minecraft mc = Minecraft.getInstance();
        int w = graphics.guiWidth(), h = graphics.guiHeight();
        float partial = (float) event.getPartialTick();
        if (canRender()) {
            double eased = strength(partial);
            int bar = (int)Math.round(h * KatanaClientConfig.BAR_FRACTION.get() * eased);
            if (bar > 0) {
                // Adapted from Cinema Scope's animated letterbox, with a capped fractional height.
                graphics.fill(0, 0, w, bar, 0xFF000000);
                graphics.fill(0, h - bar, w, h, 0xFF000000);
            }
        }
        double fage = finalFlashAge + partial;
        if (fage < 6 && KatanaClientConfig.FINAL_FLASH.get()) {
            // Crimson rim, two soft passes, easing out to nothing within six ticks.
            double a = Math.pow(1.0 - fage / 6.0, 2.0);
            for (int i = 0; i < 8; i++) {
                int o = (int)Math.round((i + 1) * Math.min(w, h) * 0.0021f);
                int ia = (int)(150 * a * (1.0 - (double) i / 8.0));
                if (ia <= 0) continue;
                int col = (ia << 24) | 0x8F1420;
                graphics.fill(0, 0, w, o, col);
                graphics.fill(0, h - o, w, h, col);
                graphics.fill(0, 0, o, h, col);
                graphics.fill(w - o, 0, w, h, col);
            }
        }
    }
}
