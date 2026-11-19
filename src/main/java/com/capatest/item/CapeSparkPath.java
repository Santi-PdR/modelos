package com.capatest.item;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

/** Only emit where there is a clear path from the wearer to the offset. */
public final class CapeSparkPath {
    private CapeSparkPath() {}

    public static boolean clearBirth(BlockGetter blocks, Entity wearer, Vec3 birth) {
        // Use the same height as the spark: a diagonal ray from the eyes
        // would incorrectly reject sparks at the hem near a step or slab.
        Vec3 origin = new Vec3(wearer.getX(), birth.y, wearer.getZ());
        return blocks.clip(new ClipContext(origin, birth, ClipContext.Block.COLLIDER,
                ClipContext.Fluid.NONE, wearer)).getType() == HitResult.Type.MISS;
    }
}
