package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.item.ItemStack;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** The client's actual equipped mesh and light layer on a controlled change of pace. */
final class CapeHaloWakeProbe {
    private static final int START = 80, BRAKE = 48, END = 96;
    private static final float PARTIAL = .375F;
    private static final double SPEED = .16;

    static int[] verify(Minecraft game, ItemStack stack, Path dir) throws IOException {
        var armor = new HumanoidModel<ArmorStand>(game.getEntityModels().bakeLayer(ModelLayers.PLAYER_INNER_ARMOR));
        var actor = stand(game);
        var chest = new CapaArmorRenderer();
        var alternate = new CapaArmorRenderer();
        var expected = new CapeResponse();
        var rows = new StringBuilder("caso\ttick\tvelocidad_b_tick\tborde_base\tinterior_base\tborde\tinterior\tvertices\n");
        int[] gpu = new int[4];
        int[] peakTicks = new int[4];
        double[] peaks = new double[4];
        for (int tick = 0; tick <= END; ++tick) {
            double speed = tick > 0 && tick <= BRAKE ? SPEED : 0;
            var draw = draw(tick <= 4 ? chest : alternate, actor, stack, armor, tick, speed, 0, PARTIAL);
            double time = time(tick);
            expected.sample(time, 2.2 * speed, 0, 0, 0, 0, 0, 0);
            int base = CapeNocturne.gains(1, time, actor.getId()).packed();
            require(draw.light == CapeNocturne.gains(1, time, actor.getId(), expected.speedWake()).packed(),
                    "submitted gains do not follow the measured travel at tick " + tick);
            var color = CapeState.IDLE.glow(time);
            require(draw.rgba == ((int) (color.red()*255) << 24 | (int) (color.green()*255) << 16
                    | (int) (color.blue()*255) << 8 | 255), "pulse changed the core tint");
            row(rows, "cueva", tick, speed, base, draw);
            int group = tick <= BRAKE ? 0 : 2;
            double edge = edge(draw.light) - edge(base), lip = inner(draw.light) - inner(base);
            if (lip > peaks[group]) { peaks[group] = lip; peakTicks[group] = tick; }
            if (edge > peaks[group+1]) { peaks[group+1] = edge; peakTicks[group+1] = tick; }
            if (tick == 0 || tick == BRAKE || tick == END) require(draw.light == base, "wake didn't settle at constant pace");
            if (tick == 4) {
                var replay = draw(alternate, actor, stack, armor, tick, 0, 15, .125F);
                require(replay.equals(draw), "clock or wake changed on an earlier replay in another renderer");
                row(rows, "repeticion", tick, 0, base, replay);
                var other = stand(game);
                var independent = draw(chest, other, stack, armor, tick, SPEED, 0, PARTIAL);
                require(independent.light == CapeNocturne.gains(1, time, other.getId()).packed(),
                        "a new wearer inherited the motion flash");
                gpu[0] = base;
                gpu[1] = draw.light;
            }
            if (tick == BRAKE + 8) {
                gpu[2] = base;
                gpu[3] = draw.light;
            }
        }
        for (int i = 0; i < peaks.length; ++i) require(.27 < peaks[i] && peaks[i] < .35, "weak/strong wake " + peaks[i]);
        require(peakTicks[1] >= peakTicks[0] + 4 && peakTicks[3] >= peakTicks[2] + 4, "both bands peaked at once");

        for (int light : new int[]{8, 15}) {
            var wearer = stand(game);
            double dusk = CapeNocturne.darkness(light);
            for (int tick = 0; tick <= 9; ++tick) {
                double speed = tick == 0 ? 0 : SPEED;
                var draw = draw(chest, wearer, stack, armor, tick, speed, light, PARTIAL);
                double t = time(tick);
                int base = CapeNocturne.gains(dusk, t, wearer.getId()).packed();
                row(rows, light == 15 ? "dia" : "penumbra", tick, speed, base, draw);
                if (light == 15) require(draw.light == base, "a light pulse in full daylight");
                else if (tick == 4) require(inner(draw.light) - inner(base) > .067 && inner(draw.light) - inner(base) < .09,
                        "mixed light didn't damp the wake");
            }
        }
        var flash = draw(alternate, actor, stack, armor, END + 1, SPEED, 0, PARTIAL);
        require(inner(flash.light) > inner(CapeNocturne.gains(1, time(END + 1), actor.getId()).packed()) + .12,
                "missing flare just before the teleport test");
        actor.xo = actor.getX() - 8;
        var cut = draw(alternate, actor, stack, armor, END + 2, SPEED, 0, PARTIAL);
        int base = CapeNocturne.gains(1, time(END + 2), actor.getId()).packed();
        row(rows, "teletransporte", END + 2, SPEED, base, cut);
        require(cut.light == base, "teleport retained the old motion halo");
        Files.writeString(dir.resolve("pulso-halo-forge.tsv"), rows);
        return gpu;
    }

    private static ArmorStand stand(Minecraft game) {
        var stand = new ArmorStand(game.level, 0, 64, 0);
        stand.yo = stand.getY();
        stand.setOnGround(true);
        return stand;
    }

    private record Draw(int light, int rgba, int vertices) {}

    private static Draw draw(CapaArmorRenderer renderer, ArmorStand wearer, ItemStack stack,
                             HumanoidModel<ArmorStand> armor, int tick, double speed, int light, float partial) {
        wearer.tickCount = START + tick;
        wearer.setDeltaMovement(0, 0, speed);
        var base = new CapeVertexProbe();
        var halo = new CapeVertexProbe();
        var type = CapeBloom.wornLight(CapeBloom.Mode.HALO);
        MultiBufferSource sinks = pass -> pass == type ? halo : base;
        var pose = new PoseStack();
        renderer.prepForRender(wearer, stack, EquipmentSlot.CHEST, armor);
        renderer.defaultRender(pose, (CapaDeteriorerItem) stack.getItem(), sinks, null, null, 0, partial,
                LightTexture.pack(light, 0));
        require(pose.clear() && base.count > 0 && halo.count == base.count, "light pass added/lost geometry");
        return new Draw(halo.light, halo.rgba, halo.count);
    }

    private static double time(int tick) { return (START + tick + (double) PARTIAL) / 20; }
    private static double edge(int light) { return (short) light / 4096.0; }
    private static double inner(int light) { return (short) (light >>> 16) / 4096.0; }

    private static void row(StringBuilder rows, String which, int tick, double speed, int base, Draw draw) {
        rows.append(String.format(Locale.ROOT, "%s\t%d\t%.3f\t%.8f\t%.8f\t%.8f\t%.8f\t%d%n",
                which, tick, speed, edge(base), inner(base), edge(draw.light), inner(draw.light), draw.vertices));
    }

    private static void require(boolean ok, String message) {
        if (!ok) throw new AssertionError("pulso del halo: " + message);
    }
}
