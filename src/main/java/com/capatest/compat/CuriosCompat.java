package com.capatest.compat;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.loading.FMLEnvironment;
import org.jetbrains.annotations.Nullable;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.type.capability.ICurioItem;
import top.theillusivec4.curios.api.type.inventory.ICurioStacksHandler;

import java.util.List;

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
    private static final List<String> BACK_SLOTS = List.of("back", "curios:back");

    private CuriosCompat() {}

    public record BackCape(String identifier, int index, boolean cosmetic, ItemStack stack) {
        public boolean matches(SlotContext context) {
            return index == context.index() && cosmetic == context.cosmetic()
                    && identifier.equals(context.identifier());
        }
    }

    public static void init(IEventBus modBus) {
        // El item se registra en RegisterEvent; CommonSetup ya lo tiene disponible.
        modBus.addListener(CuriosCompat::onCommonSetup);
        MinecraftForge.EVENT_BUS.addListener(CuriosCompat::onPlayerTick);

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
                return BACK_SLOTS.contains(slotContext.identifier());
            }
        });
    }

    /** Choose one displayed mantle, in slot order, using Curios 5's render rules. */
    public static @Nullable BackCape visibleBack(LivingEntity wearer) {
        if (wearer.getItemBySlot(EquipmentSlot.CHEST).is(CapaTestMod.CAPA_DETERIORER.get())) {
            return null;
        }
        var inventory = CuriosApi.getCuriosInventory(wearer).resolve().orElse(null);
        if (inventory == null) return null;
        for (String identifier : BACK_SLOTS) {
            ICurioStacksHandler back = inventory.getStacksHandler(identifier).orElse(null);
            if (back == null) continue;
            var renders = back.getRenders();
            for (int i = 0; i < back.getStacks().getSlots(); i++) {
                // A cosmetic overrides its functional stack, even if the
                // eye toggle hides that stack. A different cosmetic can
                // therefore hide a mantle without unequipping it.
                ItemStack shown = back.getCosmeticStacks().getStackInSlot(i);
                boolean cosmetic = !shown.isEmpty();
                if (!cosmetic && i < renders.size() && renders.get(i)) {
                    shown = back.getStacks().getStackInSlot(i);
                }
                if (shown.is(CapaTestMod.CAPA_DETERIORER.get())) {
                    return new BackCape(identifier, i, cosmetic, shown);
                }
            }
        }
        return null;
    }

    private static void onPlayerTick(TickEvent.PlayerTickEvent event) {
        Player player = event.player;
        if (event.phase != TickEvent.Phase.END || player.level().isClientSide
                || player.isSpectator() || !CapaDeteriorerItem.isAuraTick(player.tickCount)) {
            return;
        }
        // Curios doesn't call curioTick for cosmetic stacks. Resolve once
        // per emission window instead of ticking each equipped copy.
        BackCape displayed = visibleBack(player);
        if (displayed != null) {
            CapaDeteriorerItem.spawnAura(player.level(), player, displayed.stack());
        }
    }
}
