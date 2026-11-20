package com.stainkatana.katana;

import com.stainkatana.StainKatanaMod;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.ItemRenderer;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import software.bernie.geckolib.model.DefaultedItemGeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;

/** Icono plano en la interfaz; geometría GeckoLib en mano, suelo y marco. */
public class KatanaRenderer extends GeoItemRenderer<StainKatanaItem> {
    private static final ResourceLocation ICON = new ResourceLocation(StainKatanaMod.MOD_ID,
            "textures/item/katana_stain_icon.png");

    public KatanaRenderer() {
        super(new DefaultedItemGeoModel<>(new ResourceLocation(StainKatanaMod.MOD_ID, "katana_stain")));
        addRenderLayer(new software.bernie.geckolib.renderer.layer.GeoRenderLayer<StainKatanaItem>(this) {
            private final ResourceLocation glow = new ResourceLocation(StainKatanaMod.MOD_ID, "textures/item/katana_stain_glow.png");
            @Override public void render(PoseStack pose, StainKatanaItem item,
                    software.bernie.geckolib.cache.object.BakedGeoModel model, RenderType type,
                    MultiBufferSource buffers, VertexConsumer buffer, float partial, int light, int overlay) {
                RenderType emissive = RenderType.entityTranslucentEmissive(glow);
                getRenderer().reRender(model, pose, buffers, item, emissive, buffers.getBuffer(emissive),
                        partial, LightTexture.FULL_BRIGHT, overlay, 1, 1, 1, 1);
            }
        });
    }

    @Override
    public void renderByItem(ItemStack stack, ItemDisplayContext context, PoseStack poseStack,
                             MultiBufferSource buffers, int light, int overlay) {
        if (context != ItemDisplayContext.GUI) {
            poseStack.pushPose();
            // Separate hand-space adjustments: the two vanilla pipelines have different origins.
            // These are provisional and must be checked against the rendered grip, not just the bone pivot.
            if (context == ItemDisplayContext.THIRD_PERSON_RIGHT_HAND || context == ItemDisplayContext.THIRD_PERSON_LEFT_HAND)
                poseStack.translate(0, -1.2 / 16.0, 0);
            else if (context == ItemDisplayContext.FIRST_PERSON_RIGHT_HAND || context == ItemDisplayContext.FIRST_PERSON_LEFT_HAND)
                poseStack.translate(0, -1.2 / 16.0, 0);
            super.renderByItem(stack, context, poseStack, buffers, light, overlay);
            poseStack.popPose();
            return;
        }
        // El renderer de ítems ya desplazó el origen -0.5; este cuadrado 0..1
        // ocupa exactamente el espacio de un ítem GUI. UV (0,0) es arriba.
        // Text shader is unlit and alpha blended; entity shaders apply directional
        // GUI lighting even at FULL_BRIGHT and darkened the supplied icon.
        VertexConsumer vertices = buffers.getBuffer(RenderType.text(ICON));
        PoseStack.Pose pose = poseStack.last();
        vertex(vertices, pose, 0, 0, 0, 1, overlay);
        vertex(vertices, pose, 1, 0, 1, 1, overlay);
        vertex(vertices, pose, 1, 1, 1, 0, overlay);
        vertex(vertices, pose, 0, 1, 0, 0, overlay);
    }

    private static void vertex(VertexConsumer vertices, PoseStack.Pose pose,
                               float x, float y, float u, float v, int overlay) {
        vertices.vertex(pose.pose(), x, y, 0.5F)
                .color(255, 255, 255, 255).uv(u, v)
                .uv2(LightTexture.FULL_BRIGHT).endVertex();
    }
}
