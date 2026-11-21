// ARCHIVO GENERADO - NO EDITAR A MANO.
// Fuente: tools/relic_manifest.json
// Regenerar: python3 tools/gen_relic_constants.py
// Verificar: python3 tools/gen_relic_constants.py --check
package com.santipdr.holocore.common;

import java.util.List;
import software.bernie.geckolib.core.animation.RawAnimation;

/**
 * Nombres, duraciones y {@link RawAnimation} de la reliquia, generados desde
 * {@code export/relic_manifest.json} (v19). Un nombre mal escrito aqui provoca
 * que GeckoLib no encuentre la animacion y el hueso se quede en reposo, asi que
 * la lista se valida en el CI contra el propio JSON de animaciones.
 */
public final class RelicAnimations {

    private RelicAnimations() {
    }

    /** animation.relic.idle - 48 s - state_loop (loop). */
    public static final String IDLE = "animation.relic.idle";
    public static final double IDLE_SECONDS = 48;
    public static final RawAnimation IDLE_RAW = RawAnimation.begin().thenLoop(IDLE);

    /** animation.relic.idle_calm - 12 s - state_loop (loop). */
    public static final String IDLE_CALM = "animation.relic.idle_calm";
    public static final double IDLE_CALM_SECONDS = 12;
    public static final RawAnimation IDLE_CALM_RAW = RawAnimation.begin().thenLoop(IDLE_CALM);

    /** animation.relic.idle_charged - 12 s - state_loop (loop). */
    public static final String IDLE_CHARGED = "animation.relic.idle_charged";
    public static final double IDLE_CHARGED_SECONDS = 12;
    public static final RawAnimation IDLE_CHARGED_RAW = RawAnimation.begin().thenLoop(IDLE_CHARGED);

    /** animation.relic.idle_alert - 8 s - state_loop (loop). */
    public static final String IDLE_ALERT = "animation.relic.idle_alert";
    public static final double IDLE_ALERT_SECONDS = 8;
    public static final RawAnimation IDLE_ALERT_RAW = RawAnimation.begin().thenLoop(IDLE_ALERT);

    /** animation.relic.idle_dormant - 12 s - state_loop (loop). */
    public static final String IDLE_DORMANT = "animation.relic.idle_dormant";
    public static final double IDLE_DORMANT_SECONDS = 12;
    public static final RawAnimation IDLE_DORMANT_RAW = RawAnimation.begin().thenLoop(IDLE_DORMANT);

    /** animation.relic.energy_pulse - 2.8 s - oneshot_returns_to_current_state. */
    public static final String ENERGY_PULSE = "animation.relic.energy_pulse";
    public static final double ENERGY_PULSE_SECONDS = 2.8;
    public static final RawAnimation ENERGY_PULSE_RAW = RawAnimation.begin().thenPlay(ENERGY_PULSE);

    /** animation.relic.activation - 3.6 s - transition. */
    public static final String ACTIVATION = "animation.relic.activation";
    public static final double ACTIVATION_SECONDS = 3.6;
    public static final RawAnimation ACTIVATION_RAW = RawAnimation.begin().thenPlay(ACTIVATION);

    /** animation.relic.deactivation - 2.6 s - transition. */
    public static final String DEACTIVATION = "animation.relic.deactivation";
    public static final double DEACTIVATION_SECONDS = 2.6;
    public static final RawAnimation DEACTIVATION_RAW = RawAnimation.begin().thenPlay(DEACTIVATION);

    /** animation.relic.wake - 1.512 s - transition. */
    public static final String WAKE = "animation.relic.wake";
    public static final double WAKE_SECONDS = 1.512;
    public static final RawAnimation WAKE_RAW = RawAnimation.begin().thenPlay(WAKE);

    /** animation.relic.sleep - 1.3 s - transition. */
    public static final String SLEEP = "animation.relic.sleep";
    public static final double SLEEP_SECONDS = 1.3;
    public static final RawAnimation SLEEP_RAW = RawAnimation.begin().thenPlay(SLEEP);

    /** animation.relic.glitch - 1.0 s - oneshot_returns_to_current_state. */
    public static final String GLITCH = "animation.relic.glitch";
    public static final double GLITCH_SECONDS = 1.0;
    public static final RawAnimation GLITCH_RAW = RawAnimation.begin().thenPlay(GLITCH);

