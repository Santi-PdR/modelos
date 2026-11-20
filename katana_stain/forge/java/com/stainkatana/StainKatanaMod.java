package com.stainkatana;

import com.stainkatana.katana.StainKatanaItem;
import com.stainkatana.katana.KatanaClientConfig;
import com.stainkatana.katana.KatanaNetwork;
import com.stainkatana.katana.KatanaParticles;
import com.stainkatana.katana.KatanaEffects;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.config.ModConfig;
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
    // Internal render-only prop; not placed in creative tabs or used for damage.
    public static final RegistryObject<Item> DAGGER = ITEMS.register("dagger_prop", () -> new Item(new Item.Properties().stacksTo(1)));
    public static final DeferredRegister<CreativeModeTab> TABS = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MOD_ID);
    public static final RegistryObject<CreativeModeTab> TAB = TABS.register("legados", () -> CreativeModeTab.builder()
            .title(Component.translatable("itemGroup.stainkatana.legados"))
            .icon(() -> new ItemStack(KATANA_STAIN.get()))
            .displayItems((parameters, output) -> output.accept(KATANA_STAIN.get())).build());

    public StainKatanaMod() {
        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, KatanaClientConfig.SPEC);
        GeckoLib.initialize();
        KatanaNetwork.init();
        IEventBus bus = FMLJavaModLoadingContext.get().getModEventBus();
        KatanaParticles.register(bus);
        KatanaEffects.register(bus);
        ITEMS.register(bus);
        TABS.register(bus);
    }
}
