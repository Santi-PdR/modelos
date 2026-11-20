package com.stainkatana.katana;

/** Numerical rules shared by the server and its tests, in game ticks and damage points. */
public final class CombatTuning {
    public static final int MARK_TICKS = 200;
    private static final int[] COOLDOWN = {240, 100, 900};
    private CombatTuning() { }
    public static int cooldown(int ability) { return COOLDOWN[ability]; }
    public static int paralysisTicks(boolean playerTarget) { return playerTarget ? 30 : 50; }
    public static int ultimateStaggerTicks(boolean playerTarget) { return playerTarget ? 10 : 15; }
    public static float damage(double attackDamage, boolean ultimate) {
        if (!Double.isFinite(attackDamage)) attackDamage = 0;
        return (float) Math.max(4, Math.min(ultimate ? 9 : 12,
                attackDamage * (ultimate ? 0.8 : 1.15)));
    }
}
