package com.capatest.client;

import com.capatest.item.CapeState;

final class CapeChainTest {
    private static CapeChain.Motion at(CapeWornMotion motion) {
        return CapeChain.pose(motion.stride(), motion.amplitude(), motion.chainSupport(), motion.response.braking());
    }

    private static void check(boolean good, String label) {
        if (!good) throw new AssertionError(label);
    }

    private static void near(double expected, double actual, double eps) {
        check(Math.abs(expected-actual) <= eps, expected + " vs " + actual);
    }

    private static void verifyMotion() {
        var motion = new CapeWornMotion();
        float step = 0, gait = 0;
        for (int i = 0; i < 98; ++i) {
            boolean running = i >= 12 && i < 38;
            boolean crouch = i >= 60 && i < 68, flight = i >= 72 && i < 78, water = i >= 83;
            var wearer = new CapeState.Wearer(false, flight, water, false, crouch, running, running ? .16 : 0, 0);
            float next = running ? .72F : i >= 12 && i < 42 ? .72F*(42-i)/4 : 0;
            motion.sample(wearer, i, .75F, step, step+next, gait, next, water ? 1 : 0, water ? 1 : 0);
            double time = motion.time()/20;
            motion.response.sample(time, running ? .48 : 0, 0, 0, 0, water ? 1 : 0, 0, running ? 1 : 0);
            var swing = at(motion);
            motion.sample(wearer, i, .15F, step, step+next, gait, next, water ? 1 : 0, water ? 1 : 0);
            motion.response.sample(motion.time()/20, 0, 0, 0, 0, 0, 0, 0);
            check(swing.equals(at(motion)), "re-sample changed chain at the same fractional time");
            if (i < 12 || i >= 66) check(swing == CapeChain.REST, "not neutral without supported gait or wake: " + i);
            if (i == 28) check(swing.drop() > .04 && swing.away() > .06, "running did not reach the chain");
            if (i == 43) check(swing.away() > .21, "no brake carry");
            step += next;
            gait = next;
        }
        motion.response.reset();
        motion.response.sample(6, .8, 0, 0, 0, 0, 0, 0);
        check(motion.response.braking() == 0, "cut inherited a brake impulse");
    }

    public static void main(String[] args) {
        if (args.length == 1 && args[0].equals("--samples")) {
            for (int i = -10; i <= 30; i++)
                for (double pace : new double[]{0,.045,.3,.64,1})
                    for (double support : new double[]{0,.45,1})
                        for (double brake : new double[]{-.15,0,.008,.031,.115,.3}) {
                            double phase = i/20.;
                            var x = CapeChain.pose(phase, pace, support, brake);
                            System.out.println(phase+"\t"+pace+"\t"+support+"\t"+brake+"\t"+x.drop()+"\t"+x.away());
                        }
            return;
        }
        check(CapeChain.weight("v18_chain_0") == 0 && CapeChain.weight("v18_chain_7") == 0, "moved an anchor");
        check(CapeChain.weight("v18_chain_4") == 1 && CapeChain.weight("v18_chain_5") == 1, "split the shortest join");
        check(CapeChain.weight("v18_chain_10") == 0 && CapeChain.weight("v18_pad_0") == 0, "moved another part");
        for (int i = 0; i < 100; ++i) {
            var a = CapeChain.pose(i/100., 1, 1, 0);
            var b = CapeChain.pose(i/100.+.5, 1, 1, -1);
            var c = CapeChain.pose(i/100., 1, 1, 2);
            near(a.drop(), b.drop(), 2e-15);
            near(a.away(), b.away(), 2e-15);
            check(a.drop() < c.drop() && c.drop() <= .28, "drop bound");
            check(a.away() < c.away() && c.away() <= .36, "front bound");
            check(CapeChain.pose(i/100., .8, 0, 1) == CapeChain.REST, "no support");
        }
        var hit = CapeChain.pose(.08, 1, 1, 0);
        var lag = CapeChain.pose(.08+.62/(4*Math.PI), 1, 1, 0);
        check(hit.drop() > lag.drop() && lag.away() > hit.away(), "outward swing should follow the drop");
        verifyMotion();
        System.out.println("Cadena: dos apoyos, dos pisadas por ciclo, retardo y un solo muestreo por pose.");
    }
}
