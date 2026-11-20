package com.capatest.client;

/** Pose-free whole-plate transforms; the visor must use the same fit. */
public final class CapeMountPlacementTest {
    public static void main(String[] args) {
        boolean samples = args.length == 1 && args[0].equals("--samples");
        for (boolean wings : new boolean[]{false, true}) {
            for (boolean slim : new boolean[]{false, true}) {
                for (int side = 0; side < 2; ++side) {
                    var p = CapeMountPlacement.plate(wings, side == 1);
                    if (p.width() <= 0 || p.height() <= 0 || p.depth() <= 0
                            || !p.bone().equals(side == 0 ? CapePlateFit.SMALL : CapePlateFit.WIDE))
                        throw new AssertionError("invalid plate fit " + p);
                    if (samples)
                        System.out.println((wings ? 1 : 0) + "\t" + (slim ? 1 : 0) + "\t" + side + "\t"
                                + p.x() + "\t" + p.y() + "\t" + p.z() + "\t" + p.shiftX(slim) + "\t" + p.dy()
                                + "\t" + p.dz() + "\t" + p.pitch() + "\t" + p.yaw() + "\t" + p.roll()
                                + "\t" + p.width() + "\t" + p.height() + "\t" + p.depth());
                }
            }
        }
    }
}
