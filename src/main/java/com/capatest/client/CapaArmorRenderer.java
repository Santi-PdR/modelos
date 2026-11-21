package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.jetbrains.annotations.Nullable;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.util.RenderUtils;

public class CapaArmorRenderer extends GeoArmorRenderer<CapaDeteriorerItem> {
    private final CapaArmorModel capeModel;
    private static final CapeFit.YokeShape WING_LINING = CapeFit.yokeShape(0, 0, 0, true);
    private static final Matrix4f LINING_SHEAR = new Matrix4f().m21((float) CapeMountPlacement.LINING_LIFT);
    private static final Matrix3f LINING_NORMAL = new Matrix3f().m12((float) -CapeMountPlacement.LINING_LIFT);
    private boolean mountInChest;
    private boolean snugSeat;
    private boolean slimSleeves;
    private boolean elytra;
    private boolean armorPassSubmitted;
    private boolean sampleFit;

    public CapaArmorRenderer() {
        this(new CapaArmorModel(new ResourceLocation(CapaTestMod.MOD_ID, "armor/capa_deteriorer_evilsaiyan")));
    }

    private CapaArmorRenderer(CapaArmorModel model) {
        super(model);
        this.capeModel = model;
        addRenderLayer(new CapaGlowLayer(this));
    }

    /**
     * Opaque cloth with the same projection as the emissive pass.
     * armorCutoutNoCull applies a view-space depth offset. On the same
     * surface that would make entityTranslucentEmissive fail its depth test.
     * Both cape passes instead use an unshifted, depth-tested render type.
     */
    @Override
    public RenderType getRenderType(CapaDeteriorerItem animatable,
                                    ResourceLocation texture,
                                    @Nullable MultiBufferSource bufferSource,
                                    float partialTick) {
        return RenderType.entityCutoutNoCull(texture, true);
    }

    @Override
    public void prepForRender(@Nullable Entity wearer, ItemStack stack, @Nullable EquipmentSlot slot,
                              @Nullable HumanoidModel<?> model) {
        super.prepForRender(wearer, stack, slot, model);
        armorPassSubmitted = false;
    }

    @Override
    public void preRender(PoseStack poseStack, CapaDeteriorerItem item,
                          BakedGeoModel geometry,
                          @Nullable MultiBufferSource buffers, @Nullable VertexConsumer consumer,
                          boolean isReRender, float partial, int light, int overlay,
                          float red, float green, float blue, float alpha) {
        sampleFit = !isReRender;
        super.preRender(poseStack, item, geometry, buffers, consumer, isReRender, partial, light, overlay,
                red, green, blue, alpha);
    }

    private static double backArm(HumanoidModel<?> model) {
        return Math.max(CapeStride.backDegrees(model.leftArm.xRot, model.leftArm.yRot),
                CapeStride.backDegrees(model.rightArm.xRot, model.rightArm.yRot));
    }

    @Override
    public void renderToBuffer(PoseStack poseStack, VertexConsumer buffer, int light, int overlay,
                               float red, float green, float blue, float alpha) {
        // Forge prepares one model, then calls it for base, trim and foil.
        // GeckoLib obtains its own buffer; the latter two calls would replay
        // the whole opaque + light render, not just the requested material.
        if (armorPassSubmitted) return;
        armorPassSubmitted = true;
        super.renderToBuffer(poseStack, buffer, light, overlay, red, green, blue, alpha);
    }

    @Override
    public void defaultRender(PoseStack poseStack, CapaDeteriorerItem animatable,
                              MultiBufferSource buffers, @Nullable RenderType renderType,
                              @Nullable VertexConsumer buffer, float yaw, float partialTick, int light) {
        // Actual enchantments still show on the icon. Do not tint the worn
        // reference-matched material with the incoming foil buffer.
        super.defaultRender(poseStack, animatable, buffers, renderType, null, yaw, partialTick, light);
    }

    @Override
    protected void applyBaseTransformations(HumanoidModel<?> model) {
        super.applyBaseTransformations(model);
        if (!sampleFit) return;
        var player = getCurrentEntity() instanceof AbstractClientPlayer p ? p : null;
        elytra = player != null && player.getItemBySlot(EquipmentSlot.CHEST).is(Items.ELYTRA);
        slimSleeves = player != null && player.getModelName().equals("slim");
        mountInChest = bone(CapeFit.BONE) != null && bone(CapeFit.GUSSET_BONE) != null;
        snugSeat = mountInChest && !elytra && bone(CapeFit.SEAT_FRAME) != null;
        double arm = backArm(model);
        double leg = Math.max(CapeStride.backDegrees(model.leftLeg.xRot, model.leftLeg.yRot),
                CapeStride.backDegrees(model.rightLeg.xRot, model.rightLeg.yRot));
        // Locomotion and wing clearance still work. No camera or head
        // angles enter the mount, plate positions, or drape clearance.
        double wings = elytra ? CapeWingFit.topGoal(Math.toDegrees(player.elytraRotX), Math.toDegrees(player.elytraRotZ),
                Math.toDegrees(model.body.xRot), 0) : 0;
        capeModel.setClearancePose(arm, leg, model.body.xRot, wings);
    }

