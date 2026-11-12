package dev.holorelic.client;

import com.mojang.blaze3d.platform.InputConstants;
import dev.holorelic.HoloRelic;
import dev.holorelic.RelicNetwork;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.client.settings.KeyConflictContext;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import org.lwjgl.glfw.GLFW;
import top.theillusivec4.curios.api.client.CuriosRendererRegistry;

@Mod.EventBusSubscriber(modid = HoloRelic.ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class ClientEvents {
    public static final KeyMapping TOGGLE = new KeyMapping("key.holorelic.toggle", KeyConflictContext.IN_GAME,
            InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_H, "key.categories.holorelic");
    @SubscribeEvent public static void keys(RegisterKeyMappingsEvent e) { e.register(TOGGLE); }
    @SubscribeEvent public static void setup(FMLClientSetupEvent e) {
        e.enqueueWork(() -> CuriosRendererRegistry.register(HoloRelic.CORE.get(), RelicRenderer::new));
    }
    @Mod.EventBusSubscriber(modid = HoloRelic.ID, value = Dist.CLIENT)
    public static final class ForgeEvents {
        @SubscribeEvent public static void tick(TickEvent.ClientTickEvent e) {
            if (e.phase != TickEvent.Phase.END) return;
            while (TOGGLE.consumeClick()) {
                if (Minecraft.getInstance().player != null && Minecraft.getInstance().screen == null)
                    RelicNetwork.CHANNEL.sendToServer(new RelicNetwork.Action(false));
            }
        }
    }
    private ClientEvents() {}
}
