package com.santipdr.holocore.client;

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

    static Target targetFor(RelicAnimatable.LoopState state) {
        return switch (state) {
            case CALM -> new Target(0.42F, 0.60F, 0.78F, 0.70F, 0.00F, 0.000F);
            case CHARGED -> new Target(1.00F, 0.72F, 0.30F, 1.15F, 1.10F, 0.075F);
            case ALERT -> new Target(1.00F, 0.34F, 0.28F, 1.05F, 0.85F, -0.055F);
            case DORMANT -> new Target(0.34F, 0.44F, 0.60F, 0.35F, 0.00F, 0.000F);
            case IDLE -> new Target(0.55F, 0.78F, 1.00F, 1.00F, 0.45F, 0.028F);
        };
    }

    private float red = 0.55F;
    private float green = 0.78F;
    private float blue = 1.00F;
    private float aura = 1.00F;
    private float ring;
    private float spin = 0.028F;

    private boolean initialised;
    private long lastNanos;

    /** Acerca los valores al estado indicado. Se llama una vez por frame y portador. */
    void update(RelicAnimatable.LoopState state) {
        Target target = targetFor(state);

        if (!this.initialised) {
            // Primera vez que se ve este portador: sin transicion, el estado tal cual.
            this.initialised = true;
            this.red = target.red();
            this.green = target.green();
            this.blue = target.blue();
            this.aura = target.aura();
            this.ring = target.ring();
            this.spin = target.spin();
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

        this.red = lerp(this.red, target.red(), colorK);
        this.green = lerp(this.green, target.green(), colorK);
        this.blue = lerp(this.blue, target.blue(), colorK);
        this.aura = lerp(this.aura, target.aura(), weightK);
        this.ring = lerp(this.ring, target.ring(), weightK);
        this.spin = lerp(this.spin, target.spin(), weightK);
    }

    /** Factor de interpolacion exponencial: 1 - e^(-dt/tau). */
    private static float approach(float delta, float tau) {
        return 1.0F - (float) Math.exp(-delta / tau);
    }

    private static float lerp(float from, float to, float factor) {
        return from + (to - from) * factor;
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
