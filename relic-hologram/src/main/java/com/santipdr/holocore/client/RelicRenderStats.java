package com.santipdr.holocore.client;

/**
 * Contadores y tiempos del camino de render, para {@code /relic stats}.
 *
 * <p>Existen porque el ahorro de 1.0.16 y 1.0.17 no se ve: el halo sigue
 * brillando igual y el aura sigue girando igual. Lo unico que cambia es cuanto
 * cuesta cada frame, y eso solo se puede discutir con numeros.</p>
 *
 * <p>Se mide <b>por dibujo</b>, no por frame del juego: un «dibujo» es una
 * llamada a {@link RelicGeoRenderer#renderHologram}, o sea una reliquia visible
 * en un frame. De ahi salen las dos cifras que importan:</p>
 * <ul>
 *   <li><b>pases por dibujo</b>: 1 si solo queda el pase base, 4 con base,
 *       emisivo, halo y GLSL. Cada pase recorre los 977 cubos.</li>
 *   <li><b>ms de modelo por dibujo</b>: lo que cuesta dibujar una reliquia una
 *       vez. Es donde se noto quitar tres de las cuatro evaluaciones de
 *       animacion: la diferencia entre 1.0.15 y 1.0.16 se ve en este numero.</li>
 * </ul>
 *
 * <p>El coste de medir es de dos {@link System#nanoTime()} por dibujo y un
 * {@code long} sumado (del orden de decenas de nanosegundos frente a los cientos
 * de microsegundos que se miden). Todo ocurre en el hilo del cliente, que es el
 * mismo que ejecuta los comandos, asi que no hay concurrencia ni volatiles.</p>
 */
final class RelicRenderStats {

    /** Dibujos desde el ultimo reset: una reliquia visible en un frame. */
    private static long draws;
    /** Pases emitidos en esos dibujos (base y extras que estuvieran encendidos). */
    private static long passes;
    /** Nanosegundos acumulados dentro de {@code renderHologram}. */
    private static long modelNanos;
    /** Dibujos del aura (puede ser 0 si aura y anillo estan apagados). */
    private static long auraDraws;
    /** Nanosegundos acumulados dentro de {@code RelicAura.render}. */
    private static long auraNanos;
    /** Arranque de la ventana de medida, para calcular dibujos por segundo. */
    private static long since = System.nanoTime();

    private RelicRenderStats() {
    }

    /** Un dibujo del modelo, con cuantos pases se emitieron y lo que tardo. */
    static void model(long nanos, int passCount) {
        draws++;
        passes += passCount;
        modelNanos += nanos;
    }

    /** Un dibujo del aura y el anillo. */
    static void aura(long nanos) {
        auraDraws++;
        auraNanos += nanos;
    }

    static long draws() {
        return draws;
    }

    static long passes() {
        return passes;
    }

    /** Segundos de la ventana de medida. */
    static double seconds() {
        return (System.nanoTime() - since) / 1_000_000_000.0;
    }

    /** Milisegundos de media por dibujo del modelo (0 si aun no hubo ninguno). */
    static double modelMillis() {
        return draws == 0 ? 0.0 : modelNanos / 1_000_000.0 / draws;
    }

    /** Milisegundos de media por dibujo del aura (0 si no se dibujo). */
    static double auraMillis() {
        return auraDraws == 0 ? 0.0 : auraNanos / 1_000_000.0 / auraDraws;
    }

    static void reset() {
        draws = 0;
        passes = 0;
        modelNanos = 0;
        auraDraws = 0;
        auraNanos = 0;
        since = System.nanoTime();
    }
}
