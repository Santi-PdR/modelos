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
    // Valid animation ids: 0=Z cast, 1=X cast, 2=C opening, 3=X follow-up,
    // 6=Z finisher, 7..16=C strokes (overhead strokes are 9, 12, 15), -1=clear.
    // The old 16-entry CLIPS table made id 16 (final C stroke) fall off the map.
    private static final int MAX_ANIMATION_ID = 16;
    // C alternates lateral cuts from other mods (Serious Player Animations and
    // Kelvin's Better Player Animations, both MIT), compensated per phase.
    // Better Combat keeps ordinary combat; its default clips are never used.
    // The Kelvin *_sneak variants are the same cuts re-timed to a deeper crouch,
    // used for the low strokes of SENTENCE.
    private static final String[] LATERAL_CUTS = {
        "stain_c_grip_trial",       // sword_attack2-derived (Serious Player Animations)
        "stain_c_grip_trial2",      // sword_attack-derived  (Serious Player Animations)
        "kelvin_swing_first",       // sword_swing_first     (Kelvin's Better Player Animations)
        "kelvin_swing_second",      // sword_swing_second    (Kelvin's Better Player Animations)
        "kelvin_swing_first_sneak", // sword_swing_first_sneak (Kelvin's Better Player Animations)
        "kelvin_swing_second_sneak" // sword_swing_second_sneak (Kelvin's Better Player Animations)
    };
    private static final int[] OVERHEAD_STROKES = {2, 5, 8};
    private static boolean overheadStroke(int stroke) {
        for (int index : OVERHEAD_STROKES) if (index == stroke) return true;
        return false;
    }
    private static String lateralClip(int stroke) {
        int slot = 0;
        for (int i = 0; i < stroke; i++) if (!overheadStroke(i)) slot++;
        return LATERAL_CUTS[Math.floorMod(slot, LATERAL_CUTS.length)];
    }
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
        if (ability < -1 || ability > MAX_ANIMATION_ID || Minecraft.getInstance().level == null) return;
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
                : ability >= 7 ? lateralClip(ability - 7)
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
            // Frame the complete world model in the first-person pass, instead
            // of translating each arm away from its shoulder. Body offsets use
            // world blocks; arm offsets use model pixels and the model itself
            // flips X/Y. Preserve optional free-hand fine tuning separately.
            final float[] contactDelta = {0F};
            timedClip.addModifierBefore(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier(part -> {
                if (!FirstPersonMode.isFirstPersonPass()) return java.util.Optional.empty();
                boolean leftHanded = player.getMainArm() == HumanoidArm.LEFT;
                if (part.equals("body")) {
                    return java.util.Optional.of(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier.PartModifier(
                            dev.kosmx.playerAnim.core.util.Vec3f.ZERO,
                            new dev.kosmx.playerAnim.core.util.Vec3f(leftHanded ? -1.5F : .5F,
                                    leftHanded ? -.20F : -.10F, -1F)));
                }
                // The free hand is the off-hand: left for right-handed and vice versa.
                String offHand = player.getMainArm() == HumanoidArm.LEFT ? "rightArm" : "leftArm";
                if (!part.equals(offHand)) return java.util.Optional.empty();
                float contact = GestureCurve.contact(playing.getTick() + contactDelta[0]);
                return java.util.Optional.of(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier.PartModifier(
                        dev.kosmx.playerAnim.core.util.Vec3f.ZERO,
                        new dev.kosmx.playerAnim.core.util.Vec3f(
                                contact * KatanaClientConfig.BLOOD_HAND_X.get().floatValue(),
                                contact * KatanaClientConfig.BLOOD_HAND_Y.get().floatValue(),
                                contact * KatanaClientConfig.BLOOD_HAND_Z.get().floatValue())));
            }) {
                @Override public dev.kosmx.playerAnim.core.util.Vec3f get3DTransform(
                        String part, dev.kosmx.playerAnim.api.TransformType type, float tickDelta,
                        dev.kosmx.playerAnim.core.util.Vec3f value) {
                    contactDelta[0] = tickDelta;
                    return super.get3DTransform(part, type, tickDelta, value);
                }
                @Override protected float getFadeIn(float delta) { return 1F; }
            });
        }
        if (ability == 1) {
            // Keep shoulders and held item together: frame the entire model
            // only in the first-person render pass, not each arm separately.
            // Third-person motion and server hit schedule are unchanged.
            timedClip.addModifierBefore(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier(part -> {
                if (!FirstPersonMode.isFirstPersonPass() || !part.equals("body"))
                    return java.util.Optional.empty();
                boolean leftHanded = player.getMainArm() == HumanoidArm.LEFT;
                return java.util.Optional.of(new dev.kosmx.playerAnim.api.layered.modifier.AdjustmentModifier.PartModifier(
                        dev.kosmx.playerAnim.core.util.Vec3f.ZERO,
                        new dev.kosmx.playerAnim.core.util.Vec3f(leftHanded ? -1F : .5F, -.35F, -1F)));
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
