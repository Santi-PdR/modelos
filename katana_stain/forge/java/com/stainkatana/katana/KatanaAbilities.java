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
import net.minecraft.sounds.SoundEvent;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;

/** Combate resuelto en servidor: blancos, PvP, daño y cooldown no vienen del cliente. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaAbilities {
    private static final String COOLDOWNS = "StainKatanaAbilities";
    private static final Map<UUID, Cast> CASTS = new ConcurrentHashMap<>();
    private static final Map<UUID, UUID> BOUND_TARGETS = new ConcurrentHashMap<>();
    private record Backstab(UUID target, ItemStack stack, ResourceKey<Level> dimension, long start, boolean impacted) { }
    private static final Map<UUID, Backstab> BACKSTABS = new ConcurrentHashMap<>();
    private static final class Cast {
        final int ability;
        final ItemStack stack;
        final ResourceKey<Level> dimension;
        final long start;
        final UUID markedTarget;
        final AbilityTimeline timeline;
        Vec3 anchor;
        Vec3 casterAnchor;
        float attackDamage;
        boolean followUpImpacted;
        boolean durabilitySpent;
        int cinematicStroke;
        int cinematicAnimation;
        Cast(int ability, ItemStack stack, ResourceKey<Level> dimension, long start, UUID markedTarget) {
            this.ability = ability; this.stack = stack; this.dimension = dimension;
            this.start = start; this.markedTarget = markedTarget;
            this.timeline = new AbilityTimeline(ability);
        }
    }
    private KatanaAbilities() { }

    @SubscribeEvent
    public static void tick(TickEvent.PlayerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.player instanceof ServerPlayer player)) return;
        if (player.getMainHandItem().getItem() instanceof StainKatanaItem && player.tickCount % 20 == 0)
            syncCooldowns(player);
        tickBackstab(player);
        Cast cast = CASTS.get(player.getUUID());
        if (cast == null) return;
        if (!player.isAlive() || player.isSpectator() || player.hasEffect(KatanaEffects.PARALYSIS.get())
                || (cast.ability != 2 && player.getMainHandItem() != cast.stack) || !player.level().dimension().equals(cast.dimension)) {
            cancel(player, cast);
            return;
        }
        if (cast.ability == 2 && cast.casterAnchor != null) {
            player.setDeltaMovement(Vec3.ZERO);
            if (player.position().distanceToSqr(cast.casterAnchor) > 0.0025)
                player.connection.teleport(cast.casterAnchor.x, cast.casterAnchor.y, cast.casterAnchor.z, player.getYRot(), player.getXRot());
        }
        long elapsed = player.getServer().overworld().getGameTime() - cast.start;
        int events = cast.timeline.advance(elapsed);
        if (cast.ability == 2) {
            tickUltimate(player, cast, elapsed, events);
            return;
        }
        if ((events & AbilityTimeline.IMPACT) != 0) {
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
        // A broken/changed sword cannot execute the second strike in the same tick.
        if (player.getMainHandItem() != cast.stack || cast.stack.isEmpty()) {
            cast.timeline.cancel(); CASTS.remove(player.getUUID());
            KatanaNetwork.broadcastAnimation(player, -1);
            return;
        }
        if ((events & AbilityTimeline.FOLLOW_UP) != 0) {
            KatanaNetwork.broadcastAnimation(player, 3);
        }
        if ((events & AbilityTimeline.SECOND_IMPACT) != 0) {
            cast.followUpImpacted = true;
            slash(player, cast.stack, player.serverLevel(), true);
        }
        if ((events & AbilityTimeline.FADE) != 0) {
            KatanaNetwork.broadcastAnimation(player, -1);
        }
        if ((events & AbilityTimeline.FINISH) != 0) CASTS.remove(player.getUUID());
    }

    /** Enforce cinematic position after entity ticks, even when potion effects are refused. */
    @SubscribeEvent public static void holdTargets(TickEvent.LevelTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.level instanceof ServerLevel world)) return;
        for (Cast cast : CASTS.values()) {
            if (cast.ability != 2 || cast.anchor == null || !cast.dimension.equals(world.dimension())) continue;
            Entity target = world.getEntity(cast.markedTarget);
            if (!(target instanceof LivingEntity living) || !living.isAlive()) continue;
            if (target.position().distanceToSqr(cast.anchor) > 0.0001) target.teleportTo(cast.anchor.x, cast.anchor.y, cast.anchor.z);
            target.setDeltaMovement(Vec3.ZERO);
            target.hurtMarked = true;
        }
    }
    @SubscribeEvent public static void protectCaster(net.minecraftforge.event.entity.living.LivingAttackEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)
                || (event.getSource().getEntity() == null && event.getSource().getDirectEntity() == null)) return;
        Cast cast = CASTS.get(player.getUUID());
        if (cast != null && cast.ability == 2 && cast.dimension.equals(player.level().dimension())) event.setCanceled(true);
    }
    public static boolean isCinematicallyBound(LivingEntity entity) {
        return !entity.level().isClientSide && BOUND_TARGETS.containsKey(entity.getUUID());
    }

    @SubscribeEvent
    public static void serverStopped(ServerStoppedEvent event) { CASTS.clear(); BOUND_TARGETS.clear(); BACKSTABS.clear(); }

    @SubscribeEvent
    public static void logout(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.getEntity() instanceof ServerPlayer player) {
            Cast cast = CASTS.get(player.getUUID());
            if (cast != null) cancel(player, cast);
            BACKSTABS.remove(player.getUUID());
        }
    }


    public static void activate(ServerPlayer player, int ability) {
        if (ability < 0 || ability >= 3 || !player.isAlive() || player.isSpectator()
                || player.hasEffect(KatanaEffects.PARALYSIS.get())) return;
        if (CASTS.containsKey(player.getUUID()) || BACKSTABS.containsKey(player.getUUID())) return;
        ItemStack stack = player.getMainHandItem();
        if (!(stack.getItem() instanceof StainKatanaItem)) return;
        ServerLevel level = player.serverLevel();
        long now = player.getServer().overworld().getGameTime();
        CompoundTag state = player.getPersistentData().getCompound(COOLDOWNS);
        // Limita también solicitudes inválidas/repetidas, sin aceptar marcas del cliente.
        if (state.contains("last") && now - state.getLong("last") < 4) return;
        state.putLong("last", now);
        player.getPersistentData().put(COOLDOWNS, state);
        // A full blood meter changes Z itself into the rear strike. Ordinary attacks never consume it.
        if (ability == 0 && state.getInt("daggerCharges") >= 2) {
            startBackstab(player, state, now);
            return;
        }
        String key = "next" + ability;
        if (now < state.getLong(key)) {
            int seconds = (int)((state.getLong(key) - now + 19) / 20);
            player.displayClientMessage(Component.translatable("stainkatana.cooldown", seconds), true);
            return;
        }
        LivingEntity marked = ability == 0 ? markedTarget(player, stack, level, true) : null;
        if (ability == 0 && marked == null) return;
        LivingEntity ultimateTarget = ability == 2 ? ultimateTarget(player, level) : null;
        Vec3 arrival = ultimateTarget == null ? null : safePosition(player, ultimateTarget, 0);
        if (ability == 2 && ultimateTarget == null) {
            player.displayClientMessage(Component.translatable("stainkatana.no_target"), true);
            return;
        }
        if (ability == 2 && arrival == null) {
            // Airborne or very large bosses can lack safe footing. The bind still works,
            // but do not silently imply the caster was teleported.
            player.displayClientMessage(Component.translatable("stainkatana.no_safe_teleport"), true);
        }
        state.putLong(key, now + CombatTuning.cooldown(ability));
        player.getPersistentData().put(COOLDOWNS, state);
        syncCooldowns(player);
        UUID targetId = ability == 2 ? ultimateTarget.getUUID() : marked == null ? null : marked.getUUID();
        if (ability == 2) {
            BOUND_TARGETS.put(targetId, player.getUUID());
            if (arrival != null) moveTo(player, ultimateTarget, arrival);
        }
        Cast newCast = new Cast(ability, stack, level.dimension(), now, targetId);
        if (ultimateTarget != null) { newCast.anchor = ultimateTarget.position(); newCast.casterAnchor = player.position();
            newCast.attackDamage = (float) player.getAttributeValue(Attributes.ATTACK_DAMAGE); }
        CASTS.put(player.getUUID(), newCast);
        KatanaNetwork.broadcastAnimation(player, ability);
        if (ability == 2) {
            // Begin framing the server-selected victim during the opening wind-up.
            KatanaNetwork.broadcastVisual(player, ultimateTarget.getX(), ultimateTarget.getY(.55), ultimateTarget.getZ(), KatanaVisualStyle.SCENE_FOCUS);
        }
        if (ability == 0) {
            level.playSound(null, player.blockPosition(), SoundEvents.IRON_GOLEM_REPAIR, SoundSource.PLAYERS, .45F, 1.6F);
        }
    }

    /** Find solid, collision-free and visible footing near the target, without loading chunks. */
    private static Vec3 safePosition(ServerPlayer player, LivingEntity target, int phase) {
        return safePosition(player, target, phase, false);
    }
    private static Vec3 safePosition(ServerPlayer player, LivingEntity target, int phase, boolean behindOnly) {
        if (player.isPassenger()) return null;
        ServerLevel level = player.serverLevel();
        double base = Math.toRadians(target.getYRot()) + phase * Math.PI / 3.0;
        for (int attempt = 0; attempt < (behindOnly ? 3 : 8); attempt++) {
            double offset = behindOnly ? (attempt == 1 ? Math.PI / 6 : attempt == 2 ? -Math.PI / 6 : 0) : attempt * Math.PI / 4.0;
            double angle = base + offset;
            double radius = Math.max(1.65, target.getBbWidth() * .5 + .9);
            for (int dy : new int[]{0, -1, 1, -2, 2, -3}) {
                Vec3 destination = new Vec3(target.getX() + Math.sin(angle) * radius, Math.floor(target.getY()) + dy, target.getZ() - Math.cos(angle) * radius);
                var feet = net.minecraft.core.BlockPos.containing(destination);
                var below = feet.below();
                if (!level.hasChunkAt(feet) || !level.getWorldBorder().isWithinBounds(feet)
                        || !level.getBlockState(below).isFaceSturdy(level, below, net.minecraft.core.Direction.UP)
                        || !level.getFluidState(feet).isEmpty() || !level.getFluidState(feet.above()).isEmpty()) continue;
                var floor = level.getBlockState(below);
                if (floor.is(net.minecraft.world.level.block.Blocks.MAGMA_BLOCK)
                        || floor.is(net.minecraft.world.level.block.Blocks.CAMPFIRE)
                        || floor.is(net.minecraft.world.level.block.Blocks.SOUL_CAMPFIRE)
                        || floor.is(net.minecraft.world.level.block.Blocks.CACTUS)) continue;
                Vec3 delta = destination.subtract(player.position());
                if (delta.lengthSqr() > 17 * 17 || !level.noCollision(player, player.getBoundingBox().move(delta))) continue;
                var hit = level.clip(new net.minecraft.world.level.ClipContext(player.position().add(0, .6, 0), destination.add(0, .6, 0),
                        net.minecraft.world.level.ClipContext.Block.COLLIDER, net.minecraft.world.level.ClipContext.Fluid.NONE, player));
                if (hit.getType() == net.minecraft.world.phys.HitResult.Type.MISS) return destination;
            }
        }
        return null;
    }
    private static void moveTo(ServerPlayer player, LivingEntity target, Vec3 destination) {
        double dx = target.getX() - destination.x, dz = target.getZ() - destination.z;
        float yaw = (float)Math.toDegrees(Math.atan2(-dx, dz));
        // Adapted from SlashBlade: Resharped's handleServerPlayerTeleportation (MIT).
        // Same-dimension player teleport goes through the connection and keeps the
        // destination chunk briefly ticketed, instead of moving only the server entity.
        var level = player.serverLevel();
        var chunk = new net.minecraft.world.level.ChunkPos(net.minecraft.core.BlockPos.containing(destination));
        level.getChunkSource().addRegionTicket(net.minecraft.server.level.TicketType.POST_TELEPORT, chunk, 1, player.getId());
        level.playSound(null, player.blockPosition(), SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, .5F, 1.25F);
        level.sendParticles(KatanaParticles.SHARD.get(), player.getX(), player.getY(.5), player.getZ(), 6, .2, .3, .2, .025);
        player.connection.teleport(destination.x, destination.y, destination.z, yaw, player.getXRot(), java.util.Collections.emptySet());
        level.sendParticles(KatanaParticles.SHARD.get(), destination.x, destination.y + .9, destination.z, 6, .2, .3, .2, .025);
        player.setYHeadRot(yaw);
        player.setDeltaMovement(Vec3.ZERO);
    }
    private static void startBackstab(ServerPlayer player, CompoundTag data, long now) {
        Entity remembered = data.hasUUID("lastBloodTarget") ? player.serverLevel().getEntity(data.getUUID("lastBloodTarget")) : null;
        LivingEntity target = remembered instanceof LivingEntity living && legalTarget(player, living)
                && player.distanceToSqr(living) <= 64 ? living : null;
        if (target == null) {
            target = targets(player, player.serverLevel(), false).stream().findFirst().orElse(null);
        }
        if (target == null) {
            player.displayClientMessage(Component.translatable("stainkatana.no_target"), true);
            return;
        }
        Vec3 spot = safePosition(player, target, 0, true);
        if (spot == null) {
            player.displayClientMessage(Component.translatable("stainkatana.no_safe_teleport"), true);
            return;
        }
        data.putInt("daggerCharges", 0);
        data.putLong("next0", now + CombatTuning.cooldown(0));
        player.getPersistentData().put(COOLDOWNS, data);
        syncCooldowns(player);
        BACKSTABS.put(player.getUUID(), new Backstab(target.getUUID(), player.getMainHandItem(), player.level().dimension(), now, false));
        moveTo(player, target, spot);
        KatanaNetwork.broadcastAnimation(player, 6);
        // Give the short finisher camera a server-selected focus immediately;
        // otherwise it switches to third person but has nothing to frame.
        KatanaNetwork.broadcastVisual(player, target.getX(), target.getY(.55), target.getZ(), KatanaVisualStyle.SCENE_FOCUS);
    }
    private static void tickBackstab(ServerPlayer player) {
        Backstab stab = BACKSTABS.get(player.getUUID());
        if (stab == null) return;
        long age = player.getServer().overworld().getGameTime() - stab.start();
        Entity entity = player.serverLevel().getEntity(stab.target());
        if (!player.isAlive() || player.isSpectator() || player.getMainHandItem() != stab.stack()
                || !player.level().dimension().equals(stab.dimension()) || !(entity instanceof LivingEntity target)
                || !legalTarget(player, target) || player.distanceToSqr(target) > 64 || age >= 30) {
            BACKSTABS.remove(player.getUUID()); KatanaNetwork.broadcastAnimation(player, -1); return;
        }
        if (age >= 10 && !stab.impacted()) {
            BACKSTABS.put(player.getUUID(), new Backstab(stab.target(), stab.stack(), stab.dimension(), stab.start(), true));
            // Never execute an otherwise healthy ordinary target in one blow; preserve at least one health.
            float damage = CombatTuning.backstabDamage(target.getHealth(), target.getMaxHealth());
            if (damage > 0) target.hurt(player.damageSources().playerAttack(player), damage);
            KatanaNetwork.broadcastVisual(player, target.getX(), target.getY(.7), target.getZ(), KatanaVisualStyle.FINISHER);
            player.serverLevel().sendParticles(KatanaParticles.SHARD.get(), target.getX(), target.getY(.7), target.getZ(), 16, .35, .4, .35, .04);
            player.serverLevel().playSound(null, target.blockPosition(), SoundEvents.PLAYER_ATTACK_CRIT, SoundSource.PLAYERS, 1.0F, .75F);
        }
    }

    /** Closest hitbox point, including Forge multipart parts (e.g. the Ender Dragon). */
    private static Vec3 nearestPoint(Entity target, Vec3 point) {
        Vec3 best = clampToBox(target.getBoundingBox(), point);
        double distance = best.distanceToSqr(point);
        if (target.isMultipartEntity() && target.getParts() != null) {
            for (var part : target.getParts()) {
                if (part == null || !part.isAlive()) continue;
                Vec3 p = clampToBox(part.getBoundingBox(), point);
                double d = p.distanceToSqr(point);
                if (d < distance) { best = p; distance = d; }
            }
        }
        return best;
    }
    private static Vec3 clampToBox(net.minecraft.world.phys.AABB box, Vec3 point) {
        return new Vec3(net.minecraft.util.Mth.clamp(point.x, box.minX, box.maxX),
                net.minecraft.util.Mth.clamp(point.y, box.minY, box.maxY),
                net.minecraft.util.Mth.clamp(point.z, box.minZ, box.maxZ));
    }
    private static LivingEntity ultimateTarget(ServerPlayer player, ServerLevel level) {
        Vec3 eye = player.getEyePosition();
        Vec3 direction = player.getLookAngle();
        var searchBox = player.getBoundingBox().inflate(15.0);
        var candidates = new java.util.LinkedHashSet<LivingEntity>(
                level.getEntitiesOfClass(LivingEntity.class, searchBox));
        // Forge tracks multipart hitboxes separately. A large modded boss (or
        // dragon) can have a part in range while its parent box is outside the
        // query; include its loaded parent without loading additional chunks.
        for (var part : level.getPartEntities()) {
            if (part != null && part.isAlive() && part.getBoundingBox().intersects(searchBox)
                    && part.getParent() instanceof LivingEntity parent) candidates.add(parent);
        }
        return candidates.stream().filter(target -> {
                    if (target instanceof Player || BOUND_TARGETS.containsKey(target.getUUID())
                            || !target.isAlive() || target.isSpectator() || player.isAlliedTo(target)) return false;
                    Vec3 closest = nearestPoint(target, eye);
                    Vec3 delta = closest.subtract(eye);
                    if (delta.lengthSqr() > 225 || delta.lengthSqr() < 1.0e-6 || delta.normalize().dot(direction) < .35) return false;
                    return level.clip(new net.minecraft.world.level.ClipContext(eye, closest,
                            net.minecraft.world.level.ClipContext.Block.COLLIDER,
                            net.minecraft.world.level.ClipContext.Fluid.NONE, player)).getType() == net.minecraft.world.phys.HitResult.Type.MISS;
                }).min(Comparator.comparingDouble(target -> nearestPoint(target, eye).distanceToSqr(eye))).orElse(null);
    }
    private static boolean hitUltimate(ServerPlayer player, LivingEntity target, float amount) {
        if (target.isMultipartEntity() && target.getParts() != null) {
            var part = java.util.Arrays.stream(target.getParts()).filter(p -> p != null && p.isAlive())
                    .min(Comparator.comparingDouble(p -> nearestPoint(p, player.getEyePosition()).distanceToSqr(player.getEyePosition())))
                    .orElse(null);
            if (part != null) return part.hurt(player.damageSources().playerAttack(player), amount);
        }
        return target.hurt(player.damageSources().playerAttack(player), amount);
    }

    private static void cancel(ServerPlayer player, Cast cast) {
        cast.timeline.cancel();
        CASTS.remove(player.getUUID(), cast);
        if (cast.ability == 2 && cast.markedTarget != null) {
            BOUND_TARGETS.remove(cast.markedTarget, player.getUUID());
            ServerLevel world = player.getServer().getLevel(cast.dimension);
            Entity target = world == null ? null : world.getEntity(cast.markedTarget);
            if (target instanceof LivingEntity living) living.removeEffect(KatanaEffects.CINEMATIC_BIND.get());
        }
        KatanaNetwork.broadcastAnimation(player, -1);
    }

    private static void tickUltimate(ServerPlayer player, Cast cast, long elapsed, int events) {
        Entity entity = player.serverLevel().getEntity(cast.markedTarget);
        if (!(entity instanceof LivingEntity mob) || !mob.isAlive() || mob.isSpectator() || player.isAlliedTo(mob)
                || nearestPoint(mob, player.getEyePosition()).distanceToSqr(player.getEyePosition()) > 324
                || (events & AbilityTimeline.FINISH) != 0) {
            cancel(player, cast); return;
        }
        // Short refreshable effect: if the server dies, it expires without permanently changing mob AI.
        if (elapsed % 4 == 0) mob.addEffect(new MobEffectInstance(KatanaEffects.CINEMATIC_BIND.get(), 12, 0, false, false, false));
        if (mob instanceof Mob movingMob) movingMob.getNavigation().stop();
        Vec3 velocity = mob.getDeltaMovement();
        mob.setDeltaMovement(0, Math.min(velocity.y, 0), 0);
        mob.hurtMarked = true;
        // Relocate before the wind-up, so a viewer sees the strike instead of
        // a teleport and an impact on the same frame. The server owns the schedule.
        int nextStroke = cast.cinematicAnimation + 1;
        if (nextStroke < CombatTuning.ultimateStrikeCount()
                && elapsed >= CombatTuning.ultimateWindupTick(nextStroke)) {
            Vec3 next = safePosition(player, mob, nextStroke + 1);
            if (next != null) { moveTo(player, mob, next); cast.casterAnchor = player.position(); }
            KatanaNetwork.broadcastAnimation(player, 7 + cast.cinematicAnimation);
            cast.cinematicAnimation++;
        }
        if (cast.cinematicStroke < CombatTuning.ultimateStrikeCount()
                && elapsed >= CombatTuning.ultimateStrikeTick(cast.cinematicStroke)) {
            int index = cast.cinematicStroke++;
            float damage = CombatTuning.damage(cast.attackDamage, true);
            // Reserve the kill for the last cut, but never protect the mob from other damage sources.
            if (index < CombatTuning.ultimateStrikeCount() - 1) damage = Math.min(damage, Math.max(0, mob.getHealth() - 1));
            // Vanilla damage immunity can otherwise swallow consecutive cinematic cuts.
            // Clear it only immediately before a scheduled hit, never every tick.
            if (damage > 0) mob.invulnerableTime = 0;
            if (damage > 0 && hitUltimate(player, mob, damage)) {
                if (mob.isAlive()) StainKatanaItem.markTarget(cast.stack, mob, player.serverLevel());
                if (!cast.durabilitySpent) {
                    cast.durabilitySpent = true;
                    cast.stack.hurtAndBreak(1, player, p -> p.broadcastBreakEvent(InteractionHand.MAIN_HAND));
                }
            }
            KatanaNetwork.broadcastVisual(player, mob.getX(), mob.getY(.55), mob.getZ(), index == CombatTuning.ultimateStrikeCount() - 1 ? KatanaVisualStyle.ULTIMATE_FINAL
                    : index % 2 == 0 ? KatanaVisualStyle.ULTIMATE_CUT : KatanaVisualStyle.ULTIMATE_CROSS);
            double spread = Math.min(2.0, Math.max(.35, mob.getBbWidth() * .35));
            player.serverLevel().sendParticles(KatanaParticles.SHARD.get(), mob.getX(), mob.getY(.55), mob.getZ(), 12, spread, Math.min(1.5, mob.getBbHeight() * .25), spread, .03);
            player.serverLevel().playSound(null, mob.blockPosition(), katanaSwingSound(), SoundSource.PLAYERS, .65F, index % 2 == 0 ? .9F : 1.1F);
        }
        if ((events & AbilityTimeline.FADE) != 0) KatanaNetwork.broadcastAnimation(player, -1);
    }

    private static void syncCooldowns(ServerPlayer player) {
        long now = player.getServer().overworld().getGameTime();
        CompoundTag state = player.getPersistentData().getCompound(COOLDOWNS);
        int[] remaining = new int[3];
        for (int i = 0; i < 3; i++)
            remaining[i] = (int)Math.min(CombatTuning.cooldown(i), Math.max(0L, state.getLong("next" + i) - now));
        KatanaNetwork.sendCooldowns(player, remaining[0], remaining[1], remaining[2], state.getInt("daggerCharges"));
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
                || player.distanceToSqr(target) > 576.0D) {
            if (notify) player.displayClientMessage(Component.translatable("stainkatana.target_unavailable"), true);
            return null;
        }
        return target;
    }

    private static boolean stun(ServerPlayer player, ItemStack stack, ServerLevel level) {
        LivingEntity target = markedTarget(player, stack, level, true);
        if (target == null) return false;
        CompoundTag tag = stack.getTag();
        int duration = CombatTuning.paralysisTicks(target instanceof Player);
        if (!target.addEffect(new MobEffectInstance(KatanaEffects.PARALYSIS.get(), duration, 0, false, false, false))) {
            player.displayClientMessage(Component.translatable("stainkatana.resisted"), true);
            return false;
        }
        tag.remove(StainKatanaItem.MARK);
        // Count only successful stuns, never key presses or failed attempts.
        CompoundTag data = player.getPersistentData().getCompound(COOLDOWNS);
        int charges = Math.min(2, data.getInt("daggerCharges") + 1);
        data.putInt("daggerCharges", charges);
        data.putUUID("lastBloodTarget", target.getUUID());
        player.getPersistentData().put(COOLDOWNS, data);
        syncCooldowns(player);
        // The buff is applied only on a successful, server-authoritative paralysis.
        player.addEffect(new MobEffectInstance(MobEffects.DAMAGE_BOOST, 160, 1, false, false, true));
        player.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SPEED, 160, 1, false, false, true));
        KatanaNetwork.broadcastVisual(player, player.getX(), player.getY(0.7), player.getZ(), KatanaVisualStyle.BLOOD_FLASH);
        KatanaNetwork.broadcastVisual(player, target.getX(), target.getY(0.55), target.getZ(), KatanaVisualStyle.BLOOD_BIND);
        level.sendParticles(KatanaParticles.SHARD.get(), target.getX(), target.getY(0.55), target.getZ(), 10, .3, .35, .3, .02);
        Vec3 bloodHand = player.getEyePosition().add(player.getLookAngle().scale(.45)).add(0, -.45, 0);
        level.sendParticles(KatanaParticles.SHARD.get(), bloodHand.x, bloodHand.y, bloodHand.z, 8, .12, .18, .12, .01);
        level.playSound(null, player.blockPosition(), SoundEvents.HONEY_BLOCK_BREAK, SoundSource.PLAYERS, .55F, 1.25F);
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
            // Deliberadamente poderoso, pero con límites frente a atributos de otros mods.
            double base = player.getAttributeValue(Attributes.ATTACK_DAMAGE);
            float damage = CombatTuning.damage(base, ultimate);
            if (!target.hurt(player.damageSources().playerAttack(player), damage)) continue;
            hits++;
            // Marca una única víctima por corte: la primera válida y más próxima.
            if (hits == 1 && target.isAlive()) StainKatanaItem.markTarget(stack, target, level);
            if (ultimate) {
                target.addEffect(new MobEffectInstance(KatanaEffects.PARALYSIS.get(), CombatTuning.ultimateStaggerTicks(target instanceof Player), 0, false, false, false));
                KatanaNetwork.broadcastVisual(player, target.getX(), target.getY(.55), target.getZ(), KatanaVisualStyle.HIT);
            }
            level.sendParticles(KatanaParticles.SHARD.get(), target.getX(), target.getY(.55), target.getZ(), 4, .25, .25, .25, 0);
            if (!ultimate) {
                KatanaNetwork.broadcastVisual(player, target.getX(), target.getY(.55), target.getZ(), KatanaVisualStyle.HIT);
                level.playSound(null, target.blockPosition(), SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, .7F, 1.15F);
            }
        }
        // El corte existe aunque la víctima se aparte durante la preparación.
        arc(level, player, facing, ultimate);
        if (!ultimate) {
            // The extended cut travels in front of the player, even on an empty swing.
            for (double distance : new double[]{3.4, 5.3}) {
                Vec3 point = player.position().add(facing.scale(distance));
                KatanaNetwork.broadcastVisual(player, point.x, player.getY() + 1.05, point.z, KatanaVisualStyle.SWING);
            }
        }
        level.playSound(null, player.blockPosition(), katanaSwingSound(), SoundSource.PLAYERS, .8F, ultimate ? .85F : 1.0F);
        if (hits == 0) {
            if (ultimate) player.displayClientMessage(Component.translatable("stainkatana.no_target"), true);
            return false;
        }
        // La ulti puede golpear dos veces, pero desgasta el arma una sola vez.
        Cast current = CASTS.get(player.getUUID());
        if (current == null || !current.durabilitySpent) {
            if (current != null) current.durabilitySpent = true;
            stack.hurtAndBreak(1, player, p -> p.broadcastBreakEvent(InteractionHand.MAIN_HAND));
        }
        player.displayClientMessage(Component.translatable(ultimate ? "stainkatana.ultimate_used" : "stainkatana.slash_used"), true);
        return true;
    }

    private static SoundEvent katanaSwingSound() {
        // Borrow the installed Better Combat sound; never ship its audio in our JAR.
        ResourceLocation id = new ResourceLocation("bettercombat", "katana_slash");
        return ForgeRegistries.SOUND_EVENTS.containsKey(id)
                ? ForgeRegistries.SOUND_EVENTS.getValue(id) : SoundEvents.PLAYER_ATTACK_SWEEP;
    }

    private static Vec3 facing(ServerPlayer player) {
        Vec3 facing = player.getLookAngle().multiply(1, 0, 1).normalize();
        return facing.lengthSqr() < .01 ? new Vec3(0, 0, 1) : facing;
    }

    private static List<LivingEntity> targets(ServerPlayer player, ServerLevel level, boolean ultimate) {
        double range = ultimate ? 5.0 : 7.0;
        Vec3 direction = facing(player);
        List<LivingEntity> result = level.getEntitiesOfClass(LivingEntity.class, player.getBoundingBox().inflate(range),
                target -> legalTarget(player, target) && player.distanceToSqr(target) <= range * range
                        && target.position().subtract(player.position()).multiply(1, 0, 1).normalize().dot(direction) > (ultimate ? .05 : .45));
        result.sort(Comparator.comparingDouble(player::distanceToSqr));
        return result;
    }

    private static void arc(ServerLevel level, ServerPlayer player, Vec3 forward, boolean ultimate) {
        // El renderizador usa un plano orientado según el atacante, no un billboard.
        Vec3 point = player.position().add(forward.scale(1.55));
        Cast cast = CASTS.get(player.getUUID());
        int style = !ultimate ? KatanaVisualStyle.SWING : (cast != null && cast.followUpImpacted
                ? KatanaVisualStyle.ULTIMATE_CROSS : KatanaVisualStyle.ULTIMATE_CUT);
        KatanaNetwork.broadcastVisual(player, point.x, player.getY() + 1.05, point.z, style);
    }
}
