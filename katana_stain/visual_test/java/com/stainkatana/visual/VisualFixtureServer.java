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
    private static java.util.UUID weakTarget;
    private static int weakDamageEvents;
    public static volatile boolean weakSequenceVerified;

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
        System.out.println("STAIN_VISUAL_FIXTURE_READY y=" + y);
    }
}
