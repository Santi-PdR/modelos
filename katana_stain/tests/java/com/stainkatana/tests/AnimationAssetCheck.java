package com.stainkatana.tests;

import dev.kosmx.playerAnim.api.TransformType;
import dev.kosmx.playerAnim.api.layered.KeyframeAnimationPlayer;
import dev.kosmx.playerAnim.core.data.KeyframeAnimation;
import dev.kosmx.playerAnim.core.data.gson.AnimationSerializing;
import dev.kosmx.playerAnim.core.util.Vec3f;
import java.io.InputStream;

/** Exercises PlayerAnimator's actual parser and player, not just JSON syntax. */
public class AnimationAssetCheck {
    public static void main(String[] args) throws Exception {
        for (String name : new String[]{"eating_right", "sword_attack", "sword_attack2"}) {
            String path = "/assets/stainkatana/player_animation/" + name + ".json";
            try (InputStream in = AnimationAssetCheck.class.getResourceAsStream(path)) {
                if (in == null) throw new AssertionError("Missing " + path);
                var clips = AnimationSerializing.deserializeAnimation(in);
                if (clips.size() != 1) throw new AssertionError(name + ": expected one clip");
                KeyframeAnimation clip = clips.get(0);
                if (clip.isInfinite || clip.stopTick < 2 || clip.stopTick > 100)
                    throw new AssertionError(name + ": invalid duration or infinite loop");
                KeyframeAnimationPlayer player = new KeyframeAnimationPlayer(clip);
                Vec3f initial = player.get3DTransform("rightArm", TransformType.ROTATION, 0, Vec3f.ZERO);
                boolean moved = false;
                for (int i = 0; i < clip.stopTick; i++) {
                    player.tick();
                    player.setupAnim(0);
                    Vec3f value = player.get3DTransform("rightArm", TransformType.ROTATION, 0, Vec3f.ZERO);
                    double delta = Math.abs(value.getX() - initial.getX()) + Math.abs(value.getY() - initial.getY()) + Math.abs(value.getZ() - initial.getZ());
                    if (delta > 0.001) moved = true;
                }
                if (player.isActive()) throw new AssertionError(name + ": never finished");
                // eating_right is a fixed arm pose; the head moves instead.
                if (!name.equals("eating_right") && !moved) throw new AssertionError(name + ": arm never moved");
                System.out.println(name + ": parsed, stopTick=" + clip.stopTick + ", rightArmMoves=" + moved);
            }
        }
    }
}