    /** animation.relic.charge_up - 1.6 s - transition. */
    public static final String CHARGE_UP = "animation.relic.charge_up";
    public static final double CHARGE_UP_SECONDS = 1.6;
    public static final RawAnimation CHARGE_UP_RAW = RawAnimation.begin().thenPlay(CHARGE_UP);

    /** animation.relic.charge_down - 1.8 s - transition. */
    public static final String CHARGE_DOWN = "animation.relic.charge_down";
    public static final double CHARGE_DOWN_SECONDS = 1.8;
    public static final RawAnimation CHARGE_DOWN_RAW = RawAnimation.begin().thenPlay(CHARGE_DOWN);

    /** animation.relic.alert_up - 1.6 s - transition. */
    public static final String ALERT_UP = "animation.relic.alert_up";
    public static final double ALERT_UP_SECONDS = 1.6;
    public static final RawAnimation ALERT_UP_RAW = RawAnimation.begin().thenPlay(ALERT_UP);

    /** animation.relic.alert_down - 1.8 s - transition. */
    public static final String ALERT_DOWN = "animation.relic.alert_down";
    public static final double ALERT_DOWN_SECONDS = 1.8;
    public static final RawAnimation ALERT_DOWN_RAW = RawAnimation.begin().thenPlay(ALERT_DOWN);

    /** animation.relic.hit - 0.6 s - oneshot_returns_to_current_state. */
    public static final String HIT = "animation.relic.hit";
    public static final double HIT_SECONDS = 0.6;
    public static final RawAnimation HIT_RAW = RawAnimation.begin().thenPlay(HIT);

    /** animation.relic.release - 3.4 s - oneshot_returns_to_current_state. */
    public static final String RELEASE = "animation.relic.release";
    public static final double RELEASE_SECONDS = 3.4;
    public static final RawAnimation RELEASE_RAW = RawAnimation.begin().thenPlay(RELEASE);

    /** animation.relic.layer_hit - 0.6 s - layer. */
    public static final String LAYER_HIT = "animation.relic.layer_hit";
    public static final double LAYER_HIT_SECONDS = 0.6;
    public static final RawAnimation LAYER_HIT_RAW = RawAnimation.begin().thenPlay(LAYER_HIT);

    /** animation.relic.layer_bump - 1.0 s - layer. */
    public static final String LAYER_BUMP = "animation.relic.layer_bump";
    public static final double LAYER_BUMP_SECONDS = 1.0;
    public static final RawAnimation LAYER_BUMP_RAW = RawAnimation.begin().thenPlay(LAYER_BUMP);

    /** animation.relic.layer_shake - 0.9 s - layer. */
    public static final String LAYER_SHAKE = "animation.relic.layer_shake";
    public static final double LAYER_SHAKE_SECONDS = 0.9;
    public static final RawAnimation LAYER_SHAKE_RAW = RawAnimation.begin().thenPlay(LAYER_SHAKE);

    /** Las 20 animaciones, en el orden del manifiesto. */
    public static final List<RawAnimation> ALL = List.of(IDLE_RAW, IDLE_CALM_RAW, IDLE_CHARGED_RAW, IDLE_ALERT_RAW, IDLE_DORMANT_RAW, ENERGY_PULSE_RAW, ACTIVATION_RAW, DEACTIVATION_RAW, WAKE_RAW, SLEEP_RAW, GLITCH_RAW, CHARGE_UP_RAW, CHARGE_DOWN_RAW, ALERT_UP_RAW, ALERT_DOWN_RAW, HIT_RAW, RELEASE_RAW, LAYER_HIT_RAW, LAYER_BUMP_RAW, LAYER_SHAKE_RAW);

    /** Nombres exactos (los que usan los .json), mismos indices que {@link #ALL}. */
    public static final List<String> ALL_NAMES = List.of(IDLE, IDLE_CALM, IDLE_CHARGED, IDLE_ALERT, IDLE_DORMANT, ENERGY_PULSE, ACTIVATION, DEACTIVATION, WAKE, SLEEP, GLITCH, CHARGE_UP, CHARGE_DOWN, ALERT_UP, ALERT_DOWN, HIT, RELEASE, LAYER_HIT, LAYER_BUMP, LAYER_SHAKE);

    /** Transicion recomendada por el manifiesto: [4, 8] ticks. */
    public static final int TRANSITION_TICKS = 6;
}
