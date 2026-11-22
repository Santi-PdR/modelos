package com.capatest.client;

import java.util.Locale;

final class CapeHoodTest {
    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--nape")) {
            checkNape();
            return;
        }
        if (args.length == 1 && args[0].equals("--rear")) {
            checkRear();
            return;
        }
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

    private static void checkRear() {
        for (double lean : new double[]{-29, 0, 17, 20, 26, 28.65}) {
            for (double yaw : new double[]{-415,-55,-27,-7,0,7,22,27,55,415}) {
                double previous = 0;
                for (int i = -900; i <= 900; i++) {
                    double up = .1*i, tuck = CapeHood.rearTuck(up, yaw, lean);
                    if (tuck < previous || tuck - previous > .0066 || tuck < 0 || tuck > 1
                            || tuck != CapeHood.rearTuck(up, -yaw, lean))
                        throw new AssertionError("jerk, overflow or asymmetry in the rear fit");
                    if ((up <= 5 || lean <= 17 || Math.abs(yaw) <= 7) && tuck != 0)
                        throw new AssertionError("rear fit escaped the upward crouched turn");
                    previous = tuck;
                }
                for (double up : new double[]{-79, 0, 5, 14, 22, 35, 64, 89})
                    System.out.printf(Locale.ROOT,"%f\t%f\t%f\t%.12f%n", up,yaw,lean,CapeHood.rearTuck(up,yaw,lean));
            }
        }
        if (CapeHood.rearTuck(35,55,28.65) != 1 || CapeHood.rearTuck(35,55,Double.NaN) != 0
                || !CapeHood.rear("v17_cowl_back_0") || CapeHood.rear("v17_cowl_front_0")
                || CapeHood.rear("v18_pad_1") || CapeHood.rear("v17_cowl_return"))
            throw new AssertionError("incorrect crown band or crouch envelope");
    }

    private static CapeHood.Nape dryNape(double up, double yaw, double lean) {
        return CapeHood.nape(up, yaw, lean, 0);
    }

    private static void checkNape() {
        var rest = CapeHood.NO_NAPE;
        var pos = dryNape(23, 34, 28.65);
        var neg = dryNape(23, -34, 28.65);
        var center = dryNape(0, 0, 28.65);
        if (pos.chain().z() >= -.9 || pos.lip().z() >= -.75 || pos.opposite() != CapeHood.FIXED
                || neg.opposite().z() >= -.75 || neg.lip() != CapeHood.FIXED
                || !mirrored(dryNape(35, 55, 28.65).lip(), dryNape(35, -55, 28.65).lip())
                || dryNape(35, 55, 28.65).chain() != CapeHood.FIXED
                || dryNape(35, 34, 0) != rest || dryNape(0, 34, 29) != rest
                || dryNape(45, 0, 29) != rest || dryNape(-25, 0, 29) != rest
                || dryNape(35, 74, 29) != rest || dryNape(23, Double.NaN, 29) != rest
                || !pos.equals(dryNape(23, -326, 28.65)))
            throw new AssertionError("incorrect range, edge handoff or angle wrap");
        for (String n : new String[]{"v18_pad_0", "v18_pad_1", "v17_cowl_return", "v17_cowl_tooth_3",
                "v20_mount_saddle", CapeFit.SEAT_FRAME, "v17_ribbon_8_seg0"}) {
            if (pos.forBone(n) != CapeHood.FIXED || neg.forBone(n) != CapeHood.FIXED || center.forBone(n) != CapeHood.FIXED)
                throw new AssertionError("nape shifted " + n);
        }
        if (pos.forBone("v17_cowl_front_2") != pos.lip() || neg.forBone("v17_cowl_back_4") != neg.opposite()
                || center.forBone("v17_cowl_back_2") != center.crown() || pos.forBone("v18_chain_0") != pos.chain()
                || !center.crown().equals(new CapeHood.Shift(0,-1.90,-2.00))
                || !center.chain().equals(new CapeHood.Shift(0,-1.90*.60,-2.00*.60)))
            throw new AssertionError("incorrect return stroke or moved pieces");
        for (double up : new double[]{-12, 0, 10, 23, 35, 53}) {
            var last = rest;
            for (int i = -750; i <= 750; i++) {
                var p = dryNape(up, i*.1, 28.65);
                checkStroke(last.chain(), p.chain(), 2.70);
                checkStroke(last.lip(), p.lip(), 3.50);
                checkStroke(last.opposite(), p.opposite(), 3.50);
                checkStroke(last.crown(), p.crown(), 2.77);
                last = p;
            }
        }
        var stillSettling = CapeHood.nape(0, 0, 0, .75);
        if (stillSettling.crown().z() != -1.5 || Math.abs(stillSettling.chain().z() + .9) > 1e-12
                || CapeHood.nape(0, 0, 0, 0) != rest || CapeHood.nape(0,0,28,Double.NaN) != rest)
            throw new AssertionError("loss of nape follow-through on Shift release");
        for (double lean : new double[]{0, 17, 25, 28.65})
            for (double up : new double[]{-45, -18, -7, 0, 4, 9, 17, 23, 35, 57})
                for (double yaw : new double[]{-394, -55, -42, -37, -25, -9, 0, 15, 28, 46, 55, 67, 73, 385})
                    for (double crouch : new double[]{0, .74}) {
                        var n = CapeHood.nape(up, yaw, lean, crouch);
                        System.out.printf(Locale.ROOT,"%f\t%f\t%f\t%f", up,yaw,lean,crouch);
                        for (var v : new CapeHood.Shift[]{n.chain(), n.lip(), n.opposite(), n.crown()})
                            System.out.printf(Locale.ROOT,"\t%.12f\t%.12f\t%.12f", v.x(),v.y(),v.z());
                        System.out.println();
                    }
    }

    private static boolean mirrored(CapeHood.Shift a, CapeHood.Shift b) {
        return a.x() == -b.x() && a.y() == b.y() && a.z() == b.z();
    }

    private static void checkStroke(CapeHood.Shift last, CapeHood.Shift a, double limit) {
        if (Math.hypot(a.x(), Math.hypot(a.y(), a.z())) > limit || a.z() > 0
                || Math.hypot(a.x()-last.x(), Math.hypot(a.y()-last.y(), a.z()-last.z())) > .049)
            throw new AssertionError("nape stroke is discontinuous or oversized: " + a);
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
