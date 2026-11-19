package com.capatest.item;

import com.capatest.client.CapeResponse;

import java.util.HashSet;
import java.util.Set;

/** Ejecutable sin Minecraft para comprobar selección y límites de FX en CI. */
public final class CapeStateTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void mode(CapeState expected, boolean blight, boolean elytra, boolean water,
                             boolean air, boolean crouch, boolean sprint, double speed, double vertical) {
        CapeState actual = CapeState.select(blight, elytra, water, air, crouch, sprint, speed, vertical);
        check(expected == actual, expected + " != " + actual);
    }

    public static void main(String[] args) {
        if (args.length == 1 && "--spark-samples".equals(args[0])) {
            exportSparkSamples();
            return;
        }
        mode(CapeState.IDLE, false,false,false,false,false,true, 0,0);
        mode(CapeState.WALK, false,false,false,false,false,false, .024,0);
        mode(CapeState.SPRINT, false,false,false,false,false,true, .024,0);
        mode(CapeState.FALL, false,false,false,true,false,true, .024,-.1);
        mode(CapeState.AIR, false,true,false,true,false,true, .024,-.1);
        mode(CapeState.AIR, false,false,false,true,false,false, .02,.1);
        mode(CapeState.SWIM, false,false,true,true,false,true, .024,-.1);
        mode(CapeState.SNEAK, false,false,false,false,true,true, .024,0);
        mode(CapeState.BLIGHT, true,true,true,true,true,true, .024,-.1);
        check(!CapeState.deteriorated(20,20,1,100), "un arañazo no activa deterioro");
        check(!CapeState.deteriorated(11,20,64,100), "fuera de umbral");
        check(CapeState.deteriorated(10,20,0,0), "media vida");
        check(CapeState.deteriorated(20,20,65,100), "65% de desgaste");

        Set<String> clips = new HashSet<>();
        for (CapeState state : CapeState.values()) {
            check(clips.add(state.clip()), "clip duplicado");
            CapeState.Aura aura = state.aura();
            check(aura.count() >= 1 && aura.count() <= 3, "presupuesto");
            check(aura.lift() > 0 && aura.lift() <= .021, "elevación de chispa");
            boolean sawCollar = false;
            for (int pulse = 0; pulse < 16; pulse++) {
                for (int index = 0; index < aura.count(); index++) {
                    CapeState.Spark spark = state.spark(pulse, index, true, .5, .5, .5);
                    CapeState.Spark edge = state.spark(pulse, index, true, 1, 1, 1);
                    CapeState.Spark low = state.spark(pulse, index, false, 0, 0, 0);
                    check(!low.collar() && low.height() < .8, "chispa alta al volar o nadar");
                    check(Math.abs(spark.side()) >= .18 && Math.abs(edge.side()) <= .681, "anclaje lateral");
                    check(low.depth() >= .30 && spark.depth() >= .31 && edge.depth() <= .681, "chispas fuera de la espalda");
                    check(edge.height() <= 1.63, "chispa por encima del cuello");
                    check(low.height() >= 0, "chispa bajo el suelo");
                    if (spark.collar()) {
                        sawCollar = true;
                        check(spark.height() >= 1.44 && Math.abs(edge.side()) >= .436, "nace cerca de la cara");
                    }
                }
            }
            check(sawCollar == (state==CapeState.IDLE || state==CapeState.WALK ||
                    state==CapeState.SNEAK || state==CapeState.BLIGHT), "nivel de aura del estado");
            for (int i = 0; i <= 400; i++) {
                CapeState.Glow c = state.glow(i / 20.0);
                check(c.red() > .25 && c.red() <= 1 && c.green() > .25 && c.green() <= 1
                        && c.blue() > .25 && c.blue() <= 1, "RGB fuera de rango");
            }
        }
        check(clips.size() == 8, "ocho estados");
        check(CapeState.SPRINT.aura().trail() > 3 * CapeState.IDLE.aura().trail(), "no hay estela");
        check(CapeState.BLIGHT.aura().count() == 3, "falta la tercera chispa de deterioro");
        check(CapeState.BLIGHT.glow(0).red() > CapeState.BLIGHT.glow(1.5).red()
                && CapeState.BLIGHT.glow(1.5).red() > CapeState.BLIGHT.glow(.75).red(), "falta el eco");
        check(CapeState.BLIGHT.spark(2, 0, true, .5, .5, .5).side()
                * CapeState.BLIGHT.spark(2, 2, true, .5, .5, .5).side() < 0, "dos bordes del dobladillo");
        check(CapeState.WALK.spark(1, 0, true, .5, .5, .5).depth() > .6, "separación baja al fondo");
        check(CapeState.WALK.spark(7, 0, true, .5, .5, .5).height() > .40, "no hay chispa lateral");
        double at30 = simulateResponse(30), at144 = simulateResponse(144);
        check(at30 > .8 && at30 < 1 && Math.abs(at30-at144) < 1e-12,
                "respuesta distinta con 30 y 144 fps");
        CapeResponse filter = new CapeResponse();
        filter.sample(9,0,0,0,0,0,0,0);
        double first = filter.sample(9.03,1,0,0,0,0,0,0)[0];
        check(filter.sample(9.03,1,0,0,0,0,0,0)[0] == first, "dos pasadas avanzan el filtro");
        check(filter.sample(0,.5,0,0,0,0,0,0)[0] == .5, "arrastre de otro reloj");
        check(Math.abs(simulateTurn(30)-simulateTurn(144)) < 1e-12, "retardo distinto con FPS");
        filter.sample(10,0,0,0,0,0,0,0);
        filter.sample(10.1,0,0,1,0,0,0,0);
        double upper = filter.turnAt(.2), hem = filter.turnAt(1);
        check(upper > hem && hem > 0, "el dobladillo responde antes que la tela alta");
        filter.sample(10.1,0,0,-1,0,0,0,0);
        check(filter.turnAt(1) == hem, "la emisión vuelve a avanzar el dobladillo");
        filter.sample(10.75,0,0,-1,0,0,0,0);
        check(filter.turnAt(1) == -1, "se conserva un giro de una entidad anterior");
        System.out.println("CapeState: ocho clips, aura con cuatro zonas y filtro independiente de FPS verificados");
    }

    private static void exportSparkSamples() {
        for (CapeState state : CapeState.values()) {
            for (int pulse = 0; pulse < 24; pulse++) {
                for (boolean grounded : new boolean[]{false, true}) {
                    for (int i = 0; i < state.aura().count(); i++) {
                        double a = (pulse % 5) / 4.0;
                        double b = ((pulse + 3 * i + 1) % 7) / 6.0;
                        double c = (i + 1) / 4.0;
                        CapeState.Spark s = state.spark(pulse, i, grounded, a, b, c);
                        System.out.println(state.clip() + "\t" + pulse + "\t" + i + "\t" + grounded
                                + "\t" + a + "\t" + b + "\t" + c
                                + "\t" + s.side() + "\t" + s.height() + "\t" + s.depth() + "\t" + s.collar());
                    }
                }
            }
        }
    }

    private static double simulateTurn(int fps) {
        CapeResponse filter = new CapeResponse();
        filter.sample(0,0,0,0,0,0,0,0);
        for (int i = 1; i <= fps; i++)
            filter.sample(i / (double) fps,0,0,1,0,0,0,0);
        return filter.turnAt(1);
    }

    private static double simulateResponse(int fps) {
        CapeResponse filter = new CapeResponse();
        filter.sample(0,0,0,0,0,0,0,0);
        for (int i = 1; i < fps; i++)
            filter.sample(i / (double) fps,1,0,0,0,0,0,0);
        return filter.sample(1,1,0,0,0,0,0,0)[0];
    }
}
