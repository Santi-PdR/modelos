package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.item.ItemStack;
import software.bernie.geckolib.cache.object.GeoBone;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;

/** The real light layer on the real mesh, driven by one recorded landing impulse. */
final class CapeLandingLightProbe {
    private static final int START = 200;
    private static final float PARTIAL = .375F;

    static int[] verify(Minecraft game, ItemStack stack, Path dir) throws IOException {
        var armor = new HumanoidModel<ArmorStand>(game.getEntityModels().bakeLayer(ModelLayers.PLAYER_INNER_ARMOR));
        var stand = stand(game);
        var renderer = new CapaArmorRenderer();
        draw(renderer, stand, stack, armor, 0, 0, CapeLanding.REST); // bake and register the real worn rig
        int hemVertices = hemVertices(renderer);
        var rows = new StringBuilder("caso\ttick\tcabeceo_deg\tcalor\tborde_previo\tinterior_previo\t"
                + "borde_dobladillo\tinterior_dobladillo\tvertices\tdobladillo_vertices\n");
        int[] gpu = new int[2];
        int hemVertex = -1;
        double peakPitch = 0, peakHeat = 0;
        for (double lift : new double[]{-.3, .08, .36, .84, 1}) {
            double impulse = CapeLanding.strength(lift);
            for (int tick = 0; tick <= 13; ++tick) {
                double seconds = time(tick);
                var pose = CapeLanding.pose(tick + PARTIAL, impulse);
                var calm = draw(renderer, stand, stack, armor, tick, 0, CapeLanding.REST);
                var lit = draw(renderer, stand, stack, armor, tick, 0, pose);
                require(calm.count == lit.count && calm.rgba == lit.rgba,
                        "the hem echo changed the geometry or the core tint");
                int moved = calm.moved(lit);
                int base = CapeNocturne.gains(1, seconds, stand.getId()).packed();
                int echo = CapeNocturne.hemGains(1, CapeNocturne.gains(1, seconds, stand.getId()), seconds,
                        stand.getId(), pose.heat()).packed();
                if (pose.heat() == 0 || echo == base) require(moved == 0, "echo without a packed light delta");
                else require(moved == hemVertices, "echo escaped the lower hinge: " + moved + "/" + hemVertices);
                if (moved > 0) {
                    if (hemVertex < 0) hemVertex = calm.firstMoved(lit);
                    require(lit.light(hemVertex) == echo && calm.light(hemVertex) != echo,
                            "submitted UV2 does not follow the shared envelope");
                    require(calm.kept(lit, base) > 0, "the echo covered vertices above the hinge");
                }
                if (lift == .84 && tick == 3) { gpu[0] = base; gpu[1] = echo; }
                peakPitch = Math.max(peakPitch, pose.pitch());
                peakHeat = Math.max(peakHeat, pose.heat());
                rows.append(String.format(Locale.ROOT, "%.2f\t%d\t%.4f\t%.4f\t%.6f\t%.6f\t%.6f\t%.6f\t%d\t%d%n",
                        lift, tick, pose.pitch(), pose.heat(), edge(base), inner(base), edge(echo), inner(echo),
                        lit.count, moved));
            }
        }
        require(CapeLanding.pose(3, 1).pitch() == 5.5 && CapeLanding.pose(4.4, 1).heat() == 1
                        && peakPitch > 5.4 && peakHeat > .99,
                "impulse envelope out of range");

        // Full daylight, another wearer and the same draw twice stay on the
        // .41 path; only a dark frame of this wearer carries the echo.
        var strong = new CapeLanding.Motion(5.5, 1);
        var dayStand = stand(game);
        var dayRenderer = new CapaArmorRenderer();
        require(draw(dayRenderer, dayStand, stack, armor, 4, 15, strong)
                        .sameLight(draw(dayRenderer, dayStand, stack, armor, 4, 15, CapeLanding.REST)),
                "the hem echo reached full daylight");
        var other = stand(game);
        var independent = draw(new CapaArmorRenderer(), other, stack, armor, 4, 0, CapeLanding.REST);
        int expectedOther = CapeNocturne.gains(1, time(4), other.getId()).packed();
        require(Arrays.stream(independent.light).allMatch(value -> value == expectedOther),
                "a second wearer inherited another wearer's landing");
        var repeatRenderer = new CapaArmorRenderer();
        var impulse = new CapeLanding.Motion(3.2, .8);
        var first = draw(repeatRenderer, stand(game), stack, armor, 7, 0, impulse);
        var replay = draw(repeatRenderer, stand(game), stack, armor, 7, 0, impulse);
        require(Arrays.equals(first.light, replay.light) && first.rgba == replay.rgba,
                "replaying the same landing tick changed UV2");
        rows.append("repeticion\t7\t\t.8000\t\t\t").append(String.format(Locale.ROOT, "%.6f\t%.6f\t%d\t%d%n",
                edge(first.light(hemVertex)), inner(first.light(hemVertex)), first.count, hemVertices));
        Files.writeString(dir.resolve("aterrizaje-halo-forge.tsv"), rows);
        require(gpu[0] != 0 && gpu[1] != gpu[0] && hemVertex >= 0, "missing dark landing sample");
        return gpu;
    }

