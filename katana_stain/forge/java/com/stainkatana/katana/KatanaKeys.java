package com.stainkatana.katana;

import com.mojang.blaze3d.platform.InputConstants;
import com.stainkatana.StainKatanaMod;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

/** Registradas en Controles: el usuario puede reasignar cada tecla. */
public final class KatanaKeys {
    private static final String CATEGORY = "key.categories.stainkatana";
    private static final KeyMapping STUN = new KeyMapping("key.stainkatana.stun", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_Z, CATEGORY);
    private static final KeyMapping SLASH = new KeyMapping("key.stainkatana.slash", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_X, CATEGORY);
    private static final KeyMapping ULTIMATE = new KeyMapping("key.stainkatana.ultimate", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_C, CATEGORY);
    private KatanaKeys() { }

    @Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
    public static class Registration {
        @SubscribeEvent public static void register(RegisterKeyMappingsEvent event) {
            event.register(STUN); event.register(SLASH); event.register(ULTIMATE);
        }
    }
    @Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
    public static class Input {
        @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
            if (event.phase != TickEvent.Phase.END) return;
            Minecraft mc = Minecraft.getInstance();
            boolean stun = STUN.consumeClick(), slash = SLASH.consumeClick(), ultimate = ULTIMATE.consumeClick();
            if (mc.screen != null || mc.player == null || !(mc.player.getMainHandItem().getItem() instanceof StainKatanaItem)) return;
            if (stun) KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(0));
            if (slash) KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(1));
            if (ultimate) KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(2));
        }
    }
}
