package com.stainkatana.katana;

import java.util.Comparator;
import java.util.List;
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
public final class KatanaAbilities {
    private static final String COOLDOWNS = "StainKatanaAbilities";
    private static final int[] COOLDOWN = {240, 100, 900};
    private KatanaAbilities() { }

    public static void activate(ServerPlayer player, int ability) {
        if (ability < 0 || ability >= COOLDOWN.length || !player.isAlive() || player.isSpectator()
                || player.hasEffect(KatanaEffects.PARALYSIS.get())) return;
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
        boolean success = switch (ability) {
            case 0 -> stun(player, stack, level);
            case 1 -> slash(player, stack, level, false);
            case 2 -> slash(player, stack, level, true);
            default -> false;
        };
        if (success) {
            state.putLong(key, now + COOLDOWN[ability]);
            player.getPersistentData().put(COOLDOWNS, state);
            player.swing(InteractionHand.MAIN_HAND, true);
        }
    }

    private static boolean legalTarget(ServerPlayer player, LivingEntity target) {
        if (target == player || !target.isAlive() || target.isSpectator() || player.isAlliedTo(target)) return false;
        if (target instanceof Player other && (!player.getServer().isPvpAllowed() || !player.canHarmPlayer(other))) return false;
        return player.hasLineOfSight(target);
    }

    private static boolean stun(ServerPlayer player, ItemStack stack, ServerLevel level) {
        CompoundTag tag = stack.getTag();
        if (tag == null || !tag.contains(StainKatanaItem.MARK, 10)) {
            player.displayClientMessage(Component.translatable("stainkatana.no_mark"), true); return false;
        }
        CompoundTag mark = tag.getCompound(StainKatanaItem.MARK);
        if (!mark.hasUUID("Target") || !mark.getString("Dimension").equals(level.dimension().location().toString())
                || level.getGameTime() > mark.getLong("Expires")) {
            tag.remove(StainKatanaItem.MARK);
            player.displayClientMessage(Component.translatable("stainkatana.no_mark"), true); return false;
        }
        Entity entity = level.getEntity(mark.getUUID("Target"));
        if (!(entity instanceof LivingEntity target) || !legalTarget(player, target)
                || player.distanceToSqr(target) > 64.0D) {
            player.displayClientMessage(Component.translatable("stainkatana.target_unavailable"), true); return false;
        }
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
        double range = ultimate ? 5.0 : 3.5;
        int maxTargets = ultimate ? 5 : 3;
        Vec3 facing = player.getLookAngle().multiply(1, 0, 1).normalize();
        if (facing.lengthSqr() < .01) facing = new Vec3(0, 0, 1);
        final Vec3 direction = facing;
        List<LivingEntity> targets = level.getEntitiesOfClass(LivingEntity.class, player.getBoundingBox().inflate(range),
                target -> legalTarget(player, target) && player.distanceToSqr(target) <= range * range
                        && target.position().subtract(player.position()).multiply(1,0,1).normalize().dot(direction) > (ultimate ? .05 : .45));
        targets.sort(Comparator.comparingDouble(player::distanceToSqr));
        int hits = 0;
        for (LivingEntity target : targets) {
            if (hits >= maxTargets) break;
            // El arma tiene 7 de daño base; los atributos del jugador cuentan,
            // con límites para que la habilidad no multiplique sin control otros mods.
            double base = player.getAttributeValue(Attributes.ATTACK_DAMAGE);
            float damage = (float)Math.max(4, Math.min(ultimate ? 18 : 12, base * (ultimate ? 1.6 : 1.15)));
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
        arc(level, player, direction, ultimate);
        level.playSound(null, player.blockPosition(), SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, .8F, ultimate ? .7F : 1.1F);
        stack.hurtAndBreak(1, player, p -> p.broadcastBreakEvent(InteractionHand.MAIN_HAND));
        player.displayClientMessage(Component.translatable(ultimate ? "stainkatana.ultimate_used" : "stainkatana.slash_used"), true);
        return true;
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