    /** Count submitted UV2 vertices under the lower hinge from the active rig. */
    private static int hemVertices(CapaArmorRenderer renderer) {
        int vertices = 0;
        for (var bone : renderer.getGeoModel().getAnimationProcessor().getRegisteredBones()) {
            if (!(bone instanceof GeoBone geo) || !inHem(geo) || !visible(geo)) continue;
            for (var cube : geo.getCubes())
                for (var quad : cube.quads()) if (quad != null) vertices += quad.vertices().length;
        }
        require(vertices > 0, "empty lower hinge subtree");
        return vertices;
    }

    /** Include cape_bottom itself as well as its descendants. */
    private static boolean inHem(GeoBone bone) {
        if (CapeLanding.HEM.equals(bone.getName())) return true;
        for (GeoBone parent = bone.getParent(); parent != null; parent = parent.getParent())
            if (CapeLanding.HEM.equals(parent.getName())) return true;
        return false;
    }

    private static boolean visible(GeoBone bone) {
        for (GeoBone current = bone; current != null; current = current.getParent())
            if (current.isHidden() || current.isHidingChildren()) return false;
        return true;
    }

    private static ArmorStand stand(Minecraft game) {
        var stand = new ArmorStand(game.level, 0, 64, 0);
        stand.yo = stand.getY();
        stand.setOnGround(true);
        return stand;
    }

    private static double time(int tick) { return (START + tick + (double) PARTIAL) / 20; }
    private static double edge(int light) { return (short) light / 4096.0; }
    private static double inner(int light) { return (short) (light >>> 16) / 4096.0; }

    private record Draw(int count, int rgba, int[] light) {
        int light(int index) { return light[Math.min(index, light.length - 1)]; }
        boolean sameLight(Draw other) { return Arrays.equals(light, other.light); }
        int kept(Draw other, int value) {
            int kept = 0;
            for (int i = 0; i < light.length; ++i) if (light[i] == value && other.light[i] == value) ++kept;
            return kept;
        }
        int firstMoved(Draw other) {
            for (int i = 0; i < light.length; ++i) if (light[i] != other.light[i]) return i;
            return 0;
        }
        int moved(Draw other) {
            int moved = 0;
            for (int i = 0; i < light.length; ++i) if (light[i] != other.light[i]) ++moved;
            return moved;
        }
    }

    private static Draw draw(CapaArmorRenderer renderer, ArmorStand wearer, ItemStack stack,
                             HumanoidModel<ArmorStand> armor, int tick, int light, CapeLanding.Motion motion) {
        wearer.tickCount = START + tick;
        wearer.setDeltaMovement(0, 0, 0);
        renderer.probeLanding(motion);
        var sink = new Probe();
        var type = CapeBloom.wornLight(CapeBloom.Mode.HALO);
        var pose = new PoseStack();
        renderer.prepForRender(wearer, stack, EquipmentSlot.CHEST, armor);
        renderer.defaultRender(pose, (CapaDeteriorerItem) stack.getItem(), pass -> pass == type ? sink : new Probe(),
                null, null, 0, PARTIAL, LightTexture.pack(light, 0));
        require(pose.clear() && sink.count > 0, "missing halo draw");
        return new Draw(sink.count, sink.rgba, sink.lights.stream().mapToInt(Integer::intValue).toArray());
    }

    /** The shipped probe's sink plus the per-vertex light stream. */
    private static final class Probe implements VertexConsumer {
        final List<Integer> lights = new ArrayList<>();
        int count, rgba, pending = Integer.MIN_VALUE;

        @Override public VertexConsumer vertex(double x, double y, double z) { return this; }
        @Override public VertexConsumer color(int r, int g, int b, int a) { rgba = r << 24 | g << 16 | b << 8 | a; return this; }
        @Override public VertexConsumer uv(float u, float v) { return this; }
        @Override public VertexConsumer overlayCoords(int u, int v) { return this; }
        @Override public VertexConsumer uv2(int u, int v) { pending = (u & 0xffff) | v << 16; return this; }
        @Override public VertexConsumer normal(float x, float y, float z) { return this; }
        @Override public void endVertex() { lights.add(pending); pending = Integer.MIN_VALUE; ++count; }
        @Override public void defaultColor(int r, int g, int b, int a) {}
        @Override public void unsetDefaultColor() {}
    }

    private static void require(boolean ok, String message) {
        if (!ok) throw new AssertionError("aterrizaje del halo: " + message);
    }
}
