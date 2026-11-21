package com.capatest.client;

import java.util.Locale;

final class CapeSprintEdgeTest {
    public static void main(String[] args) {
        for (int ribbon = 0; ribbon < 12; ++ribbon) for (int segment = 0; segment <= 6; ++segment) {
            String name = "v17_ribbon_" + ribbon + "_seg" + segment;
            var offset = CapeSprintEdge.offset(name, "cape_top");
            boolean freeEdge = (ribbon < 4 || ribbon >= 8) && segment > 0 && segment <= 4;
            if ((offset != null) != freeEdge || CapeSprintEdge.offset(name, "chestplate") != null)
                throw new AssertionError("sprint fit left the free edges: " + name);
            if (offset != null && (Math.signum(offset.x()) != (ribbon < 6 ? -1 : 1)
                    || offset.z() <= 0 || Math.hypot(offset.x(), offset.z()) > 1.34))
                throw new AssertionError("wrong sleeve clearance for " + name);
            System.out.printf(Locale.ROOT, "%d\t%d\t%.12f\t%.12f%n", ribbon, segment,
                    offset == null ? 0 : offset.x(), offset == null ? 0 : offset.z());
        }
    }
}
