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
    /** Constante de tiempo del destello de un evento, en segundos. */
    private static final float FLASH_TAU = 0.42F;
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
    private int idleCountdown = -1;

    /**
     * Destello de evento (0..1.2): sube de golpe cuando pasa algo y se apaga
     * solo. Lo usa el brillo del modelo y el aura; ver {@link #flash()}.
     */
    private float flash;
    private long flashNanos;

    public RelicAnimatable(UUID wearer) {
        this.wearer = wearer;
        this.stateController = new AnimationController<>(this, "state",
                RelicAnimations.TRANSITION_TICKS, this::stateHandler);
        this.layerController = new AnimationController<>(this, LAYER_CONTROLLER, 4,
                state -> PlayState.CONTINUE);
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

    /**
     * Destello actual, de 0 a ~1.2. Es lo que convierte un evento del servidor
     * (pulso, liberacion, golpe, subida de nivel, despertar) en algo visible: el
     * halo, el pase GLSL y el aura lo multiplican, y el anillo se enciende
     * aunque el estado no lo tuviera.
     */
    public float flash() {
        return this.flash;
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
        // El destello se apaga con tiempo real y no con ticks: asi no se queda a
        // medias cuando el juego va a 5 FPS.
        decayFlash();

        boolean wasActive = this.active;
        this.active = snapshot.active();
        if (wasActive != this.active) {
            this.toggledAt = now;
        }

        // --- Eventos puntuales (sellos de gameTime) -------------------
        if (snapshot.pulse() != this.seenPulse) {
            this.seenPulse = snapshot.pulse();
            if (this.active && isRecent(now, snapshot.pulse())) {
                request(RelicAnimations.ENERGY_PULSE);
                boostFlash(0.60F);
            }
        }
        if (snapshot.release() != this.seenRelease) {
            this.seenRelease = snapshot.release();
            if (isRecent(now, snapshot.release())) {
                request(RelicAnimations.RELEASE);
                boostFlash(0.80F);
            }
        }
        if (snapshot.hit() != this.seenHit) {
            this.seenHit = snapshot.hit();
            if (this.active && isRecent(now, snapshot.hit())) {
                // Doble capa: la reaccion del modelo y el envoltorio relic_react.
                request(RelicAnimations.HIT);
                triggerLayer(RelicAnimations.LAYER_HIT);
                boostFlash(0.30F);
            }
        }
        if (snapshot.bump() != this.seenBump) {
            this.seenBump = snapshot.bump();
            if (isRecent(now, snapshot.bump())) {
                triggerLayer(RelicAnimations.LAYER_BUMP);
                boostFlash(0.40F);
            }
        }

        if (now == this.lastLogicTick) {
            return;
        }
        this.lastLogicTick = now;

        if (this.firstFrame) {
            this.firstFrame = false;
            if (this.active) {
                request(RelicAnimations.ACTIVATION);
            } else {
                // Si se equipa dormida no hay activacion que reproducir: se
                // entra directamente en el bucle apagado.
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

        // --- Variaciones de reposo: la reliquia tambien hace cosas sola ----
        // Antes solo habia un glitch cada 20-60 s; ahora se elige entre varias
        // animaciones de una vez (y capas) para que el standby no sea un bucle
        // congelado esperando a que el jugador pulse una tecla.
        if (this.idleCountdown < 0) {
            this.idleCountdown = nextIdleDelay();
        } else if (--this.idleCountdown <= 0) {
            // Solo en reposo y con la cola vacia: encadenar animaciones de una vez
            // se veria como un tic nervioso.
            if (this.active && isRest(this.loop) && !RelicConfig.REDUCED_EFFECTS.get()
                    && this.pending.isEmpty()) {
                playIdleVariation();
            }
            this.idleCountdown = nextIdleDelay();
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
            // Sin destello: entrar al mundo o despertar la reliquia no es un
            // evento, y encender el brillo a tope al entrar se veia como un flash
            // blanco encima del jugador.
            request(quick ? RelicAnimations.WAKE : RelicAnimations.ACTIVATION);
        } else if (previous != LoopState.DORMANT && next == LoopState.DORMANT) {
            request(quick ? RelicAnimations.SLEEP : RelicAnimations.DEACTIVATION);
        }

        if (restBefore && next == LoopState.CHARGED) {
            request(RelicAnimations.CHARGE_UP);
        } else if (previous == LoopState.CHARGED && restAfter) {
            request(RelicAnimations.CHARGE_DOWN);
        }

        if (restBefore && next == LoopState.ALERT) {
            request(RelicAnimations.ALERT_UP);
        } else if (previous == LoopState.ALERT && restAfter) {
            request(RelicAnimations.ALERT_DOWN);
        }

        // Saltos directos entre alerta y cargado: bajar uno y subir el otro.
        if (previous == LoopState.ALERT && next == LoopState.CHARGED) {
            request(RelicAnimations.ALERT_DOWN);
            request(RelicAnimations.CHARGE_UP);
        } else if (previous == LoopState.CHARGED && next == LoopState.ALERT) {
            request(RelicAnimations.CHARGE_DOWN);
            request(RelicAnimations.ALERT_UP);
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

    private int nextIdleDelay() {
        int min = RelicConfig.GLITCH_MIN_SECONDS.get();
        int max = Math.max(min, RelicConfig.GLITCH_MAX_SECONDS.get());
        // RandomSource propio: no toca el RNG del mundo (que debe seguir siendo
        // determinista) ni el del jugador.
        return this.random.nextInt(min, max + 1) * 20;
    }

    /**
     * Una variacion de reposo: nombre exacto del JSON, si va en el controlador de
     * capas, peso relativo y destello que deja.
     */
    private record IdleVariation(String name, boolean layer, int weight, float flash) {
    }

    /**
     * Repertorio de standby. Las capas ({@code layer_*}) solo animan
     * {@code relic_react}, asi que se pueden disparar encima de cualquier bucle
     * sin romperlo; {@code energy_pulse} y {@code release} son de una vez y
     * vuelven al estado actual, por eso van con peso bajo.
     */
    private static final IdleVariation[] IDLE_VARIATIONS = {
            new IdleVariation(RelicAnimations.LAYER_SHAKE, true, 35, 0.00F),
            new IdleVariation(RelicAnimations.GLITCH, false, 30, 0.15F),
            new IdleVariation(RelicAnimations.LAYER_BUMP, true, 20, 0.00F),
            new IdleVariation(RelicAnimations.ENERGY_PULSE, false, 12, 0.30F),
            new IdleVariation(RelicAnimations.RELEASE, false, 3, 0.40F),
    };

    private void playIdleVariation() {
        IdleVariation variation = pickIdleVariation();
        if (variation.layer()) {
            triggerLayer(variation.name());
        } else {
            request(variation.name());
        }
        if (variation.flash() > 0.0F) {
            boostFlash(variation.flash());
        }
    }

    private IdleVariation pickIdleVariation() {
        if (!RelicConfig.IDLE_VARIATIONS.get()) {
            // Comportamiento anterior: solo el glitch.
            return IDLE_VARIATIONS[1];
        }
        int total = 0;
        for (IdleVariation variation : IDLE_VARIATIONS) {
            total += variation.weight();
        }
        int roll = this.random.nextInt(total);
        for (IdleVariation variation : IDLE_VARIATIONS) {
            roll -= variation.weight();
            if (roll < 0) {
                return variation;
            }
        }
        return IDLE_VARIATIONS[0];
    }

    /** Sube el destello, nunca lo baja: dos golpes seguidos no se apagan entre si. */
    private void boostFlash(float strength) {
        if (strength > this.flash) {
            this.flash = strength;
        }
    }

    private void decayFlash() {
        long now = System.nanoTime();
        if (this.flashNanos == 0L) {
            this.flashNanos = now;
            return;
        }
        float delta = (now - this.flashNanos) / 1_000_000_000.0F;
        this.flashNanos = now;
        if (this.flash <= 0.0F || delta <= 0.0F) {
            return;
        }
        this.flash *= (float) Math.exp(-Math.min(delta, 0.25F) / FLASH_TAU);
        if (this.flash < 0.01F) {
            this.flash = 0.0F;
        }
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

    /**
     * Encola una animacion de una sola vez como <b>instancia nueva</b>.
     *
     * <p>GeckoLib compara la animacion pedida con la actual por identidad, asi
     * que reutilizar la constante haria que dos peticiones seguidas de la misma
     * animacion (dos pulsos, dos golpes) se fundieran en una. Construir el
     * {@link RawAnimation} en cada peticion las distingue; son eventos raros,
     * la asignacion no importa.</p>
     */
    private void request(String animation) {
        if (this.pending.size() >= 4) {
            this.pending.poll();
        }
        this.pending.add(RawAnimation.begin().thenPlay(animation));
    }

    /**
     * Dispara una capa en su propio controlador, sin tocar el bucle.
     *
     * <p>{@code forceAnimationReset()} es necesario porque GeckoLib compara las
     * {@link RawAnimation} por valor: sin el reset, dos golpes seguidos con la
     * misma capa se fundirian en uno (la segunda peticion se considera "la misma
     * animacion ya cargada").</p>
     */
    private void triggerLayer(String name) {
        this.layerController.forceAnimationReset();
        this.layerController.setAnimation(RawAnimation.begin().thenPlay(name));
    }

    private PlayState stateHandler(AnimationState<RelicAnimatable> state) {
        AnimationController<RelicAnimatable> controller = state.getController();
        RawAnimation head = this.pending.peek();
        if (head != null) {
            if (controller.getCurrentRawAnimation() != head) {
                // Reset explicito: RawAnimation.equals compara por valor, asi que
                // dos "energy_pulse" seguidos se considerarian la misma animacion
                // ya cargada y el segundo no se reproduciria.
                controller.forceAnimationReset();
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
