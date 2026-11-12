package dev.holorelic;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.config.ModConfig;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

@Mod(HoloRelic.ID)
public final class HoloRelic {
    public static final String ID = "holorelic";
    private static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, ID);
    public static final RegistryObject<Item> CORE = ITEMS.register("holographic_core",
            () -> new Item(new Item.Properties().stacksTo(1)));

    public HoloRelic() {
        var bus = FMLJavaModLoadingContext.get().getModEventBus();
        ITEMS.register(bus);
        bus.addListener(this::creative);
        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, RelicConfig.CLIENT);
        ModLoadingContext.get().registerConfig(ModConfig.Type.SERVER, RelicConfig.SERVER);
        RelicNetwork.register();
    }

    private void creative(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == CreativeModeTabs.TOOLS_AND_UTILITIES) event.accept(CORE);
    }
}
