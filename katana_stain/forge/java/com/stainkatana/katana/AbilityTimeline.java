package com.stainkatana.katana;

/** Pure, server-tick timeline. Each event can be emitted at most once. */
public final class AbilityTimeline {
    public static final int IMPACT = 1, FOLLOW_UP = 2, SECOND_IMPACT = 4, FADE = 8, FINISH = 16;
    private static final int[] IMPACT_TICK = {9, 7, 10};
    private static final int[] FADE_TICK = {18, 13, 40};
    private static final int[] FINISH_TICK = {21, 16, 46};
    private final int ability;
    private int emitted;
    private boolean cancelled;
    private long previous = -1;

    public AbilityTimeline(int ability) {
        if (ability < 0 || ability >= IMPACT_TICK.length) throw new IllegalArgumentException("ability");
        this.ability = ability;
    }

    /** Returns all newly due events; the caller applies them in chronological order. */
    public int advance(long elapsed) {
        if (cancelled || elapsed < 0 || elapsed < previous) return 0;
        previous = elapsed;
        int due = 0;
        if (elapsed >= IMPACT_TICK[ability]) due |= IMPACT;
        if (ability == 2 && elapsed >= 22) due |= FOLLOW_UP;
        if (ability == 2 && elapsed >= 32) due |= SECOND_IMPACT;
        if (elapsed >= FADE_TICK[ability]) due |= FADE;
        if (elapsed >= FINISH_TICK[ability]) due |= FINISH;
        int result = due & ~emitted;
        emitted |= due;
        return result;
    }

    public void cancel() { cancelled = true; }
}
