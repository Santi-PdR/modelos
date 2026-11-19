package com.capatest.client;

public final class CapeWingFitTest {
    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--samples")) {
            for (double body : new double[]{0, 14, Math.toDegrees(CapeFit.CROUCH_RADIANS)}) {
                for (double roll : new double[]{0, 15, 17, 32, 45, 61, 74, 90}) {
                    for (double pitch : new double[]{10, 15, 20, 40}) {
                        for (double depth : new double[]{0, 1.4, 4.5}) {
                            for (double top : new double[]{5, 20, 29, 46}) {
                                double arm = 20 + 3 * (int) (top % 3), leg = 24 + 8 * (int) (top % 4), mid = 6;
                                double goal = CapeWingFit.topGoal(pitch, roll, body, depth);
                                double side = CapeStride.armGoal(arm, Math.toRadians(body), depth);
                                double knee = CapeStride.legGoal(leg, Math.toRadians(body), depth);
                                double a = Math.max(CapeStride.topLift(top, side, knee), CapeWingFit.topLift(top, goal));
                                double b = CapeStride.midLift(top + a, mid, knee);
                                System.out.println(pitch + "\t" + roll + "\t" + body + "\t" + depth + "\t" + arm + "\t" + leg
                                        + "\t" + top + "\t" + mid + "\t" + goal + "\t" + a + "\t" + b);
                            }
                        }
                    }
                }
            }
            return;
        }
        double fold = CapeWingFit.topGoal(15, -15, 0, 0);
        check(fold == CapeWingFit.topGoal(15, 15, 0, 0), "the two wings disagree");
        check(CapeWingFit.topLift(4, fold) >= 21, "the folded wing has almost no extra room");
        check(CapeWingFit.topLift(5, fold) + 5 > CapeWingFit.topLift(4, fold) + 4,
                "the hinge pinned an authored clip to one angle");
        check(CapeWingFit.topLift(49, fold) == 0, "the air clip already clears the folded wing");
        check(CapeWingFit.topGoal(15, 15, 0, 3) < fold, "head backset was counted twice");
        check(CapeWingFit.topGoal(40, 45, 28, 2) < fold, "lean was counted twice");
        check(CapeWingFit.topGoal(Double.NaN, 15, 0, 0) == 0, "bad wing transform");
        check(CapeWingFit.topLift(Double.NaN, fold) == 0, "bad rig transform");
        double prev = fold;
        for (double angle = 15; angle <= 90; angle += .125) {
            double goal = CapeWingFit.topGoal(15, angle, 0, 0);
            check(goal <= prev && prev-goal < .12, "a wing transition jumps");
            prev = goal;
        }
        check(prev == 0, "the guide still lifts a fully spread wing");
        check(CapeWingFit.topLift(-80, fold) == 25, "lost the lift cap");
        System.out.println("CapeWingFit: folded, opening/landing, head fit, and uncapped authored air pose");
    }

    private static void check(boolean ok, String label) {
        if (!ok) throw new AssertionError(label);
    }
}
