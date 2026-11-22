package com.capatest.client;

import com.capatest.item.CapeState;

public final class CapeWornLightTest {
    public static void main(String[] args) {
        var a = new CapeWornLight();
        var b = new CapeWornLight();
        var day = a.sample(CapeState.IDLE, 15, 15, 1, 40, .15F, 1);
        var transition = a.sample(CapeState.SNEAK, 0, 0, 1, 40, .75F, 1);
        check(transition.halo().edge() > day.halo().edge() && transition.halo().edge() < .85,
                "went straight from day to night");
        check(a.sample(CapeState.SNEAK, 0, 0, 1, 40, .25F, 1) == transition,
                "an earlier pass reset the crossfade");
        check(a.sample(CapeState.SPRINT, 15, 15, 1, 40, .75F, 1) == transition,
                "same-pose replay consumed new inputs");
        check(b.sample(CapeState.IDLE, 15, 15, 1, 40, .75F, 2).halo().equals(day.halo()),
                "darkness leaked to another wearer");
        var later = a.sample(CapeState.SNEAK, 0, 0, 1, 42, .75F, 1);
        check(later.halo().edge() > transition.halo().edge() && later.halo().edge() < 1.50,
                "exposure did not resume");
        check(later.glow().red() < transition.glow().red(), "tint stopped blending");
        var rewind = a.sample(CapeState.SPRINT, 15, 15, 1, 1, 0, 1);
        check(rewind.halo().equals(day.halo()) && rewind.glow().equals(CapeState.SPRINT.glow(.05)),
                "old color or exposure persisted across a new clock");
        System.out.println("Worn light: fade, same-tick replay, independent wearers and real clock reset verified.");
    }

    private static void check(boolean condition, String reason) {
        if (!condition) throw new AssertionError(reason);
    }
}
