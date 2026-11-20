package com.capatest.client;

/** Fixed mount with a physical alternative for wing equipment, and no aim input. */
public final class CapeMountPlacementTest {
    public static void main(String[] args) {
        boolean samples = args.length == 1 && args[0].equals("--samples");
        for (boolean wings : new boolean[]{false, true}) {
            var pose = CapeMountPlacement.worn(wings);
            if (pose.depth() < 0 || pose.dy() > 0 || pose.linkScale() <= 0 || pose.drape() < pose.pitch())
                throw new AssertionError("invalid worn pose " + pose);
            if (wings && (pose.depth() != 0 || pose.drape() != 0 || pose.linkScale() != 1))
                throw new AssertionError("wing clearance hinge was moved " + pose);
            if (samples)
                System.out.println((wings ? 1 : 0) + "\t" + pose.depth() + "\t" + pose.dy() + "\t" + pose.pitch()
                        + "\t" + pose.drape() + "\t" + pose.linkPitch() + "\t" + pose.linkScale());
        }
    }
}
