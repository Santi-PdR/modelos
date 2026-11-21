package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.KatanaVisualStyle;
import com.stainkatana.katana.StainKatanaItem;
import com.mojang.logging.LogUtils;
import java.lang.reflect.Proxy;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.world.entity.HumanoidArm;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;

/** Optional integration: Better Combat owns the hit schedule and damage. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class KatanaBetterCombatFx {
    private static int cueCount;
    private KatanaBetterCombatFx() { }
    public static int cueCount() { return cueCount; }

    @SubscribeEvent public static void setup(FMLClientSetupEvent event) {
        if (!ModList.get().isLoaded("bettercombat")) return;
        event.enqueueWork(() -> {
            try {
                // Optional dependency: no BC class is linked when the mod is absent.
                Class<?> events = Class.forName("net.bettercombat.api.client.BetterCombatClientEvents");
                Class<?> listener = Class.forName("net.bettercombat.api.client.BetterCombatClientEvents$PlayerAttackHit");
                Object callback = Proxy.newProxyInstance(listener.getClassLoader(), new Class<?>[]{listener}, (proxy, method, args) -> {
                    if (method.getDeclaringClass() == Object.class) {
                        if (method.getName().equals("toString")) return "StainKatanaBetterCombatFx";
                        if (method.getName().equals("hashCode")) return System.identityHashCode(proxy);
                        if (method.getName().equals("equals")) return proxy == args[0];
                        return null;
                    }
                    if (args != null && args.length >= 1 && args[0] instanceof LocalPlayer player
                            && player.getMainHandItem().getItem() instanceof StainKatanaItem) {
                        var forward = player.getLookAngle().multiply(1, 0, 1).normalize();
                        var point = player.position().add(forward.scale(1.5));
                        KatanaVisuals.spawn(player.getId(), point.x, player.getY() + 1.05, point.z,
                                player.getYRot(), KatanaVisualStyle.SWING, player.getMainArm() == HumanoidArm.LEFT);
                        cueCount++;
                    }
                    return null;
                });
                Object publisher = events.getField("ATTACK_HIT").get(null);
                publisher.getClass().getMethod("register", Object.class).invoke(publisher, callback);
            } catch (ReflectiveOperationException | LinkageError | RuntimeException e) {
                LogUtils.getLogger().warn("Better Combat visual callback unavailable; regular combat remains unchanged", e);
            }
        });
    }
}
