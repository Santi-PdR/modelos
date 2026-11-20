package com.stainkatana.tests;

import com.stainkatana.katana.CombatTuning;

public final class CombatTuningCheck {
    public static void main(String[] args) {
        if (CombatTuning.MARK_TICKS != 200 || CombatTuning.cooldown(0) != 240
                || CombatTuning.cooldown(1) != 100 || CombatTuning.cooldown(2) != 900)
            throw new AssertionError("cooldowns or mark");
        if (CombatTuning.paralysisTicks(true) >= CombatTuning.paralysisTicks(false)
                || CombatTuning.ultimateStaggerTicks(true) >= CombatTuning.paralysisTicks(true))
            throw new AssertionError("PvP crowd control must remain shorter");
        if (Math.abs(CombatTuning.damage(7, false) - 8.05) > .001
                || Math.abs(CombatTuning.damage(7, true) - 5.6) > .001)
            throw new AssertionError("diamond sword baseline damage");
        for (boolean ultimate : new boolean[]{false, true}) {
            double previous = 0;
            for (int i = -100; i < 1000; i++) {
                float damage = CombatTuning.damage(i, ultimate);
                if (damage < previous || damage < 4 || damage > (ultimate ? 9 : 12))
                    throw new AssertionError("damage bounds or monotonicity");
                previous = damage;
            }
            if (CombatTuning.damage(Double.NaN, ultimate) != 4) throw new AssertionError("nonfinite damage");
        }
        System.out.println("OK: cooldowns, PvP duration and damage bounds");
    }
}
