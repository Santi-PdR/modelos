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
            check(aura.depth() > 0.25 && aura.depth() <= .65, "distancia de la espalda");
            check(aura.lift() > 0 && aura.lift() <= .021, "elevación de chispa");
            boolean sawCollar = false;
            for (int pulse = 0; pulse < 16; pulse++) {
                for (int index = 0; index < aura.count(); index++) {
                    CapeState.Spark spark = state.spark(pulse, index, true, .5, .5, .5);
                    CapeState.Spark edge = state.spark(pulse, index, true, 1, 1, 1);
                    CapeState.Spark low = state.spark(pulse, index, false, 1, 1, 1);
                    check(!low.collar() && low.height() < .8, "chispa alta al volar o nadar");
                    check(Math.abs(spark.side()) >= .24 && Math.abs(edge.side()) < .62, "anclaje lateral");
                    check(spark.depth() > .26 && edge.depth() <= .601, "chispas fuera de la espalda");
                    check(edge.height() <= 1.52, "chispa por encima del cuello");
                    if (spark.collar()) {
                        sawCollar = true;
                        check(spark.height() >= 1.36 && Math.abs(spark.side()) >= .50, "nace cerca de la cara");
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
                == -CapeState.BLIGHT.spark(2, 2, true, .5, .5, .5).side(), "dos bordes del dobladillo");
        double at30 = simulateResponse(30), at144 = simulateResponse(144);
        check(at30 > .8 && at30 < 1 && Math.abs(at30-at144) < 1e-12,
                "respuesta distinta con 30 y 144 fps");
        CapeResponse filter = new CapeResponse();
        filter.sample(9,0,0,0,0,0,0,0);
        double first = filter.sample(9.03,1,0,0,0,0,0,0)[0];
        check(filter.sample(9.03,1,0,0,0,0,0,0)[0] == first, "dos pasadas avanzan el filtro");
        check(filter.sample(0,.5,0,0,0,0,0,0)[0] == .5, "arrastre de otro reloj");
        System.out.println("CapeState: ocho clips, aura con dos niveles y filtro independiente de FPS verificados");
    }

    private static double simulateResponse(int fps) {
        CapeResponse filter = new CapeResponse();
        filter.sample(0,0,0,0,0,0,0,0);
        for (int i = 1; i < fps; i++)
            filter.sample(i / (double) fps,1,0,0,0,0,0,0);
        return filter.sample(1,1,0,0,0,0,0,0)[0];
    }
}
