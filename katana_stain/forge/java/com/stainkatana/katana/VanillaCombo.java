package com.stainkatana.katana;

import com.stainkatana.StainKatanaMod;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;

/** Vanilla-only damage progression. Better Combat owns its own attack attributes. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class VanillaCombo {
    private record Pending(UUID target, long time, boolean charged) { }
    private record Chain(int count, long time) { }
    private static final Map<UUID, Pending> pending = new HashMap<>();
    private static final Map<UUID, Chain> chains = new HashMap<>();
    private VanillaCombo() { }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void attack(AttackEntityEvent event) {
        if (ModList.get().isLoaded("bettercombat") || !(event.getEntity() instanceof ServerPlayer player)
                || !(event.getTarget() instanceof LivingEntity target)
                || !(player.getMainHandItem().getItem() instanceof StainKatanaItem)) return;
        long now = player.getServer().overworld().getGameTime();
        pending.put(player.getUUID(), new Pending(target.getUUID(), now, player.getAttackStrengthScale(0.5F) >= 0.9F));
    }
    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void hurt(LivingHurtEvent event) {
        if (!(event.getSource().getEntity() instanceof ServerPlayer player)
                || event.getSource().getDirectEntity() != player || event.getAmount() <= 0) return;
        Pending p = pending.remove(player.getUUID());
        long now = player.getServer().overworld().getGameTime();
        if (p == null || p.time() != now || !p.target().equals(event.getEntity().getUUID()) || !p.charged()) return;
        Chain prior = chains.get(player.getUUID());
        int count = prior == null || now - prior.time() > 60 ? 1 : prior.count() % 4 + 1;
        chains.put(player.getUUID(), new Chain(count, now));
        if (count == 4) event.setAmount(event.getAmount() * 1.6F);
    }
    @SubscribeEvent public static void tick(TickEvent.PlayerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.player instanceof ServerPlayer player)) return;
        long now = player.getServer().overworld().getGameTime();
        Pending p = pending.get(player.getUUID());
        if (p != null && p.time() < now) pending.remove(player.getUUID());
        Chain c = chains.get(player.getUUID());
        if (c != null && (now - c.time() > 60 || !(player.getMainHandItem().getItem() instanceof StainKatanaItem))) chains.remove(player.getUUID());
    }
    @SubscribeEvent public static void logout(PlayerEvent.PlayerLoggedOutEvent e) {
        pending.remove(e.getEntity().getUUID()); chains.remove(e.getEntity().getUUID());
    }
    @SubscribeEvent public static void stop(ServerStoppedEvent e) { pending.clear(); chains.clear(); }
}
