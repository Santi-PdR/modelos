package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import dev.kosmx.playerAnim.api.firstPerson.FirstPersonMode;
import dev.kosmx.playerAnim.api.firstPerson.FirstPersonConfiguration;
import dev.kosmx.playerAnim.core.data.KeyframeAnimation;
import dev.kosmx.playerAnim.core.data.gson.AnimationSerializing;
import dev.kosmx.playerAnim.api.layered.IAnimation;
import com.mojang.logging.LogUtils;
import java.io.InputStream;
import org.slf4j.Logger;
import dev.kosmx.playerAnim.api.layered.KeyframeAnimationPlayer;
import dev.kosmx.playerAnim.api.layered.ModifierLayer;
import dev.kosmx.playerAnim.api.layered.modifier.AbstractFadeModifier;
import dev.kosmx.playerAnim.api.layered.modifier.MirrorModifier;
import dev.kosmx.playerAnim.api.layered.modifier.SpeedModifier;
import dev.kosmx.playerAnim.core.util.Ease;
import net.minecraft.world.entity.HumanoidArm;
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
    private static final Logger LOGGER = LogUtils.getLogger();
    // Official Better Combat katana moves; loaded from the user's installed mod/resource pack,
    // not redistributed by this mod. Z uses a credited Emotecraft item-inspection gesture.
    private static final String[] BETTER_COMBAT = {null, "two_handed_slash_horizontal_right", "two_handed_slash_vertical_right", "two_handed_slash_horizontal_left"};
    private static final String[] CLIPS = {"inspect", "sword_attack", "sword_attack2", "sword_attack"};
    private KatanaAnimations() { }

    private static final class AbilityLayer extends ModifierLayer<IAnimation> {
        private final MirrorModifier mirror = new MirrorModifier(false);
        AbilityLayer() {
            addModifierBefore(mirror);
        }
    }

    @SubscribeEvent
    public static void setup(FMLClientSetupEvent event) {
        event.enqueueWork(() -> PlayerAnimationFactory.ANIMATION_DATA_FACTORY.registerFactory(
                LAYER, 2500, player -> new AbilityLayer()));
    }

    public static void play(int entityId, int ability) {
        if (ability < -1 || ability >= CLIPS.length || Minecraft.getInstance().level == null) return;
        if (!(Minecraft.getInstance().level.getEntity(entityId) instanceof AbstractClientPlayer player)) return;
        var data = PlayerAnimationAccess.getPlayerAssociatedData(player).get(LAYER);
        if (!(data instanceof AbilityLayer animation)) return;
        if (ability == -1) {
            animation.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(3, Ease.INOUTSINE), null);
            return;
        }
        KeyframeAnimation clip = loadBetterCombat(ability);
        boolean external = clip != null;
        if (!external) clip = PlayerAnimationRegistry.getAnimation(new ResourceLocation(StainKatanaMod.MOD_ID, CLIPS[ability]));
        if (clip == null) {
            LOGGER.warn("Missing katana animation for ability {}", ability);
            return;
        }
        // Better Combat 1.9.0 starts at tick zero; beginTick is its wind-up, not a seek offset.
        animation.mirror.setEnabled(player.getMainArm() == HumanoidArm.LEFT);
        KeyframeAnimationPlayer playing = new KeyframeAnimationPlayer(clip, 0)
                .setFirstPersonMode(FirstPersonMode.THIRD_PERSON_MODEL)
                .setFirstPersonConfiguration(new FirstPersonConfiguration()
                        .setShowRightArm(true).setShowLeftArm(true));
        // Keep playback speed inside the clip, so the outer fade remains in real ticks.
        ModifierLayer<IAnimation> timedClip = new ModifierLayer<>(playing);
        timedClip.addModifierBefore(new SpeedModifier(ability == 0 ? 4F : 2F));
        animation.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(2, Ease.INOUTSINE), timedClip, true);
    }

    private static KeyframeAnimation loadBetterCombat(int ability) {
        String name = BETTER_COMBAT[ability];
        if (name == null) return null;
        ResourceLocation id = new ResourceLocation("bettercombat", "attack_animations/" + name + ".json");
        var resource = Minecraft.getInstance().getResourceManager().getResource(id);
        if (resource.isEmpty()) return null;
        try (InputStream input = resource.get().open()) {
            var clips = AnimationSerializing.deserializeAnimation(input);
            return clips.isEmpty() ? null : clips.get(0);
        } catch (Exception e) {
            LOGGER.warn("Cannot load Better Combat animation {}; using fallback", id, e);
            return null;
        }
    }
}
