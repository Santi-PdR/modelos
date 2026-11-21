package com.santipdr.holocore.client;

import com.santipdr.holocore.common.RelicAnimations;
import com.santipdr.holocore.config.RelicConfig;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.UUID;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import software.bernie.geckolib.core.animatable.GeoAnimatable;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;
import software.bernie.geckolib.util.RenderUtils;

/**
 * Maquina de estados de una reliquia <b>por portador</b>.
 *
 * <p>Hay dos controladores, como pide el diseno del modelo:</p>
 * <ul>
 *   <li>{@code state}: reproduce los bucles de reposo y, cuando hay algo en la
 *       cola, la animacion de una sola vez correspondiente. GeckoLib mezcla la
 *       transicion (6 ticks) entre ambos, que es justo lo que el modelo espera
 *       porque todas las animaciones de una vez terminan en la pose de reposo.</li>
 *   <li>{@code layer}: solo recibe disparos de las animaciones {@code layer_*}.
 *       Estas solo animan {@code relic_react}, asi que no pisan los giros del
 *       bucle y no provocan saltos.</li>
 * </ul>
 */
public final class RelicAnimatable implements GeoAnimatable {

    /** Todos los renderers de una instancia usan el mismo id de manager. */
    public static final long INSTANCE_ID = 0L;

    /** Ticks durante los que se considera "reciente" un sello del servidor. */
    private static final int EVENT_WINDOW_TICKS = 40;
    /** Ticks durante los que se usa wake/sleep en vez de activation/deactivation. */
    private static final int QUICK_TOGGLE_WINDOW = 400;
    private static final String LAYER_CONTROLLER = "layer";

    public enum LoopState {
        IDLE,
        CALM,
        CHARGED,
        ALERT,
        DORMANT
    }

    private final UUID wearer;
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
    private final AnimationController<RelicAnimatable> stateController;
    private final AnimationController<RelicAnimatable> layerController;
    private final Deque<RawAnimation> pending = new ArrayDeque<>(4);
    private final RandomSource random = RandomSource.create();

    private LoopState loop = LoopState.IDLE;
    private boolean active = true;
    private boolean firstFrame = true;
    private long lastLogicTick = Long.MIN_VALUE;
    private long lastRenderTick;
    private long toggledAt = Long.MIN_VALUE;
    private long seenHit;
    private long seenPulse;
    private long seenRelease;
    private long seenBump;
    private int combatTicks;
    private int threatTicks;
    private int scanCooldown;
    private int glitchCountdown = -1;

    public RelicAnimatable(UUID wearer) {
        this.wearer = wearer;
        this.stateController = new AnimationController<>(this, "state",
                RelicAnimations.TRANSITION_TICKS, this::stateHandler);
        this.layerController = new AnimationController<>(this, LAYER_CONTROLLER, 4,
                state -> PlayState.CONTINUE)
                .receiveTriggeredAnimations()
                .triggerableAnim("layer_hit", RelicAnimations.LAYER_HIT_RAW)
                .triggerableAnim("layer_bump", RelicAnimations.LAYER_BUMP_RAW)
                .triggerableAnim("layer_shake", RelicAnimations.LAYER_SHAKE_RAW);
    }

