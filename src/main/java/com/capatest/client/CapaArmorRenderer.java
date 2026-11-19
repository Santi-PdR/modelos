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
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.cache.object.GeoCube;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.util.RenderUtils;

public class CapaArmorRenderer extends GeoArmorRenderer<CapaDeteriorerItem> {
    private final CapaArmorModel capeModel;
    private float wearerDepth;
    private float seating;
    private float plateFit;
    private float shoulderReach = (float) CapeFit.SHOULDER_MIN;
    private CapeFit.YokeShape yoke = CapeFit.yokeShape(0, 0, 0, true);
    private CapeBacking.Shape backing = CapeBacking.TUCKED;
    private boolean armorPassSubmitted;
    private float wearerPartial;
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
        wearerPartial = partial;
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
        // Fit against the stride envelope, not the instantaneous crossing
        // of the arms. This keeps the top mount from pumping twice a step.
        double mountArm = arm;
        seating = plateFit = 0;
        if (getCurrentEntity() instanceof LivingEntity living && !living.isFallFlying()
                && !living.isPassenger() && !living.isAutoSpinAttack()) {
            double speed = Math.min(1, living.walkAnimation.speed(wearerPartial));
            float dry = 1 - living.getSwimAmount(wearerPartial);
            mountArm = CapeStride.walkEnvelope(arm, 0, speed, dry, 1);
            seating = (float) CapeFit.seating(model.body.xRot, model.body.yRot, model.head.xRot,
                    model.head.yRot, mountArm, hasWings) * dry;
            // A sleeve can sweep into a fitted plate while reaching forward
            // as well as back. Keep both rotations and the stride envelope.
            double sleeve = Math.max(Math.hypot(model.leftArm.xRot, model.leftArm.yRot),
                    Math.hypot(model.rightArm.xRot, model.rightArm.yRot));
            plateFit = CapePlateFit.influence(model.body.xRot, model.head.yRot - model.body.yRot,
                    model.head.xRot, Math.max(mountArm, Math.toDegrees(sleeve)), hasWings) * dry;
        }
        yoke = CapeFit.yokeShape(model.body.xRot, model.head.xRot, mountArm, hasWings);
        backing = CapeBacking.shape(model.body.xRot, model.body.yRot, model.head.xRot, model.head.yRot, wearerDepth, hasWings);
        capeModel.setClearancePose(arm, leg, model.body.xRot, wearerDepth, wings);
    }

    @Override
    public void renderRecursively(PoseStack poseStack, CapaDeteriorerItem animatable, GeoBone bone,
                                  RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                                  boolean isReRender, float partialTick, int light, int overlay,
                                  float red, float green, float blue, float alpha) {
        String name = bone.getName();
        CapePlateFit.Plate plate = plateFit > 0 ? CapePlateFit.forBone(name) : null;
        boolean shoulder = CapeFit.SHOULDERS_BONE.equals(name);
        boolean underYoke = CapeFit.UNDER_YOKE_BONE.equals(name);
        boolean backingLeft = CapeBacking.LEFT.equals(name);
        boolean backingRight = CapeBacking.RIGHT.equals(name);
        boolean seatFrame = seating > 0 && CapeFit.SEAT_FRAME.equals(name);
        boolean drape = CapeFit.DRAPE_BONE.equals(name);
        boolean fitted = plate != null || seatFrame || shoulder || underYoke || backingLeft || backingRight
                || drape && (wearerDepth > 0 || seating > 0)
                || wearerDepth > 0 && (CapeFit.BONE.equals(name) || CapeFit.GUSSET_BONE.equals(name));
        if (fitted)
            poseStack.pushPose();
        try {
            // Apply the same deformation in the cutout and emission passes.
            // It is relative to the live chestplate, never to camera/world.
            if (plate != null) {
                float k = plateFit;
                poseStack.translate(plate.x()/16F, (plate.y() + k*plate.lift())/16F,
                        (plate.z() + k*plate.advance())/16F);
                poseStack.mulPose(Axis.YP.rotationDegrees(plate.yaw()*k));
                poseStack.mulPose(Axis.XP.rotationDegrees(plate.pitch()*k));
                poseStack.scale(1 + k*(plate.width()-1), 1 + k*(plate.height()-1), 1 + k*(plate.depth()-1));
                poseStack.translate(-plate.x()/16F, -plate.y()/16F, -plate.z()/16F);
            } else if (fitted && CapeFit.BONE.equals(name)) {
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

    @Override
    public void renderCubesOfBone(PoseStack poseStack, GeoBone bone, VertexConsumer buffer,
                                  int light, int overlay, float red, float green, float blue, float alpha) {
        if (plateFit <= 0 || CapePlateFit.forBone(bone.getName()) == null) {
            super.renderCubesOfBone(poseStack, bone, buffer, light, overlay, red, green, blue, alpha);
            return;
        }
        if (bone.isHidden()) return;
        for (GeoCube cube : bone.getCubes()) {
            poseStack.pushPose();
            try {
                applyPlateRim(poseStack, bone, cube);
                renderCube(poseStack, cube, buffer, light, overlay, red, green, blue, alpha);
            } finally {
                poseStack.popPose();
            }
        }
    }

    // Used in both passes before GeckoLib applies the cube's own authored pivot.
    void applyPlateRim(PoseStack poseStack, GeoBone bone, GeoCube cube) {
        var plate = plateFit > 0 ? CapePlateFit.forBone(bone.getName()) : null;
        if (plate == null || bone.getCubes().size() <= CapePlateFit.RIM_CUBE
                || cube != bone.getCubes().get(CapePlateFit.RIM_CUBE)) return;
        var rim = plate.rim();
        float rise = CapePlateFit.rimRise(plateFit), reach = CapePlateFit.rimReach(plateFit);
        if (rise == 0 && reach == 0) return;
        poseStack.translate((rim.x()+reach*rim.across())/16F, (rim.y()+rise*rim.lift())/16F,
                (rim.z()+reach*rim.advance())/16F);
        poseStack.mulPose(Axis.XP.rotationDegrees(rim.pitch()*rise));
        poseStack.scale(1+reach*(rim.width()-1), 1+rise*(rim.height()-1), 1+reach*(rim.depth()-1));
        poseStack.translate(-rim.x()/16F, -rim.y()/16F, -rim.z()/16F);
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
