package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.StainKatanaItem;
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
    private static final Map<UUID, Boolean> alternates = new HashMap<>();
    private static ClientLevel lastLevel;
    private KatanaVanillaSwings() { }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level != lastLevel) { lastLevel = mc.level; lastSwing.clear(); alternates.clear(); }
        if (mc.level == null || mc.isPaused() || ModList.get().isLoaded("bettercombat")) return;
        Set<UUID> present = new HashSet<>();
        for (AbstractClientPlayer player : mc.level.players()) {
            UUID id = player.getUUID(); present.add(id);
            int current = player.swinging && player.swingingArm == InteractionHand.MAIN_HAND
                    && player.getMainHandItem().getItem() instanceof StainKatanaItem ? player.swingTime : -1;
            int previous = lastSwing.getOrDefault(id, -1);
            if (current >= 0 && (previous < 0 || current < previous)) {
                boolean alternate = alternates.getOrDefault(id, false);
                alternates.put(id, !alternate);
                KatanaAnimations.swing(player, alternate);
            }
            lastSwing.put(id, current);
        }
        lastSwing.keySet().retainAll(present);
        alternates.keySet().retainAll(present);
    }
}
