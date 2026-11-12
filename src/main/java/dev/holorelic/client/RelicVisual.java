package dev.holorelic.client;

import dev.holorelic.RelicNetwork;
import net.minecraft.world.entity.LivingEntity;
import software.bernie.geckolib.core.animatable.GeoAnimatable;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

final class RelicVisual implements GeoAnimatable {
    private static final RawAnimation IDLE = loop("idle");
    private static final RawAnimation DORMANT = loop("idle_dormant");
    private static final RawAnimation ACTIVATE = once("activation", "idle");
    private static final RawAnimation DEACTIVATE = once("deactivation", "idle_dormant");
    private static final RawAnimation PULSE = once("energy_pulse", "idle");
    private static final RawAnimation GLITCH = once("glitch", "idle");
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this, false);
    private long revision = -1, consumed = Long.MIN_VALUE;
    private RawAnimation animation = ACTIVATE;
    double tick;
    void update(LivingEntity entity, float partialTick, RelicNetwork.Snapshot state) {
        tick = entity.tickCount + partialTick;
        if (state != null && state.revision() != revision) {
            revision = state.revision();
            // If this wearer was off-screen, do not replay an already expired one-shot.
            int action = entity.level().getGameTime() < state.actionUntil() ? state.action() : 0;
            animation = switch (action) {
                case 1 -> ACTIVATE;
                case 2 -> DEACTIVATE;
                case 3 -> PULSE;
                case 4 -> GLITCH;
                default -> state.active() ? IDLE : DORMANT;
            };
        }
    }
    @Override public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "state", 0, state -> {
            if (consumed != revision) {
                // No initial blend from bind pose: flash and shock_ring are visible there.
                state.getController().transitionLength(consumed == Long.MIN_VALUE ? 0 : 2);
                state.getController().forceAnimationReset(); consumed = revision;
            }
            state.setAnimation(animation);
            return PlayState.CONTINUE;
        }));
    }
    @Override public AnimatableInstanceCache getAnimatableInstanceCache() { return cache; }
    @Override public double getTick(Object object) { return tick; }
    private static RawAnimation loop(String name) { return RawAnimation.begin().thenLoop("animation.relic." + name); }
    private static RawAnimation once(String name, String loop) {
        return RawAnimation.begin().thenPlay("animation.relic." + name).thenLoop("animation.relic." + loop);
    }
}
