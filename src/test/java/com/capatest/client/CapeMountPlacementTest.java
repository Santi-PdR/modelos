package com.capatest.client;

/** Head-aim sweep without a game dependency; samples are also checked against the visor. */
public final class CapeMountPlacementTest {
    public static void main(String[] args) {
        boolean sample = args.length == 1 && args[0].equals("--samples");
        for (double stance : new double[]{0, .11, .29, .49, 1})
            for (double look : new double[]{-88, -58, 0, 14, 25, 41, 71, 86, 89})
                for (double yaw : new double[]{-79, -43, 0, 39, 68})
                    for (double effort : new double[]{0, 8, 35})
                        for (double dry : new double[]{1, .3, 0})
                            for (boolean wings : new boolean[]{false, true})
                                verify(stance, look, yaw, effort, dry, wings, sample);
    }

    private static void verify(double stance, double look, double yaw, double effort, double dry,
                               boolean wings, boolean sample) {
        double body = stance * CapeFit.CROUCH_RADIANS;
        double pitch = Math.toRadians(-look), turn = Math.toRadians(yaw);
        var pose = CapeMountPlacement.solve(body, 0, pitch, turn, effort, dry, !wings);
        if (pose.depth() < 0 || pose.dy() > 0 || pose.linkScale() <= 0 || pose.plate() < 0 || pose.plate() > 1)
            throw new AssertionError("invalid position " + pose);
        if (wings || dry == 0 || stance == 1) {
            if (pose.movesMount() || pose.depth() != CapeFit.backset(body, 0, pitch, turn)
                    || pose.plate() != 0 || pose.fitPitch() != pitch)
                throw new AssertionError("changed the preserved fit " + pose);
        } else if (stance == 0 && dry == 1 && look >= 71 && pose.depth() >= 3.5) {
            throw new AssertionError("too much rear travel " + pose);
        }
        if (sample) {
            double[] row = {stance, look, yaw, effort, dry, wings ? 1 : 0, pose.depth(), pose.settledDepth(),
                    -Math.toDegrees(pose.fitPitch()), pose.dy(), pose.pitch(), pose.drape(), pose.linkPitch(),
                    pose.linkScale(), pose.plate()};
            StringBuilder b = new StringBuilder();
            for (double value : row) {
                if (!b.isEmpty()) b.append('\t');
                b.append(value);
            }
            System.out.println(b);
        }
    }
}
