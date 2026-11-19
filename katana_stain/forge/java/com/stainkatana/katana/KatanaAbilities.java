package com.stainkatana.katana;

import java.util.Comparator;
import java.util.List;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;
import org.joml.Vector3f;

/** Combate resuelto en servidor: blancos, PvP, daño y cooldown no vienen del cliente. */
public final class KatanaAbilities {
    private static final DustParticleOptions BLOOD = new DustParticleOptions(new Vector3f(0.62F, 0.025F, 0.04F), 0.85F);
    private static final DustParticleOptions DARK = new DustParticleOptions(new Vector3f(0.24F, 0.015F, 0.025F), 1.0F);
    private static final String COOLDOWNS = "StainKatanaAbilities";
    private static final int[] COOLDOWN = {240, 100, 900};
    private KatanaAbilities() { }

    public static void activate(ServerPlayer player, int ability) {
        if (ability < 0 || ability >= COOLDOWN.length || !player.isAlive() || player.isSpectator()) return;
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
        target.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 60, 10));
        target.addEffect(new MobEffectInstance(MobEffects.WEAKNESS, 60, 4));
        tag.remove(StainKatanaItem.MARK);
        spiral(level, target, 24);
        level.sendParticles(BLOOD, target.getX(), target.getY(0.55), target.getZ(), 18, .3, .4, .3, .01);
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
            float damage = ultimate ? 9.0F : 5.0F;
            if (!target.hurt(player.damageSources().playerAttack(player), damage)) continue;
            hits++;
            if (ultimate) {
                target.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SLOWDOWN, 50, 2));
                level.sendParticles(DARK, target.getX(), target.getY(.5), target.getZ(), 12, .22, .25, .22, .01);
            }
            level.sendParticles(ParticleTypes.SWEEP_ATTACK, target.getX(), target.getY(.55), target.getZ(), 1, 0, 0, 0, 0);
            level.sendParticles(BLOOD, target.getX(), target.getY(.55), target.getZ(), ultimate ? 14 : 8, .22, .22, .22, .02);
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
        double center = Math.atan2(forward.z, forward.x);
        int points = ultimate ? 32 : 18;
        double radius = ultimate ? 2.8 : 2.0;
        for (int i=0; i<points; i++) {
            double angle = center - 1.1 + 2.2*i/(points-1.0);
            double x = player.getX() + Math.cos(angle)*radius;
            double z = player.getZ() + Math.sin(angle)*radius;
            double y = player.getY()+1.0 + .16*Math.sin(i*.45);
            level.sendParticles(i % 3 == 0 ? DARK : BLOOD, x, y, z, 1, 0, 0, 0, 0);
        }
    }
    private static void spiral(ServerLevel level, LivingEntity target, int points) {
        for (int i=0; i<points; i++) {
            double angle = i*Math.PI*4/points, y=target.getY(.1)+target.getBbHeight()*i/points;
            level.sendParticles(i % 2 == 0 ? BLOOD : DARK, target.getX()+Math.cos(angle)*.4, y,
                    target.getZ()+Math.sin(angle)*.4, 1, 0, 0, 0, 0);
        }
    }
}
