package com.capatest.item;

import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

/** Only emit where there is a clear path from the wearer to the offset. */
public final class CapeSparkPath {
    private CapeSparkPath() {}

    public static boolean clearBirth(BlockGetter blocks, Entity wearer, Vec3 birth) {
        // Keep the same-height ray on the ground. The tilted model can extend
        // beyond the short hitbox: trace from inside the wearer in that case,
        // not from empty space above a wall or below a floor.
        var box = wearer.getBoundingBox();
        double y = Mth.clamp(birth.y, box.minY + 0.0001D, box.maxY - 0.0001D);
        Vec3 origin = new Vec3(wearer.getX(), y, wearer.getZ());
        return blocks.clip(new ClipContext(origin, birth, ClipContext.Block.COLLIDER,
                ClipContext.Fluid.NONE, wearer)).getType() == HitResult.Type.MISS;
    }
}
