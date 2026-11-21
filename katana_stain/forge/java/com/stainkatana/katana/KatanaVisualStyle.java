package com.stainkatana.katana;

/** Networked visual cues only; they never carry authority over damage or target selection. */
public final class KatanaVisualStyle {
    public static final int SWING = 0, ULTIMATE_CUT = 1, HIT = 2, ULTIMATE_CROSS = 3;
    public static final int BLOOD_FLASH = 4, DAGGER = 5, BLOOD_BIND = 6, FINISHER = 7;
    public static final int SCENE_FOCUS = 8, ULTIMATE_FINAL = 9;
    private KatanaVisualStyle() { }
    public static boolean valid(int style) { return style >= SWING && style <= ULTIMATE_FINAL; }
}
