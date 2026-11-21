package com.capatest.client;

import java.util.Locale;

final class CapeHoodTest {
    public static void main(String[] args) {
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
}
