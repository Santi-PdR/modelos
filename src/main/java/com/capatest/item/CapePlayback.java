package com.capatest.item;

/** One selector per GeckoLib instance. The server's aura remains stateless. */
public final class CapePlayback {
    public static final int FIRST_BLEND = 8;
    private static final int AIR_BLEND = 3;
    private static final int WATER_BLEND = 4;
    private static final int STRIDE_BLEND = 5;
    private static final int GROUND_BLEND = 6;
    private static final double WALK_ENTER = .0016;  // 0.04 blocks/tick squared
    private static final double WALK_EXIT = .000484; // 0.022 blocks/tick squared
    private static final double FALL_ENTER = -.08;
    private static final double FALL_EXIT = -.035;

    private CapeState locomotion;
    private CapeState pose;
    private int lastTick;
    private int blendTicks = FIRST_BLEND;

    public CapeState sample(CapeState.Wearer wearer, int tick) {
        return sample(wearer, tick, false);
    }

    /** The GeckoLib fallback can choose a discrete swim clip. The worn mixer
     * instead uses the upright family and adds the interpolated swim pose. */
    public CapeState sample(CapeState.Wearer wearer, int tick, boolean horizontalSwim) {
        if (tick < lastTick || tick - lastTick > 10) locomotion = null;
        lastTick = tick;
        if (wearer.elytra()) {
            locomotion = CapeState.AIR;
        } else if (wearer.water() && horizontalSwim) {
            locomotion = CapeState.SWIM;
        } else if (wearer.airborne() && !wearer.water()) {
            double threshold = locomotion == CapeState.FALL ? FALL_EXIT : FALL_ENTER;
            locomotion = wearer.vertical() < threshold ? CapeState.FALL : CapeState.AIR;
        } else if (wearer.crouching()) {
            locomotion = CapeState.SNEAK;
        } else {
            double threshold = isStride(locomotion) ? WALK_EXIT : WALK_ENTER;
            locomotion = wearer.horizontalSquared() > threshold
                    ? (!wearer.water() && wearer.sprinting() ? CapeState.SPRINT : CapeState.WALK) : CapeState.IDLE;
        }

        // The damaged rest pose still has its heartbeat. While moving the cloth must
        // follow locomotion; glow and sparks still use the existing blight priority.
        CapeState next = wearer.blight() && locomotion == CapeState.IDLE ? CapeState.BLIGHT : locomotion;
        if (pose != next) {
            blendTicks = transition(pose, next);
            pose = next;
        }
        return pose;
    }

    public int blendTicks() {
        return blendTicks;
    }

    public void reset() {
        locomotion = pose = null;
        blendTicks = FIRST_BLEND;
    }

    public static int transition(CapeState from, CapeState to) {
        if (from == null) return FIRST_BLEND;
        if (isAir(from) || isAir(to)) return AIR_BLEND;
        if (from == CapeState.SWIM || to == CapeState.SWIM) return WATER_BLEND;
        if (isStride(from) && isStride(to)) return STRIDE_BLEND;
        return GROUND_BLEND;
    }

    private static boolean isStride(CapeState mode) {
        return mode == CapeState.WALK || mode == CapeState.SPRINT;
    }

    private static boolean isAir(CapeState mode) {
        return mode == CapeState.AIR || mode == CapeState.FALL;
    }
}
