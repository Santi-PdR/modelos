package com.stainkatana.visual;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.KatanaNetwork;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.io.File;

/** Deterministic graphical smoke fixture. Only present in the CI client. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class VisualFixtureClient {
    private static int tick;
    private static String capture;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || mc.player.getMainHandItem().isEmpty()) return;
        tick++;
        switch (tick) {
            case 35 -> mc.setScreen(new InventoryScreen(mc.player));
            case 40 -> capture = "01_inventory.png";
            case 48 -> mc.setScreen(null);
            case 58 -> { mc.options.setCameraType(CameraType.FIRST_PERSON); capture = "02_first_person.png"; }
            case 70 -> { mc.options.setCameraType(CameraType.THIRD_PERSON_BACK); capture = "03_third_back.png"; }
            case 82 -> { mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT); capture = "04_third_front.png"; }
            case 95 -> mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
            case 105 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(1));
            case 111 -> capture = "05_slash_windup.png";
            case 114 -> capture = "06_slash_impact.png";
            case 150 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(2));
            case 155 -> capture = "07_ultimate_windup.png";
            case 159 -> capture = "08_ultimate_first.png";
            case 170 -> capture = "09_ultimate_second.png";
            case 205 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(0));
            case 213 -> capture = "10_paralysis.png";
            case 245 -> { System.out.println("STAIN_VISUAL_FIXTURE_FINISHED"); mc.stop(); }
            default -> { }
        }
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event) {
        if (event.phase != TickEvent.Phase.END || capture == null) return;
        String name = capture; capture = null;
        Minecraft mc = Minecraft.getInstance();
        try (var image = Screenshot.takeScreenshot(mc.getMainRenderTarget())) {
            File directory = new File(mc.gameDirectory, "stain-visual-test");
            if (!directory.isDirectory() && !directory.mkdirs()) throw new IllegalStateException("Cannot create screenshots folder");
            image.writeToFile(new File(directory, name));
            System.out.println("STAIN_VISUAL_CAPTURE " + name + " tick=" + tick);
        } catch (Exception e) { throw new IllegalStateException("Screenshot failed: " + name, e); }
    }
}
