package com.santipdr.holocore.client;

import com.santipdr.holocore.HoloCore;
import com.santipdr.holocore.common.ModItems;
import com.santipdr.holocore.common.RelicServer;
import com.santipdr.holocore.network.RelicActionPacket;
import com.santipdr.holocore.network.RelicNetwork;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.RegisterClientCommandsEvent;
import net.minecraftforge.client.event.RegisterClientReloadListenersEvent;
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

    /**
     * Ticks en los que se considera que el portador se esta viendo. Se cuenta
     * desde el ultimo dibujo, asi que un portador lejos ({@code fade = 0}) o en
     * primera persona deja de contar y sus animaciones no se encolan.
     */
    private static final long VISIBLE_WINDOW_TICKS = 20L;

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

        /**
         * El shader propio se compila en cada recarga de recursos, no al cargar
         * el mod: asi se rehace si el jugador cambia de pack.
         */
        @SubscribeEvent
        public static void registerReloadListeners(RegisterClientReloadListenersEvent event) {
            RelicShaders.register(event);
        }

    }

    /**
     * Los comandos se registran en el bus FORGE (RegisterClientCommandsEvent no
     * es un IModBusEvent); ponerlo en la clase del bus MOD rompia el arranque.
     */
    @SubscribeEvent
    public static void registerCommands(RegisterClientCommandsEvent event) {
        RelicClientCommands.register(event.getDispatcher());
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
        tickLocalRelic(minecraft);

        while (RelicKeys.TOGGLE.consumeClick()) {
            RelicNetwork.sendToServer(new RelicActionPacket(RelicActionPacket.Action.TOGGLE));
        }
    }

    /**
     * Actualiza la reliquia del jugador local <b>aunque no se dibuje</b>.
     *
     * <p>Curios solo llama al renderer cuando la entidad se dibuja, y en primera
     * persona el jugador local no se dibuja: hasta 1.0.18 la maquina de estados se
     * quedaba congelada (sin alerta, sin variaciones de reposo, con
     * {@code /relic info} sin estado) y el visual ademas se podaba a los 40 ticks
     * sin dibujarse, con lo que al volver a tercera persona la reliquia arrancaba
     * de cero con su {@code activation}.</p>
     *
     * <p>El estado queda vivo; las animaciones que habrian tocado no se encolan
     * mientras no se ve (ver {@code RelicAnimatable.update(..., visible)}), para no
     * reproducir de golpe lo que paso mientras mirabas a otro lado.</p>
     */
    private static void tickLocalRelic(Minecraft minecraft) {
        LocalPlayer player = minecraft.player;
        if (player == null || player.isSpectator() || player.level() == null) {
            return;
        }
        // Curios responde en cliente: es una busqueda en las ranuras del jugador
        // local, no una pregunta al servidor.
        if (RelicServer.findRelic(player).isEmpty()) {
            return;
        }
        // existing() primero: computeIfAbsent con un lambda que captura al
        // jugador reserva un objeto por tick, y esto corre 20 veces por segundo.
        RelicVisuals.RelicVisual visual = RelicVisuals.existing(player);
        if (visual == null) {
            visual = RelicVisuals.visual(player);
        }
        RelicAnimatable animatable = visual.animatable();
        long now = player.level().getGameTime();
        boolean visible = now - animatable.lastRenderTick() <= VISIBLE_WINDOW_TICKS;
        animatable.update(player, ClientRelicStates.get(player.getUUID()), 1.0F, visible);
        // El brillo (color y fuerzas) se interpola con tiempo real: se mantiene al
        // dia para que al girarse la camara ya este en el estado correcto.
        visual.glow().update(animatable.loopState(), animatable.flash());
    }

    @SubscribeEvent
    public static void onLoggingOut(ClientPlayerNetworkEvent.LoggingOut event) {
        RelicVisuals.clear();
        ClientRelicStates.clear();
    }
}
