package com.capatest.compat;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.loading.FMLEnvironment;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.type.capability.ICurioItem;

/**
 * Integración OPCIONAL con Curios. Esta clase sólo se carga por reflexión desde
 * CapaTestMod cuando ModList detecta "curios", por lo que el mod sigue
 * funcionando con Forge + GeckoLib a secas.
 *
 * Curios usa el validador curios:tag, así que además del registro hacen falta:
 *   data/curios/tags/items/back.json          -> tag curios:back
 *   data/capatest/curios/entities/player.json -> concede el slot back al jugador
 */
public final class CuriosCompat {
    private CuriosCompat() {
    }

    public static void init(IEventBus modBus) {
        // El item se registra en RegisterEvent; CommonSetup ya lo tiene disponible.
        modBus.addListener(CuriosCompat::onCommonSetup);

        if (FMLEnvironment.dist == Dist.CLIENT) {
            // Reflexión también aquí: las clases client-only no deben resolverse
            // en un servidor dedicado, aunque el branch esté apagado.
            try {
                Class.forName("com.capatest.compat.CuriosClientCompat")
                        .getMethod("register", IEventBus.class)
                        .invoke(null, modBus);
            } catch (ReflectiveOperationException e) {
                CapaTestMod.LOGGER.error("No se pudo registrar el renderer de Curios", e);
            }
        }
    }

    private static void onCommonSetup(FMLCommonSetupEvent event) {
        CuriosApi.registerCurio(CapaTestMod.CAPA_DETERIORER.get(), new ICurioItem() {
            @Override
            public boolean canEquip(SlotContext slotContext, ItemStack stack) {
                String id = slotContext.identifier();
                return "back".equals(id) || "curios:back".equals(id);
            }

            @Override
            public void curioTick(SlotContext slotContext, ItemStack stack) {
                if (slotContext.entity() instanceof Player player) {
                    CapaDeteriorerItem.spawnAura(player.level(), player);
                }
            }
        });
    }
}