    @Override
    public void renderRecursively(PoseStack poseStack, CapaDeteriorerItem animatable, GeoBone bone,
                                  RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                                  boolean isReRender, float partialTick, int light, int overlay,
                                  float red, float green, float blue, float alpha) {
        String name = bone.getName();
        // The two plates are drawn once from chestplate, not from the
        // original rear placement. Do not reparent the shared baked model.
        if (mountInChest && placedPlate(bone)) return;
        boolean backing = CapeBacking.LEFT.equals(name) || CapeBacking.RIGHT.equals(name);
        boolean rim = snugSeat && CapeMountPlacement.rim(name);
        boolean saddle = mountInChest && CapeMountPlacement.SADDLE_BONE.equals(name);
        boolean shoulder = CapeFit.SHOULDERS_BONE.equals(name);
        boolean underYoke = CapeFit.UNDER_YOKE_BONE.equals(name);
        boolean seat = snugSeat && CapeMountPlacement.SEAT_BONE.equals(name);
        boolean gusset = snugSeat && CapeFit.GUSSET_BONE.equals(name);
        boolean drape = snugSeat && CapeFit.DRAPE_BONE.equals(name);
        boolean fitted = backing || rim || saddle || shoulder || seat || gusset || drape || (underYoke && (snugSeat || elytra));
        if (fitted) poseStack.pushPose();
        try {
            if (snugSeat && (rim || shoulder)) {
                double y = CapeMountPlacement.RIM_Y / 16, z = CapeMountPlacement.BACK_PLANE / 16;
                poseStack.translate(0, y - CapeMountPlacement.RIM_DROP / 16, z);
                poseStack.scale(1, (float) CapeMountPlacement.RIM_HEIGHT, (float) CapeMountPlacement.RIM_DEPTH);
                poseStack.translate(0, -y, -z);
            }
            if (rim) {
                if (name.equals("v17_cowl_return")) {
                    poseStack.translate(0, -CapeMountPlacement.RETURN_DROP / 16, 0);
                } else if (!name.startsWith("v17_cowl_tooth_")) {
                    double y = CapeMountPlacement.TRIM_Y / 16, z = CapeMountPlacement.TRIM_Z / 16;
                    poseStack.translate(0, y - CapeMountPlacement.TRIM_DROP / 16, z);
                    poseStack.scale((float) CapeMountPlacement.TRIM_WIDTH, (float) CapeMountPlacement.TRIM_HEIGHT, 1);
                    poseStack.translate(0, -y, -z);
                }
            } else if (seat || gusset || (snugSeat && underYoke)) {
                squeezeDepth(poseStack, gusset ? CapeMountPlacement.GUSSET_DEPTH : CapeMountPlacement.RIM_DEPTH);
            } else if (fitted) {
                if (backing && snugSeat) {
                    // Shear the outer lip up into the collar without pulling
                    // its inner seam away from the actual back plane. Use the
                    // inverse transpose for normals in both render passes.
                    double z = CapeMountPlacement.LINING_PLANE / 16;
                    poseStack.translate(0, -CapeMountPlacement.LINING_DROP / 16, z);
                    poseStack.mulPoseMatrix(LINING_SHEAR);
                    poseStack.last().normal().mul(LINING_NORMAL);
                    poseStack.translate(0, 0, -z);
                    squeezeDepth(poseStack, CapeMountPlacement.LINING_DEPTH);
                }
                RenderUtils.translateToPivotPoint(poseStack, bone);
                if (saddle) {
                    if (snugSeat) {
                        poseStack.translate(0, -CapeMountPlacement.SADDLE_DROP / 16, CapeMountPlacement.SADDLE_DEPTH / 16);
                        poseStack.scale((float) CapeMountPlacement.SADDLE_WIDTH, (float) CapeMountPlacement.SADDLE_HEIGHT,
                                (float) CapeMountPlacement.SADDLE_THICKNESS);
                    } else {
                        poseStack.translate(0, 0, CapeMountPlacement.WING_SADDLE_DEPTH / 16);
                        poseStack.scale((float) CapeMountPlacement.WING_SADDLE_WIDTH, 1, 1);
                    }
                } else if (shoulder) {
                    if (elytra) {
                        poseStack.scale(1, (float) (CapeFit.SHOULDER_HEIGHT + (1-CapeFit.SHOULDER_HEIGHT)*CapeFit.SHOULDER_MIN),
                                (float) CapeFit.SHOULDER_MIN);
                    } else if (snugSeat) {
                        poseStack.translate(0, CapeMountPlacement.SHOULDER_RISE / 16, 0);
                        poseStack.scale(1, (float) CapeMountPlacement.SHOULDER_HEIGHT, (float) CapeMountPlacement.SHOULDER_REACH);
                    }
                } else if (underYoke) {
                    poseStack.scale(WING_LINING.width(), WING_LINING.height(), WING_LINING.depth());
                } else if (backing) {
                    var fold = elytra ? CapeBacking.TUCKED : CapeBacking.SEATED;
                    poseStack.scale(1, fold.left(), fold.depth());
                } else if (drape) {
                    poseStack.translate(0, -CapeMountPlacement.DRAPE_DROP / 16, -CapeMountPlacement.DRAPE_ADVANCE / 16);
                    poseStack.mulPose(Axis.XP.rotationDegrees((float) -CapeMountPlacement.DRAPE_PITCH));
                }
                RenderUtils.translateAwayFromPivotPoint(poseStack, bone);
            }
            super.renderRecursively(poseStack, animatable, bone, renderType, buffers, buffer,
                    isReRender, partialTick, light, overlay, red, green, blue, alpha);
        } finally {
            if (fitted) poseStack.popPose();
        }
    }

