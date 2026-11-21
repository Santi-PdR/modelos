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

    private static void checkNape() {
        var rest = CapeHood.NO_NAPE;
        var active = CapeHood.nape(23, 34, 28.65);
        if (active.chain().z() >= -.9 || active.lip().z() >= -.75 || CapeHood.nape(35, 55, 28.65).chain() != CapeHood.FIXED
                || CapeHood.nape(35, 34, 0) != rest || CapeHood.nape(0, 34, 29) != rest || CapeHood.nape(35, 0, 29) != rest
                || CapeHood.nape(35, 74, 29) != rest || CapeHood.nape(23, Double.NaN, 29) != rest
                || !active.equals(CapeHood.nape(23, -326, 28.65)))
            throw new AssertionError("incorrect nape range or wrap");
        for (String n : new String[]{"v18_pad_0", "v18_pad_1", "v17_cowl_return", "v17_cowl_back_2",
                "v17_cowl_tooth_3", "v20_mount_saddle", CapeFit.SEAT_FRAME, "v17_ribbon_8_seg0"}) {
            if (active.forBone(n) != CapeHood.FIXED) throw new AssertionError("nape shifted " + n);
        }
        for (String n : new String[]{"v17_cowl_back_0", "v17_cowl_back_1", "v17_cowl_front_0",
                "v17_cowl_front_2", "v17_cowl_front_3"}) {
            if (active.forBone(n) != active.lip()) throw new AssertionError("nape missed " + n);
        }
        if (active.forBone("v18_chain_0") != active.chain()) throw new AssertionError("missing chain fit");
        var previous = rest;
        for (int i = 0; i <= 750; i++) {
            double yaw = i*.1;
            var p = CapeHood.nape(35, yaw, 28.65);
            var q = CapeHood.nape(35, -yaw, 28.65);
            checkStroke(previous.chain(), p.chain(), q.chain(), 1.46);
            checkStroke(previous.lip(), p.lip(), q.lip(), 2.10);
            previous = p;
        }
        for (double lean : new double[]{0, 17, 25, 28.65})
            for (double up : new double[]{-18, 4, 9, 17, 23, 35})
                for (double yaw : new double[]{-394, -55, -37, -9, 0, 15, 28, 46, 55, 67, 73, 385}) {
                    var n = CapeHood.nape(up, yaw, lean);
                    var a = n.chain();
                    var b = n.lip();
                    System.out.printf(Locale.ROOT,"%f\t%f\t%f\t%.12f\t%.12f\t%.12f\t%.12f\t%.12f\t%.12f%n",
                            up,yaw,lean,a.x(),a.y(),a.z(),b.x(),b.y(),b.z());
                }
    }

    private static void checkStroke(CapeHood.Shift last, CapeHood.Shift a, CapeHood.Shift mirror, double limit) {
        if (Math.hypot(a.x(), Math.hypot(a.y(), a.z())) > limit || a.z() > 0
                || Math.hypot(a.x()-last.x(), Math.hypot(a.y()-last.y(), a.z()-last.z())) > .025
                || a.x() != -mirror.x() || a.y() != mirror.y() || a.z() != mirror.z())
            throw new AssertionError("nape stroke is discontinuous, oversized or asymmetric: " + a);
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
