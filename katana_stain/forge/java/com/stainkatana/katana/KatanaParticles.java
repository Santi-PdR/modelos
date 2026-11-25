package com.stainkatana.katana;

import com.stainkatana.StainKatanaMod;
import net.minecraft.core.particles.ParticleType;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

/** Tipos para recursos adaptados de Better Combat Particle; licencia en META-INF. */
public final class KatanaParticles {
    private static final DeferredRegister<ParticleType<?>> TYPES = DeferredRegister.create(ForgeRegistries.PARTICLE_TYPES, StainKatanaMod.MOD_ID);
    public static final RegistryObject<SimpleParticleType> SLASH = TYPES.register("slash_arc", () -> new SimpleParticleType(false));
    public static final RegistryObject<SimpleParticleType> SHARD = TYPES.register("blood_shard", () -> new SimpleParticleType(false));
    public static final RegistryObject<SimpleParticleType> PULSE = TYPES.register("blood_pulse", () -> new SimpleParticleType(false));
    public static final RegistryObject<SimpleParticleType> RING = TYPES.register("blood_ring", () -> new SimpleParticleType(false));
    public static final RegistryObject<SimpleParticleType> MOTE = TYPES.register("blood_mote", () -> new SimpleParticleType(false));
    private KatanaParticles() { }
    public static void register(IEventBus bus) { TYPES.register(bus); }
}