    private static void squeezeDepth(PoseStack poseStack, double scale) {
        double z = CapeMountPlacement.BACK_PLANE / 16;
        poseStack.translate(0, 0, z);
        poseStack.scale(1, 1, (float) scale);
        poseStack.translate(0, 0, -z);
    }

    @Override
    public void renderChildBones(PoseStack poseStack, CapaDeteriorerItem animatable, GeoBone bone,
                                 RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                                 boolean isReRender, float partialTick, int light, int overlay,
                                 float red, float green, float blue, float alpha) {
        super.renderChildBones(poseStack, animatable, bone, renderType, buffers, buffer,
                isReRender, partialTick, light, overlay, red, green, blue, alpha);
        if (!mountInChest || !bone.getName().equals("chestplate") || bone.isHidingChildren()) return;
        drawShoulder(poseStack, animatable, CapeMountPlacement.plate(elytra, false), renderType, buffers, buffer,
                isReRender, partialTick, light, overlay, red, green, blue, alpha);
        drawShoulder(poseStack, animatable, CapeMountPlacement.plate(elytra, true), renderType, buffers, buffer,
                isReRender, partialTick, light, overlay, red, green, blue, alpha);
    }

    private void drawShoulder(PoseStack poseStack, CapaDeteriorerItem animatable, CapeMountPlacement.Plate fit,
                              RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                              boolean isReRender, float partialTick, int light, int overlay,
                              float red, float green, float blue, float alpha) {
        GeoBone plate = bone(fit.bone());
        if (plate == null || !placedPlate(plate)) return;
        poseStack.pushPose();
        try {
            double x = -fit.x()/16, y = fit.y()/16, z = fit.z()/16;
            poseStack.translate(x-fit.shiftX(slimSleeves)/16, y+fit.dy()/16, z+fit.dz()/16);
            poseStack.mulPose(Axis.ZP.rotationDegrees((float) fit.roll()));
            poseStack.mulPose(Axis.YP.rotationDegrees((float) -fit.yaw()));
            poseStack.mulPose(Axis.XP.rotationDegrees((float) -fit.pitch()));
            poseStack.scale((float) fit.width(), (float) fit.height(), (float) fit.depth());
            poseStack.translate(-x, -y, -z);
            // Same complete plate geometry, cutout and emission. Nothing is
            // added to the GEO or attached to the camera/helmet/hand pose.
            super.renderRecursively(poseStack, animatable, plate, renderType, buffers, buffer,
                    isReRender, partialTick, light, overlay, red, green, blue, alpha);
        } finally {
            poseStack.popPose();
        }
    }

    private static boolean placedPlate(GeoBone bone) {
        return (CapePlateFit.SMALL.equals(bone.getName()) || CapePlateFit.WIDE.equals(bone.getName()))
                && bone.getParent() != null && CapeFit.BONE.equals(bone.getParent().getName());
    }

    private GeoBone bone(String name) {
        return getGeoModel().getBone(name).orElse(null);
    }

    @Override
    public @Nullable GeoBone getHeadBone() {
        return bone("helmet"); // Separate, hidden in the chest slot; not a parent of the mantle.
    }

    @Override
    public @Nullable GeoBone getBodyBone() {
        return bone("chestplate");
    }

    @Override
    public @Nullable GeoBone getRightArmBone() {
        return bone("rightArm");
    }

    @Override
    public @Nullable GeoBone getLeftArmBone() {
        return bone("leftArm");
    }

    @Override
    public @Nullable GeoBone getRightLegBone() {
        return bone("rightLeg");
    }

    @Override
    public @Nullable GeoBone getLeftLegBone() {
        return bone("leftLeg");
    }

    @Override
    public @Nullable GeoBone getRightBootBone() {
        return bone("rightBoot");
    }

    @Override
    public @Nullable GeoBone getLeftBootBone() {
        return bone("leftBoot");
    }
}
