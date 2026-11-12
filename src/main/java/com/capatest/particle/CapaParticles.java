package com.capatest.particle;

import com.capatest.CapaTestMod;
import net.minecraft.core.particles.ParticleType;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public final class CapaParticles {
    public static final DeferredRegister<ParticleType<?>> PARTICLES =
            DeferredRegister.create(ForgeRegistries.PARTICLE_TYPES, CapaTestMod.MOD_ID);

    /** Brasa propia del mod: 3 sprites animados definidos en particles/capa_ember.json. */
    public static final RegistryObject<SimpleParticleType> CAPA_EMBER =
            PARTICLES.register("capa_ember", () -> new SimpleParticleType(false));

    /** v1.9.0: mota fría y MUDA de Blight Star, 3 sprites en particles/capa_blight_mote.json. */
    public static final RegistryObject<SimpleParticleType> CAPA_BLIGHT_MOTE =
            PARTICLES.register("capa_blight_mote", () -> new SimpleParticleType(false));

    /** v1224: esquirla de deterioro, 3 sprites en particles/capa_shard.json. */
    public static final RegistryObject<SimpleParticleType> CAPA_SHARD =
            PARTICLES.register("capa_shard", () -> new SimpleParticleType(false));

    private CapaParticles() {
    }

    public static void register(IEventBus modBus) {
        PARTICLES.register(modBus);
    }
}
