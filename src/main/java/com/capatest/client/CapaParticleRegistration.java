package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.particle.CapaParticles;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterParticleProvidersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Registro del proveedor de partículas, sólo en cliente y en el mod bus.
 * v1.3.0: sigue usando registerSpriteSet (obligatorio para
 * PARTICLE_SHEET_TRANSLUCENT), pero el provider aplica fade, deriva mínima y
 * alpha bajo; la frecuencia de emisión se controla en spawnAura.
 *
 * v1.9.0 registra además la mota fría de Blight Star con su propio SpriteSet:
 * las brasas cálidas y las motas cian conviven sin mezclar texturas.
 */
@Mod.EventBusSubscriber(modid = CapaTestMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class CapaParticleRegistration {
    private CapaParticleRegistration() {
    }

    @SubscribeEvent
    public static void onRegisterParticleProviders(RegisterParticleProvidersEvent event) {
        event.registerSpriteSet(CapaParticles.CAPA_EMBER.get(), CapaEmberParticle.Provider::new);
        event.registerSpriteSet(CapaParticles.CAPA_BLIGHT_MOTE.get(), CapaBlightParticle.Provider::new);
        // v1224: el tercer SpriteSet reutiliza el provider de brasa (fade y
        // deriva minima) pero con los cristales alargados de capa_shard_*.
        event.registerSpriteSet(CapaParticles.CAPA_SHARD.get(), CapaEmberParticle.Provider::new);
    }
}
