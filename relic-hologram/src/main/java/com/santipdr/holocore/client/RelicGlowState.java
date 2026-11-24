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
    private static final float DARK_RED = 0.80F;
    private static final float DARK_GREEN = 0.95F;
    private static final float DARK_BLUE = 1.00F;
    private static final float RAIN_RED = 0.45F;
    private static final float RAIN_GREEN = 0.68F;
    private static final float RAIN_BLUE = 0.95F;
    /** Noche despejada: frio de hielo, pero muy poco mezclado (casi el reposo). */
    private static final float NIGHT_RED = 0.38F;
    private static final float NIGHT_GREEN = 0.72F;
    private static final float NIGHT_BLUE = 1.00F;
    /** Ardiendo: naranja de brasa, el unico estado calido de los diez. */
    private static final float BURNING_RED = 1.00F;
    private static final float BURNING_GREEN = 0.42F;
    private static final float BURNING_BLUE = 0.16F;
    /** Congelandose: hielo palido, el estado mas frio de la paleta. */
    private static final float FREEZING_RED = 0.62F;
    private static final float FREEZING_GREEN = 0.88F;
    private static final float FREEZING_BLUE = 1.00F;
    /** Portal cerca: violeta de obsidiana encantada, el color mas "magico" de todos. */
    private static final float PORTAL_RED = 0.78F;
    private static final float PORTAL_GREEN = 0.42F;
    private static final float PORTAL_BLUE = 1.00F;
    /**
     * Nether: brasa de forja, mas roja y mas honda que el naranja de ardiendo. No
     * se pueden confundir porque ardiendo manda sobre el sitio: si te quemas en el
     * Nether el color es el de ardiendo.
     */
    private static final float NETHER_RED = 0.98F;
    private static final float NETHER_GREEN = 0.38F;
    private static final float NETHER_BLUE = 0.20F;
    /** End: hueso verdoso del vacio. Es el unico estado claro y desaturado. */
    private static final float END_RED = 0.78F;
    private static final float END_GREEN = 0.86F;
    private static final float END_BLUE = 0.64F;
    /** Bajo el agua: verdoso de fondo de rio, con el anillo casi apagado. */
    private static final float SUBMERGED_RED = 0.30F;
    private static final float SUBMERGED_GREEN = 0.88F;
    private static final float SUBMERGED_BLUE = 0.86F;

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
            case DARK -> {
                // En la oscuridad la reliquia es la unica luz: se pone casi blanca
                // y sube bastante. Es el estado que mas se nota en una cueva.
                red = lerp(red, DARK_RED, 0.50F);
                green = lerp(green, DARK_GREEN, 0.50F);
                blue = lerp(blue, DARK_BLUE, 0.50F);
                aura += 0.20F;
                ring += 0.10F;
            }
            case RAIN -> {
                red = lerp(red, RAIN_RED, 0.45F);
                green = lerp(green, RAIN_GREEN, 0.45F);
                blue = lerp(blue, RAIN_BLUE, 0.45F);
                aura += 0.05F;
                ring -= 0.15F;
            }
            case BURNING -> {
                // Naranja de brasa y el aura arriba: si te estas quemando, la
                // reliquia lo dice con el color mas calido que hay en el mod.
                red = lerp(red, BURNING_RED, 0.60F);
                green = lerp(green, BURNING_GREEN, 0.60F);
                blue = lerp(blue, BURNING_BLUE, 0.60F);
                aura += 0.18F;
                ring += 0.30F;
                spin += 0.060F;
            }
            case FREEZING -> {
                // Hielo: azul casi blanco, poco aura y el giro mas quieto de todos.
                // El frio no acelera nada, lo apaga.
                red = lerp(red, FREEZING_RED, 0.55F);
                green = lerp(green, FREEZING_GREEN, 0.55F);
                blue = lerp(blue, FREEZING_BLUE, 0.55F);
                aura += 0.08F;
                ring += 0.04F;
                spin -= 0.014F;
            }
            case PORTAL -> {
                // Un portal tira del color y del giro: es el unico estado "de sitio"
                // que se nota a distancia, y el violeta no lo tiene ningun otro.
                red = lerp(red, PORTAL_RED, 0.50F);
                green = lerp(green, PORTAL_GREEN, 0.50F);
                blue = lerp(blue, PORTAL_BLUE, 0.50F);
                aura += 0.14F;
                ring += 0.20F;
                spin += 0.040F;
            }
            case SUBMERGED -> {
                // El agua se come el rojo: la reliquia tira a verde azulado y el
                // anillo se queda casi apagado, que es lo que pasa bajo el agua.
                red = lerp(red, SUBMERGED_RED, 0.45F);
                green = lerp(green, SUBMERGED_GREEN, 0.45F);
                blue = lerp(blue, SUBMERGED_BLUE, 0.45F);
                aura += 0.02F;
                ring -= 0.20F;
                spin -= 0.020F;
            }
            case NETHER -> {
                // El sitio calienta la reliquia: brasa, mas aura y el giro avivado.
                red = lerp(red, NETHER_RED, 0.45F);
                green = lerp(green, NETHER_GREEN, 0.45F);
                blue = lerp(blue, NETHER_BLUE, 0.45F);
                aura += 0.12F;
                ring += 0.22F;
                spin += 0.045F;
            }
            case END -> {
                // El vacio no empuja: casi sin anillo, por debajo del reposo.
                red = lerp(red, END_RED, 0.45F);
                green = lerp(green, END_GREEN, 0.45F);
                blue = lerp(blue, END_BLUE, 0.45F);
                aura += 0.04F;
                ring -= 0.25F;
                spin -= 0.018F;
            }
            case NIGHT -> {
                // Noche despejada: casi el reposo, un punto mas frio y con el aura
                // baja. La reliquia se apaga, no se enciende: el cielo ya ilumina.
                red = lerp(red, NIGHT_RED, 0.30F);
                green = lerp(green, NIGHT_GREEN, 0.30F);
                blue = lerp(blue, NIGHT_BLUE, 0.30F);
                aura -= 0.06F;
                spin -= 0.010F;
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
