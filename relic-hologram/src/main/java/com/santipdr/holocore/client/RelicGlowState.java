package com.santipdr.holocore.client;

import com.santipdr.holocore.config.RelicConfig;

/**
 * Aspecto actual del aura y del anillo de un portador, <b>interpolado</b>.
 *
 * <p>Sin esto, un cambio de estado (reposo → cargada, por ejemplo) hacia que el
 * azul saltara a ambar en un frame. El salto canta, sobre todo en algo tan grande
 * como el anillo. Aqui el color, la fuerza y el giro se acercan al objetivo con
 * una constante de tiempo, y el giro del anillo pasa por cero al cambiar de
 * sentido en vez de invertirse de golpe.</p>
 *
 * <p>La interpolacion usa el tiempo real entre frames de <b>ese</b> portador (no
 * ticks ni un factor por frame), asi que se ve igual a 30 que a 240 FPS y no se
 * acelera cuando la reliquia deja de renderizarse una temporada. Hay una
 * instancia por portador, creada en {@link RelicVisuals}.</p>
 */
final class RelicGlowState {

    /** Constante de tiempo del color, en segundos (63% del recorrido). */
    private static final float COLOR_TAU = 0.30F;
    /** Los pesos y el giro van algo mas rapidos que el color. */
    private static final float WEIGHT_TAU = 0.22F;
    /** Tope del delta: si el juego se congela, no interpolar de golpe. */
    private static final float MAX_DELTA = 0.25F;

    /** Lo que pide cada estado. {@code ring} = 0 significa que no se dibuja. */
    record Target(float red, float green, float blue, float aura, float ring, float spin) {
    }

    /**
     * Los cinco destinos, creados <b>una vez</b>. Son constantes: el estado que
     * pide cada uno no cambia en caliente (la config se aplica al usarlos, no
     * aqui), asi que no hay motivo para crear un {@code Target} por portador y
     * frame.
     */
    private static final Target TARGET_CALM = new Target(0.42F, 0.60F, 0.78F, 0.70F, 0.00F, 0.000F);
    private static final Target TARGET_CHARGED = new Target(1.00F, 0.72F, 0.30F, 1.15F, 1.10F, 0.075F);
    private static final Target TARGET_ALERT = new Target(1.00F, 0.34F, 0.28F, 1.05F, 0.85F, -0.055F);
    private static final Target TARGET_DORMANT = new Target(0.34F, 0.44F, 0.60F, 0.35F, 0.00F, 0.000F);
    private static final Target TARGET_IDLE = new Target(0.55F, 0.78F, 1.00F, 1.00F, 0.45F, 0.028F);

    static Target targetFor(RelicAnimatable.LoopState state) {
        return switch (state) {
            case CALM -> TARGET_CALM;
            case CHARGED -> TARGET_CHARGED;
            case ALERT -> TARGET_ALERT;
            case DORMANT -> TARGET_DORMANT;
            case IDLE -> TARGET_IDLE;
        };
    }

    /**
     * Destello de evento sin suavizar: {@link RelicAnimatable#flash()} ya viene
     * con su propia envolvente de decaimiento, asi que aqui solo se guarda.
     */
    private float flash;

    private float red = 0.55F;
    private float green = 0.78F;
    private float blue = 1.00F;
    private float aura = 1.00F;
    private float ring;
    private float spin = 0.028F;

    private boolean initialised;
    private long lastNanos;

    // Colores y pesos de los estados de brillo (ver RelicAnimatable.Mood). Son
    // constantes sueltas y no un Target porque la mezcla se hace en locales: el
    // CI (Validate render path allocations) no admite ni un objeto nuevo por
    // frame en esta clase.
    private static final float WOUNDED_RED = 1.00F;
    private static final float WOUNDED_GREEN = 0.30F;
    private static final float WOUNDED_BLUE = 0.28F;
    private static final float STORM_RED = 0.75F;
    private static final float STORM_GREEN = 0.92F;
    private static final float STORM_BLUE = 1.00F;
    private static final float RESONANT_RED = 0.85F;
    private static final float RESONANT_GREEN = 0.62F;
    private static final float RESONANT_BLUE = 1.00F;

