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
    private float wearerFold;

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
     * v1.33.0: render type OPACO y con test de profundidad explícito.
     *
     * El default de GeckoLib ya es {@code armorCutoutNoCull} (opaco, doble
     * cara, alpha-test), pero lo re-afirmamos aquí para que la capa NUNCA
     * quede translúcida. La textura base es 100% opaca (alpha 255), así que
     * el alpha-test no descarta nada y la capa se dibuja opaca. El test de
     * profundidad asegura que, en la vista F5 (espalda), la parte de la
     * capa detrás del cuerpo se OCLUDA correctamente (no se dibuje como un
     * fantasma translúcido sobre el cuerpo).
     */
    @Override
    public RenderType getRenderType(CapaDeteriorerItem animatable,
                                    ResourceLocation texture,
                                    @Nullable MultiBufferSource bufferSource,
                                    float partialTick) {
        return RenderType.armorCutoutNoCull(texture);
    }

    @Override
    protected void applyBaseTransformations(HumanoidModel<?> model) {
        super.applyBaseTransformations(model);
        wearerFold = (float) CapeFit.foldDegrees(model.body.xRot, model.body.yRot,
                model.head.xRot, model.head.yRot);
    }

    @Override
    public void renderRecursively(PoseStack poseStack, CapaDeteriorerItem animatable, GeoBone bone,
                                  RenderType renderType, MultiBufferSource buffers, VertexConsumer buffer,
                                  boolean isReRender, float partialTick, int light, int overlay,
                                  float red, float green, float blue, float alpha) {
        boolean fit = wearerFold != 0 && CapeFit.BONE.equals(bone.getName());
        if (fit) {
            // A rigid, common rotation about the GEO pivot, in both passes.
            // No animation snapshot or pose from another wearer is changed.
            poseStack.pushPose();
            RenderUtils.translateToPivotPoint(poseStack, bone);
            poseStack.mulPose(Axis.XP.rotationDegrees(wearerFold));
            RenderUtils.translateAwayFromPivotPoint(poseStack, bone);
        }
        try {
            super.renderRecursively(poseStack, animatable, bone, renderType, buffers, buffer,
                    isReRender, partialTick, light, overlay, red, green, blue, alpha);
        } finally {
            if (fit)
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
