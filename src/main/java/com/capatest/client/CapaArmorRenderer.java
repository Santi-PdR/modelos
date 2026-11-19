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
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.util.RenderUtils;

public class CapaArmorRenderer extends GeoArmorRenderer<CapaDeteriorerItem> {
    private final CapaArmorModel capeModel;
    private float wearerDepth;
    private float seating;
    private float shoulderReach = (float) CapeFit.SHOULDER_MIN;
    private CapeFit.YokeShape yoke = CapeFit.yokeShape(0, 0, 0, true);
    private CapeBacking.Shape backing = CapeBacking.TUCKED;
    private boolean armorPassSubmitted;

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
        // Snapshot once for both the opaque pass and GeckoLib's emissive
        // re-render, which calls preRender again with the same fitted body.
        seating = 0;
        if (model != null && wearer instanceof LivingEntity living && !living.isFallFlying()
                && !living.isPassenger() && !living.isAutoSpinAttack()) {
            seating = (float) CapeFit.seating(model.body.xRot, model.body.yRot, model.head.xRot,
                    model.head.yRot, backArm(model), living.getItemBySlot(EquipmentSlot.CHEST).is(Items.ELYTRA))
                    * (1 - living.getSwimAmount(1));
        }
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
        wearerDepth = (float) CapeFit.backset(model.body.xRot, model.body.yRot,
                model.head.xRot, model.head.yRot);
        double arm = backArm(model);
        double leg = Math.max(CapeStride.backDegrees(model.leftLeg.xRot, model.leftLeg.yRot),
                CapeStride.backDegrees(model.rightLeg.xRot, model.rightLeg.yRot));
        // Curios renders after the vanilla ElytraLayer has updated these
        // smoothed angles. Don't recalculate that animation or touch the wings.
        double wings = 0;
        boolean hasWings = false;
        if (getCurrentEntity() instanceof AbstractClientPlayer player
                && player.getItemBySlot(EquipmentSlot.CHEST).is(Items.ELYTRA)) {
            hasWings = true;
            wings = CapeWingFit.topGoal(Math.toDegrees(player.elytraRotX), Math.toDegrees(player.elytraRotZ),
                    Math.toDegrees(model.body.xRot), wearerDepth);
        }
        shoulderReach = (float) CapeFit.shoulderReach(model.body.xRot, model.body.yRot,
                model.head.xRot, model.head.yRot, hasWings);
        yoke = CapeFit.yokeShape(model.body.xRot, model.head.xRot, arm, hasWings);
        backing = CapeBacking.shape(model.body.xRot, model.body.yRot, model.head.xRot, model.head.yRot, wearerDepth, hasWings);
        capeModel.setClearanceGoals(CapeStride.armGoal(arm, model.body.xRot, wearerDepth),
                CapeStride.legGoal(leg, model.body.xRot, wearerDepth), wings);
    }

    @Override
    public void renderRecursively(PoseStack poseStack, CapaDeteriorerItem animatable, GeoBone bone,
                                  RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                                  boolean isReRender, float partialTick, int light, int overlay,
                                  float red, float green, float blue, float alpha) {
        String name = bone.getName();
        boolean shoulder = CapeFit.SHOULDERS_BONE.equals(name);
        boolean underYoke = CapeFit.UNDER_YOKE_BONE.equals(name);
        boolean backingLeft = CapeBacking.LEFT.equals(name);
        boolean backingRight = CapeBacking.RIGHT.equals(name);
        boolean seatFrame = seating > 0 && CapeFit.SEAT_FRAME.equals(name);
        boolean drape = CapeFit.DRAPE_BONE.equals(name);
        boolean fitted = seatFrame || shoulder || underYoke || backingLeft || backingRight
                || drape && (wearerDepth > 0 || seating > 0)
                || wearerDepth > 0 && (CapeFit.BONE.equals(name) || CapeFit.GUSSET_BONE.equals(name));
        if (fitted)
            poseStack.pushPose();
        try {
            // Apply the same deformation in the cutout and emission passes.
            // It is relative to the live chestplate, never to camera/world.
            if (fitted && CapeFit.BONE.equals(name)) {
                poseStack.translate(0, 0, wearerDepth / 16.0F);
            } else if (fitted) {
                RenderUtils.translateToPivotPoint(poseStack, bone);
                if (seatFrame)
                    poseStack.scale(1, 1, (float) CapeFit.seatDepthScale(seating));
                else if (shoulder)
                    poseStack.scale((float) CapeFit.seatReturnWidth(seating),
                            (float) (CapeFit.SHOULDER_HEIGHT + (1 - CapeFit.SHOULDER_HEIGHT) * shoulderReach), shoulderReach);
                else if (underYoke)
                    poseStack.scale(yoke.width(), yoke.height(), yoke.depth());
                else if (backingLeft || backingRight)
                    poseStack.scale(1, backingLeft ? backing.left() : backing.right(), backing.depth());
                else if (drape)
                    poseStack.mulPose(Axis.XP.rotationDegrees((float) CapeFit.seatedDrapeDegrees(wearerDepth, seating)));
                else
                    poseStack.scale(1, 1, (float) CapeFit.gussetScale(wearerDepth));
                RenderUtils.translateAwayFromPivotPoint(poseStack, bone);
            }
            super.renderRecursively(poseStack, animatable, bone, renderType, buffers, buffer,
                    isReRender, partialTick, light, overlay, red, green, blue, alpha);
        } finally {
            if (fitted)
                poseStack.popPose();
        }
    }

    private GeoBone bone(String name) {
        return getGeoModel().getBone(name).orElse(null);
    }

    @Override
    public @Nullable GeoBone getHeadBone() {
        return bone("helmet");
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