    /**
     * Acerca los valores al estado indicado, con el matiz del {@code mood}, y
     * guarda el destello del evento. Se llama una vez por frame y portador.
     */
    void update(RelicAnimatable.LoopState state, float flash, RelicAnimatable.Mood mood) {
        this.flash = Math.max(0.0F, Math.min(1.2F, flash));
        Target base = targetFor(state);

        // El mood tira del color del estado hacia el suyo y sube aura, anillo y
        // giro. Herido manda sobre tormenta, y tormenta sobre resonancia: es el
        // orden en el que importan las cosas.
        float red = base.red();
        float green = base.green();
        float blue = base.blue();
        float aura = base.aura();
        float ring = base.ring();
        float spin = base.spin();
        switch (mood) {
            case WOUNDED -> {
                red = lerp(red, WOUNDED_RED, 0.55F);
                green = lerp(green, WOUNDED_GREEN, 0.55F);
                blue = lerp(blue, WOUNDED_BLUE, 0.55F);
                aura += 0.10F;
                ring += 0.55F;
                spin += 0.030F;
            }
            case STORM -> {
                red = lerp(red, STORM_RED, 0.45F);
                green = lerp(green, STORM_GREEN, 0.45F);
                blue = lerp(blue, STORM_BLUE, 0.45F);
                aura += 0.15F;
                ring += 0.25F;
                spin += 0.050F;
            }
            case RESONANT -> {
                red = lerp(red, RESONANT_RED, 0.40F);
                green = lerp(green, RESONANT_GREEN, 0.40F);
                blue = lerp(blue, RESONANT_BLUE, 0.40F);
                aura += 0.12F;
                ring += 0.35F;
                spin += 0.060F;
            }
            default -> {
                // NEUTRAL: el estado tal cual.
            }
        }

        if (!this.initialised) {
            // Primera vez que se ve este portador: sin transicion, el estado tal cual.
            this.initialised = true;
            this.red = red;
            this.green = green;
            this.blue = blue;
            this.aura = aura;
            this.ring = ring;
            this.spin = spin;
            this.lastNanos = System.nanoTime();
            return;
        }

        long now = System.nanoTime();
        float delta = Math.min(MAX_DELTA, (now - this.lastNanos) / 1_000_000_000.0F);
        this.lastNanos = now;
        if (delta <= 0.0F) {
            return;
        }

        float colorK = approach(delta, COLOR_TAU);
        float weightK = approach(delta, WEIGHT_TAU);

        this.red = lerp(this.red, red, colorK);
        this.green = lerp(this.green, green, colorK);
        this.blue = lerp(this.blue, blue, colorK);
        this.aura = lerp(this.aura, aura, weightK);
        this.ring = lerp(this.ring, ring, weightK);
        this.spin = lerp(this.spin, spin, weightK);
    }

    /** Factor de interpolacion exponencial: 1 - e^(-dt/tau). */
    private static float approach(float delta, float tau) {
        return 1.0F - (float) Math.exp(-delta / tau);
    }

    private static float lerp(float from, float to, float factor) {
        return from + (to - from) * factor;
    }

    /**
     * Destello (0..1.2) ya escalado por {@code visuals.flashIntensity}: es el
     * unico sitio donde se aplica esa config, para que halo, GLSL y aura suban
     * exactamente lo mismo.
     */
    float flashScaled() {
        if (this.flash <= 0.0F) {
            return 0.0F;
        }
        double configured = RelicConfig.FLASH_INTENSITY.get();
        return this.flash * (float) Math.max(0.0D, Math.min(2.0D, configured));
    }

    float red() {
        return this.red;
    }

    float green() {
        return this.green;
    }

    float blue() {
        return this.blue;
    }

    float aura() {
        return this.aura;
    }

    float ring() {
        return this.ring;
    }

    float spin() {
        return this.spin;
    }
}
