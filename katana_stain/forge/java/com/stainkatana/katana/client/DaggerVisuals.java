package com.stainkatana.katana.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.stainkatana.StainKatanaMod;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Quaternionf;

/** Short-lived render-only daggers; damage is independently resolved on the server. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class DaggerVisuals {
    private record Flight(Vec3 start, Vec3 end, long birth) { }
    private static final List<Flight> flights = new ArrayList<>();
    private static ClientLevel world;
    private DaggerVisuals() { }
    public static boolean hasFlights() { return !flights.isEmpty(); }
    public static void spawn(int entityId, double x, double y, double z) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.level.getEntity(entityId) == null) return;
        if (world != mc.level) { world = mc.level; flights.clear(); }
        Vec3 start = mc.level.getEntity(entityId).getEyePosition().add(0, -.35, 0);
        long now = mc.level.getGameTime();
        Vec3 end = new Vec3(x, y, z);
        for (int i = 0; i < 3; i++) {
            if (flights.size() >= 32) flights.remove(0);
            double offset = (i - 1.0) * .18;
            flights.add(new Flight(start.add(offset, 0, 0), end.add(offset * .3, offset * .3, 0), now + i * 12));
        }
    }
    @SubscribeEvent public static void render(RenderLevelStageEvent event) {
        if (event.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level != world) { flights.clear(); world = mc.level; return; }
        if (world == null || flights.isEmpty()) return;
        double time = world.getGameTime() + event.getPartialTick();
        Vec3 camera = event.getCamera().getPosition();
        PoseStack pose = event.getPoseStack();
        var buffer = mc.renderBuffers().bufferSource();
        Iterator<Flight> iterator = flights.iterator();
        while (iterator.hasNext()) {
            Flight flight = iterator.next();
            double age = time - flight.birth();
            if (age > 12) { iterator.remove(); continue; }
            if (age < 0) continue;
            double t = Math.min(1, age / 10.0);
            Vec3 point = flight.start().lerp(flight.end(), t);
            Vec3 direction = flight.end().subtract(flight.start()).normalize();
            float yaw = (float)Math.atan2(direction.x, direction.z);
            float pitch = (float)-Math.asin(direction.y);
            pose.pushPose();
            pose.translate(point.x - camera.x, point.y - camera.y, point.z - camera.z);
            pose.mulPose(new Quaternionf().rotateY(yaw).rotateX(pitch).rotateX((float)Math.PI / 2));
            pose.scale(.55F, .55F, .55F);
            mc.getItemRenderer().renderStatic(new ItemStack(StainKatanaMod.DAGGER.get()), ItemDisplayContext.FIXED,
                    LightTexture.FULL_BRIGHT, OverlayTexture.NO_OVERLAY, pose, buffer, world, 0);
            pose.popPose();
        }
        buffer.endBatch();
    }
}
