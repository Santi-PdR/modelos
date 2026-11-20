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
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.util.RenderUtils;

public class CapaArmorRenderer extends GeoArmorRenderer<CapaDeteriorerItem> {
    private final CapaArmorModel capeModel;
    private CapeMountPlacement.Pose placement = CapeMountPlacement.worn(false);
    private static final CapeFit.YokeShape LINING = CapeFit.yokeShape(0, 0, 0, true);
    private boolean mountInChest;
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
        boolean hasWings = player != null && player.getItemBySlot(EquipmentSlot.CHEST).is(Items.ELYTRA);
        placement = CapeMountPlacement.worn(hasWings);
        mountInChest = bone(CapeFit.BONE) != null && bone(CapeFit.GUSSET_BONE) != null;
        double arm = backArm(model);
        double leg = Math.max(CapeStride.backDegrees(model.leftLeg.xRot, model.leftLeg.yRot),
                CapeStride.backDegrees(model.rightLeg.xRot, model.rightLeg.yRot));
        // Locomotion and wing clearance still work. No camera or head
        // angles enter the mount, plate positions, or drape clearance.
        double depth = mountInChest ? placement.depth() : 0;
        double wings = hasWings ? CapeWingFit.topGoal(Math.toDegrees(player.elytraRotX), Math.toDegrees(player.elytraRotZ),
                Math.toDegrees(model.body.xRot), depth) : 0;
        double fall = mountInChest ? placement.drape() - placement.pitch() : 0;
        capeModel.setClearancePose(arm, leg, model.body.xRot, depth, fall, wings);
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
        boolean mount = mountInChest && CapeFit.BONE.equals(name);
        boolean backing = CapeBacking.LEFT.equals(name) || CapeBacking.RIGHT.equals(name);
        boolean trim = mountInChest && placement.pitch() != 0 && CapeMountPlacement.trim(name);
        boolean gusset = mountInChest && placement.linkPitch() != 0 && CapeFit.GUSSET_BONE.equals(name);
        boolean drape = mountInChest && placement.drape() != 0 && CapeFit.DRAPE_BONE.equals(name);
        boolean saddle = mountInChest && CapeMountPlacement.SADDLE_BONE.equals(name);
        boolean shoulder = CapeFit.SHOULDERS_BONE.equals(name);
        boolean underYoke = CapeFit.UNDER_YOKE_BONE.equals(name);
        boolean fitted = mount || backing || trim || gusset || drape || saddle || shoulder || underYoke;
        if (fitted) poseStack.pushPose();
        try {
            if (mount) {
                poseStack.translate(0, placement.dy()/16, placement.depth()/16);
                double y = CapeMountPlacement.PIVOT_Y/16, z = CapeMountPlacement.PIVOT_Z/16;
                poseStack.translate(0, y, z);
                poseStack.mulPose(Axis.XP.rotationDegrees((float) placement.pitch()));
                poseStack.translate(0, -y, -z);
            } else if (trim) {
                double y = CapeMountPlacement.TRIM_Y/16, z = CapeMountPlacement.TRIM_Z/16;
                poseStack.translate(0, y - CapeMountPlacement.TRIM_DROP/16, z);
                poseStack.scale((float) CapeMountPlacement.TRIM_WIDTH, (float) CapeMountPlacement.TRIM_HEIGHT, 1);
                poseStack.translate(0, -y, -z);
            } else if (fitted) {
                RenderUtils.translateToPivotPoint(poseStack, bone);
                if (saddle) {
                    double depth = placement.pitch() == 0 ? CapeMountPlacement.WING_SADDLE_DEPTH : CapeMountPlacement.SADDLE_DEPTH;
                    poseStack.translate(0, 0, depth/16);
                    poseStack.scale((float) CapeMountPlacement.SADDLE_WIDTH, 1, 1);
                } else if (shoulder)
                    poseStack.scale(1, (float) (CapeFit.SHOULDER_HEIGHT + (1-CapeFit.SHOULDER_HEIGHT)*CapeFit.SHOULDER_MIN),
                            (float) CapeFit.SHOULDER_MIN);
                else if (underYoke)
                    poseStack.scale(LINING.width(), LINING.height(), LINING.depth());
                else if (backing) {
                    var fold = placement.pitch() == 0 ? CapeBacking.TUCKED : CapeBacking.STATIONARY;
                    poseStack.scale(1, fold.left(), fold.depth());
                } else if (drape)
                    poseStack.mulPose(Axis.XP.rotationDegrees((float) -placement.drape()));
                else if (gusset) {
                    poseStack.mulPose(Axis.XP.rotationDegrees((float) placement.linkPitch()));
                    float scale = (float) placement.linkScale();
                    poseStack.scale(1, scale, scale);
                }
                RenderUtils.translateAwayFromPivotPoint(poseStack, bone);
            }
            super.renderRecursively(poseStack, animatable, bone, renderType, buffers, buffer,
                    isReRender, partialTick, light, overlay, red, green, blue, alpha);
        } finally {
            if (fitted) poseStack.popPose();
        }
    }

    @Override
    public void renderChildBones(PoseStack poseStack, CapaDeteriorerItem animatable, GeoBone bone,
                                 RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                                 boolean isReRender, float partialTick, int light, int overlay,
                                 float red, float green, float blue, float alpha) {
        super.renderChildBones(poseStack, animatable, bone, renderType, buffers, buffer,
                isReRender, partialTick, light, overlay, red, green, blue, alpha);
        if (!mountInChest || !bone.getName().equals("chestplate") || bone.isHidingChildren()) return;
        drawShoulder(poseStack, animatable, CapeMountPlacement.SMALL, renderType, buffers, buffer,
                isReRender, partialTick, light, overlay, red, green, blue, alpha);
        drawShoulder(poseStack, animatable, CapeMountPlacement.WIDE, renderType, buffers, buffer,
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
            poseStack.translate(x-fit.dx()/16, y+fit.dy()/16, z+fit.dz()/16);
            poseStack.mulPose(Axis.ZP.rotationDegrees(fit.roll()));
            poseStack.mulPose(Axis.YP.rotationDegrees(-fit.yaw()));
            poseStack.mulPose(Axis.XP.rotationDegrees(-fit.pitch()));
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
