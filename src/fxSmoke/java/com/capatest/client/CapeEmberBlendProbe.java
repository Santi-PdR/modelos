package com.capatest.client;

import com.capatest.particle.CapaParticles;
import net.minecraft.client.Minecraft;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.RandomSource;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** Check the actual particle atlas and submitted quad, including the legacy three-sprite layout. */
final class CapeEmberBlendProbe {
    private static final int STEPS = CapeEmber.LAST_SPRITE / 2;

    static void verify(Minecraft game, BlockPos panel, Path shots) throws IOException {
        var atlas = (TextureAtlas) game.getTextureManager().getTexture(TextureAtlas.LOCATION_PARTICLES);
        double x = panel.getX() + .12, y = panel.getY() + .36, z = panel.getZ() + 1.5;
        var sprite = CapaParticles.CAPA_SPARK.get();
        Particle live = game.particleEngine.createParticle(sprite, x, y, z, .04, .007, 0);
        require(live instanceof CapaSparkParticle, "particle provider missing");
        var legacy = new CapaSparkParticle(game.level, x, y, z, .04, .007, 0, new SpriteSet() {
            @Override public TextureAtlasSprite get(int index, int span) { return key(atlas, index * 2 / span); }
            @Override public TextureAtlasSprite get(RandomSource random) { return key(atlas, random.nextInt(3)); }
        });
        StringBuilder rows = new StringBuilder("secuencia\tvida_ticks\tinstante_ticks\tsprite\tvertices\talfa\n");
        try {
            record(game, live, atlas, true, rows);
            record(game, legacy, atlas, false, rows);
        } finally {
            live.remove();
            legacy.remove();
        }
        Files.writeString(shots.resolve("secuencia-brasa-forge.tsv"), rows);
    }

    private static TextureAtlasSprite key(TextureAtlas atlas, int index) {
        return atlas.getSprite(new ResourceLocation("capatest", "capa_spark_" + index));
    }

    private static void record(Minecraft game, Particle particle, TextureAtlas atlas, boolean blends,
                               StringBuilder rows) {
        int life = particle.getLifetime(), age = 0;
        double[] centers = {.25, .63};
        int[] offsets = {-3, -1, 0, 1, 3};
        int[] frames = {0, 3, STEPS/2, STEPS-3, STEPS};
        for (int pair = 0; pair < centers.length; ++pair) {
            for (int i = 0; i < offsets.length; ++i) {
                double moment = centers[pair] * life + offsets[i];
                // Away from the exact discrete cut in the legacy control.
                if (!blends && offsets[i] == 0) moment += .001;
                int tick = (int) moment;
                while (age < tick + 1) { particle.tick(); age++; }
                float partial = (float) (moment - tick);
                int k = frames[i];
                String name = blends && k > 0 && k < STEPS
                        ? String.format(Locale.ROOT, "capa_spark_mix_%d%d_%02d", pair, pair+1, k)
                        : "capa_spark_" + (pair + (offsets[i] >= (blends ? 3 : 0) ? 1 : 0));
                var id = new ResourceLocation("capatest", name);
                var expected = atlas.getSprite(id);
                require(expected.contents().name().equals(id), "missing atlas sprite " + name);
                var pos = particle.getPos();
                var actual = draw(game, particle, partial);
                require(actual.count == 4 && actual.light == LightTexture.FULL_BRIGHT && (actual.rgba & 255) > 0,
                        "transition did not submit a single fullbright quad");
                require(actual.minU == expected.getU0() && actual.maxU == expected.getU1()
                                && actual.minV == expected.getV0() && actual.maxV == expected.getV1(),
                        "expected atlas sprite " + name + " at tick " + moment + " for life " + life);
                draw(game, particle, Math.min(1, partial + .2F));
                var replay = draw(game, particle, partial);
                require(actual.rgba == replay.rgba && actual.light == replay.light
                                && actual.minU == replay.minU && actual.maxU == replay.maxU
                                && actual.minV == replay.minV && actual.maxV == replay.maxV
                                && actual.count == replay.count,
                        "sub-tick replay changed appearance or atlas frame");
                require(pos.equals(particle.getPos()), "drawing advanced the particle position");
                rows.append(String.format(Locale.ROOT, "%s\t%d\t%.5f\t%s\t%d\t%d%n",
                        blends ? "interpolada" : "tres-sprites", life, moment, name, actual.count, actual.rgba & 255));
            }
        }
    }

    private static CapeVertexProbe draw(Minecraft game, Particle particle, float partial) {
        var probe = new CapeVertexProbe();
        particle.render(probe, game.gameRenderer.getMainCamera(), partial);
        return probe;
    }

    private static void require(boolean ok, String message) {
        if (!ok) throw new AssertionError("ember sprites: " + message);
    }
}
