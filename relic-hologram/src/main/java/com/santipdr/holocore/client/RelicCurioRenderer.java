package com.santipdr.holocore.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.santipdr.holocore.config.RelicConfig;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.client.ICurioRenderer;

/**
 * Render del accesorio sobre el jugador.
 *
 * <p>Se ancla al hueso {@code body} del modelo del portador con
 * {@link net.minecraft.client.model.geom.ModelPart#translateAndRotate}. Eso da
 * tres cosas gratis: el nucleo sigue la rotacion del torso, se inclina y baja
 * al agacharse (sneak) como una mochila, y los offsets quedan en el mismo
 * espacio que el modelo del jugador (Y+ hacia abajo, Z+ hacia la espalda), que
 * es exactamente la convencion en la que esta hecho el .geo.json.</p>
 *
 * <p>No se dibuja en primera persona porque Curios solo llama a este renderer
 * desde las capas del renderer de la entidad; el jugador local no se renderiza
 * en primera persona.</p>
 */
public class RelicCurioRenderer implements ICurioRenderer {

    private static final float PIXEL = 1.0F / 16.0F;


    @Override
    public <T extends LivingEntity, M extends EntityModel<T>> void render(
            ItemStack stack, SlotContext slotContext, PoseStack poseStack,
            RenderLayerParent<T, M> renderLayerParent, MultiBufferSource bufferSource, int light,
            float limbSwing, float limbSwingAmount, float partialTicks, float ageInTicks,
            float netHeadYaw, float headPitch) {

        if (!(slotContext.entity() instanceof Player player)) {
            return;
        }
        if (player.isInvisible() || player.isSpectator()) {
            return;
        }

        Player local = Minecraft.getInstance().player;
        if (local != null && player != local) {
            double max = RelicConfig.MAX_RENDER_DISTANCE.get();
            if (local.distanceToSqr(player) > max * max) {
                return;
            }
        }

        RelicVisuals.RelicVisual visual = RelicVisuals.visual(player);
        RelicAnimatable animatable = visual.animatable();
        animatable.update(player, ClientRelicStates.get(player.getUUID()), partialTicks);

        EntityModel<T> parentModel = renderLayerParent.getModel();

        poseStack.pushPose();
        if (parentModel instanceof HumanoidModel<?> humanoid) {
            // Origen en el pivote del torso: hombros/ cuello, Y+ abajo, Z+ espalda.
            humanoid.body.translateAndRotate(poseStack);
        } else {
            // Fallback para portadores no humanoides: altura aproximada de hombros.
            poseStack.translate(0.0F, 1.35F, 0.0F);
        }

        float sideSign = RelicConfig.SHOULDER.get() == RelicConfig.Shoulder.LEFT ? 1.0F : -1.0F;
        poseStack.translate(
                sideSign * RelicConfig.OFFSET_X.get().floatValue() * PIXEL,
                RelicConfig.OFFSET_Y.get().floatValue() * PIXEL,
                RelicConfig.OFFSET_Z.get().floatValue() * PIXEL);

        float scale = RelicConfig.SCALE.get().floatValue();
        poseStack.scale(scale, scale, scale);

        // Luz maxima: el nucleo es una fuente de luz, no debe depender del
        // lightmap (cuevas, noche, agua).
        visual.renderer().renderHologram(poseStack, animatable, bufferSource, partialTicks,
                LightTexture.FULL_BRIGHT);

        poseStack.popPose();
    }
}
