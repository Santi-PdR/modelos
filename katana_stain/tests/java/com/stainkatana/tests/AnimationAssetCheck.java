package com.stainkatana.tests;

import dev.kosmx.playerAnim.api.TransformType;
import dev.kosmx.playerAnim.api.layered.KeyframeAnimationPlayer;
import dev.kosmx.playerAnim.core.data.KeyframeAnimation;
import dev.kosmx.playerAnim.core.data.gson.AnimationSerializing;
import dev.kosmx.playerAnim.core.util.Vec3f;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

/** Exercises PlayerAnimator's actual parser and player, not just JSON syntax. */
public class AnimationAssetCheck {
    public static void main(String[] args) throws Exception {
        for (String name : new String[]{"inspect", "sword_attack", "sword_attack2"}) {
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
                if (!moved) throw new AssertionError(name + ": arm never moved");
                System.out.println(name + ": parsed, stopTick=" + clip.stopTick + ", rightArmMoves=" + moved);
            }
        }
        String external = System.getenv("STAIN_BC_TEST_DIR");
        if (external == null) throw new AssertionError("STAIN_BC_TEST_DIR must contain upstream Better Combat samples");
        for (String name : new String[]{"two_handed_slash_horizontal_right", "two_handed_slash_vertical_right", "two_handed_slash_horizontal_left"}) {
            try (InputStream in = Files.newInputStream(Path.of(external, name + ".json"))) {
                var clips = AnimationSerializing.deserializeAnimation(in);
                if (clips.size() != 1) throw new AssertionError(name + ": expected one clip");
                var clip = clips.get(0);
                if (clip.isInfinite || clip.beginTick < 0 || clip.endTick <= clip.beginTick || clip.stopTick <= clip.endTick)
                    throw new AssertionError(name + ": unexpected timeline");
                var player = new KeyframeAnimationPlayer(clip, 0);
                Vec3f first = player.get3DTransform("rightArm", TransformType.ROTATION, 0, Vec3f.ZERO);
                boolean moved = false;
                for (int i = 0; i <= clip.stopTick; i++) {
                    player.tick(); player.setupAnim(0);
                    Vec3f v = player.get3DTransform("rightArm", TransformType.ROTATION, 0, Vec3f.ZERO);
                    if (Math.abs(v.getX() - first.getX()) + Math.abs(v.getY() - first.getY()) + Math.abs(v.getZ() - first.getZ()) > 0.001) moved = true;
                }
                if (player.isActive() || !moved) throw new AssertionError(name + ": not moving or not finishing");
                System.out.println(name + ": upstream parsed, beginTick=" + clip.beginTick + ", endTick=" + clip.endTick);
            }
        }
    }
}
