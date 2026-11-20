package com.stainkatana.katana.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.StainKatanaItem;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.entity.player.PlayerRenderer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.HumanoidArm;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderHandEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Vanilla normally omits the arm while holding an item. Render the skin arm as well. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaFirstPersonArm {
    private KatanaFirstPersonArm() { }
    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void arm(RenderHandEvent event) {
        Minecraft mc = Minecraft.getInstance();
        if (event.isCanceled() || mc.player == null || mc.player.isInvisible()
                || !(event.getItemStack().getItem() instanceof StainKatanaItem)
                || KatanaAnimations.isPlaying(mc.player)) return;
        HumanoidArm arm = event.getHand() == net.minecraft.world.InteractionHand.MAIN_HAND
                ? mc.player.getMainArm() : mc.player.getMainArm().getOpposite();
        boolean right = arm == HumanoidArm.RIGHT;
        float sign = right ? 1 : -1;
        float swing = event.getSwingProgress();
        float root = Mth.sqrt(swing);
        PoseStack pose = event.getPoseStack();
        pose.pushPose();
        pose.translate(sign * (-.3F * Mth.sin(root * Mth.PI) + .98F),
                .4F * Mth.sin(root * Mth.TWO_PI) - .6F - event.getEquipProgress() * .6F,
                -.4F * Mth.sin(swing * Mth.PI) - .72F);
        pose.mulPose(Axis.YP.rotationDegrees(sign * 45));
        pose.mulPose(Axis.YP.rotationDegrees(sign * Mth.sin(root * Mth.PI) * 70));
        pose.mulPose(Axis.ZP.rotationDegrees(sign * Mth.sin(swing * swing * Mth.PI) * -20));
        pose.translate(sign * -1, 3.6, 3.5);
        pose.mulPose(Axis.ZP.rotationDegrees(sign * 120));
        pose.mulPose(Axis.XP.rotationDegrees(200));
        pose.mulPose(Axis.YP.rotationDegrees(sign * -135));
        pose.translate(sign * 5.6, 0, 0);
        var renderer = mc.getEntityRenderDispatcher().getRenderer(mc.player);
        if (renderer instanceof PlayerRenderer playerRenderer) {
            if (right) playerRenderer.renderRightHand(pose, event.getMultiBufferSource(), event.getPackedLight(), mc.player);
            else playerRenderer.renderLeftHand(pose, event.getMultiBufferSource(), event.getPackedLight(), mc.player);
        }
        pose.popPose();
        // Do not cancel: let Forge/Better Combat render the item normally.
    }
}
