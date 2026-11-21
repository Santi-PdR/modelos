package com.capatest.client;

import java.util.HashMap;
import java.util.Map;

/** Let the free outer ribbons trail inboard of the sleeves at running pace. */
final class CapeSprintEdge {
    // Index by distance from the outside of the 12 authored ribbons. The
    // centre four, the sewn segment 0 and the heavy hinges do not move.
    private static final double[] EDGE_WEIGHT = {1, 1, .84, .68, 0, 0};
    // Local section space, in model pixels. Taper towards the hem so the
    // bundled terminal cubes keep the same motion as their shared pivot.
    private static final double[] INBOARD = {0, .90, 1.10, .80, .22};
    private static final double[] TRAIL = {0, .50, .75, .60, .24};
    private static final Map<String, Offset> RIBBONS = ribbons();

    record Offset(double x, double z) {}

    private CapeSprintEdge() {}

    private static Map<String, Offset> ribbons() {
        var result = new HashMap<String, Offset>();
        int count = 2 * EDGE_WEIGHT.length;
        for (int ribbon = 0; ribbon < count; ++ribbon) {
            double edge = EDGE_WEIGHT[Math.min(ribbon, count - 1 - ribbon)];
            if (edge == 0) continue;
            // Baked GEO X is mirrored. Inboard is -X for ribbons 0..3.
            double side = ribbon < EDGE_WEIGHT.length ? -1 : 1;
            for (int segment = 1; segment < INBOARD.length; ++segment)
                result.put("v17_ribbon_" + ribbon + "_seg" + segment,
                        new Offset(side * edge * INBOARD[segment], edge * TRAIL[segment]));
        }
        return Map.copyOf(result);
    }

    static Offset offset(String name, String parent) {
        return switch (parent) {
            case "cape_top", "cape_mid", "cape_bottom" -> RIBBONS.get(name);
            default -> null;
        };
    }
}
