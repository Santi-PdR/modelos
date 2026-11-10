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

    private CapaParticles() {
    }

    public static void register(IEventBus modBus) {
        PARTICLES.register(modBus);
    }
}
