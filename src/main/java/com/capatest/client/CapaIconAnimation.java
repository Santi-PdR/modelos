package com.capatest.client;

import com.capatest.CapaTestMod;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.item.ItemProperties;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;

/**
 * v1.24.0 — ICONO ANIMADO EN LA HOTBAR, sin BEWLR.
 *
 * El usuario pidió: «el icono puede ser animado en la hotbar y tener
 * efectos, además de que debe verse bien como item».
 *
 * Se usa el MISMO mecanismo que el compass y el reloj de vanilla: una
 * propiedad de modelo `capatest:frame` (0, 0.25, 0.5, 0.75) evaluada en
 * cada render, y tres `overrides` en el modelo del item que seleccionan
 * la textura de la frame correspondiente. Así:
 *
 *   * la animación funciona en hotbar, inventario, mano, suelo y marco;
 *   * NO se registra ningún renderer 3D (`getCustomRenderer`), así que
 *     el icono 2D plano sigue siendo el que se ve (regla v1.17.2);
 *   * los efectos viven en las propias frames: pulso viajero de las
 *     grietas, broche que alterna y dos motas que suben (tools/texture_pipeline).
 *
 * Se registra en {@code FMLClientSetupEvent} (mod bus, sólo cliente): la
 * clase nunca se carga en servidor.
 */
@Mod.EventBusSubscriber(modid = CapaTestMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class CapaIconAnimation {
    private static final ResourceLocation FRAME =
            new ResourceLocation(CapaTestMod.MOD_ID, "frame");

    private CapaIconAnimation() {
    }

    @SubscribeEvent
    public static void onClientSetup(FMLClientSetupEvent event) {
        event.enqueueWork(() -> ItemProperties.register(
                CapaTestMod.CAPA_DETERIORER.get(), FRAME,
                (stack, world, entity, seed) -> {
                    // 4 game ticks por frame => bucle de 0.8 s: un latido
                    // vivo sin resultar nervioso en la hotbar.
                    int tick = world != null ? (int) (world.getGameTime() / 4L) : 0;
                    return (tick & 3) * 0.25F;
                }));
    }
}
