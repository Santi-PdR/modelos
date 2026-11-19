package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import software.bernie.geckolib.util.RenderUtils;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Project each actual plate quad, to distinguish the plates from the old lining in F5. */
final class CapePlateProbe extends GeoRenderLayer<CapaDeteriorerItem> {
    private record Face(int side, Vector3f[] xy) {}
    private final List<Face> faces = new ArrayList<>();
    private final Matrix4f[] solid = new Matrix4f[2];
    private boolean active;

    private CapePlateProbe(CapaArmorRenderer renderer) { super(renderer); }

    static void arm(CapaArmorRenderer renderer) {
        var probe = renderer.getRenderLayers().stream().filter(CapePlateProbe.class::isInstance)
                .map(CapePlateProbe.class::cast).findFirst().orElseGet(() -> {
                    var p = new CapePlateProbe(renderer);
                    renderer.addRenderLayer(p);
                    return p;
                });
        probe.faces.clear();
        probe.active = true;
        for (int i = 0; i < 2; i++) {
            probe.solid[i] = null;
            bone(renderer, i).setTrackingMatrices(true);
        }
    }

    @Override
    public void renderForBone(PoseStack pose, CapaDeteriorerItem item, GeoBone bone, RenderType type,
                              MultiBufferSource buffers, VertexConsumer consumer, float partial, int light, int overlay) {
        if (!active || bone.isHidden()) return;
        int side = switch (bone.getName()) {
            case CapePlateFit.SMALL -> 0;
            case CapePlateFit.WIDE -> 1;
            default -> -1;
        };
        if (side < 0) return;
        solid[side] = new Matrix4f(bone.getModelSpaceMatrix());
        Matrix4f view = new Matrix4f(RenderSystem.getProjectionMatrix()).mul(RenderSystem.getModelViewMatrix());
        for (var cube : bone.getCubes()) {
            pose.pushPose();
            try {
                RenderUtils.translateToPivotPoint(pose, cube);
                RenderUtils.rotateMatrixAroundCube(pose, cube);
                RenderUtils.translateAwayFromPivotPoint(pose, cube);
                Matrix4f clip = new Matrix4f(view).mul(pose.last().pose());
                for (var quad : cube.quads()) {
                    if (quad == null) continue;
                    Vector3f[] xy = new Vector3f[4];
                    for (int i = 0; i < xy.length; i++)
                        xy[i] = clip.transformProject(new Vector3f(quad.vertices()[i].position()));
                    faces.add(new Face(side, xy));
                }
            } finally {
                pose.popPose();
            }
        }
    }

    static CapePlateProbe finish(CapaArmorRenderer renderer) {
        var probe = renderer.getRenderLayers().stream().filter(CapePlateProbe.class::isInstance)
                .map(CapePlateProbe.class::cast).findFirst().orElseThrow();
        probe.active = false;
        for (int i = 0; i < 2; i++) {
            var b = bone(renderer, i);
            b.setTrackingMatrices(false);
            if (probe.solid[i] == null || !probe.solid[i].equals(b.getModelSpaceMatrix(), .00008F))
                throw new AssertionError("plate invisible or solid/emissive transforms differ for " + b.getName());
        }
        return probe;
    }

    static void hide(CapaArmorRenderer renderer, boolean hidden) {
        for (int i = 0; i < 2; i++) bone(renderer, i).setHidden(hidden);
    }

    private static GeoBone bone(CapaArmorRenderer renderer, int side) {
        return renderer.getGeoModel().getBone(side == 0 ? CapePlateFit.SMALL : CapePlateFit.WIDE).orElseThrow();
    }

    void write(Path path, int width, int height) throws IOException {
        StringBuilder rows = new StringBuilder();
        for (Face face : faces) {
            rows.append(face.side());
            for (Vector3f point : face.xy()) rows.append('\t').append((1 + point.x)*width/2)
                    .append('\t').append((1 - point.y)*height/2);
            rows.append('\n');
        }
        Files.writeString(path, rows);
    }
}
