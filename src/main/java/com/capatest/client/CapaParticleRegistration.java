package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.particle.CapaParticles;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterParticleProvidersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * v1.23.0: un ÚNICO SpriteSet, el de la chispa exclusiva de la capa.
 *
 * `registerSpriteSet` es obligatorio para PARTICLE_SHEET_TRANSLUCENT:
 * sin él Minecraft no carga `capatest:capa_spark_0..2`. Ya no se registran
 * brasas, motas frías ni esquirlas, y no se usa ningún tipo vanilla.
 */
@Mod.EventBusSubscriber(modid = CapaTestMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class CapaParticleRegistration {
    private CapaParticleRegistration() {
    }

    @SubscribeEvent
    public static void onRegisterParticleProviders(RegisterParticleProvidersEvent event) {
        event.registerSpriteSet(CapaParticles.CAPA_SPARK.get(), CapaSparkParticle.Provider::new);
    }
}
