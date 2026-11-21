package com.santipdr.holocore;

import com.santipdr.holocore.common.ModCreativeTabs;
import com.santipdr.holocore.common.ModItems;
import com.santipdr.holocore.common.RelicServer;
import com.santipdr.holocore.config.RelicConfig;
import com.santipdr.holocore.network.RelicNetwork;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.ModLoadingContext;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.config.ModConfig;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import software.bernie.geckolib.GeckoLib;

/**
 * Punto de entrada de la reliquia cosmetica "Nucleo Holografico".
 *
 * <p>Depende de GeckoLib 4.8.1 y Curios API 5.14.1 (ambas obligatorias). El
 * modid es corto a proposito porque aparece en cada ruta de recurso.</p>
 */
@Mod(HoloCore.MOD_ID)
public class HoloCore {

    public static final String MOD_ID = "holocore";
    public static final Logger LOGGER = LogManager.getLogger(MOD_ID);

    public HoloCore() {
        // Obligatorio en GeckoLib 4: registra el reload listener del cliente y
        // el canal de red interno de la libreria. Sin esto no se cargan los
        // .geo.json ni las animaciones.
        GeckoLib.initialize();

        IEventBus modBus = FMLJavaModLoadingContext.get().getModEventBus();
        ModItems.register(modBus);
        ModCreativeTabs.register(modBus);

        ModLoadingContext.get().registerConfig(ModConfig.Type.CLIENT, RelicConfig.SPEC);

        RelicNetwork.register();
        // Los eventos de servidor (golpes, subidas de nivel, login) viven en
        // RelicServer; se registra la clase entera para no olvidar ninguno.
        MinecraftForge.EVENT_BUS.register(RelicServer.class);
    }
}
