package com.stainkatana.katana;

/** Numerical rules shared by the server and its tests, in game ticks and damage points. */
public final class CombatTuning {
    public static final int MARK_TICKS = 200;
    private static final int[] COOLDOWN = {120, 60, 360};
    private CombatTuning() { }
    public static int cooldown(int ability) { return COOLDOWN[ability]; }
    public static int paralysisTicks(boolean playerTarget) { return playerTarget ? 40 : 80; }
    public static int ultimateStaggerTicks(boolean playerTarget) { return playerTarget ? 12 : 20; }
    public static float damage(double attackDamage, boolean ultimate) {
        if (!Double.isFinite(attackDamage)) attackDamage = 0;
        return (float) Math.max(8, Math.min(ultimate ? 36 : 26,
                attackDamage * (ultimate ? 2.8 : 2.2)));
    }
}
