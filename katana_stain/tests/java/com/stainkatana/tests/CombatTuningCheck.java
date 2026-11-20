package com.stainkatana.tests;

import com.stainkatana.katana.CombatTuning;

public final class CombatTuningCheck {
    public static void main(String[] args) {
        if (CombatTuning.MARK_TICKS != 200 || CombatTuning.cooldown(0) != 120
                || CombatTuning.cooldown(1) != 60 || CombatTuning.cooldown(2) != 360)
            throw new AssertionError("cooldowns or mark");
        if (CombatTuning.paralysisTicks(true) >= CombatTuning.paralysisTicks(false)
                || CombatTuning.ultimateStaggerTicks(true) >= CombatTuning.paralysisTicks(true))
            throw new AssertionError("PvP crowd control must remain shorter");
        if (Math.abs(CombatTuning.damage(11, false) - 24.2) > .001
                || Math.abs(CombatTuning.damage(11, true) - 30.8) > .001)
            throw new AssertionError("netherite sword baseline damage");
        for (boolean ultimate : new boolean[]{false, true}) {
            double previous = 0;
            for (int i = -100; i < 1000; i++) {
                float damage = CombatTuning.damage(i, ultimate);
                if (damage < previous || damage < 8 || damage > (ultimate ? 36 : 26))
                    throw new AssertionError("damage bounds or monotonicity");
                previous = damage;
            }
            if (CombatTuning.damage(Double.NaN, ultimate) != 8) throw new AssertionError("nonfinite damage");
        }
        System.out.println("OK: cooldowns, PvP duration and damage bounds");
    }
}
