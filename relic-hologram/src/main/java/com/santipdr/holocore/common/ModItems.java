package com.santipdr.holocore.common;

import com.santipdr.holocore.HoloCore;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Rarity;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

/** Registro del unico item del mod. */
public final class ModItems {

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, HoloCore.MOD_ID);

    /**
     * Sin {@code GeoItem}: el item se dibuja como icono plano 2D en inventario y
     * mano. El modelo 3D se renderiza unicamente en el hombro via Curios.
     */
    public static final RegistryObject<Item> HOLOGRAPHIC_CORE = ITEMS.register(
            "holographic_core",
            () -> new HolographicCoreItem(new Item.Properties()
                    .stacksTo(1)
                    .rarity(Rarity.EPIC)));

    private ModItems() {
    }

    public static void register(IEventBus modBus) {
        ITEMS.register(modBus);
    }
}
