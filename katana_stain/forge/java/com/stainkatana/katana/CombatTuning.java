package com.stainkatana.katana;

/** Numerical rules shared by the server and its tests, in game ticks and damage points. */
public final class CombatTuning {
    public static final int MARK_TICKS = 200;
    private static final int[] COOLDOWN = {120, 60, 360};
    // An accelerating opening, a short pause and a deliberate final stroke.
    private static final int[] ULTIMATE_STRIKES = {10, 26, 40, 58, 77, 99, 119, 138, 158, 185};
    public static int ultimateStrikeCount() { return ULTIMATE_STRIKES.length; }
    public static int ultimateStrikeTick(int index) { return ULTIMATE_STRIKES[index]; }
    public static int ultimateWindupTick(int index) { return ultimateStrikeTick(index) - 6; }
    private CombatTuning() { }
    public static int cooldown(int ability) { return COOLDOWN[ability]; }
    public static int paralysisTicks(boolean playerTarget) { return playerTarget ? 40 : 80; }
    public static int ultimateStaggerTicks(boolean playerTarget) { return playerTarget ? 12 : 20; }
    /** Cap the raw strike at 90% of maximum health, while allowing a weakened target to be finished. */
    public static float backstabDamage(float health, float maximumHealth) {
        if (!Float.isFinite(health) || !Float.isFinite(maximumHealth)) return 0;
        return Math.max(0F, Math.min(60F, Math.min(maximumHealth * .90F, health)));
    }
    /** Distribute remaining health over remaining cuts without killing before the finale.
     * This limits raw damage only; armor, absorption, immunity and other mods remain authoritative. */
    public static float ultimateStrikeDamage(float baseDamage, float health, int index) {
        if (!Float.isFinite(baseDamage) || !Float.isFinite(health) || baseDamage <= 0F || health <= 0F
                || index < 0 || index >= ultimateStrikeCount()) return 0F;
        int remaining = ultimateStrikeCount() - index;
        return remaining == 1 ? baseDamage : Math.min(baseDamage, health / remaining);
    }
    public static float damage(double attackDamage, boolean ultimate) {
        if (!Double.isFinite(attackDamage)) attackDamage = 0;
        return (float) Math.max(8, Math.min(ultimate ? 36 : 26,
                attackDamage * (ultimate ? 2.8 : 2.2)));
    }
}
