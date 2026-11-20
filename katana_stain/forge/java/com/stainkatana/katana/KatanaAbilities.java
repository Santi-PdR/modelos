package com.stainkatana.katana;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import com.stainkatana.StainKatanaMod;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.Level;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;

/** Combate resuelto en servidor: blancos, PvP, daño y cooldown no vienen del cliente. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaAbilities {
    private static final String COOLDOWNS = "StainKatanaAbilities";
    private static final int[] COOLDOWN = {240, 100, 900};
    // Timings in server ticks: wind-up, then recovery. Damage is revalidated at impact.
    private static final int[] IMPACT_TICK = {2, 7, 7};
    private static final int[] RECOVERY_TICK = {6, 16, 29};
    private static final int[] FADE_OUT_TICK = {4, 13, 24};
    private static final Map<UUID, Cast> CASTS = new ConcurrentHashMap<>();
    private static final class Cast {
        final int ability;
        final ItemStack stack;
        final ResourceKey<Level> dimension;
        final long start;
        final UUID markedTarget;
        boolean impacted;
        boolean followUpStarted;
        boolean followUpImpacted;
        boolean fading;
        boolean durabilitySpent;
        Cast(int ability, ItemStack stack, ResourceKey<Level> dimension, long start, UUID markedTarget) {
            this.ability = ability; this.stack = stack; this.dimension = dimension;
            this.start = start; this.markedTarget = markedTarget;
        }
    }
    private KatanaAbilities() { }

    @SubscribeEvent
    public static void tick(TickEvent.PlayerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.player instanceof ServerPlayer player)) return;
        Cast cast = CASTS.get(player.getUUID());
        if (cast == null) return;
        if (!player.isAlive() || player.isSpectator() || player.hasEffect(KatanaEffects.PARALYSIS.get())
                || player.getMainHandItem() != cast.stack || player.level().dimension() != cast.dimension) {
            CASTS.remove(player.getUUID());
            KatanaNetwork.broadcastAnimation(player, -1);
            return;
        }
        long elapsed = player.getServer().overworld().getGameTime() - cast.start;
        if (!cast.impacted && elapsed >= IMPACT_TICK[cast.ability]) {
            cast.impacted = true;
            if (cast.ability == 0) {
                // A second normal hit during the wind-up must not switch the intended victim.
                CompoundTag tag = cast.stack.getTag();
                CompoundTag mark = tag == null ? new CompoundTag() : tag.getCompound(StainKatanaItem.MARK);
                if (mark.hasUUID("Target") && mark.getUUID("Target").equals(cast.markedTarget))
                    stun(player, cast.stack, player.serverLevel());
            } else {
                slash(player, cast.stack, player.serverLevel(), cast.ability == 2);
            }
        }
        if (cast.ability == 2 && !cast.followUpStarted && elapsed >= 11) {
            cast.followUpStarted = true;
            KatanaNetwork.broadcastAnimation(player, 3);
        }
        if (cast.ability == 2 && !cast.followUpImpacted && elapsed >= 18) {
            cast.followUpImpacted = true;
            slash(player, cast.stack, player.serverLevel(), true);
        }
        if (!cast.fading && elapsed >= FADE_OUT_TICK[cast.ability]) {
            cast.fading = true;
            KatanaNetwork.broadcastAnimation(player, -1);
        }
        if (elapsed >= RECOVERY_TICK[cast.ability]) CASTS.remove(player.getUUID());
    }

    @SubscribeEvent
    public static void serverStopped(ServerStoppedEvent event) { CASTS.clear(); }

    @SubscribeEvent
    public static void logout(PlayerEvent.PlayerLoggedOutEvent event) {
        CASTS.remove(event.getEntity().getUUID());
    }


    public static void activate(ServerPlayer player, int ability) {
        if (ability < 0 || ability >= COOLDOWN.length || !player.isAlive() || player.isSpectator()
                || player.hasEffect(KatanaEffects.PARALYSIS.get())) return;
        if (CASTS.containsKey(player.getUUID())) return;
        ItemStack stack = player.getMainHandItem();
        if (!(stack.getItem() instanceof StainKatanaItem)) return;
        ServerLevel level = player.serverLevel();
        long now = player.getServer().overworld().getGameTime();
        CompoundTag state = player.getPersistentData().getCompound(COOLDOWNS);
        // Limita también solicitudes inválidas/repetidas, sin aceptar marcas del cliente.
        if (state.contains("last") && now - state.getLong("last") < 4) return;
        state.putLong("last", now);
        player.getPersistentData().put(COOLDOWNS, state);
        String key = "next" + ability;
        if (now < state.getLong(key)) {
            int seconds = (int)((state.getLong(key) - now + 19) / 20);
            player.displayClientMessage(Component.translatable("stainkatana.cooldown", seconds), true);
            return;
        }
        LivingEntity marked = ability == 0 ? markedTarget(player, stack, level, true) : null;
        if (ability == 0 && marked == null) return;
        if (ability != 0 && targets(player, level, ability == 2).isEmpty()) {
            player.displayClientMessage(Component.translatable("stainkatana.no_target"), true);
            return;
        }
        state.putLong(key, now + COOLDOWN[ability]);
        player.getPersistentData().put(COOLDOWNS, state);
        CASTS.put(player.getUUID(), new Cast(ability, stack, level.dimension(), now,
                marked == null ? null : marked.getUUID()));
        KatanaNetwork.broadcastAnimation(player, ability);
    }

    private static boolean legalTarget(ServerPlayer player, LivingEntity target) {
        if (target == player || !target.isAlive() || target.isSpectator() || player.isAlliedTo(target)) return false;
        if (target instanceof Player other && (!player.getServer().isPvpAllowed() || !player.canHarmPlayer(other))) return false;
        return player.hasLineOfSight(target);
    }

    private static LivingEntity markedTarget(ServerPlayer player, ItemStack stack, ServerLevel level, boolean notify) {
        CompoundTag tag = stack.getTag();
        if (tag == null || !tag.contains(StainKatanaItem.MARK, 10)) {
            if (notify) player.displayClientMessage(Component.translatable("stainkatana.no_mark"), true);
            return null;
        }
        CompoundTag mark = tag.getCompound(StainKatanaItem.MARK);
        if (!mark.hasUUID("Target") || !mark.getString("Dimension").equals(level.dimension().location().toString())
                || level.getGameTime() > mark.getLong("Expires")) {
            tag.remove(StainKatanaItem.MARK);
            if (notify) player.displayClientMessage(Component.translatable("stainkatana.no_mark"), true);
            return null;
        }
        Entity entity = level.getEntity(mark.getUUID("Target"));
        if (!(entity instanceof LivingEntity target) || !legalTarget(player, target)
                || player.distanceToSqr(target) > 64.0D) {
            if (notify) player.displayClientMessage(Component.translatable("stainkatana.target_unavailable"), true);
            return null;
        }
        return target;
    }

    private static boolean stun(ServerPlayer player, ItemStack stack, ServerLevel level) {
        LivingEntity target = markedTarget(player, stack, level, true);
        if (target == null) return false;
        CompoundTag tag = stack.getTag();
        int duration = target instanceof Player ? 40 : 60;
        if (!target.addEffect(new MobEffectInstance(KatanaEffects.PARALYSIS.get(), duration, 0, false, false, false))) {
            player.displayClientMessage(Component.translatable("stainkatana.resisted"), true);
            return false;
        }
        tag.remove(StainKatanaItem.MARK);
        level.sendParticles(KatanaParticles.PULSE.get(), target.getX(), target.getY(0.55), target.getZ(), 1, 0, 0, 0, 0);
        level.sendParticles(KatanaParticles.SHARD.get(), target.getX(), target.getY(0.55), target.getZ(), 1, 0, 0, 0, 0);
        level.playSound(null, target.blockPosition(), SoundEvents.PLAYER_ATTACK_CRIT, SoundSource.PLAYERS, .7F, .65F);
        player.displayClientMessage(Component.translatable("stainkatana.stun_used"), true);
        return true;
    }

    private static boolean slash(ServerPlayer player, ItemStack stack, ServerLevel level, boolean ultimate) {
        int maxTargets = ultimate ? 5 : 3;
        Vec3 facing = facing(player);
        List<LivingEntity> targets = targets(player, level, ultimate);
        int hits = 0;
        for (LivingEntity target : targets) {
            if (hits >= maxTargets) break;
            // El arma tiene 7 de daño base; los atributos del jugador cuentan,
            // con límites para que la habilidad no multiplique sin control otros mods.
            double base = player.getAttributeValue(Attributes.ATTACK_DAMAGE);
            float damage = (float)Math.max(4, Math.min(ultimate ? 9 : 12, base * (ultimate ? 0.8 : 1.15)));
            if (!target.hurt(player.damageSources().playerAttack(player), damage)) continue;
            hits++;
            if (ultimate) {
                target.addEffect(new MobEffectInstance(KatanaEffects.PARALYSIS.get(), 15, 0, false, false, false));
                level.sendParticles(KatanaParticles.PULSE.get(), target.getX(), target.getY(.5), target.getZ(), 1, 0, 0, 0, 0);
            }
            level.sendParticles(KatanaParticles.SLASH.get(), target.getX(), target.getY(.6), target.getZ(), 1, 0, 0, 0, 0);
            level.sendParticles(KatanaParticles.SHARD.get(), target.getX(), target.getY(.55), target.getZ(), 1, 0, 0, 0, 0);
        }
        if (hits == 0) {
            player.displayClientMessage(Component.translatable("stainkatana.no_target"), true); return false;
        }
        arc(level, player, facing, ultimate);
        level.playSound(null, player.blockPosition(), SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, .8F, ultimate ? .7F : 1.1F);
        // La ulti puede golpear dos veces, pero desgasta el arma una sola vez.
        Cast current = CASTS.get(player.getUUID());
        if (current == null || !current.durabilitySpent) {
            if (current != null) current.durabilitySpent = true;
            stack.hurtAndBreak(1, player, p -> p.broadcastBreakEvent(InteractionHand.MAIN_HAND));
        }
        player.displayClientMessage(Component.translatable(ultimate ? "stainkatana.ultimate_used" : "stainkatana.slash_used"), true);
        return true;
    }

    private static Vec3 facing(ServerPlayer player) {
        Vec3 facing = player.getLookAngle().multiply(1, 0, 1).normalize();
        return facing.lengthSqr() < .01 ? new Vec3(0, 0, 1) : facing;
    }

    private static List<LivingEntity> targets(ServerPlayer player, ServerLevel level, boolean ultimate) {
        double range = ultimate ? 5.0 : 3.5;
        Vec3 direction = facing(player);
        List<LivingEntity> result = level.getEntitiesOfClass(LivingEntity.class, player.getBoundingBox().inflate(range),
                target -> legalTarget(player, target) && player.distanceToSqr(target) <= range * range
                        && target.position().subtract(player.position()).multiply(1, 0, 1).normalize().dot(direction) > (ultimate ? .05 : .45));
        result.sort(Comparator.comparingDouble(player::distanceToSqr));
        return result;
    }

    private static void arc(ServerLevel level, ServerPlayer player, Vec3 forward, boolean ultimate) {
        // Dos cortes superpuestos para la ulti, uno para el ataque rápido.
        Vec3 side = new Vec3(-forward.z, 0, forward.x);
        int strokes = ultimate ? 3 : 1;
        for (int i = 0; i < strokes; i++) {
            double shift = (i - (strokes - 1) / 2.0) * .6;
            Vec3 point = player.position().add(forward.scale(1.8 + i * .25)).add(side.scale(shift));
            level.sendParticles(KatanaParticles.SLASH.get(), point.x, player.getY() + 1.05 + shift * .2,
                    point.z, 1, 0, 0, 0, 0);
        }
    }
}
