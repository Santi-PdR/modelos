package com.capatest;

import com.capatest.item.CapaArmorMaterial;
import com.capatest.katana.StainKatanaItem;
import com.capatest.item.CapaDeteriorerItem;
import com.capatest.particle.CapaParticles;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.CreativeModeTabs;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.Rarity;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import software.bernie.geckolib.GeckoLib;

@Mod(CapaTestMod.MOD_ID)
public class CapaTestMod {
    public static final String MOD_ID = "capatest";
    public static final Logger LOGGER = LogManager.getLogger();

    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, MOD_ID);

    public static final RegistryObject<Item> CAPA_DETERIORER = ITEMS.register(
            "capa_deteriorer_evilsaiyan",
            () -> new CapaDeteriorerItem(
                    CapaArmorMaterial.INSTANCE,
                    ArmorItem.Type.CHESTPLATE,
                    // Épico + resistente al fuego: la última luz de Blight Star no se apaga.
                    new Item.Properties().stacksTo(1).rarity(Rarity.EPIC).fireResistant()
            )
    );

    public static final RegistryObject<Item> KATANA_STAIN = ITEMS.register(
            "katana_stain", StainKatanaItem::new);
    public static final DeferredRegister<CreativeModeTab> TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MOD_ID);
    public static final RegistryObject<CreativeModeTab> LEGADOS_TAB = TABS.register(
            "legados", () -> CreativeModeTab.builder()
                    .title(Component.translatable("itemGroup.capatest.legados"))
                    .icon(() -> new ItemStack(KATANA_STAIN.get()))
                    .displayItems((parameters, output) -> {
                        output.accept(CAPA_DETERIORER.get());
                        output.accept(KATANA_STAIN.get());
                    }).build());

    public CapaTestMod() {
        GeckoLib.initialize();

        IEventBus modBus = FMLJavaModLoadingContext.get().getModEventBus();
        ITEMS.register(modBus);
        TABS.register(modBus);
        CapaParticles.register(modBus);
        modBus.addListener(this::addCreative);

        initCuriosCompat(modBus);
    }

    private void addCreative(BuildCreativeModeTabContentsEvent event) {
        if (event.getTabKey() == CreativeModeTabs.COMBAT
                || event.getTabKey() == CreativeModeTabs.TOOLS_AND_UTILITIES) {
            event.accept(CAPA_DETERIORER);
            if (event.getTabKey() == CreativeModeTabs.COMBAT) event.accept(KATANA_STAIN);
        }
    }

    /**
     * Curios es una dependencia blanda: se carga por reflexión para que ninguna
     * clase que importe top.theillusivec4.* se verifique/cargue cuando el mod
     * no está instalado. Sin Curios la capa sigue funcionando en el slot de pecho.
     */
    private static void initCuriosCompat(IEventBus modBus) {
        if (!ModList.get().isLoaded("curios")) {
            return;
        }
        try {
            Class.forName("com.capatest.compat.CuriosCompat")
                    .getMethod("init", IEventBus.class)
                    .invoke(null, modBus);
        } catch (ReflectiveOperationException e) {
            LOGGER.error("No se pudo inicializar la compatibilidad con Curios", e);
        }
    }
}
