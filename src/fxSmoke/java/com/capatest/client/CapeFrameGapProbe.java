package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.item.ItemStack;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** Exercise the actual rig and UV2 submission on a controlled render schedule, without stalling the client. */
final class CapeFrameGapProbe extends GeoRenderLayer<CapaDeteriorerItem> {
    private static final int START = 40, DARK = 8, BRIGHT = 22, END = 28;
    private Matrix4f body;
    private Vector3f tip;

    private CapeFrameGapProbe(CapaArmorRenderer renderer) { super(renderer); }

    static void verify(Minecraft game, ItemStack stack, Path dir) throws IOException {
        var renderer = new CapaArmorRenderer();
        var probe = new CapeFrameGapProbe(renderer);
        renderer.addRenderLayer(probe);
        var armor = new HumanoidModel<ArmorStand>(game.getEntityModels().bakeLayer(ModelLayers.PLAYER_INNER_ARMOR));
        // Never add this wearer to the world. Keep its phase and rig exactly
        // the same for the dense and sparse schedules by rewinding its clock.
        var wearer = new ArmorStand(game.level, 0, 64, 0);
        wearer.yo = wearer.getY();
        wearer.setOnGround(true);
        var reference = new Draw[END + 1];
        for (int tick = 0; tick <= END; ++tick)
            reference[tick] = probe.draw(renderer, wearer, stack, armor, tick, shade(tick), .375F);

        StringBuilder rows = new StringBuilder("tick\tsombra\tpunta_x\tpunta_y\tpunta_z\terror_punta_u"
                + "\tgiro_extremo\thalo_borde\thalo_interior\tvertices_halo\n");
        for (int tick = 0; tick <= END; ++tick) {
            if (tick > 0 && tick < DARK || tick > DARK + 6 && tick < BRIGHT) continue;
            var actual = probe.draw(renderer, wearer, stack, armor, tick, shade(tick), .375F);
            double error = actual.tip.distance(reference[tick].tip);
            require(error <= .0001 && actual.light == reference[tick].light && actual.vertices == reference[tick].vertices,
                    "gap changed the submitted cape or halo at tick " + tick + ", tip delta " + error
                            + ", UV2 " + actual.light + "/" + reference[tick].light);
            if (tick == DARK || tick == BRIGHT) {
                var replay = probe.draw(renderer, wearer, stack, armor, tick, !shade(tick), .125F);
                require(replay.tip.equals(actual.tip, .0001F) && replay.light == actual.light,
                        "earlier same-tick pass advanced the hem or the halo");
                require(tick == DARK ? actual.turn > .6 && actual.turn < .65 : actual.turn < -.50,
                        "the late reversal consumed the entire draw gap");
            }
            rows.append(String.format(Locale.ROOT, "%d\t%d\t%.8f\t%.8f\t%.8f\t%.8f\t%.8f\t%.8f\t%.8f\t%d%n",
                    tick, shade(tick) ? 1 : 0, actual.tip.x, actual.tip.y, actual.tip.z, error, actual.turn,
                    (short) actual.light / 4096.0, (short) (actual.light >>> 16) / 4096.0, actual.vertices));
        }
        // A real positional cut bypasses the short-gap policy on the cloth.
        wearer.xo = wearer.getX() + 8;
        var cut = probe.draw(renderer, wearer, stack, armor, END + 1, false, .375F);
        require(cut.turn == 0, "teleport retained the old turn in the renderer");
        Files.writeString(dir.resolve("pausa-render-forge.tsv"), rows);
    }

    private static boolean shade(int tick) { return tick >= DARK && tick < BRIGHT; }

    private Draw draw(CapaArmorRenderer renderer, ArmorStand wearer, ItemStack stack,
                      HumanoidModel<ArmorStand> armor, int tick, boolean shade, float partial) {
        body = null;
        tip = null;
        wearer.tickCount = START + tick;
        wearer.yBodyRotO = 0;
        wearer.yBodyRot = shade ? -14 : 14;
        wearer.setDeltaMovement(shade ? -.08 : .18, 0, 0);
        var base = new CapeVertexProbe();
        var halo = new CapeVertexProbe();
        RenderType haloType = CapeBloom.wornLight(CapeBloom.Mode.HALO);
        MultiBufferSource sinks = type -> type == haloType ? halo : base;
        renderer.prepForRender(wearer, stack, EquipmentSlot.CHEST, armor);
        var pose = new PoseStack();
        renderer.defaultRender(pose, (CapaDeteriorerItem) stack.getItem(), sinks, null, null, 0, partial,
                LightTexture.pack(shade ? 0 : 15, 0));
        require(pose.clear() && body != null && tip != null && halo.count > 0 && base.count > 0,
                "missing actual pose or vertex submission");
        var motion = CapaArmorModel.wornMotion(wearer);
        return new Draw(body.invert().transformPosition(tip, new Vector3f()).mul(16),
                motion.response.turnAt(1), halo.light, halo.count);
    }

    @Override
    public void renderForBone(PoseStack pose, CapaDeteriorerItem item, GeoBone bone, RenderType type,
                              MultiBufferSource buffers, VertexConsumer consumer, float partial, int light, int overlay) {
        if (CapeWalkProbe.BODY.equals(bone.getName())) body = new Matrix4f(pose.last().pose());
        if (CapeWalkProbe.TIP.equals(bone.getName())) tip = pose.last().pose().transformPosition(0, 0, .36F, new Vector3f());
    }

    private record Draw(Vector3f tip, double turn, int light, int vertices) {}

    private static void require(boolean test, String message) {
        if (!test) throw new AssertionError("draw gap: " + message);
    }
}
