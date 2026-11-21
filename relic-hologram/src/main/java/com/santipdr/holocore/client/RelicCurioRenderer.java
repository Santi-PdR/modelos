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
    /** Bloques en los que la reliquia de otro jugador se apaga al alejarse. */
    private static final double FADE_BLOCKS = 8.0;


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

        // Distancia: fuera de maxRenderDistance no se dibuja, y en los ultimos
        // bloques se apaga poco a poco en vez de desaparecer de golpe.
        float fade = 1.0F;
        Player local = Minecraft.getInstance().player;
        if (local != null && player != local) {
            double max = RelicConfig.MAX_RENDER_DISTANCE.get();
            double distance = Math.sqrt(local.distanceToSqr(player));
            if (distance > max) {
                return;
            }
            fade = (float) Math.max(0.0, Math.min(1.0, (max - distance) / FADE_BLOCKS));
        }

        RelicVisuals.RelicVisual visual = RelicVisuals.visual(player);
        RelicAnimatable animatable = visual.animatable();
        animatable.update(player, ClientRelicStates.get(player.getUUID()), partialTicks);
        // Se esta dibujando: el camino de tick no debe descartar animaciones para
        // este portador.
        animatable.markRendered(player.level().getGameTime());

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
        // El estado de brillo se actualiza antes de dibujar nada: el modelo usa el
        // mismo factor que el aura, asi que dormida se apaga todo a la vez.
        RelicAnimatable.LoopState state = animatable.loopState();
        visual.glow().update(state, animatable.flash());

        visual.renderer().renderHologram(poseStack, animatable, bufferSource, partialTicks,
                LightTexture.FULL_BRIGHT, visual.glow(), fade);

        // Aura + anillo: billboards aditivos sobre el mismo anclaje (incluye la
        // escala de la config, que se lee de la matriz).
        if (RelicAura.enabled()) {
            // Cronometrado aparte para que /relic stats diga cuanto es modelo y
            // cuanto aura: son dos palancas distintas (pases vs billboards).
            long began = System.nanoTime();
            RelicAura.render(poseStack, bufferSource, partialTicks, state, visual.glow(), fade);
            RelicRenderStats.aura(System.nanoTime() - began);
        }

        poseStack.popPose();
    }
}
