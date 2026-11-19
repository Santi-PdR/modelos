package com.capatest.client;

/** Body-space backing under the high collar. No dependence on F5 or the camera. */
final class CapeBacking {
    static final String LEFT = "v20_mount_backing_left";
    static final String RIGHT = "v20_mount_backing_right";
    private static final double Y_PIVOT = 14.27, Z_PIVOT = 1.58;
    private static final double INNER = .01, INFLATE = .01;
    private static final double SPAN = 4.12, MAX_BACKSET = 3.2;
    private static final double TUCK_Y = .019, TUCK_Z = .64, WING_Z = .078;
    private static final double FOLD_MIN = .14, FOLD_SPAN = .38;
    private static final double HEAD_HALF = 4.60, SOFT_RISE = .72;
    // Width, front center Y/Z, rise, reach, thickness. Seat the first
    // fold in the shirt, turn a lip *over* its upper rear edge, then lap
    // both folds into the saddle. The old rising ramp reached the collar
    // but left the shirt showing between it and the actual shoulder line.
    // The same panels are used by the GEO and Blockbench exporters.
    private static final double[][] PANELS = {
            {3.24, 19.19, 1.21, 0.00, 1.34, 9.73},
            {3.25, 24.05, 1.78, -2.35, 3.93, 1.56},
            {3.14, 17.15, 2.13, 5.09, 3.27, 1.90}
    };
    private static final Panel[] EDGES = edges();
    private static final double[] BODY_X = {1,0,0}, BODY_Y = {0,1,0}, BODY_Z = {0,0,1};

    record Shape(float left, float right, float depth) {}
    private record Panel(double width, double[] y, double[] z) {}
    // The folded wings can occupy the whole gusset, not just its upper
    // section. Hide the backing *inside* the torso, never inside the wings.
    static final Shape TUCKED = new Shape((float) TUCK_Y, (float) TUCK_Y, (float) WING_Z);

    static Shape shape(double bodyPitch, double bodyYaw, double headPitch, double headYaw,
                       double backset, boolean elytra) {
        if (elytra || !Double.isFinite(bodyPitch) || !Double.isFinite(headPitch)
                || !Double.isFinite(headYaw - bodyYaw) || !Double.isFinite(backset)) return TUCKED;
        double stance = clamp(bodyPitch / CapeFit.CROUCH_RADIANS);
        double lean = stance * CapeFit.CROUCH_RADIANS;
        double side = headYaw - bodyYaw;
        double co = Math.cos(-headPitch), si = Math.sin(-headPitch);
        double cy = Math.cos(side), sy = Math.sin(side);
        double cl = Math.cos(lean), sl = Math.sin(lean);
        // Outer vanilla head, in the body's pivot space, including crouch.
        double[] x = {cy, sl*sy, -cl*sy};
        double[] y = {sy*si, cl*co-sl*cy*si, sl*co+cl*cy*si};
        double[] z = {sy*co, -cl*si-sl*cy*co, -sl*si+cl*cy*co};
        double[] center = {4*y[0], 24-stance*cl+4*y[1], -stance*sl+4*y[2]};
        double[][] axes = {BODY_X, BODY_Y, BODY_Z, x, y, z};
        double stretched = 1 + Math.min(MAX_BACKSET, Math.max(0, backset))/SPAN;
        double left = rise(1,stretched,axes,center,x,y,z), right = rise(-1,stretched,axes,center,x,y,z);
        // Don't leave a long shelf below the collar when fully ducked.
        double fold = clamp((Math.max(left,right)-FOLD_MIN)/FOLD_SPAN);
        double depth = TUCK_Z + (stretched-TUCK_Z)*fold*fold*(3-2*fold);
        if (depth < stretched - 1e-8) {
            left = Math.min(left, rise(1,depth,axes,center,x,y,z));
            right = Math.min(right, rise(-1,depth,axes,center,x,y,z));
        }
        return new Shape((float) left,(float) right,(float) depth);
    }

    private static Panel[] edges() {
        Panel[] panels = new Panel[PANELS.length];
        for (int i = 0; i < PANELS.length; ++i) {
            double[] a = PANELS[i];
            double length = Math.hypot(a[3], a[4]), sin = a[3]/length, cos = a[4]/length;
            double[] ys = new double[4], zs = new double[4];
            double half = a[5]/2 + INFLATE;
            for (int v = 0; v < 4; v++) {
                double h = (v&1) == 0 ? -half : half;
                double d = (v&2) == 0 ? -INFLATE : length+INFLATE;
                ys[v] = a[1] + h*cos + d*sin - Y_PIVOT;
                zs[v] = a[2] - h*sin + d*cos - Z_PIVOT;
            }
            panels[i] = new Panel(a[0],ys,zs);
        }
        return panels;
    }

    private static double rise(int side, double depth, double[][] axes, double[] center,
                               double[] x, double[] y, double[] z) {
        double limit = 1;
        for (Panel p : EDGES) {
            double best = 0;
            for (double[] n : axes) {
                double middle = dot(n,center);
                double extent = HEAD_HALF * (Math.abs(dot(n,x)) + Math.abs(dot(n,y)) + Math.abs(dot(n,z)));
                for (int sign = 1; sign >= -1; sign -= 2) {
                    double ax = sign*n[0], ay = sign*n[1], az = sign*n[2];
                    double socket = Math.max(ax*side*(INNER-INFLATE), ax*side*(INNER+p.width+INFLATE));
                    double room = sign*middle-extent - socket-ay*Y_PIVOT-az*Z_PIVOT;
                    double safe = 1;
                    for (int v = 0; v < 4; ++v)
                        safe = Math.min(safe,(room-az*depth*p.z[v])/Math.max(SOFT_RISE,ay*p.y[v]));
                    best = Math.max(best, safe);
                }
            }
            // Any separating plane is enough for a panel; all panels must
            // clear. The positive denominator floor eases horizontal grazes.
            limit = Math.min(limit,best);
        }
        return Math.max(TUCK_Y,limit);
    }

    private static double dot(double[] a, double[] b) {
        return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
    }

    private static double clamp(double x) {
        return Math.min(1, Math.max(0, x));
    }
}
