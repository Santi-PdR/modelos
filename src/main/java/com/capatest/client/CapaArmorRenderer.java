package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
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
import net.minecraft.world.entity.Pose;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.util.RenderUtils;

public class CapaArmorRenderer extends GeoArmorRenderer<CapaDeteriorerItem> {
    private final CapaArmorModel capeModel;
    private static final CapeFit.YokeShape WING_LINING = CapeFit.yokeShape(0, 0, 0, true);
    private boolean mountInChest;
    private boolean slimSleeves;
    private boolean elytra;
    private boolean armorPassSubmitted;
    private boolean sampleFit;
    private double hoodClearance, rearTuck;
    private double hoodUp, hoodTurn, hoodLean;
    private boolean dryHood;
    private CapeHood.Nape nape = CapeHood.NO_NAPE;

    double hoodClearance() { return hoodClearance; }
    double rearTuck() { return rearTuck; }
    double sprintEdge() { return mountInChest && !elytra ? capeModel.sprintEdge() : 0; }

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
        double arm = backArm(model);
        double leg = Math.max(CapeStride.backDegrees(model.leftLeg.xRot, model.leftLeg.yRot),
                CapeStride.backDegrees(model.rightLeg.xRot, model.rightLeg.yRot));
        boolean upright = player != null && !player.isFallFlying() && !player.isSwimming() && !player.isPassenger();
        // Head and torso keep the crouched pose through an ordinary hop.
        // Losing floor contact must not undo the local nape fit in one frame.
        boolean dryUpright = upright && (player.getPose() == Pose.STANDING || player.getPose() == Pose.CROUCHING)
                && !player.isInWaterOrBubble() && !player.onClimbable();
        fitHood(model, mountInChest && !elytra && upright, dryUpright);
        double wings = elytra ? CapeWingFit.topGoal(Math.toDegrees(player.elytraRotX), Math.toDegrees(player.elytraRotZ),
                Math.toDegrees(model.body.xRot), 0) : 0;
        capeModel.setClearancePose(arm, leg, model.body.xRot, wings);
    }

    // Aim is local to the hood, sampled once per base draw. Never use
    // camera orientation, move the rigid mount, or touch the Elytra fit.
    private void fitHood(HumanoidModel<?> model, boolean enabled, boolean dryUpright) {
        hoodClearance = rearTuck = 0;
        nape = CapeHood.NO_NAPE;
        dryHood = enabled && dryUpright;
        if (!enabled) return;
        double up = -Math.toDegrees(model.head.xRot);
        double turn = Math.toDegrees(model.head.yRot - model.body.yRot);
        double lean = Math.toDegrees(model.body.xRot);
        hoodClearance = CapeHood.lookClearance(up, turn, lean);
        if (dryHood) {
            rearTuck = CapeHood.rearTuck(up, turn, lean);
            hoodUp = up;
            hoodTurn = turn;
            hoodLean = lean;
        }
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
        boolean seat = mountInChest && !elytra && CapeFit.SEAT_FRAME.equals(name);
        boolean backing = elytra && (CapeBacking.LEFT.equals(name) || CapeBacking.RIGHT.equals(name));
        boolean saddle = mountInChest && CapeMountPlacement.SADDLE_BONE.equals(name);
        boolean shoulder = (mountInChest || elytra) && CapeFit.SHOULDERS_BONE.equals(name);
        boolean underYoke = elytra && CapeFit.UNDER_YOKE_BONE.equals(name);
        GeoBone parent = bone.getParent();
        boolean collarPart = mountInChest && !elytra && parent != null && CapeFit.BONE.equals(parent.getName());
        boolean hood = collarPart && CapeHood.moves(name);
        var trim = collarPart ? nape.forBone(name) : CapeHood.FIXED;
        double sprint = sprintEdge();
        var edge = sprint > 0 && parent != null ? CapeSprintEdge.offset(name, parent.getName()) : null;
        boolean wingFit = elytra && (backing || saddle || shoulder || underYoke);
        boolean fitted = seat || saddle || shoulder || wingFit || hood || trim != CapeHood.FIXED || edge != null;
        if (fitted) poseStack.pushPose();
        try {
            // Shared by cutout and bloom. Part of the return stroke follows
            // through on the chain so it remains connected to the cowl.
            if (trim != CapeHood.FIXED) poseStack.translate(trim.x() / 16, trim.y() / 16, trim.z() / 16);
            if (seat) {
                // One rigid displacement in chest space, shared by the
                // solid and glow passes. Never rescale the worn mantle.
                poseStack.translate(0, -CapeMountPlacement.BACK_DROP / 16, -CapeMountPlacement.BACK_FORWARD / 16);
            } else if (saddle && !elytra) {
                poseStack.translate(0, 0, CapeMountPlacement.SADDLE_SET / 16);
            } else if (hood) {
                // The same local hinge in both passes: no writes to shared
                // bones, neck alignment, or translation of the sewn roots.
                var fold = capeModel.hood();
                double tuck = CapeHood.rear(name) ? rearTuck : 0;
                double y = CapeHood.PIVOT_Y / 16, z = CapeHood.PIVOT_Z / 16;
                poseStack.translate(0, y - tuck * CapeHood.REAR_DROP / 16,
                        z + (CapeHood.SET_BACK - tuck * CapeHood.REAR_INSET) / 16);
                poseStack.mulPose(Axis.ZP.rotationDegrees((float) fold.roll()));
                poseStack.mulPose(Axis.YP.rotationDegrees((float) fold.yaw()));
                poseStack.mulPose(Axis.XP.rotationDegrees((float) (fold.pitch() + hoodClearance - tuck * CapeHood.REAR_FOLD)));
                poseStack.translate(0, -y, -z);
            } else if (edge != null) {
                // Render-only offset in the section frame, identical in cutout and glow.
                poseStack.translate(sprint * edge.x() / 16, 0, sprint * edge.z() / 16);
            } else if (shoulder && !elytra) {
                poseStack.translate(0, CapeMountPlacement.SHOULDER_LIFT / 16, -CapeMountPlacement.SHOULDER_FORWARD / 16);
            } else if (wingFit) {
                // A pose-stack push for the nape alone must not scale the trim.
                // Only the pre-existing lining/fold clearance for Elytra.
                RenderUtils.translateToPivotPoint(poseStack, bone);
                if (saddle) {
                    poseStack.translate(0, 0, CapeMountPlacement.WING_SADDLE_DEPTH / 16);
                    poseStack.scale((float) CapeMountPlacement.WING_SADDLE_WIDTH, 1, 1);
                } else if (shoulder) {
                    poseStack.scale(1, (float) (CapeFit.SHOULDER_HEIGHT + (1-CapeFit.SHOULDER_HEIGHT)*CapeFit.SHOULDER_MIN),
                            (float) CapeFit.SHOULDER_MIN);
                } else if (underYoke) {
                    poseStack.scale(WING_LINING.width(), WING_LINING.height(), WING_LINING.depth());
                } else {
                    var fold = CapeBacking.TUCKED;
                    poseStack.scale(1, fold.left(), fold.depth());
                }
                RenderUtils.translateAwayFromPivotPoint(poseStack, bone);
            }
            super.renderRecursively(poseStack, animatable, bone, renderType, buffers, buffer,
                    isReRender, partialTick, light, overlay, red, green, blue, alpha);
        } finally {
            if (fitted) poseStack.popPose();
        }
    }

    boolean hidesInteriorLip(GeoBone bone) {
        return mountInChest && !elytra && (CapeBacking.LEFT.equals(bone.getName()) || CapeBacking.RIGHT.equals(bone.getName()))
                && bone.getParent() != null && CapeFit.SEAT_FRAME.equals(bone.getParent().getName())
                && bone.getCubes().size() == CapeMountPlacement.LINING_CUBES;
    }

    @Override
    public void renderCubesOfBone(PoseStack poseStack, GeoBone bone, VertexConsumer buffer, int light, int overlay,
                                  float red, float green, float blue, float alpha) {
        if (!hidesInteriorLip(bone)) {
            super.renderCubesOfBone(poseStack, bone, buffer, light, overlay, red, green, blue, alpha);
            return;
        }
        if (bone.isHidden()) return;
        // Keep the spine and lower return. Exclude only the obsolete upper
        // lip from both passes; never mutate the shared baked geometry.
        for (int i = 0; i < bone.getCubes().size(); ++i) {
            if (i == CapeMountPlacement.LINING_LIP_CUBE) continue;
            poseStack.pushPose();
            try {
                renderCube(poseStack, bone.getCubes().get(i), buffer, light, overlay, red, green, blue, alpha);
            } finally {
                poseStack.popPose();
            }
        }
    }

    @Override
    public void renderChildBones(PoseStack poseStack, CapaDeteriorerItem animatable, GeoBone bone,
                                 RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                                 boolean isReRender, float partialTick, int light, int overlay,
                                 float red, float green, float blue, float alpha) {
        if (dryHood && !isReRender && CapeFit.BONE.equals(bone.getName())
                && getCurrentEntity() instanceof AbstractClientPlayer player) {
            // The clip sampler has now advanced the cloth to this draw. Reuse
            // that Shift release, and keep the identical fit in the glow pass.
            var motion = CapaArmorModel.wornMotion(player);
            nape = CapeHood.nape(hoodUp, hoodTurn, hoodLean, motion == null ? 0 : motion.weight(CapeState.SNEAK));
        }
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
