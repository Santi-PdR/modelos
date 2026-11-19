package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.util.RenderUtils;

public class CapaArmorRenderer extends GeoArmorRenderer<CapaDeteriorerItem> {
    private float wearerDepth;

    public CapaArmorRenderer() {
        // Apunta a:
        // assets/capatest/geo/item/armor/capa_deteriorer_evilsaiyan.geo.json
        // assets/capatest/animations/item/armor/capa_deteriorer_evilsaiyan.animation.json
        // assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan.png
        // y *_glowmask.png (GeckoLib 4.8 usa el sufijo "_glowmask").
        super(new CapaArmorModel(
                new ResourceLocation(CapaTestMod.MOD_ID, "armor/capa_deteriorer_evilsaiyan")
        ));

        // Emisivo pulsante en vez del AutoGlowingGeoLayer plano.
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
    }

    @Override
    public void renderRecursively(PoseStack poseStack, CapaDeteriorerItem animatable, GeoBone bone,
                                  RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                                  boolean isReRender, float partialTick, int light, int overlay,
                                  float red, float green, float blue, float alpha) {
        String name = bone.getName();
        boolean fitted = wearerDepth > 0 && (CapeFit.BONE.equals(name)
                || CapeFit.DRAPE_BONE.equals(name) || CapeFit.GUSSET_BONE.equals(name));
        if (fitted)
            poseStack.pushPose();
        try {
            // Apply the same deformation in the cutout and emission passes.
            // It is relative to the live chestplate, never to camera/world.
            if (fitted && CapeFit.BONE.equals(name)) {
                poseStack.translate(0, 0, wearerDepth / 16.0F);
            } else if (fitted) {
                RenderUtils.translateToPivotPoint(poseStack, bone);
                if (CapeFit.DRAPE_BONE.equals(name))
                    poseStack.mulPose(Axis.XP.rotationDegrees((float) CapeFit.drapeDegrees(wearerDepth)));
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
