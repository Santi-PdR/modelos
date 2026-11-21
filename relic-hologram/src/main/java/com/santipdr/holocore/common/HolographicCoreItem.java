package com.santipdr.holocore.common;

import java.util.List;
import javax.annotation.Nullable;
import net.minecraft.ChatFormatting;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.type.capability.ICurioItem;

/**
 * La reliquia. El unico estado persistente es {@link #ACTIVE_TAG}, que se guarda
 * en el NBT del propio ItemStack (asi sobrevive a guardar/cargar el mundo y a
 * cambiar de dimension) y se replica a los clientes por paquete, no por el
 * inventario de Curios: mutar NBT en el sitio no siempre marca el slot como
 * modificado y el brillo del cliente se quedaria desincronizado.
 */
public class HolographicCoreItem extends Item implements ICurioItem {

    public static final String ACTIVE_TAG = "Active";

    public HolographicCoreItem(Properties properties) {
        super(properties);
    }

    /** Activa por defecto: una reliquia recien crafteada ya brilla. */
    public static boolean isActive(ItemStack stack) {
        CompoundTag tag = stack.getTag();
        return tag == null || !tag.contains(ACTIVE_TAG) || tag.getBoolean(ACTIVE_TAG);
    }

    public static void setActive(ItemStack stack, boolean active) {
        stack.getOrCreateTag().putBoolean(ACTIVE_TAG, active);
    }

    /** Maximo una unidad equipada y sin restricciones de portador. */
    @Override
    public boolean canEquip(SlotContext slotContext, ItemStack stack) {
        return true;
    }

    @Override
    public void onEquip(SlotContext slotContext, ItemStack previousStack, ItemStack stack) {
        if (slotContext.entity() instanceof ServerPlayer player) {
            RelicServer.syncFromStack(player, stack);
        }
    }

    @Override
    public void onUnequip(SlotContext slotContext, ItemStack newStack, ItemStack stack) {
        if (slotContext.entity() instanceof ServerPlayer player) {
            RelicServer.syncFromStack(player, ItemStack.EMPTY);
        }
    }

    /**
     * El estado de animacion no se calcula aqui: el renderer de cliente deduce
     * combate/alerta/glitch de lo que ya esta sincronizado (hurtTime, swing,
     * entidades cercanas). Evita paquetes por tick.
     */
    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level,
                                List<Component> tooltip, TooltipFlag flag) {
        tooltip.add(Component.translatable("tooltip.holocore.state",
                Component.translatable(isActive(stack)
                        ? "tooltip.holocore.state.active"
                        : "tooltip.holocore.state.dormant"))
                .withStyle(ChatFormatting.AQUA));
        tooltip.add(Component.translatable("tooltip.holocore.hint")
                .withStyle(ChatFormatting.DARK_AQUA));
    }
}
