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
        if (tick == 1) {
            var id = new net.minecraft.resources.ResourceLocation("bettercombat", "attack_animations/two_handed_slash_vertical_right.json");
            System.out.println("STAIN_FIXTURE_BETTERCOMBAT=" + net.minecraftforge.fml.ModList.get().isLoaded("bettercombat"));
            System.out.println("STAIN_FIXTURE_CLIP=" + (mc.getResourceManager().getResource(id).isPresent() ? "bettercombat" : "fallback"));
        }
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
            case 113 -> capture = "06a_slash_impact.png";
            case 114 -> capture = "06b_slash_impact.png";
            case 115 -> capture = "06c_slash_impact.png";
            case 116 -> capture = "06d_slash_impact.png";
            case 140 -> { mc.options.setCameraType(CameraType.FIRST_PERSON); KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(0)); }
            case 151 -> capture = "10_paralysis.png";
            case 153 -> capture = "11_blood_feedback.png";
            case 180 -> {
                mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
                if (net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) mc.options.keyAttack.setDown(true);
                else mc.player.swing(net.minecraft.world.InteractionHand.MAIN_HAND);
            }
            case 183 -> {
                if (!net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) {
                    if (!com.stainkatana.katana.client.KatanaAnimations.isPlaying(mc.player))
                        throw new IllegalStateException("Vanilla swing animation did not start");
                    System.out.println("STAIN_VANILLA_SWING_PLAYING");
                }
                capture = "12_normal_attack.png";
            }
            case 186 -> capture = "13_normal_attack.png";
            case 190 -> mc.options.keyAttack.setDown(false);
            case 220 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(2));
            case 230 -> capture = "07_ultimate_start.png";
            case 260 -> capture = "08_ultimate_2s.png";
            case 300 -> capture = "09_ultimate_4s.png";
            case 340 -> capture = "14_ultimate_6s.png";
            case 380 -> capture = "15_ultimate_8s.png";
            case 430 -> capture = "16_ultimate_end.png";
            case 445 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(0));
            case 479 -> {
                if (!com.stainkatana.katana.client.DaggerVisuals.hasFlights())
                    throw new IllegalStateException("Second successful Z did not launch dagger visuals");
                System.out.println("STAIN_DAGGERS_VERIFIED");
                capture = "17_dagger_1.png";
            }
            case 491 -> capture = "18_dagger_2.png";
            case 503 -> capture = "19_dagger_3.png";
            case 540 -> { System.out.println("STAIN_VISUAL_FIXTURE_FINISHED"); mc.stop(); }
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
