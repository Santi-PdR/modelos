package com.santipdr.holocore.client;

import com.santipdr.holocore.HoloCore;
import com.santipdr.holocore.common.ModItems;
import com.santipdr.holocore.network.RelicActionPacket;
import com.santipdr.holocore.network.RelicNetwork;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.RegisterClientCommandsEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import top.theillusivec4.curios.api.client.CuriosRendererRegistry;

/**
 * Todo lo que solo existe en el cliente: registro del renderer de Curios, tecla,
 * comandos de ajuste y limpieza de caches al salir del mundo.
 */
@Mod.EventBusSubscriber(modid = HoloCore.MOD_ID, value = Dist.CLIENT)
public final class RelicClientEvents {

    private RelicClientEvents() {
    }

    @Mod.EventBusSubscriber(modid = HoloCore.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
    public static final class ModBus {

        private ModBus() {
        }

        @SubscribeEvent
        public static void clientSetup(FMLClientSetupEvent event) {
            // Curios pide registrar el renderer en el setup de cliente; el
            // supplier se resuelve luego en EntityRenderersEvent.AddLayers.
            CuriosRendererRegistry.register(ModItems.HOLOGRAPHIC_CORE.get(), RelicCurioRenderer::new);
        }

        @SubscribeEvent
        public static void registerKeys(RegisterKeyMappingsEvent event) {
            event.register(RelicKeys.TOGGLE);
        }

        @SubscribeEvent
        public static void registerCommands(RegisterClientCommandsEvent event) {
            RelicClientCommands.register(event.getDispatcher());
        }
    }

    @SubscribeEvent
    public static void onClientTick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        if (minecraft.level == null) {
            RelicVisuals.clear();
            return;
        }
        RelicVisuals.prune(minecraft.level.getGameTime());

        while (RelicKeys.TOGGLE.consumeClick()) {
            RelicNetwork.sendToServer(new RelicActionPacket(RelicActionPacket.Action.TOGGLE));
        }
    }

    @SubscribeEvent
    public static void onLoggingOut(ClientPlayerNetworkEvent.LoggingOut event) {
        RelicVisuals.clear();
        ClientRelicStates.clear();
    }
}
