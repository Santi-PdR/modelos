package com.capatest.client;

import java.util.Locale;

final class CapeHoodTest {
    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--aim")) {
            checkAim();
            return;
        }
        boolean samples = args.length == 1 && args[0].equals("--samples");
        double low = 100, high = 0;
        for (int i = 0; i < 32; i++) for (double pace : new double[]{0,.7,1}) {
            double ticks = i * 1.375, stride = i / 16., turn = Math.sin(i), side = Math.cos(i);
            int seed = i + 14;
            var pose = CapeHood.pose(ticks, stride, pace, turn, side, seed);
            var next = CapeHood.pose(ticks, stride + 1, pace, turn, side, seed);
            if (Math.abs(next.pitch()-pose.pitch()) > 1e-12 || Math.abs(next.yaw()-pose.yaw()) > 1e-12
                    || Math.abs(next.roll()-pose.roll()) > 1e-12)
                throw new AssertionError("hood doesn't loop with stride");
            if (pose.pitch() < 1.50 || pose.pitch() > 7.90 || Math.abs(pose.yaw()) > 1.61 || Math.abs(pose.roll()) > 1.43)
                throw new AssertionError("hood left its sewn range: " + pose);
            low = Math.min(low,pose.pitch());
            high = Math.max(high,pose.pitch());
            if (samples) System.out.printf(Locale.ROOT,"%.12f\t%.12f\t%.12f\t%.12f\t%.12f\t%d\t%.12f\t%.12f\t%.12f%n",
                    ticks,stride,pace,turn,side,seed,pose.pitch(),pose.yaw(),pose.roll());
        }
        if (high-low < 3) throw new AssertionError("hood didn't move");
        if (CapeHood.moves("v17_cowl_return") || CapeHood.moves("v17_cowl_tooth_3") || CapeHood.moves("cape_top")
                || !CapeHood.moves("v17_cowl_back_1") || !CapeHood.moves("v17_cowl_front_2"))
            throw new AssertionError("hood hinge reached the mount");
    }

    private static void checkAim() {
        double before = 0;
        for (int i = -900; i <= 900; ++i) {
            double up = .1 * i;
            double extra = CapeHood.lookClearance(up, 0, 0);
            if (extra < before || extra - before > .19 || extra > 56 || up <= 21 && extra != 0)
                throw new AssertionError("discontinuous hood clearance at " + up);
            before = extra;
        }
        if (CapeHood.lookClearance(64, 0, 0) < 50 || CapeHood.lookClearance(64, 0, 28.65) != 0
                || CapeHood.lookClearance(64, 90, 0) != 0 || CapeHood.lookClearance(Double.NaN, 0, 0) != 0)
            throw new AssertionError("clearance escaped the upright high look");
        for (double up : new double[]{-89, -8, 21, 28, 45, 64, 89})
            for (double yaw : new double[]{-390,-90,-55,0,30,55,90,390})
                for (double lean : new double[]{0,6,28.65})
                    System.out.printf(Locale.ROOT,"%f\t%f\t%f\t%.12f%n", up, yaw, lean,
                            CapeHood.lookClearance(up,yaw,lean));
    }
}
