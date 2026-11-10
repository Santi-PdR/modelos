package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.particle.CapaParticles;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterParticleProvidersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Registro del proveedor de partículas, sólo en cliente y en el mod bus. */
@Mod.EventBusSubscriber(modid = CapaTestMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class CapaParticleRegistration {
    private CapaParticleRegistration() {
    }

    @SubscribeEvent
    public static void onRegisterParticleProviders(RegisterParticleProvidersEvent event) {
        event.registerSpriteSet(CapaParticles.CAPA_EMBER.get(), CapaEmberParticle.Provider::new);
    }
}
