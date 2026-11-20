package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.event.GeoRenderEvent;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import software.bernie.geckolib.util.RenderUtils;

import java.lang.reflect.Field;
import java.util.Map;
import java.util.TreeMap;

/** Opt-in A/B: same live wearer and light, with the actual pre-branch material/rig. */
final class CapeHistoricFitProbe extends GeoRenderLayer<CapaDeteriorerItem> {
    static final boolean ENABLED = Boolean.getBoolean("cape.history");
    private static GeoArmorRenderer<CapaDeteriorerItem> oldRenderer;
    private final GeoArmorRenderer<CapaDeteriorerItem> renderer;
    private final Map<String, Bounds> bounds = new TreeMap<>();
    private Matrix4f toBody;
    private boolean active;

    private CapeHistoricFitProbe(GeoArmorRenderer<CapaDeteriorerItem> renderer) {
        super(renderer);
        this.renderer = renderer;
    }

    @SuppressWarnings("unchecked")
    private static GeoArmorRenderer<CapaDeteriorerItem> legacy() throws ReflectiveOperationException {
        if (oldRenderer == null)
            oldRenderer = (GeoArmorRenderer<CapaDeteriorerItem>) Class.forName(
                    "com.capatest.client.CapeHistoricalArmorRenderer").getConstructor().newInstance();
        return oldRenderer;
    }

    static boolean isLegacy(GeoArmorRenderer<?> renderer) { return renderer == oldRenderer; }

    static void substitute(GeoRenderEvent.Armor.Pre event, CapaArmorRenderer live) {
        try {
            var renderer = legacy();
            Field base = GeoArmorRenderer.class.getDeclaredField("baseModel");
            base.setAccessible(true);
            var stack = live.getCurrentStack();
            // Vanilla and Curios still own the pose, lighting and dispatch. In
            // these standing views the old Curios sneak helpers were no-ops.
            renderer.prepForRender(live.getCurrentEntity(), stack, live.getCurrentSlot(), (HumanoidModel<?>) base.get(live));
            event.setCanceled(true);
            renderer.defaultRender(event.getPoseStack(), live.getAnimatable(), event.getBufferSource(),
                    null, null, 0, event.getPartialTick(), event.getPackedLight());
        } catch (ReflectiveOperationException error) {
            throw new AssertionError("missing compiled pre-branch Forge fixture", error);
        }
    }

    static void arm(GeoArmorRenderer<CapaDeteriorerItem> renderer) {
        var probe = renderer.getRenderLayers().stream().filter(CapeHistoricFitProbe.class::isInstance)
                .map(CapeHistoricFitProbe.class::cast).findFirst().orElseGet(() -> {
                    var value = new CapeHistoricFitProbe(renderer);
                    renderer.addRenderLayer(value);
                    return value;
                });
        probe.bounds.clear();
        probe.toBody = null;
        probe.active = true;
    }

    @Override
    public void renderForBone(PoseStack pose, CapaDeteriorerItem item, GeoBone bone, RenderType type,
                              MultiBufferSource buffers, VertexConsumer consumer, float partial, int light, int overlay) {
        if (!active) return;
        String name = bone.getName();
        if (name.equals("chestplate")) {
            toBody = new Matrix4f(pose.last().pose()).invert();
            return;
        }
        if (bone.isHidden() || toBody == null || !(name.startsWith("v18_pad_") || name.startsWith("v17_cowl_")
                || name.startsWith("v19_cuellito_") || name.startsWith("v18_chain_")
                || name.startsWith("v17_ribbon_") && name.endsWith("_seg0"))) return;
        var range = new Bounds();
        for (var cube : bone.getCubes()) {
            pose.pushPose();
            try {
                if (renderer instanceof CapaArmorRenderer cape) cape.applyPlateRim(pose, bone, cube);
                RenderUtils.translateToPivotPoint(pose, cube);
                RenderUtils.rotateMatrixAroundCube(pose, cube);
                RenderUtils.translateAwayFromPivotPoint(pose, cube);
                var matrix = new Matrix4f(toBody).mul(pose.last().pose());
                for (var quad : cube.quads()) {
                    if (quad == null) continue;
                    for (var vertex : quad.vertices()) {
                        var point = matrix.transformPosition(vertex.position(), new Vector3f()).mul(16);
                        range.include(point);
                    }
                }
            } finally {
                pose.popPose();
            }
        }
        if (range.count > 0) bounds.put(name, range);
    }

    static String finish(GeoArmorRenderer<?> renderer) {
        var probe = renderer.getRenderLayers().stream().filter(CapeHistoricFitProbe.class::isInstance)
                .map(CapeHistoricFitProbe.class::cast).findFirst().orElseThrow();
        probe.active = false;
        if (!probe.bounds.containsKey("v18_pad_0") || !probe.bounds.containsKey("v18_pad_1")
                || !probe.bounds.containsKey("v17_cowl_back_0") || !probe.bounds.containsKey("v17_ribbon_5_seg0"))
            throw new AssertionError("missing solid draw of the worn collar, plates or roots: " + probe.bounds.keySet());
        var out = new StringBuilder("part\tmin_x\tmin_y\tmin_z\tmax_x\tmax_y\tmax_z\n");
        probe.bounds.forEach((name, range) -> out.append(name).append('\t').append(range.tsv()).append('\n'));
        return out.toString();
    }

    private static final class Bounds {
        final Vector3f lo = new Vector3f(Float.POSITIVE_INFINITY);
        final Vector3f hi = new Vector3f(Float.NEGATIVE_INFINITY);
        int count;

        void include(Vector3f p) {
            lo.min(p);
            hi.max(p);
            count++;
        }

        String tsv() {
            return lo.x + "\t" + lo.y + "\t" + lo.z + "\t" + hi.x + "\t" + hi.y + "\t" + hi.z;
        }
    }
}
