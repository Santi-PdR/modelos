package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.client.ICurioRenderer;

/**
 * Renderiza la capa cuando va en el slot "back" de Curios.
 *
 * Reutiliza el GeoArmorRenderer (con su capa de brillo pulsante y sus ocho
 * animaciones) en vez de duplicar el modelo: Curios nos da el PoseStack del
 * cuerpo y el HumanoidModel del portador, que es exactamente lo que
 * GeoArmorRenderer necesita en prepForRender().
 */
public class CapaCurioRenderer implements ICurioRenderer {
    private final CapaArmorRenderer cape = new CapaArmorRenderer();

    @Override
    public <T extends LivingEntity, M extends EntityModel<T>> void render(
            ItemStack stack,
            SlotContext slotContext,
            PoseStack poseStack,
            RenderLayerParent<T, M> parent,
            MultiBufferSource buffer,
            int light,
            float limbSwing,
            float limbSwingAmount,
            float partialTicks,
            float ageInTicks,
            float netHeadYaw,
            float headPitch) {

        if (stack == null || stack.isEmpty()
                || !(stack.getItem() instanceof CapaDeteriorerItem animatable)
                || slotContext == null || parent == null
                || !(parent.getModel() instanceof HumanoidModel<?> humanoid)) {
            return;
        }

        LivingEntity wearer = slotContext.entity();
        // GeckoLib 4.8.x puede recibir un portador nulo en renders de GUI/HUD
        // con otros mods de render instalados; no intentar prepForRender().
        if (wearer == null)
            return;
        // Si también está en el pecho, sólo se dibuja esa copia: evita
        // z-fighting y el doble glow, con la misma prioridad que el aura.
        if (wearer.getItemBySlot(EquipmentSlot.CHEST).is(stack.getItem()))
            return;
        // GeckoLib already copies the pitched/lowered HumanoidModel body.
        // Applying Curios' sneak helpers on top tilted and lowered it twice.
        // Both slots use exactly the same wearer fit and glow pass.
        this.cape.prepForRender(wearer, stack, EquipmentSlot.CHEST, humanoid);
        RenderType renderType = this.cape.getRenderType(
                animatable, this.cape.getTextureLocation(animatable), buffer, partialTicks);
        poseStack.pushPose();
        try {
            this.cape.defaultRender(poseStack, animatable, buffer, renderType,
                    null, 0, partialTicks, light);
        } finally {
            poseStack.popPose();
        }
    }
}
