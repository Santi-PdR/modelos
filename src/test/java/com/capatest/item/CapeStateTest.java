package com.capatest.item;

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
        System.out.println("CapeState: ocho clips, prioridades, umbrales y perfiles RGB/chispas verificados");
    }
}
