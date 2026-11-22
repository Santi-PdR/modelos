package com.santipdr.holocore.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.santipdr.holocore.HoloCore;
import com.santipdr.holocore.common.ModItems;
import com.santipdr.holocore.common.RelicServer;
import com.santipdr.holocore.network.RelicActionPacket;
import com.santipdr.holocore.network.RelicNetwork;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import org.joml.Vector3f;
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

    /** Cada cuantos ticks se tiran los estados de jugadores que ya no estan. */
    private static final int STATE_PRUNE_TICKS = 200;

    private static int pruneCountdown;

    /** Distancia por defecto (bloques) de la vista previa delante de la camara. */
    public static final float PREVIEW_DEFAULT_DISTANCE = 2.5F;

    private static boolean preview;
    private static float previewDistance = PREVIEW_DEFAULT_DISTANCE;

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
        pruneRemoteStates(minecraft);
        tickLocalRelic(minecraft);

        while (RelicKeys.TOGGLE.consumeClick()) {
            RelicNetwork.sendToServer(new RelicActionPacket(RelicActionPacket.Action.TOGGLE));
        }
    }

    /**
     * Tira los estados de jugadores que ya no estan en el mundo (salieron del
     * servidor o cambiaron de dimension). Al volver a verlos, el servidor reenvia
     * su estado en {@code StartTracking} o al entrar, asi que no se pierde nada.
     */
    private static void pruneRemoteStates(Minecraft minecraft) {
        if (--pruneCountdown > 0) {
            return;
        }
        pruneCountdown = STATE_PRUNE_TICKS;
        java.util.Set<java.util.UUID> vivos = new java.util.HashSet<>();
        for (var player : minecraft.level.players()) {
            vivos.add(player.getUUID());
        }
        ClientRelicStates.retain(vivos);
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
            // Sin reliquia no hay nada que vigilar, y la vista previa dejaria de
            // tener sentido (dibujaria un visual a punto de podarse).
            preview = false;
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

    /** {@code /relic preview}: dibuja la reliquia delante de la camara. */
    public static void preview(boolean on, float distance) {
        preview = on;
        previewDistance = distance;
    }

    public static boolean previewEnabled() {
        return preview;
    }

    public static float previewDistance() {
        return previewDistance;
    }

    /**
     * Vista previa: la misma reliquia del jugador local, dibujada a una distancia
     * fija delante de la camara, con los mismos cuatro pases y el mismo aura.
     *
     * <p>Sirve para mirar el brillo y el aura de cerca y siempre a la misma
     * distancia (sobre nieve, arena, cueva) sin depender de la posicion del hombro
     * ni de ponerse en tercera persona. No toca nada del render normal: es un
     * dibujo extra mientras el comando este activo.</p>
     */
    @SubscribeEvent
    public static void onRenderStage(RenderLevelStageEvent event) {
        if (!preview || event.getStage() != RenderLevelStageEvent.Stage.AFTER_ENTITIES) {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        if (player == null || minecraft.level == null) {
            return;
        }
        RelicVisuals.RelicVisual visual = RelicVisuals.existing(player);
        if (visual == null) {
            return;
        }
        Camera camera = minecraft.gameRenderer.getMainCamera();
        Vector3f look = camera.getLookVector();
        PoseStack poseStack = event.getPoseStack();
        poseStack.pushPose();
        poseStack.translate(look.x() * previewDistance, look.y() * previewDistance - 0.15D,
                look.z() * previewDistance);

        float partialTick = event.getPartialTick();
        RelicAnimatable animatable = visual.animatable();
        // Se esta viendo: que encole sus animaciones como en tercera persona.
        animatable.markRendered(minecraft.level.getGameTime());
        visual.glow().update(animatable.loopState(), animatable.flash());

        MultiBufferSource.BufferSource buffers = minecraft.renderBuffers().bufferSource();
        visual.renderer().renderHologram(poseStack, animatable, buffers, partialTick,
                LightTexture.FULL_BRIGHT, visual.glow(), 1.0F);
        if (RelicAura.enabled()) {
            RelicAura.render(poseStack, buffers, partialTick, animatable.loopState(), visual.glow(), 1.0F);
        }
        buffers.endBatch();
        poseStack.popPose();
    }

    @SubscribeEvent
    public static void onLoggingOut(ClientPlayerNetworkEvent.LoggingOut event) {
        preview = false;
        RelicVisuals.clear();
        ClientRelicStates.clear();
    }
}
