package com.capatest.client;

import com.capatest.item.CapePlayback;
import com.capatest.item.CapeState;

/** Worn controller, clearance and tint checks runnable without Forge. */
public final class CapeRuntimeTest {
    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }

    private static CapeState.Wearer ground(boolean blight, boolean sprint, double speed) {
        return new CapeState.Wearer(blight, false, false, false, false, sprint, speed * speed, 0);
    }

    private static CapeState.Wearer airborne(boolean elytra, boolean water, double dy) {
        return new CapeState.Wearer(true, elytra, water, true, false, true, .024, dy);
    }

    public static void main(String[] args) {
        if (args.length == 1 && "--stride-samples".equals(args[0])) {
            exportStride();
            return;
        }
        playback();
        tint();
        stride();
        System.out.println("CapeRuntime: cambios breves, histéresis, deterioro, RGB y holgura rotacional verificados");
    }

    private static void playback() {
        CapePlayback p = new CapePlayback(), other = new CapePlayback();
        check(p.sample(ground(false, false, .034), 0) == CapeState.IDLE, "no arrancar por vibración");
        check(p.sample(ground(false, false, .041), 1) == CapeState.WALK, "umbral de entrada");
        for (int tick = 2; tick <= 7; tick++) {
            check(p.sample(ground(false, false, tick % 2 == 0 ? .027 : .039), tick) == CapeState.WALK,
                    "reposo y marcha alternan cerca del umbral");
            check(p.blendTicks() == 6, "repetir el estado cambia la duración de la mezcla");
        }
        check(other.sample(ground(false, false, .027), 7) == CapeState.IDLE, "otro portador heredó la marcha");
        check(p.sample(ground(false, false, .021), 8) == CapeState.IDLE, "umbral de salida");
        check(p.sample(ground(true, false, 0), 9) == CapeState.BLIGHT, "falta el deterioro quieto");
        CapeState.Wearer dash = ground(true, true, .30);
        check(p.sample(dash, 10) == CapeState.SPRINT && dash.cosmeticState() == CapeState.BLIGHT,
                "el deterioro frenó el paño o perdió sus FX");

        // An illustrative jump: both substates live less than the original 8-tick blend.
        double height = 0, velocity = .42;
        int air = 0, fall = 0;
        for (int tick = 11; tick < 23; tick++) {
            double dy = velocity;
            height += velocity;
            velocity = (velocity - .08) * .98;
            if (height <= 0) break;
            CapeState state = p.sample(airborne(false, false, Math.min(dy, velocity)), tick);
            if (state == CapeState.AIR) air++;
            else if (state == CapeState.FALL) fall++;
            else throw new AssertionError(state);
            check(p.blendTicks() == 3, "mezcla lenta en un salto breve");
        }
        check(air > p.blendTicks() && fall > p.blendTicks() && air < 8 && fall < 8,
                "no se alcanza la reproducción del ciclo durante subida y bajada");
        check(p.sample(airborne(false, false, -.05), 22) == CapeState.FALL, "oscilación cerca del ápice");
        check(p.sample(dash, 23) == CapeState.SPRINT && p.blendTicks() == 3, "aterrizaje tardío");
        var wading = new CapeState.Wearer(false, false, true, true, false, true, .024, -.2);
        check(p.sample(wading, 24) == CapeState.WALK && wading.cosmeticState() == CapeState.SWIM,
                "vadear no selecciona nado ni carrera, pero conserva los FX acuáticos");
        check(p.sample(wading, 25, true) == CapeState.SWIM && p.blendTicks() == 4, "nado en el fallback");
        check(p.sample(wading, 26) == CapeState.WALK && p.blendTicks() == 4, "fin del nado con el cuerpo aún en el agua");
        check(p.sample(airborne(true, true, -.2), 27, true) == CapeState.AIR, "prioridad de planeo");
        check(p.sample(ground(false, false, .038), 200) == CapeState.IDLE, "historia de otro tramo");
        p.reset();
        check(p.sample(ground(true, false, 0), 0) == CapeState.BLIGHT && p.blendTicks() == 8, "reinicio de modelo");
    }

    private static void tint() {
        CapeTint t = new CapeTint(), other = new CapeTint();
        CapeState.Glow a = t.sample(CapeState.SNEAK, 12);
        check(a.equals(CapeState.SNEAK.glow(12)), "RGB de entrada");
        check(t.sample(CapeState.SPRINT, 12).equals(a), "salto cromático al cambiar");
        CapeState.Glow b = t.sample(CapeState.SPRINT, 12.09);
        check(b.red() > a.red() && b.red() < CapeState.SPRINT.glow(12.09).red(), "sin fundido");
        check(t.sample(CapeState.BLIGHT, 12.09).equals(b), "fundido interrumpido desde otro color");
        check(t.sample(CapeState.BLIGHT, 12.09).equals(b), "el doble pase avanzó el reloj");
        check(other.sample(CapeState.SPRINT, 12.09).equals(CapeState.SPRINT.glow(12.09)), "RGB compartido");
        check(t.sample(CapeState.BLIGHT, 12.30).equals(CapeState.BLIGHT.glow(12.30)), "no converge");
        check(t.sample(CapeState.WALK, 1).equals(CapeState.WALK.glow(1)), "arrastre al cambiar el reloj");
        CapeTint guarded = new CapeTint();
        var safe = guarded.sample(CapeState.SPRINT, 5.2);
        check(guarded.sample(CapeState.BLIGHT, Double.NaN).equals(safe), "reloj inválido envenenó el RGB actual");
        check(guarded.sample(CapeState.SPRINT, 5.3).equals(CapeState.SPRINT.glow(5.3)),
                "la transición no reanudó desde el último reloj válido");
        CapeTint firstInvalid = new CapeTint();
        check(firstInvalid.sample(CapeState.BLIGHT, Double.POSITIVE_INFINITY).equals(CapeState.BLIGHT.glow(0)),
                "el primer reloj inválido no usó una época finita");
    }

    private static void stride() {
        check(CapeStride.backDegrees(-.5, 0) == 0, "el brazo que va por el frente empuja el paño");
        check(Math.abs(CapeStride.backDegrees(.5, 0) - Math.toDegrees(.5)) < 1e-10, "signo del giro");
        check(CapeStride.backDegrees(.5, Math.PI / 2) < 1e-10, "brazo girado hacia el lateral");
        check(CapeStride.backDegrees(Double.NaN, 0) == 0, "ángulo inválido");
        check(CapeStride.topLift(10, 0, 0) == 0 && CapeStride.midLift(0, 6, 0) == 0, "se mueve en reposo");
        double arm = CapeStride.armGoal(34, 0, 0), leg = CapeStride.legGoal(48, 0, 0);
        double d = CapeStride.topLift(10, arm, leg);
        check(d > 18 && d < 26 && CapeStride.midLift(10 + d, 5, leg) > 0, "sin holgura al paso");
        check(CapeStride.topLift(48, arm, leg) == 0, "el paño ya está levantado");
        check(CapeStride.topLift(0, 100, 0) < 50, "límite de giro alto");
        check(CapeStride.armGoal(34, .5, 2.4) < arm, "duplica el ajuste al agacharse");
        check(CapeStride.topLift(10, 10.01, 0) < .001, "borde brusco al entrar");
    }

    private static void exportStride() {
        for (double stance : new double[]{0, .25, .75, 1}) {
            for (double arm : new double[]{0, 12, 23, 34, 48, 57.3, 70}) {
                for (double leg : new double[]{0, 32, 48, 68, 80}) {
                    double depth = stance * 2.39 + (leg == 48 ? .8 : 0);
                    double top = 8 + arm * .21, mid = 5.5 + leg * .16;
                    double pitch = stance * CapeFit.CROUCH_RADIANS;
                    double upper = CapeStride.topLift(top, CapeStride.armGoal(arm, pitch, depth),
                            CapeStride.legGoal(leg, pitch, depth));
                    double middle = CapeStride.midLift(top + upper, mid, CapeStride.legGoal(leg, pitch, depth));
                    System.out.println(top + "\t" + mid + "\t" + arm + "\t" + leg + "\t" + stance + "\t"
                            + depth + "\t" + upper + "\t" + middle);
                }
            }
        }
    }
}
