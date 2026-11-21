package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.StainKatanaItem;
import com.stainkatana.katana.KatanaClientConfig;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;

/** Observe vanilla's already-synchronized swings; never change hit detection. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaVanillaSwings {
    private static final Map<UUID, Integer> lastSwing = new HashMap<>();
    private static final Map<UUID, Integer> alternates = new HashMap<>();
    private static final Map<UUID, Integer> lastAttackTick = new HashMap<>();
    private static ClientLevel lastLevel;
    private KatanaVanillaSwings() { }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level != lastLevel) { lastLevel = mc.level; lastSwing.clear(); alternates.clear(); lastAttackTick.clear(); }
        if (mc.level == null || mc.isPaused() || !KatanaClientConfig.VANILLA_SWINGS.get() || ModList.get().isLoaded("bettercombat")) return;
        Set<UUID> present = new HashSet<>();
        for (AbstractClientPlayer player : mc.level.players()) {
            UUID id = player.getUUID(); present.add(id);
            int current = player.swinging && player.swingingArm == InteractionHand.MAIN_HAND
                    && player.getMainHandItem().getItem() instanceof StainKatanaItem ? player.swingTime : -1;
            int previous = lastSwing.getOrDefault(id, -1);
            if (current >= 0 && (previous < 0 || current < previous)) {
                int step = player.tickCount - lastAttackTick.getOrDefault(id, player.tickCount - 61) > 60
                        ? 0 : alternates.getOrDefault(id, 0);
                lastAttackTick.put(id, player.tickCount);
                alternates.put(id, (step + 1) % 4);
                // Only the fallback path owns these cues; Better Combat already
                // supplies its own swing audio/visuals. Keep hit damage server-side.
                if (!KatanaAnimations.isPlaying(player)) {
                    var direction = player.getLookAngle().multiply(1, 0, 1).normalize();
                    var point = player.position().add(direction.scale(1.5));
                    KatanaVisuals.spawn(player.getId(), point.x, player.getY() + 1.05, point.z,
                            player.getYRot(), step % 2 == 0 ? com.stainkatana.katana.KatanaVisualStyle.SWING
                                    : com.stainkatana.katana.KatanaVisualStyle.ULTIMATE_CROSS,
                            player.getMainArm() == net.minecraft.world.entity.HumanoidArm.LEFT);
                    mc.level.playLocalSound(player.getX(), player.getY(), player.getZ(),
                            net.minecraft.sounds.SoundEvents.PLAYER_ATTACK_SWEEP,
                            net.minecraft.sounds.SoundSource.PLAYERS, .35F, 1.25F, false);
                }
                KatanaAnimations.swing(player, step);
            }
            lastSwing.put(id, current);
        }
        lastSwing.keySet().retainAll(present);
        alternates.keySet().retainAll(present);
        lastAttackTick.keySet().retainAll(present);
    }
}
