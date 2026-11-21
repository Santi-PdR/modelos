package com.santipdr.holocore.common;

import com.santipdr.holocore.network.RelicNetwork;
import com.santipdr.holocore.network.RelicStatePacket;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.UnaryOperator;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerXpEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.SlotResult;

/**
 * Autoridad del servidor sobre la reliquia.
 *
 * <p>El estado "activa/dormida" vive en el NBT del ItemStack para persistir, y
 * los eventos puntuales son sellos de {@code gameTime} que se replican a todos
 * los clientes: el cliente compara el sello con el ultimo que vio y dispara la
 * animacion una sola vez. Asi el mismo evento se ve igual en todos los clientes
 * y no hace falta sincronizar el reloj de animacion.</p>
 */
public final class RelicServer {

    private static final Map<UUID, Stamps> STAMPS = new ConcurrentHashMap<>();

    private RelicServer() {
    }

    public record Stamps(long hit, long pulse, long release, long bump) {
        public static final Stamps EMPTY = new Stamps(0L, 0L, 0L, 0L);

        Stamps withHit(long value) {
            return new Stamps(value, pulse, release, bump);
        }

        Stamps withPulse(long value) {
            return new Stamps(hit, value, release, bump);
        }

        Stamps withRelease(long value) {
            return new Stamps(hit, pulse, value, bump);
        }

        Stamps withBump(long value) {
            return new Stamps(hit, pulse, release, value);
        }
    }

    public static Optional<ItemStack> findRelic(LivingEntity entity) {
        return CuriosApi.getCuriosInventory(entity).resolve()
                .flatMap(handler -> handler.findFirstCurio(ModItems.HOLOGRAPHIC_CORE.get()))
                .map(SlotResult::stack);
    }

    private static Stamps stamps(ServerPlayer player) {
        return STAMPS.getOrDefault(player.getUUID(), Stamps.EMPTY);
    }

    private static Stamps update(ServerPlayer player, UnaryOperator<Stamps> change) {
        return STAMPS.compute(player.getUUID(),
                (uuid, current) -> change.apply(current == null ? Stamps.EMPTY : current));
    }

    private static RelicStatePacket packetOf(ServerPlayer player, boolean active) {
        Stamps s = stamps(player);
        return new RelicStatePacket(player.getUUID(), active, s.hit(), s.pulse(), s.release(), s.bump());
    }

    /** Reenvia el estado completo a todos los clientes. */
    public static void broadcast(ServerPlayer player, boolean active) {
        if (player.level().isClientSide()) {
            return;
        }
        RelicNetwork.toAll(packetOf(player, active));
    }

    /** Llamado al equipar/desequipar (server side) para que el cambio se vea ya. */
    public static void syncFromStack(ServerPlayer player, ItemStack stack) {
        if (player.level().isClientSide()) {
            return;
        }
        broadcast(player, !stack.isEmpty() && HolographicCoreItem.isActive(stack));
    }

    public static void toggle(ServerPlayer player) {
        Optional<ItemStack> relic = findRelic(player);
        if (relic.isEmpty()) {
            player.displayClientMessage(Component.translatable("message.holocore.not_equipped"), true);
            return;
        }
        ItemStack stack = relic.get();
        boolean active = !HolographicCoreItem.isActive(stack);
        HolographicCoreItem.setActive(stack, active);
        broadcast(player, active);
        player.displayClientMessage(Component.translatable(
                active ? "message.holocore.awake" : "message.holocore.dormant"), true);
    }

    public static void pulse(ServerPlayer player) {
        if (findRelic(player).isEmpty()) {
            player.displayClientMessage(Component.translatable("message.holocore.not_equipped"), true);
            return;
        }
        update(player, s -> s.withPulse(player.level().getGameTime()));
        broadcast(player, HolographicCoreItem.isActive(findRelic(player).orElse(ItemStack.EMPTY)));
    }

    public static void release(ServerPlayer player) {
        if (findRelic(player).isEmpty()) {
            player.displayClientMessage(Component.translatable("message.holocore.not_equipped"), true);
            return;
        }
        update(player, s -> s.withRelease(player.level().getGameTime()));
        broadcast(player, HolographicCoreItem.isActive(findRelic(player).orElse(ItemStack.EMPTY)));
    }

    // ------------------------------------------------------------------
    // Eventos
    // ------------------------------------------------------------------

    @SubscribeEvent
    public static void onLivingHurt(LivingHurtEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player) || player.level().isClientSide()) {
            return;
        }
        if (findRelic(player).isEmpty()) {
            return;
        }
        update(player, s -> s.withHit(player.level().getGameTime()));
        broadcast(player, HolographicCoreItem.isActive(findRelic(player).orElse(ItemStack.EMPTY)));
    }

    @SubscribeEvent
    public static void onLevelChange(PlayerXpEvent.LevelChange event) {
        if (!(event.getEntity() instanceof ServerPlayer player) || event.getLevels() <= 0) {
            return;
        }
        if (findRelic(player).isEmpty()) {
            return;
        }
        update(player, s -> s.withBump(player.level().getGameTime()));
        broadcast(player, HolographicCoreItem.isActive(findRelic(player).orElse(ItemStack.EMPTY)));
    }

    @SubscribeEvent
    public static void onLoggedIn(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player) || player.level().isClientSide()) {
            return;
        }
        // El que entra necesita saber el estado de todos; el resto necesita el suyo.
        for (ServerPlayer other : player.server.getPlayerList().getPlayers()) {
            boolean active = findRelic(other)
                    .map(HolographicCoreItem::isActive)
                    .orElse(false);
            RelicNetwork.toPlayer(player, packetOf(other, active));
        }
        syncFromStack(player, findRelic(player).orElse(ItemStack.EMPTY));
    }

    @SubscribeEvent
    public static void onStartTracking(PlayerEvent.StartTracking event) {
        if (!(event.getTarget() instanceof ServerPlayer target)
                || !(event.getEntity() instanceof ServerPlayer tracker)
                || target.level().isClientSide()) {
            return;
        }
        boolean active = findRelic(target).map(HolographicCoreItem::isActive).orElse(false);
        RelicNetwork.toPlayer(tracker, packetOf(target, active));
    }

    @SubscribeEvent
    public static void onLoggedOut(PlayerEvent.PlayerLoggedOutEvent event) {
        STAMPS.remove(event.getEntity().getUUID());
    }

    @SubscribeEvent
    public static void onRespawn(PlayerEvent.PlayerRespawnEvent event) {
        if (event.getEntity() instanceof ServerPlayer player && !player.level().isClientSide()) {
            syncFromStack(player, findRelic(player).orElse(ItemStack.EMPTY));
        }
    }

    @SubscribeEvent
    public static void onChangedDimension(PlayerEvent.PlayerChangedDimensionEvent event) {
        if (event.getEntity() instanceof ServerPlayer player && !player.level().isClientSide()) {
            syncFromStack(player, findRelic(player).orElse(ItemStack.EMPTY));
        }
    }
}
