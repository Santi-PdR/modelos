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
    private static int boundTicks;
    private static boolean boundSeen, boundChecked;
    @SubscribeEvent public static void verify(net.minecraftforge.event.TickEvent.PlayerTickEvent event) {
        if (event.phase != net.minecraftforge.event.TickEvent.Phase.END || !(event.player instanceof ServerPlayer player) || boundChecked) return;
        var mobs = player.serverLevel().getEntitiesOfClass(Zombie.class, player.getBoundingBox().inflate(20));
        if (mobs.isEmpty()) return;
        boolean bound = mobs.get(0).hasEffect(com.stainkatana.katana.KatanaEffects.CINEMATIC_BIND.get());
        if (bound) { boundSeen = true; boundTicks++; }
        else if (boundSeen) {
            if (boundTicks < 180) throw new IllegalStateException("Ultimate ended early, bound ticks=" + boundTicks);
            if (mobs.get(0).getHealth() >= 1000F) throw new IllegalStateException("Ultimate caused no damage");
            boundChecked = true;
            System.out.println("STAIN_ULTIMATE_VERIFIED ticks=" + boundTicks);
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
