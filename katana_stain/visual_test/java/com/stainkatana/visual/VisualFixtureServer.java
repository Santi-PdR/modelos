package com.stainkatana.visual;

import com.stainkatana.StainKatanaMod;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.GameRules;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.core.BlockPos;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** CI fixture only. Not compiled into the distributed mod. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class VisualFixtureServer {
    private static int boundTicks, ultimateHealthDrops;
    private static float lastBoundHealth;
    private static boolean boundSeen, boundChecked;
    private static net.minecraft.world.phys.Vec3 casterPosition;
    private static boolean casterMoved, casterLockVerified;
    private static boolean xSoundVerified;
    private static java.util.UUID weakTarget, primaryTarget;
    public record ImpactCapture(int index, long serverTick) { }
    public static final java.util.concurrent.ConcurrentLinkedQueue<ImpactCapture> confirmedImpacts = new java.util.concurrent.ConcurrentLinkedQueue<>();
    private static int confirmedImpactCount;
    private static int weakDamageEvents;
    public static volatile boolean weakSequenceVerified;

    /** Observe only the initial high-health C target, never synthetic preview clips. */
    @SubscribeEvent public static void captureConfirmedImpact(net.minecraftforge.event.entity.living.LivingDamageEvent event) {
        if (confirmedImpactCount >= com.stainkatana.katana.CombatTuning.ultimateStrikeCount()
                || primaryTarget == null || !primaryTarget.equals(event.getEntity().getUUID())
                || event.getEntity().level().isClientSide || event.getAmount() <= 0
                || !(event.getSource().getEntity() instanceof ServerPlayer)
                || !com.stainkatana.katana.KatanaAbilities.isCinematicallyBound(event.getEntity())) return;
        confirmedImpacts.add(new ImpactCapture(++confirmedImpactCount, event.getEntity().level().getGameTime()));
    }

    // A separate, stationary target for real Better Combat client attacks. The
    // server observes damage; the client observes selected animation IDs.
    public static volatile java.util.UUID bcComboTarget;
    private static volatile int bcComboDamageEvents;
    private static net.minecraft.world.phys.Vec3 bcComboAnchor;
    public static void startBetterCombatCombo(ServerPlayer player) {
        var level = player.serverLevel();
        int x = 150, z = 150;
        int y = level.getHeight(Heightmap.Types.MOTION_BLOCKING, x, z);
        player.teleportTo(level, x + .5, y, z + .5, 0, 0);
        player.setYRot(0); player.setXRot(0);
        player.setGameMode(GameType.SURVIVAL);
        player.getInventory().setItem(player.getInventory().selected, new ItemStack(StainKatanaMod.KATANA_STAIN.get()));
        var victim = EntityType.HUSK.create(level);
        if (victim == null) throw new IllegalStateException("Cannot create Better Combat combo target");
        victim.setNoAi(true); victim.setPersistenceRequired();
        victim.getAttribute(Attributes.MAX_HEALTH).setBaseValue(1000);
        victim.setHealth(1000);
        bcComboAnchor = new net.minecraft.world.phys.Vec3(x + .5, y, z + 2.8);
        victim.moveTo(bcComboAnchor.x, bcComboAnchor.y, bcComboAnchor.z, 180, 0);
        level.addFreshEntity(victim);
        bcComboDamageEvents = 0;
        bcComboTarget = victim.getUUID();
    }
    @SubscribeEvent public static void keepBetterCombatTarget(net.minecraftforge.event.TickEvent.LevelTickEvent event) {
        if (event.phase != net.minecraftforge.event.TickEvent.Phase.END || !(event.level instanceof ServerLevel level)
                || bcComboTarget == null || bcComboAnchor == null) return;
        var entity = level.getEntity(bcComboTarget);
        if (entity instanceof Zombie victim && victim.isAlive()) {
            victim.teleportTo(bcComboAnchor.x, bcComboAnchor.y, bcComboAnchor.z);
            victim.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
        }
    }
    @SubscribeEvent public static void countBetterCombatDamage(net.minecraftforge.event.entity.living.LivingDamageEvent event) {
        if (bcComboTarget != null && bcComboTarget.equals(event.getEntity().getUUID())
                && !event.getEntity().level().isClientSide && event.getAmount() > 0
                && event.getSource().getEntity() instanceof ServerPlayer) bcComboDamageEvents++;
    }
    public static void verifyBetterCombatCombo() {
        if (bcComboDamageEvents < 4) throw new IllegalStateException("Better Combat target received only " + bcComboDamageEvents + " damaging hits");
        System.out.println("STAIN_BC_COMBO_DAMAGE_VERIFIED=" + bcComboDamageEvents);
        bcComboTarget = null;
        bcComboAnchor = null;
    }

    /** Separate 20-health control: all ten cuts must deal positive damage. */
    public static void startWeakSequence(ServerPlayer player) {
        var level = player.serverLevel();
        level.getEntitiesOfClass(Zombie.class, player.getBoundingBox().inflate(40)).forEach(zombie -> zombie.discard());
        var victim = EntityType.HUSK.create(level);
        if (victim == null) throw new IllegalStateException("Cannot create low-health test target");
        victim.setNoAi(true); victim.setPersistenceRequired(); victim.setHealth(20F);
        victim.moveTo(player.getX(), player.getY(), player.getZ() + 3, 180, 0);
        level.addFreshEntity(victim);
        weakTarget = victim.getUUID(); weakDamageEvents = 0; weakSequenceVerified = false;
        player.setYRot(0); player.setXRot(0);
        var state = player.getPersistentData().getCompound("StainKatanaAbilities");
        state.putLong("next2", 0); state.remove("last");
        player.getPersistentData().put("StainKatanaAbilities", state);
        com.stainkatana.katana.KatanaAbilities.activate(player, 2);
        if (state.getLong("next2") == 0) throw new IllegalStateException("Low-health C did not activate");
    }
    @SubscribeEvent public static void weakDamage(net.minecraftforge.event.entity.living.LivingDamageEvent event) {
        if (weakTarget == null || !weakTarget.equals(event.getEntity().getUUID()) || event.getEntity().level().isClientSide) return;
        if (event.getAmount() <= 0F || !(event.getSource().getEntity() instanceof ServerPlayer))
            throw new IllegalStateException("Invalid weak-target C damage");
        weakDamageEvents++;
        if (weakDamageEvents > com.stainkatana.katana.CombatTuning.ultimateStrikeCount())
            throw new IllegalStateException("Too many weak-target strikes");
    }
    public static void verifyWeakSequence() {
        if (weakDamageEvents != com.stainkatana.katana.CombatTuning.ultimateStrikeCount())
            throw new IllegalStateException("Low-health target did not receive ten damaging cuts: " + weakDamageEvents);
        weakSequenceVerified = true;
        System.out.println("STAIN_WEAK_C_TEN_DAMAGE_EVENTS_VERIFIED");
    }

    private static Zombie weakFinisherTarget;
    public static void startWeakFinisher(ServerPlayer player) {
        var level = player.serverLevel();
        var victim = EntityType.HUSK.create(level);
        if (victim == null) throw new IllegalStateException("Cannot create weak finisher target");
        victim.setNoAi(true); victim.setPersistenceRequired();
        victim.moveTo(player.getX(), player.getY(), player.getZ() + 3, 180, 0);
        level.addFreshEntity(victim);
        victim.setHealth(1F);
        // Simulate a recent hit still covered by vanilla's hurt cooldown.
        victim.invulnerableTime = 30;
        weakFinisherTarget = victim;
        var state = player.getPersistentData().getCompound("StainKatanaAbilities");
        state.putInt("daggerCharges", 2);
        state.putUUID("lastBloodTarget", victim.getUUID());
        state.remove("last"); state.putLong("next0", 0);
        player.getPersistentData().put("StainKatanaAbilities", state);
        com.stainkatana.katana.KatanaAbilities.activate(player, 0);
        if (state.getInt("daggerCharges") != 0)
            throw new IllegalStateException("Weak finisher did not activate");
    }
    public static void verifyWeakFinisher() {
        if (weakFinisherTarget == null || weakFinisherTarget.getHealth() >= 1F)
            throw new IllegalStateException("Z finisher did not damage a one-health target with hurt cooldown; health="
                    + (weakFinisherTarget == null ? "missing" : weakFinisherTarget.getHealth()));
        System.out.println("STAIN_WEAK_FINISHER_DAMAGE_VERIFIED");
    }

    private static Zombie originalMarked, newlyMarked;
    public static void startRemarkDuringZ(ServerPlayer player) {
        var level = player.serverLevel();
        originalMarked = EntityType.HUSK.create(level);
        newlyMarked = EntityType.HUSK.create(level);
        if (originalMarked == null || newlyMarked == null) throw new IllegalStateException("Cannot create Z mark targets");
        originalMarked.setNoAi(true); newlyMarked.setNoAi(true);
        originalMarked.moveTo(player.getX() - 1, player.getY(), player.getZ() + 3, 180, 0);
        newlyMarked.moveTo(player.getX() + 1, player.getY(), player.getZ() + 3, 180, 0);
        level.addFreshEntity(originalMarked); level.addFreshEntity(newlyMarked);
        var state = player.getPersistentData().getCompound("StainKatanaAbilities");
        state.putInt("daggerCharges", 0); state.putLong("next0", 0); state.remove("last");
        player.getPersistentData().put("StainKatanaAbilities", state);
        var sword = player.getMainHandItem();
        sword.hurtEnemy(originalMarked, player);
        com.stainkatana.katana.KatanaAbilities.activate(player, 0);
        if (state.getLong("next0") == 0) throw new IllegalStateException("Z mark test did not activate");
        // Simulate an unrelated sword hit after the server accepted Z.
        sword.hurtEnemy(newlyMarked, player);
    }
    public static void verifyRemarkDuringZ(ServerPlayer player) {
        var mark = player.getMainHandItem().getOrCreateTag().getCompound("StainBloodMark");
        if (originalMarked == null || newlyMarked == null
                || !originalMarked.hasEffect(com.stainkatana.katana.KatanaEffects.PARALYSIS.get())
                || newlyMarked.hasEffect(com.stainkatana.katana.KatanaEffects.PARALYSIS.get())
                || !mark.hasUUID("Target") || !mark.getUUID("Target").equals(newlyMarked.getUUID()))
            throw new IllegalStateException("Z did not retain its target and preserve the newer mark");
        System.out.println("STAIN_Z_LOCKED_MARK_VERIFIED");
    }

    private static Zombie blockedXTarget, visibleXTarget;
    private static BlockPos xWall;
    private static net.minecraft.world.level.block.state.BlockState xPreviousBlock;
    public static void startXWallCheck(ServerPlayer player) {
        var level = player.serverLevel();
        // Isolated flat-world setup: one target behind a wall and one beside it.
        int x = 100, z = 100;
        int y = level.getHeight(Heightmap.Types.MOTION_BLOCKING, x, z);
        player.teleportTo(level, x + .5, y, z + .5, 0, 0);
        player.setYRot(0); player.setXRot(0);
        xWall = new BlockPos(x, y + 1, z + 2);
        xPreviousBlock = level.getBlockState(xWall);
        level.setBlockAndUpdate(xWall, net.minecraft.world.level.block.Blocks.STONE.defaultBlockState());
        blockedXTarget = EntityType.HUSK.create(level);
        visibleXTarget = EntityType.HUSK.create(level);
        if (blockedXTarget == null || visibleXTarget == null) throw new IllegalStateException("Cannot create X targets");
        blockedXTarget.setNoAi(true); visibleXTarget.setNoAi(true);
        blockedXTarget.moveTo(x + .5, y, z + 4.5, 180, 0);
        visibleXTarget.moveTo(x + 3.0, y, z + 4.5, 180, 0);
        level.addFreshEntity(blockedXTarget); level.addFreshEntity(visibleXTarget);
        var state = player.getPersistentData().getCompound("StainKatanaAbilities");
        state.putLong("next1", 0); state.remove("last");
        player.getPersistentData().put("StainKatanaAbilities", state);
        com.stainkatana.katana.KatanaAbilities.activate(player, 1);
        if (state.getLong("next1") == 0) throw new IllegalStateException("X wall test did not activate");
    }
    public static void verifyXWallCheck(ServerPlayer player) {
        player.serverLevel().setBlockAndUpdate(xWall, xPreviousBlock);
        if (blockedXTarget == null || visibleXTarget == null
                || blockedXTarget.getHealth() != blockedXTarget.getMaxHealth()
                || visibleXTarget.getHealth() >= visibleXTarget.getMaxHealth())
            throw new IllegalStateException("X line of sight: blocked="
                    + (blockedXTarget == null ? "missing" : blockedXTarget.getHealth())
                    + " visible=" + (visibleXTarget == null ? "missing" : visibleXTarget.getHealth()));
        System.out.println("STAIN_X_WALL_AND_VISIBLE_TARGET_VERIFIED");
    }

    @SubscribeEvent public static void observeAbilitySound(net.minecraftforge.event.PlayLevelSoundEvent.AtPosition event) {
        if (xSoundVerified || !(event.getLevel() instanceof ServerLevel) || event.getSound() == null
                || event.getSource() != net.minecraft.sounds.SoundSource.PLAYERS
                || event.getOriginalVolume() != .8F || event.getOriginalPitch() != 1F) return;
        var sound = event.getSound().value();
        var expected = net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")
                ? net.minecraftforge.registries.ForgeRegistries.SOUND_EVENTS.getValue(
                        new net.minecraft.resources.ResourceLocation("bettercombat", "katana_slash"))
                : net.minecraft.sounds.SoundEvents.PLAYER_ATTACK_SWEEP;
        if (sound != expected) throw new IllegalStateException("X sent the wrong swing sound: " + sound);
        xSoundVerified = true;
        System.out.println("STAIN_X_SOUND_DISPATCH_VERIFIED");
    }
    @SubscribeEvent public static void verifyCasterLock(net.minecraftforge.event.TickEvent.LevelTickEvent event) {
        if (event.phase != net.minecraftforge.event.TickEvent.Phase.END || !(event.level instanceof ServerLevel level)
                || casterLockVerified || boundTicks == 0 || boundTicks > 5 || level.players().isEmpty()) return;
        ServerPlayer player = level.players().get(0);
        if (!casterMoved) {
            casterPosition = player.position();
            player.setPos(casterPosition.x + .4, casterPosition.y, casterPosition.z);
            player.setDeltaMovement(.4, 0, 0);
            casterMoved = true;
        } else {
            if (player.position().distanceToSqr(casterPosition) > .01)
                throw new IllegalStateException("Ultimate caster was not held at its cinematic anchor");
            casterLockVerified = true;
            System.out.println("STAIN_CASTER_MOVEMENT_LOCK_VERIFIED");
        }
    }
    @SubscribeEvent public static void verify(net.minecraftforge.event.TickEvent.PlayerTickEvent event) {
        if (event.phase != net.minecraftforge.event.TickEvent.Phase.END || !(event.player instanceof ServerPlayer player) || boundChecked) return;
        var mobs = player.serverLevel().getEntitiesOfClass(Zombie.class, player.getBoundingBox().inflate(20));
        if (mobs.isEmpty()) return;
        boolean bound = mobs.get(0).hasEffect(com.stainkatana.katana.KatanaEffects.CINEMATIC_BIND.get());
        if (bound) {
            float health = mobs.get(0).getHealth();
            if (boundSeen && health < lastBoundHealth - .001F) ultimateHealthDrops++;
            lastBoundHealth = health;
            boundSeen = true; boundTicks++;
        } else if (boundSeen) {
            if (boundTicks < 180) throw new IllegalStateException("Ultimate ended early, bound ticks=" + boundTicks);
            if (ultimateHealthDrops != com.stainkatana.katana.CombatTuning.ultimateStrikeCount())
                throw new IllegalStateException("Ultimate did not cause ten separate health drops: " + ultimateHealthDrops);
            boundChecked = true;
            System.out.println("STAIN_ULTIMATE_VERIFIED ticks=" + boundTicks + " healthDrops=" + ultimateHealthDrops);
        }
    }
    @SubscribeEvent public static void login(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        ServerLevel level = player.serverLevel();
        int y = level.getHeight(Heightmap.Types.MOTION_BLOCKING, 0, 0);
        player.setGameMode(GameType.CREATIVE);
        player.teleportTo(level, .5, y, .5, 0, 0);
        player.getInventory().selected = 0;
        player.getInventory().setItem(0, new ItemStack(StainKatanaMod.KATANA_STAIN.get()));
        level.setDayTime(6000);
        level.getGameRules().getRule(GameRules.RULE_DOMOBSPAWNING).set(false, level.getServer());
        Zombie zombie = EntityType.HUSK.create(level);
        if (zombie == null) throw new IllegalStateException("Cannot create fixture zombie");
        zombie.setNoAi(true);
        zombie.setPersistenceRequired();
        zombie.getAttribute(Attributes.MAX_HEALTH).setBaseValue(1000.0);
        zombie.setHealth(1000.0F);
        zombie.moveTo(2.0, y, 3.0, 180, 0);
        level.addFreshEntity(zombie);
        primaryTarget = zombie.getUUID(); confirmedImpactCount = 0; confirmedImpacts.clear();
        System.out.println("STAIN_VISUAL_FIXTURE_READY y=" + y);
    }
}
