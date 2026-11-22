package com.stainkatana.tests;

import com.stainkatana.katana.CombatTuning;
import com.stainkatana.katana.KatanaVisualStyle;

public final class CombatTuningCheck {
    public static void main(String[] args) {
        int[] styles = {KatanaVisualStyle.SWING, KatanaVisualStyle.ULTIMATE_CUT, KatanaVisualStyle.HIT,
                KatanaVisualStyle.ULTIMATE_CROSS, KatanaVisualStyle.BLOOD_FLASH, KatanaVisualStyle.DAGGER,
                KatanaVisualStyle.BLOOD_BIND, KatanaVisualStyle.FINISHER, KatanaVisualStyle.SCENE_FOCUS,
                KatanaVisualStyle.ULTIMATE_FINAL};
        for (int i = 0; i < styles.length; i++)
            if (styles[i] != i || !KatanaVisualStyle.valid(styles[i])) throw new AssertionError("visual style id");
        if (KatanaVisualStyle.valid(-1) || KatanaVisualStyle.valid(styles.length)) throw new AssertionError("visual style bounds");
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
        if (CombatTuning.ultimateStrikeCount() != 10 || CombatTuning.ultimateStrikeTick(0) != 10
                || CombatTuning.ultimateStrikeTick(9) >= 196) throw new AssertionError("ultimate schedule endpoints");
        for (int i = 1; i < CombatTuning.ultimateStrikeCount(); i++) {
            int windup = CombatTuning.ultimateWindupTick(i);
            if (windup <= CombatTuning.ultimateStrikeTick(i - 1)
                    || windup >= CombatTuning.ultimateStrikeTick(i))
                throw new AssertionError("windup must follow the previous impact and precede its own");
        }
        if (CombatTuning.backstabDamage(20, 20) != 18 || CombatTuning.backstabDamage(5, 20) != 5
                || CombatTuning.backstabDamage(1, 20) != 1 || CombatTuning.backstabDamage(1000, 1000) != 60)
            throw new AssertionError("backstab cap");
        for (int maximum = 1; maximum <= 1000; maximum++) {
            for (int health = 1; health <= maximum; health += Math.max(1, maximum / 25)) {
                float hit = CombatTuning.backstabDamage(health, maximum);
                if (!Float.isFinite(hit) || hit < 0 || hit > 60 || hit > health)
                    throw new AssertionError("backstab must remain finite and capped");
            }
        }
        if (CombatTuning.backstabDamage(Float.NaN, 20) != 0
                || CombatTuning.backstabDamage(20, Float.POSITIVE_INFINITY) != 0)
            throw new AssertionError("backstab nonfinite input");
        for (float initial : new float[]{1F, 20F, 100F, 1000F}) {
            float health = initial;
            for (int i = 0; i < CombatTuning.ultimateStrikeCount(); i++) {
                float damage = CombatTuning.ultimateStrikeDamage(30F, health, i);
                if (!(damage > 0F) || !Float.isFinite(damage))
                    throw new AssertionError("C strike did not have positive damage: " + initial + " strike=" + i);
                if (i < CombatTuning.ultimateStrikeCount() - 1 && damage >= health)
                    throw new AssertionError("C killed before final strike");
                health = Math.max(0F, health - damage);
            }
        }
        if (CombatTuning.ultimateStrikeDamage(30F, Float.NaN, 0) != 0F
                || CombatTuning.ultimateStrikeDamage(30F, 20F, -1) != 0F
                || CombatTuning.ultimateStrikeDamage(30F, 20F, 10) != 0F)
            throw new AssertionError("C strike damage input validation");
        System.out.println("OK: cooldowns, PvP duration and damage bounds");
    }
}
