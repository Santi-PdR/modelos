package com.stainkatana.tests;

import com.stainkatana.katana.AbilityTimeline;

/** Tests timing and idempotence without needing a world or Minecraft client. */
public class AbilityTimelineCheck {
    private static void eq(int actual, int expected, String where) {
        if (actual != expected) throw new AssertionError(where + ": " + actual + " != " + expected);
    }
    public static void main(String[] args) {
        for (int ability = 0; ability < 3; ability++) {
            AbilityTimeline t = new AbilityTimeline(ability);
            int first = ability == 0 ? 9 : ability == 2 ? 10 : 7;
            eq(t.advance(first - 1), 0, "before impact");
            eq(t.advance(first), AbilityTimeline.IMPACT, "first impact");
            eq(t.advance(first), 0, "duplicate tick");
            if (ability == 2) {
                eq(t.advance(21), 0, "before follow up");
                eq(t.advance(22), AbilityTimeline.FOLLOW_UP, "follow up");
                eq(t.advance(32), AbilityTimeline.SECOND_IMPACT, "second impact");
                eq(t.advance(196), AbilityTimeline.FADE, "ultimate fade");
                eq(t.advance(200), AbilityTimeline.FINISH, "ultimate finish");
            } else {
                eq(t.advance(ability == 0 ? 18 : 13), AbilityTimeline.FADE, "fade");
                eq(t.advance(ability == 0 ? 21 : 16), AbilityTimeline.FINISH, "finish");
            }
            eq(t.advance(300), 0, "completed timeline emits nothing twice");
        }
        AbilityTimeline skipped = new AbilityTimeline(2);
        eq(skipped.advance(300), 31, "skipped ticks emit all events once");
        eq(skipped.advance(300), 0, "skipped tick cannot repeat");
        AbilityTimeline cancelled = new AbilityTimeline(2);
        cancelled.cancel();
        eq(cancelled.advance(100), 0, "cancelled cast");
        try { new AbilityTimeline(3); throw new AssertionError("invalid ability accepted"); }
        catch (IllegalArgumentException expected) { }
        System.out.println("OK: all ability timelines, skipped ticks, idempotence and cancellation");
    }
}
