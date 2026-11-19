package com.stainkatana;

import com.stainkatana.katana.StainKatanaItem;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import software.bernie.geckolib.GeckoLib;

/** Punto de entrada exclusivo de la prueba: no registra ni carga la capa. */
@Mod(StainKatanaMod.MOD_ID)
public class StainKatanaMod {
    public static final String MOD_ID = "stainkatana";
    public static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MOD_ID);
    public static final RegistryObject<Item> KATANA_STAIN = ITEMS.register("katana_stain", StainKatanaItem::new);
    public static final DeferredRegister<CreativeModeTab> TABS = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MOD_ID);
    public static final RegistryObject<CreativeModeTab> TAB = TABS.register("legados", () -> CreativeModeTab.builder()
            .title(Component.translatable("itemGroup.stainkatana.legados"))
            .icon(() -> new ItemStack(KATANA_STAIN.get()))
            .displayItems((parameters, output) -> output.accept(KATANA_STAIN.get())).build());

    public StainKatanaMod() {
        GeckoLib.initialize();
        IEventBus bus = FMLJavaModLoadingContext.get().getModEventBus();
        ITEMS.register(bus);
        TABS.register(bus);
        bus.addListener(this::addCreative);
    }
    private void addCreative(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == CreativeModeTabs.COMBAT) event.accept(KATANA_STAIN);
    }
}
