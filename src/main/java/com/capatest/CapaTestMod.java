package com.capatest;

import com.capatest.item.CapaArmorMaterial;
import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.Item;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import software.bernie.geckolib.GeckoLib;

@Mod(CapaTestMod.MOD_ID)
public class CapaTestMod {
    public static final String MOD_ID = "capatest";

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, MOD_ID);

    public static final RegistryObject<Item> CAPA_DETERIORER = ITEMS.register(
            "capa_deteriorer_evilsaiyan",
            () -> new CapaDeteriorerItem(
                    CapaArmorMaterial.INSTANCE,
                    ArmorItem.Type.CHESTPLATE,
                    new Item.Properties().stacksTo(1)
            )
    );

    public CapaTestMod() {
        GeckoLib.initialize();

        IEventBus modBus = FMLJavaModLoadingContext.get().getModEventBus();
        ITEMS.register(modBus);
        modBus.addListener(this::addCreative);
    }

    private void addCreative(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == CreativeModeTabs.COMBAT) {
            event.accept(CAPA_DETERIORER);
        }
    }
}