    // ------------------------------------------------------------------
    // Ciclo de vida
    // ------------------------------------------------------------------

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(this.stateController, this.layerController);
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return this.cache;
    }

    /** GeckoLib usa este reloj para animatables que no son entidades. */
    @Override
    public double getTick(Object object) {
        return RenderUtils.getCurrentTick();
    }

    public UUID wearer() {
        return this.wearer;
    }

    public long lastRenderTick() {
        return this.lastRenderTick;
    }

    public LoopState loopState() {
        return this.loop;
    }

    public boolean isActive() {
        return this.active;
    }

    // ------------------------------------------------------------------
    // Logica de estado
    // ------------------------------------------------------------------

    /**
     * Se llama cada frame desde el renderer, antes de dibujar. La parte pesada
     * (escaneo de monstruos) va limitada a una vez cada 10 ticks; los sellos del
     * servidor solo disparan cuando cambian.
     */
    public void update(Player player, ClientRelicStates.Snapshot snapshot, float partialTick) {
        long now = player.level().getGameTime();
        this.lastRenderTick = now;

        boolean wasActive = this.active;
        this.active = snapshot.active();
        if (wasActive != this.active) {
            this.toggledAt = now;
        }

        // --- Eventos puntuales (sellos de gameTime) -------------------
        if (snapshot.pulse() != this.seenPulse) {
            this.seenPulse = snapshot.pulse();
            if (this.active && isRecent(now, snapshot.pulse())) {
                request(RelicAnimations.ENERGY_PULSE_RAW);
            }
        }
        if (snapshot.release() != this.seenRelease) {
            this.seenRelease = snapshot.release();
            if (isRecent(now, snapshot.release())) {
                request(RelicAnimations.RELEASE_RAW);
            }
        }
        if (snapshot.hit() != this.seenHit) {
            this.seenHit = snapshot.hit();
            if (this.active && isRecent(now, snapshot.hit())) {
                // Doble capa: la reaccion del modelo y el envoltorio relic_react.
                request(RelicAnimations.HIT_RAW);
                triggerLayer("layer_hit");
            }
        }
        if (snapshot.bump() != this.seenBump) {
            this.seenBump = snapshot.bump();
            if (isRecent(now, snapshot.bump())) {
                triggerLayer("layer_bump");
            }
        }

        if (now == this.lastLogicTick) {
            return;
        }
        this.lastLogicTick = now;

        if (this.firstFrame) {
            this.firstFrame = false;
            if (this.active) {
                request(RelicAnimations.ACTIVATION_RAW);
            } else {
                this.loop = LoopState.DORMANT;
            }
        }

        // --- Combate: se deduce de datos ya sincronizados -------------
        boolean fighting = player.hurtTime > 0
                || player.swinging
                || player.getAttackAnim(partialTick) > 0.1F;
        if (fighting) {
            this.combatTicks = RelicConfig.COMBAT_HOLD_TICKS.get();
        } else if (this.combatTicks > 0) {
            this.combatTicks--;
        }

        // --- Alerta: monstruos cerca (escaneo limitado) ---------------
        if (this.scanCooldown-- <= 0) {
            this.scanCooldown = 10;
            this.threatTicks = hasThreat(player) ? 40 : Math.max(0, this.threatTicks - 10);
        }

        // --- Glitch aleatorio, solo en reposo ------------------------
        if (this.glitchCountdown < 0) {
            this.glitchCountdown = nextGlitchDelay();
        } else if (--this.glitchCountdown <= 0) {
            if (this.active && isRest(this.loop) && !RelicConfig.REDUCED_EFFECTS.get()) {
                request(RelicAnimations.GLITCH_RAW);
            }
            this.glitchCountdown = nextGlitchDelay();
        }

        LoopState desired = !this.active ? LoopState.DORMANT
                : this.combatTicks > 0 ? LoopState.CHARGED
                : this.threatTicks > 0 ? LoopState.ALERT
                : reducedRest();
        applyLoop(desired, now);
    }

    private LoopState reducedRest() {
        boolean calm = RelicConfig.REDUCED_EFFECTS.get()
                || RelicConfig.QUALITY.get() == RelicConfig.Quality.LITE;
        return calm ? LoopState.CALM : LoopState.IDLE;
    }

    /** Transiciones encadenables: todas acaban en una pose compatible con el reposo. */
    private void applyLoop(LoopState next, long now) {
        if (next == this.loop) {
            return;
        }
        LoopState previous = this.loop;
        boolean restBefore = isRest(previous);
        boolean restAfter = isRest(next);
        boolean quick = this.toggledAt != Long.MIN_VALUE && now - this.toggledAt < QUICK_TOGGLE_WINDOW;

        if (previous == LoopState.DORMANT && next != LoopState.DORMANT) {
            request(quick ? RelicAnimations.WAKE_RAW : RelicAnimations.ACTIVATION_RAW);
        } else if (previous != LoopState.DORMANT && next == LoopState.DORMANT) {
            request(quick ? RelicAnimations.SLEEP_RAW : RelicAnimations.DEACTIVATION_RAW);
        }

        if (restBefore && next == LoopState.CHARGED) {
            request(RelicAnimations.CHARGE_UP_RAW);
        } else if (previous == LoopState.CHARGED && restAfter) {
            request(RelicAnimations.CHARGE_DOWN_RAW);
        }

        if (restBefore && next == LoopState.ALERT) {
            request(RelicAnimations.ALERT_UP_RAW);
        } else if (previous == LoopState.ALERT && restAfter) {
            request(RelicAnimations.ALERT_DOWN_RAW);
        }

        // Saltos directos entre alerta y cargado: bajar uno y subir el otro.
        if (previous == LoopState.ALERT && next == LoopState.CHARGED) {
            request(RelicAnimations.ALERT_DOWN_RAW);
            request(RelicAnimations.CHARGE_UP_RAW);
        } else if (previous == LoopState.CHARGED && next == LoopState.ALERT) {
            request(RelicAnimations.CHARGE_DOWN_RAW);
            request(RelicAnimations.ALERT_UP_RAW);
        }

        this.loop = next;
    }

    private static boolean isRest(LoopState state) {
        return state == LoopState.IDLE || state == LoopState.CALM;
    }

    private boolean hasThreat(Player player) {
        double radius = RelicConfig.ALERT_RADIUS.get();
        return !player.level().getEntitiesOfClass(Monster.class,
                player.getBoundingBox().inflate(radius),
                monster -> monster.isAlive() && !monster.isSpectator()).isEmpty();
    }

    private int nextGlitchDelay() {
        int min = RelicConfig.GLITCH_MIN_SECONDS.get();
        int max = Math.max(min, RelicConfig.GLITCH_MAX_SECONDS.get());
        // RandomSource propio: no toca el RNG del mundo (que debe seguir siendo
        // determinista) ni el del jugador.
        return this.random.nextInt(min, max + 1) * 20;
    }

    private static boolean isRecent(long now, long stamp) {
        if (stamp <= 0L) {
            return false;
        }
        long age = now - stamp;
        return age >= 0L && age <= EVENT_WINDOW_TICKS;
    }

    // ------------------------------------------------------------------
    // Controladores
    // ------------------------------------------------------------------

    private void request(RawAnimation animation) {
        if (this.pending.size() >= 4) {
            this.pending.poll();
        }
        this.pending.add(animation);
    }

    private void triggerLayer(String name) {
        AnimatableManager<RelicAnimatable> manager = this.cache.getManagerForId(INSTANCE_ID);
        manager.tryTriggerAnimation(LAYER_CONTROLLER, name);
    }

    private PlayState stateHandler(AnimationState<RelicAnimatable> state) {
        AnimationController<RelicAnimatable> controller = state.getController();
        RawAnimation head = this.pending.peek();
        if (head != null) {
            if (controller.getCurrentRawAnimation() != head) {
                controller.setAnimation(head);
            } else if (controller.hasAnimationFinished()) {
                this.pending.poll();
            }
            return PlayState.CONTINUE;
        }
        controller.setAnimation(loopRaw());
        return PlayState.CONTINUE;
    }

    private RawAnimation loopRaw() {
        return switch (this.loop) {
            case CALM -> RelicAnimations.IDLE_CALM_RAW;
            case CHARGED -> RelicAnimations.IDLE_CHARGED_RAW;
            case ALERT -> RelicAnimations.IDLE_ALERT_RAW;
            case DORMANT -> RelicAnimations.IDLE_DORMANT_RAW;
            default -> RelicAnimations.IDLE_RAW;
        };
    }
}
