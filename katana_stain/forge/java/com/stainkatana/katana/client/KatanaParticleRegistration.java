package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.KatanaParticles;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterParticleProvidersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class KatanaParticleRegistration {
    private KatanaParticleRegistration() { }
    @SubscribeEvent public static void register(RegisterParticleProvidersEvent event) {
        event.registerSpriteSet(KatanaParticles.SLASH.get(), KatanaParticle.SlashProvider::new);
        event.registerSpriteSet(KatanaParticles.SHARD.get(), KatanaParticle.ShardProvider::new);
        event.registerSpriteSet(KatanaParticles.PULSE.get(), KatanaParticle.PulseProvider::new);
        event.registerSpriteSet(KatanaParticles.RING.get(), KatanaParticle.RingProvider::new);
        event.registerSpriteSet(KatanaParticles.MOTE.get(), KatanaParticle.MoteProvider::new);
    }
}
