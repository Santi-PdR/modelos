package com.capatest.particle;

import com.capatest.CapaTestMod;
import net.minecraft.core.particles.ParticleType;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

/**
 * v1.23.0: UNA SOLA partícula, EXCLUSIVA de esta capa, con textura propia.
 *
 * Se retiran `capa_ember`, `capa_blight_mote` y `capa_shard`, y dejan de
 * usarse `DustParticleOptions` / `DustColorTransitionOptions` (vanilla).
 * El sprite `capatest:capa_spark_*` lo pinta
 * tools/texture_pipeline.py::build_spark_sprites() y lo interpreta
 * com.capatest.client.CapaSparkParticle con su propio SpriteSet.
 */
public final class CapaParticles {
    public static final DeferredRegister<ParticleType<?>> PARTICLES =
            DeferredRegister.create(ForgeRegistries.PARTICLE_TYPES, CapaTestMod.MOD_ID);

    /** Chispa rectangular vertical magenta/rosa, centro brillante, sin gravedad. */
    public static final RegistryObject<SimpleParticleType> CAPA_SPARK =
            PARTICLES.register("capa_spark", () -> new SimpleParticleType(false));

    private CapaParticles() {
    }

    public static void register(IEventBus modBus) {
        PARTICLES.register(modBus);
    }
}
