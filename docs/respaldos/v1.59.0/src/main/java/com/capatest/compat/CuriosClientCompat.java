package com.capatest.compat;

import com.capatest.CapaTestMod;
import com.capatest.client.CapaCurioRenderer;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import top.theillusivec4.curios.api.client.CuriosRendererRegistry;

/** Sólo se carga en cliente y sólo si Curios está presente. */
public final class CuriosClientCompat {
    private CuriosClientCompat() {
    }

    public static void register(IEventBus modBus) {
        modBus.addListener(CuriosClientCompat::onClientSetup);
    }

    private static void onClientSetup(FMLClientSetupEvent event) {
        event.enqueueWork(() -> CuriosRendererRegistry.register(
                CapaTestMod.CAPA_DETERIORER.get(), CapaCurioRenderer::new));
    }
}
