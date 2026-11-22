package com.santipdr.holocore.client;

import com.santipdr.holocore.common.RelicAnimations;
import com.santipdr.holocore.common.RelicServer;
import com.santipdr.holocore.config.RelicConfig;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.LightLayer;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
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
    /** Constante de tiempo de la energia de movimiento, en segundos. */
    private static final float MOTION_TAU = 0.30F;
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

    /**
     * Estados de <b>brillo</b> que corren por encima del ciclo de animacion: no
     * cambian que animacion suena (eso es {@link LoopState}), cambian de que color
     * y con que fuerza late el aura, el halo y el anillo.
     *
     * <p>Van aparte a proposito. Meterlos como {@code LoopState} nuevos obligaria a
     * escribir transiciones para cada pareja (reposo, combate, alerta, dormida...) y
     * una mal escrita deja el modelo en una pose que no toca. Aqui el ciclo de
     * animacion se queda como estaba y lo nuevo es solo luz.</p>
     */
    public enum Mood {
        NEUTRAL,
        /** Otro portador cerca: las dos reliquias se "oyen". */
        RESONANT,
        /** Tormenta encima del portador. */
        STORM,
        /** Portador con poca vida. */
        WOUNDED,
        /** Poca luz donde esta el portador: la reliquia es su propia luz. */
        DARK,
        /** Cae lluvia (sin tormenta) encima del portador. */
        RAIN,
        /**
         * Noche despejada: hay cielo (no es el Nether ni el End), es de noche y no
         * llueve. Antes esto contaba como "oscuridad", pero una reliquia al aire
         * libre bajo las estrellas no esta encerrada: se queda quieta y palida.
         */
        NIGHT,
        /**
         * El portador tiene los ojos dentro del agua: la reliquia se hunde en el
         * ritmo (velocidad 0.66), flota menos y cambia las chispas por burbujas.
         */
        SUBMERGED,
        /**
         * Un portal (del Nether, del End o de salida) a menos de cuatro bloques: la
         * reliquia se pone violeta y nerviosa. Se mira una vez por segundo, no en
         * cada tick, y con una posicion reutilizable: esto corre por portador.
         */
        PORTAL
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
    /** Ultimo tick en el que se actualizo (se dibujara o no). */
    private long lastUpdateTick;
    /** Ultimo tick en el que se dibujo de verdad. */
    private long lastRenderTick;
    /**
     * Si el portador se esta viendo ahora mismo. Cuando no (primera persona),
     * {@link #update} sigue moviendo el estado pero no encola animaciones: si no,
     * se acumularian en la cola y al volver a tercera persona se reproducirian de
     * golpe, como ponerse al dia de lo que paso mientras no mirabas.
     */
    private boolean animate = true;
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

    /**
     * Energia de movimiento (0..1): correr o nadar la sube, quedarse quieto o
     * agachado la baja. Es un eje aparte del estado de brillo: el brillo dice
     * <b>donde</b> estas (tormenta, cueva, agua) y esto dice <b>que estas haciendo</b>,
     * y se pueden dar a la vez. El aura la usa para girar y latir mas rapido.
     */
    private float motion;
    private long motionNanos;

    /** Radio (bloques) al que se nota otro portador. */
    private static final double RESONANCE_RADIUS = 12.0D;
    /** Por debajo de esta fraccion de vida el brillo pasa a herido. */
    private static final float WOUNDED_HEALTH = 0.35F;
    /** Por debajo de esta luz de bloque (0-15) el brillo pasa a "en la oscuridad". */
    private static final int DARK_LIGHT = 4;
    /**
     * Y por debajo de esta luz de cielo, tambien: a cielo abierto de noche no hay
     * luz de bloque pero si cielo, y aquello no es una cueva. Sin este corte, la
     * noche al aire libre se comia el estado nuevo.
     */
    private static final int DARK_SKY = 8;

    /**
     * Ticks minimos entre dos glitch de cambio de estado. Sin esto, caminar por el
     * borde de una cueva o el paso de dia a noche encadenaba animaciones de una
     * sola vez y la reliquia parecia tiritar en vez de reaccionar.
     */
    private static final int MOOD_GLITCH_TICKS = 120;

    private Mood mood = Mood.NEUTRAL;
    /** Ultimo tick en el que el cambio de estado encolo su glitch. */
    private long moodGlitchedAt = Long.MIN_VALUE;
    /**
     * Estado forzado con {@code /relic mood} o la tecla M: sirve para ver tormenta,
     * herido o resonancia sin montar la escena (una tormenta de verdad, dos
     * jugadores...). {@code null} = automatico.
     */
    private static Mood forced;
    /** Velocidad aplicada al controlador de estado (1.0 = la de la animacion). */
    private double animSpeed = 1.0D;
    private int resonanceCooldown;
    private boolean resonanceNear;
    /** Cada cuantos ticks se mira si hay un portal cerca: uno por segundo sobra. */
    private static final int PORTAL_SCAN_TICKS = 20;
    /** Radio (bloques) del escaneo de portal, a la altura de los pies y la cabeza. */
    private static final int PORTAL_RADIUS = 4;
    private int portalCooldown;
    private boolean portalNear;
    /** Posicion reutilizable del escaneo: crear una por bloque seria absurdo. */
    private final BlockPos.MutableBlockPos scanPos = new BlockPos.MutableBlockPos();

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

    /** Ultimo tick dibujado: lo usa el camino de tick para saber si se ve. */
    public long lastRenderTick() {
        return this.lastRenderTick;
    }

    /** Ultimo tick actualizado: lo usa el prune para no tirar visuales vivos. */
    public long lastUpdateTick() {
        return this.lastUpdateTick;
    }

    /** Marca que este portador se dibujo en {@code gameTime}. */
    public void markRendered(long gameTime) {
        this.lastRenderTick = gameTime;
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

    /** Energia de movimiento de ahora mismo, 0 (quieto) .. 1 (corriendo o nadando). */
    public float motion() {
        return this.motion;
    }

    /** Estado de brillo de ahora mismo (ver {@link Mood}). */
    public Mood mood() {
        return this.mood;
    }

    /** Fuerza un estado de brillo, o {@code null} para volver a automatico. */
    public static void forceMood(Mood mood) {
        forced = mood;
    }

    /** Estado forzado, o {@code null} si manda la deteccion automatica. */
    public static Mood forcedMood() {
        return forced;
    }

    /**
     * Siguiente estado de la ronda: automatico -> neutral -> ... -> sumergido ->
     * automatico. La comparten la tecla M y {@code /relic mood next}, para que la
     * ronda sea una sola y no dos ordenes distintos que se pisen.
     *
     * @return el estado que queda forzado, o {@code null} si ha vuelto a automatico
     */
    public static Mood cycleForcedMood() {
        Mood[] valores = Mood.values();
        int siguiente = forced == null ? 0 : forced.ordinal() + 1;
        forced = siguiente >= valores.length ? null : valores[siguiente];
        return forced;
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
        update(player, snapshot, partialTick, true);
    }

    /**
     * Igual que {@link #update(Player, ClientRelicStates.Snapshot, float)}, pero
     * diciendo si el portador se esta viendo.
     *
     * <p>El camino de tick del cliente llama a esta version para el jugador
     * local: en primera persona no hay renderer, y sin esto la maquina de estados
     * se quedaba congelada (ni alerta, ni variaciones de reposo, ni
     * {@code /relic info} con datos). Con {@code visible = false} el estado sigue
     * avanzando pero las animaciones que se pedirian no se encolan.</p>
     */
    public void update(Player player, ClientRelicStates.Snapshot snapshot, float partialTick,
                       boolean visible) {
        long now = player.level().getGameTime();
        this.lastUpdateTick = now;
        this.animate = visible;
        // El destello se apaga con tiempo real y no con ticks: asi no se queda a
        // medias cuando el juego va a 5 FPS.
        decayFlash();
        updateMotion(player);

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
                RelicSounds.pulse(this.wearer);
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

        // --- Estados de brillo: vida baja, tormenta y otro portador cerca ----
        // El escaneo de portadores va cada 20 ticks (una pasada por la lista de
        // jugadores del mundo): hacerlo por tick es gratis hoy y caro en un
        // servidor con mucha gente.
        if (this.resonanceCooldown-- <= 0) {
            this.resonanceCooldown = 20;
            this.resonanceNear = anotherBearerNear(player);
        }
        Mood nextMood = forced != null ? forced : detectMood(player);
        // La velocidad del bucle tambien cuenta: herido va lento (le cuesta), la
        // tormenta acelera y la resonancia se pone nerviosa. Solo se llama al
        // cambiar: setAnimationSpeed crea un lambda que captura la velocidad, y
        // esto corre 20 veces por segundo y portador.
        double speed = speedFor(nextMood);
        if (speed != this.animSpeed) {
            this.animSpeed = speed;
            this.stateController.setAnimationSpeed(speed);
        }

        if (nextMood != this.mood) {
            // Un toque de luz al cambiar, para que se note que la reliquia ha
            // reaccionado a algo y no que se ha recoloreado sola.
            if (nextMood != Mood.NEUTRAL) {
                boostFlash(0.25F);
            }
            // El primer cambio estrena el glitch: con el centinela, la resta daria
            // la vuelta (Long.MIN_VALUE) y el primero no sonaria nunca.
            if (this.active && (this.moodGlitchedAt == Long.MIN_VALUE
                    || this.lastLogicTick - this.moodGlitchedAt >= MOOD_GLITCH_TICKS)) {
                // Glitch de una sola vez: es el mismo lenguaje que el shader (que
                // abre su glitch con el destello), y no hay que inventar keyframes:
                // los .json exportados estan bloqueados por CI contra el zip del
                // modelo, y una animacion nueva se hace en Blockbench, no a ciegas.
                request(RelicAnimations.GLITCH);
                this.moodGlitchedAt = this.lastLogicTick;
            }
            this.mood = nextMood;
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
            RelicSounds.awake(this.wearer);
        } else if (previous != LoopState.DORMANT && next == LoopState.DORMANT) {
            request(quick ? RelicAnimations.SLEEP : RelicAnimations.DEACTIVATION);
            RelicSounds.sleep(this.wearer);
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

    /** Velocidad del bucle de animacion segun el estado de brillo. */
    private static double speedFor(Mood mood) {
        return switch (mood) {
            case WOUNDED -> 0.72D;
            case STORM -> 1.32D;
            case DARK -> 1.06D;
            case RAIN -> 0.92D;
            case NIGHT -> 0.85D;
            // La mas lenta de todas: bajo el agua todo pesa.
            case SUBMERGED -> 0.66D;
            // Un portal tira de la reliquia: es el estado mas nervioso.
            case PORTAL -> 1.22D;
            case RESONANT -> 1.18D;
            case NEUTRAL -> 1.0D;
        };
    }

    /**
     * Estado que pide la escena, sin contar el forzado. El orden es el de
     * importancia: primero lo que le pasa al portador, despues el tiempo, luego
     * la luz y al final la compania.
     */
    private Mood detectMood(Player player) {
        if (!this.active) {
            return Mood.NEUTRAL;
        }
        if (player.getHealth() < player.getMaxHealth() * WOUNDED_HEALTH) {
            return Mood.WOUNDED;
        }
        if (player.level().isThundering()) {
            return Mood.STORM;
        }
        // Bajo el agua manda sobre la luz y el tiempo: es la escena que se ve.
        if (player.isEyeInFluid(FluidTags.WATER)) {
            return Mood.SUBMERGED;
        }
        if (portalNear(player)) {
            return Mood.PORTAL;
        }
        int bloque = player.level().getBrightness(LightLayer.BLOCK, player.blockPosition());
        if (bloque < DARK_LIGHT
                && player.level().getBrightness(LightLayer.SKY, player.blockPosition()) < DARK_SKY) {
            return Mood.DARK;
        }
        if (player.level().isRainingAt(player.blockPosition())) {
            return Mood.RAIN;
        }
        if (player.level().isNight()) {
            return Mood.NIGHT;
        }
        return this.resonanceNear ? Mood.RESONANT : Mood.NEUTRAL;
    }

    /**
     * Portal a menos de cuatro bloques. Se mira una vez por segundo y se guarda:
     * buscar 486 bloques por tick y por portador no lo paga nadie, y un portal no
     * aparece ni desaparece de un tick a otro. La posicion es un campo reutilizable
     * (`MutableBlockPos`) porque un `BlockPos` por bloque escaneado seria asignar
     * 486 objetos por segundo y portador.
     */
    private boolean portalNear(Player player) {
        if (this.portalCooldown-- > 0) {
            return this.portalNear;
        }
        this.portalCooldown = PORTAL_SCAN_TICKS;
        BlockPos base = player.blockPosition();
        boolean found = false;
        for (int dx = -PORTAL_RADIUS; dx <= PORTAL_RADIUS && !found; dx++) {
            for (int dy = -2; dy <= 3 && !found; dy++) {
                for (int dz = -PORTAL_RADIUS; dz <= PORTAL_RADIUS && !found; dz++) {
                    this.scanPos.set(base.getX() + dx, base.getY() + dy, base.getZ() + dz);
                    BlockState state = player.level().getBlockState(this.scanPos);
                    found = state.is(Blocks.NETHER_PORTAL) || state.is(Blocks.END_PORTAL)
                            || state.is(Blocks.END_GATEWAY);
                }
            }
        }
        this.portalNear = found;
        return found;
    }

    /**
     * Otro portador a menos de 12 bloques. Se mira Curios en cliente (Curios
     * sincroniza las ranuras de los jugadores que te ven) y, por si esa consulta
     * no responde para otros jugadores, tambien si su reliquia esta dibujada.
     */
    private static boolean anotherBearerNear(Player player) {
        double radio = RESONANCE_RADIUS * RESONANCE_RADIUS;
        for (Player other : player.level().players()) {
            if (other == player || other.isSpectator()) {
                continue;
            }
            if (other.distanceToSqr(player) > radio) {
                continue;
            }
            if (RelicServer.findRelic(other).isPresent() || RelicVisuals.existing(other) != null) {
                return true;
            }
        }
        return false;
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

    /**
     * Reproduce una animacion por su nombre exacto. Lo usa {@code /relic anim}
     * para poder revisar las 20 sin depender de que un mob te pegue o de esperar
     * a que salga una variacion de reposo.
     *
     * @return {@code false} si el nombre no existe, para que el comando avise
     */
    public boolean play(String nombre) {
        if (!RelicAnimations.ALL_NAMES.contains(nombre)) {
            return false;
        }
        // Pedido a mano: se encola aunque en este momento no se dibuje, para que
        // se vea en cuanto el jugador pase a tercera persona.
        this.animate = true;
        if (isLayer(nombre)) {
            triggerLayer(nombre);
        } else {
            request(nombre);
        }
        return true;
    }

    private static boolean isLayer(String nombre) {
        return nombre.equals(RelicAnimations.LAYER_HIT)
                || nombre.equals(RelicAnimations.LAYER_BUMP)
                || nombre.equals(RelicAnimations.LAYER_SHAKE);
    }

    /** Sube el destello, nunca lo baja: dos golpes seguidos no se apagan entre si. */
    private void boostFlash(float strength) {
        if (strength > this.flash) {
            this.flash = strength;
        }
    }

    /**
     * Energia de movimiento, suavizada con tiempo real (como el destello, para que
     * no se note el tick): correr o nadar la lleva a 1, agacharse a 0.1 y andar la
     * deja a media con la velocidad horizontal. Se mide por tick y no por frame
     * porque el estado del jugador solo cambia por tick.
     */
    private void updateMotion(Player player) {
        long now = System.nanoTime();
        float target;
        if (player.isCrouching()) {
            target = 0.1F;
        } else if (player.isSprinting() || player.isSwimming()) {
            target = 1.0F;
        } else {
            // andar es ~0.1 bloques/tick al cuadrado => ~0.01; correr, ~0.04.
            double rapidez = player.getDeltaMovement().horizontalDistanceSqr();
            target = (float) Math.min(0.6D, rapidez * 12.0D);
        }
        if (this.motionNanos == 0L) {
            this.motionNanos = now;
            this.motion = target;
            return;
        }
        float delta = (now - this.motionNanos) / 1_000_000_000.0F;
        this.motionNanos = now;
        if (delta <= 0.0F) {
            return;
        }
        this.motion += (target - this.motion) * (1.0F - (float) Math.exp(-Math.min(delta, 0.25F) / MOTION_TAU));
        if (Math.abs(target - this.motion) < 0.01F) {
            this.motion = target;
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
        if (!this.animate) {
            return;
        }
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
        if (!this.animate) {
            return;
        }
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
