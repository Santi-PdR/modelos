package com.capatest.client;

import com.capatest.particle.CapaParticles;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Locale;

/** Measure the actual submitted quad from three cameras, without advancing the same spark. */
final class CapeEmberBankProbe {
    private static final String[] VIEWS = {"lateral", "alineada", "opuesta"};
    private record Quad(double bank, double side, double error) {}

    static void verify(Minecraft game, BlockPos pane, Path shots) throws IOException {
        var eye = new ArmorStand(game.level, pane.getX() - 2, pane.getY(), pane.getZ());
        Camera[] views = new Camera[3];
        for (int i = 0; i < views.length; i++) {
            float yaw = i * 90;
            eye.setYRot(yaw); eye.yRotO = yaw;
            // Camera reads the view (head), not the armor stand's body yaw.
            eye.setYHeadRot(yaw); eye.yHeadRotO = yaw;
            eye.setXRot(18); eye.xRotO = 18;
            views[i] = new Camera();
            views[i].setup(game.level, eye, false, false, 1);
        }
        double r0 = basis(views[0], 1, 0).x, r1 = basis(views[1], 1, 0).x, r2 = basis(views[2], 1, 0).x;
        require(Math.abs(r0) > .999 && Math.abs(r1) < .001 && Math.abs(r0 + r2) < .001, "invalid camera setup");
        double x = pane.getX() + .12, y = pane.getY() + .36;
        var rows = new StringBuilder("vuelo\tvista\tfase\tedad_ticks\tvida_ticks\tinclinacion_deg\tavance_x_b_tick\tlado_cuadro_b\terror_centro_b\n");
        for (String mode : new String[]{"libre", "panel", "vertical"}) {
            double z = pane.getZ() + (mode.equals("panel") ? .5 : 1.5);
            var particle = game.particleEngine.createParticle(CapaParticles.CAPA_SPARK.get(), x, y, z,
                    mode.equals("vertical") ? 0 : .04, .007, 0);
            require(particle instanceof CapaSparkParticle, "provider");
            try {
                record(particle, views, mode, rows);
            } finally {
                particle.remove();
            }
        }
        Files.writeString(shots.resolve("inclinacion-brasas-forge.tsv"), rows);
    }

    private static void record(Particle particle, Camera[] views, String mode, StringBuilder rows) {
        int life = particle.getLifetime(), tail = 1 + (int) Math.ceil(life * .85);
        for (int age = 1; age <= tail; ++age) {
            var boundary = age >= 3 && age <= 14 ? draw(particle, views[0], 1) : null;
            Vec3 previous = particle.getPos();
            particle.tick();
            if (boundary != null) {
                var after = draw(particle, views[0], 0);
                appearance(boundary, after);
                for (int k = 0; k < 12; k++)
                    require(Math.abs(boundary.xyz[k] - after.xyz[k]) < .00002, "tilt jumped at the tick boundary");
            }
            String stage = age == 6 ? "inicio" : age == 14 ? "avance" : age == tail ? "apagado" : null;
            if (stage == null) continue;
            Vec3 live = particle.getPos();
            var first = draw(particle, views[0], .5F);
            var center = previous.lerp(live, .5D);
            var q0 = axes(first, views[0], center);
            for (int i = 0; i < views.length; ++i) {
                var trace = i == 0 ? first : draw(particle, views[i], .5F);
                appearance(first, trace);
                var quad = axes(trace, views[i], center);
                require(Math.abs(quad.side() - q0.side()) < .00002, "bank resized the quad");
                require(Math.abs(quad.bank()) < .441, "bank exceeded its limit");
                if (i == 1) require(Math.abs(quad.bank()) < .001, "head-on view leaned");
                if (i == 2) require(Math.abs(quad.bank() + q0.bank()) < .001, "opposite view didn't mirror the tilt");
                rows.append(String.format(Locale.ROOT, "%s\t%s\t%s\t%d\t%d\t%.5f\t%.6f\t%.6f\t%.7f%n",
                        mode, VIEWS[i], stage, age, life, Math.toDegrees(quad.bank()), live.x - previous.x, quad.side(), quad.error()));
            }
            if (mode.equals("libre") && age <= 14) {
                double sideTravel = basis(views[0], 1, 0).x * (live.x - previous.x);
                require(Math.abs(q0.bank()) > (age == 6 ? .40 : .09) && q0.bank() * sideTravel < 0,
                        "free spark didn't lean into its motion");
            }
            if (mode.equals("vertical") || (mode.equals("panel") && age >= 14) || age == tail)
                require(Math.abs(q0.bank()) < .001, "stopped or cool spark still tilted");
            var replay = draw(particle, views[0], .5F);
            appearance(first, replay);
            require(Arrays.equals(first.xyz, replay.xyz) && particle.getPos().equals(live), "camera render changed the simulation or replay");
        }
    }

    private static CapeVertexProbe draw(Particle particle, Camera view, float partial) {
        var trace = new CapeVertexProbe();
        particle.render(trace, view, partial);
        require(trace.count == 4 && trace.light == LightTexture.FULL_BRIGHT && (trace.rgba & 255) > 0, "not one visible fullbright quad");
        return trace;
    }

    private static void appearance(CapeVertexProbe a, CapeVertexProbe b) {
        require(a.rgba == b.rgba && Arrays.equals(a.uv, b.uv), "tilt changed opacity, tint or atlas");
    }

    private static Quad axes(CapeVertexProbe trace, Camera view, Vec3 center) {
        Vec3 vertical = null, horizontal = null, sum = Vec3.ZERO;
        Vec3 origin = point(trace, 0);
        float u = trace.uv[0], v = trace.uv[1];
        for (int i = 0; i < 4; ++i) {
            var at = point(trace, i);
            sum = sum.add(at);
            float a = trace.uv[2*i], b = trace.uv[2*i+1];
            if (u == a && v != b) vertical = at.subtract(origin).scale(v > b ? 1 : -1);
            if (u != a && v == b) horizontal = at.subtract(origin);
        }
        require(vertical != null && horizontal != null, "unexpected atlas winding");
        double side = vertical.length();
        require(side > .01 && Math.abs(side - horizontal.length()) < .00002
                && Math.abs(vertical.dot(horizontal)) < .00001, "quad stopped being square");
        double bank = Math.atan2(-vertical.dot(basis(view, 1, 0)), vertical.dot(basis(view, 0, 1)));
        double error = sum.scale(.25).add(view.getPosition()).distanceTo(center);
        require(error < .00002, "bank moved the particle centre");
        return new Quad(bank, side, error);
    }

    private static Vec3 point(CapeVertexProbe trace, int i) {
        return new Vec3(trace.xyz[3*i], trace.xyz[3*i+1], trace.xyz[3*i+2]);
    }

    private static Vec3 basis(Camera view, float x, float y) {
        var axis = view.rotation().transform(new Vector3f(x, y, 0));
        return new Vec3(axis.x(), axis.y(), axis.z());
    }

    private static void require(boolean ok, String message) {
        if (!ok) throw new AssertionError("inclinación de brasas: " + message);
    }
}
