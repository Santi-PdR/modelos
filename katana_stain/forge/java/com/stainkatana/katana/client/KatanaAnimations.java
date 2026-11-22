package com.stainkatana.katana.client;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.KatanaClientConfig;
import dev.kosmx.playerAnim.api.firstPerson.FirstPersonMode;
import dev.kosmx.playerAnim.api.firstPerson.FirstPersonConfiguration;
import dev.kosmx.playerAnim.core.data.KeyframeAnimation;
import dev.kosmx.playerAnim.api.layered.IAnimation;
import com.mojang.logging.LogUtils;
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
    private static final String[] CLIPS = {
        "inspect", "stain_x_cut", "scene_01", "sword_attack", "sword_attack2", "sword_attack", "combo_heavy",
        "scene_02", "scene_03", "scene_04", "scene_05", "scene_06", "scene_07", "scene_08", "scene_09", "scene_10"
    };
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
        if (player == Minecraft.getInstance().player) {
            if (ability == 2 || ability == 6) KatanaScene.start(ability == 6);
            else if (ability == -1) KatanaScene.stop();
        }
        var data = PlayerAnimationAccess.getPlayerAssociatedData(player).get(LAYER);
        if (!(data instanceof AbilityLayer animation)) return;
        if (ability == -1) {
            animation.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(3, Ease.INOUTSINE), null);
            return;
        }
        // Use credited motions from other mods regardless of whether Better Combat
        // is installed. It remains authoritative for ordinary weapon hits.
        boolean overhead = ability == 2 || ability == 9 || ability == 12 || ability == 15;
        String clipName = ability == 0 ? "inspect" : ability == 1 ? "stain_x_cut"
                : overhead ? "stain_c_overhead"
                : ((ability & 1) == 0 ? "sword_attack" : "sword_attack2");
        KeyframeAnimation clip = PlayerAnimationRegistry.getAnimation(new ResourceLocation(StainKatanaMod.MOD_ID, clipName));
        if (clip == null) {
            LOGGER.warn("Missing katana animation for ability {}", ability);
            return;
        }
        animation.mirror.setEnabled(player.getMainArm() == HumanoidArm.LEFT);
        KeyframeAnimationPlayer playing = new KeyframeAnimationPlayer(clip, 0)
                .setFirstPersonMode(FirstPersonMode.THIRD_PERSON_MODEL)
                .setFirstPersonConfiguration(new FirstPersonConfiguration()
                        .setShowRightArm(true).setShowLeftArm(true));
        // Keep playback speed inside the clip, so the outer fade remains in real ticks.
        ModifierLayer<IAnimation> timedClip = new ModifierLayer<>(playing);
        if (ability == 0) {
            // PlayerAnimator renders world-model arms in first person. Lift those
            // arms only in that render pass so the blood-draw stays in view;
            // the third-person animation and gameplay positions are unchanged.
            // SpeedModifier passes the clip-relative fractional tick to the
            // adjustment; using only getTick() visibly steps at render rates
            // above the animation tick rate.
            final float[] contactDelta = {0F};
            timedClip.addModifierBefore(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier(part -> {
                if (!FirstPersonMode.isFirstPersonPass() || !(part.equals("leftArm") || part.equals("rightArm")))
                    return java.util.Optional.empty();
                // The animation's free hand is leftArm before the outer mirror
                // modifier swaps it for left-handed players.
                boolean free = part.equals("leftArm");
                // The mirrored world-model pass is not a simple screen-space
                // reflection, so both handedness settings need separate framing.
                boolean leftHanded = player.getMainArm() == HumanoidArm.LEFT;
                // The offset is for the contact phase, not the whole gesture.
                // Ease it back out before recovery so the free arm does not
                // remain displaced after it leaves the blade.
                float contact = free ? GestureCurve.contact(playing.getTick() + contactDelta[0]) : 0;
                return java.util.Optional.of(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier.PartModifier(
                        dev.kosmx.playerAnim.core.util.Vec3f.ZERO,
                        new dev.kosmx.playerAnim.core.util.Vec3f(
                                (leftHanded ? 24 : -8) + contact * ((leftHanded ? -8 : 4)
                                        + KatanaClientConfig.BLOOD_HAND_X.get().floatValue()),
                                -3 + contact * ((leftHanded ? -12 : -8)
                                        + KatanaClientConfig.BLOOD_HAND_Y.get().floatValue()),
                                -16 + contact * ((leftHanded ? -3 : 0)
                                        + KatanaClientConfig.BLOOD_HAND_Z.get().floatValue()))));
            }) {
                @Override public dev.kosmx.playerAnim.core.util.Vec3f get3DTransform(
                        String part, dev.kosmx.playerAnim.api.TransformType type, float tickDelta,
                        dev.kosmx.playerAnim.core.util.Vec3f value) {
                    contactDelta[0] = tickDelta;
                    return super.get3DTransform(part, type, tickDelta, value);
                }
                // Inspect begins at tick zero; the library's default fade divides
                // by beginTick. The enclosing layer already performs the fade.
                @Override protected float getFadeIn(float delta) { return 1F; }
            });
        }
        if (ability == 1) {
            // The world-model arm can otherwise fill the entire first-person
            // view. Move only the first-person render pass into a readable frame;
            // the third-person pose and server hit schedule are unchanged.
            timedClip.addModifierBefore(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier(part -> {
                if (!FirstPersonMode.isFirstPersonPass() || !(part.equals("leftArm") || part.equals("rightArm")))
                    return java.util.Optional.empty();
                return java.util.Optional.of(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier.PartModifier(
                        dev.kosmx.playerAnim.core.util.Vec3f.ZERO,
                        new dev.kosmx.playerAnim.core.util.Vec3f(0, 1, 5)));
            }) {
                @Override protected float getFadeIn(float delta) { return 1F; }
            });
        }
        // Contact estimates in source clips are 8.75 ticks (Improved Animations)
        // and 7.5 ticks (Serious Player Animations). Damage remains server-timed.
        float speed = ability == 0 ? 3F : ability == 1 ? 1F
                : overhead ? (ability == 2 ? .875F : 8.75F / 6F) : 7.5F / 6F;
        timedClip.addModifierBefore(new SpeedModifier(speed));
        animation.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(2, Ease.INOUTSINE), timedClip, true);
    }

    public static boolean isPlaying(AbstractClientPlayer player) {
        var data = PlayerAnimationAccess.getPlayerAssociatedData(player).get(LAYER);
        return data instanceof AbilityLayer layer && layer.isActive();
    }

    /** Local, visual-only vanilla swing: the original attack remains authoritative. */
    public static void swing(AbstractClientPlayer player, int step) {
        var data = PlayerAnimationAccess.getPlayerAssociatedData(player).get(LAYER);
        if (!(data instanceof AbilityLayer animation) || animation.isActive()) return;
        int comboStep = Math.floorMod(step, 4);
        // Only used without Better Combat; motions are adapted from other mods.
        KeyframeAnimation clip = PlayerAnimationRegistry.getAnimation(new ResourceLocation(StainKatanaMod.MOD_ID,
                new String[]{"sword_attack", "sword_attack2", "stain_c_overhead", "stain_c_overhead"}[comboStep]));
        if (clip == null) return;
        animation.mirror.setEnabled(player.getMainArm() == HumanoidArm.LEFT);
        KeyframeAnimationPlayer playing = new KeyframeAnimationPlayer(clip, 0)
                .setFirstPersonMode(FirstPersonMode.THIRD_PERSON_MODEL)
                .setFirstPersonConfiguration(new FirstPersonConfiguration().setShowRightArm(true).setShowLeftArm(true));
        ModifierLayer<IAnimation> timed = new ModifierLayer<>(playing);
        timed.addModifierBefore(new SpeedModifier(2.0F));
        animation.replaceAnimationWithFade(AbstractFadeModifier.standardFadeIn(2, Ease.INOUTSINE), timed, true);
    }

}
