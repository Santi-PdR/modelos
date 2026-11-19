package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import dev.kosmx.playerAnim.api.layered.IAnimation;
import dev.kosmx.playerAnim.api.layered.KeyframeAnimationPlayer;
import dev.kosmx.playerAnim.api.layered.ModifierLayer;
import dev.kosmx.playerAnim.minecraftApi.PlayerAnimationAccess;
import dev.kosmx.playerAnim.minecraftApi.PlayerAnimationFactory;
import dev.kosmx.playerAnim.minecraftApi.PlayerAnimationRegistry;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;

/** Client-only animation layer, fed only by successful server activations. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class KatanaAnimations {
    private static final ResourceLocation LAYER = new ResourceLocation(StainKatanaMod.MOD_ID, "abilities");
    private static final String[] CLIPS = {"eating_right", "sword_attack", "sword_attack2"};
    private KatanaAnimations() { }

    @SubscribeEvent
    public static void setup(FMLClientSetupEvent event) {
        event.enqueueWork(() -> PlayerAnimationFactory.ANIMATION_DATA_FACTORY.registerFactory(
                LAYER, 1000, player -> new ModifierLayer<>()));
    }

    public static void play(int entityId, int ability) {
        if (ability < 0 || ability >= CLIPS.length || Minecraft.getInstance().level == null) return;
        if (!(Minecraft.getInstance().level.getEntity(entityId) instanceof AbstractClientPlayer player)) return;
        var clip = PlayerAnimationRegistry.getAnimation(new ResourceLocation(StainKatanaMod.MOD_ID, CLIPS[ability]));
        if (clip == null) return;
        var data = PlayerAnimationAccess.getPlayerAssociatedData(player).get(LAYER);
        if (data instanceof ModifierLayer<?> layer) {
            @SuppressWarnings("unchecked") ModifierLayer<IAnimation> animation = (ModifierLayer<IAnimation>) layer;
            animation.setAnimation(new KeyframeAnimationPlayer(clip));
        }
    }
}
