package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.compat.CuriosCompat;
import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeSparkPath;
import com.capatest.particle.CapaParticles;
import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.AccessibilityOnboardingScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Difficulty;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.level.GameRules;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.LevelSettings;
import net.minecraft.world.level.WorldDataConfiguration;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.WorldOptions;
import net.minecraft.world.level.levelgen.presets.WorldPresets;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.event.GeoRenderEvent;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.type.inventory.ICurioStacksHandler;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

/** Dev client only, in build/fx-smoke-run. No probes or extra mods in the distribution. */
@Mod.EventBusSubscriber(modid = CapaTestMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
public final class CapeFxSmoke {
    private static final String ATLAS = "assets/capatest/textures/item/armor/capa_deteriorer_evilsaiyan";
    private static final String FRAGMENT = "assets/capatest/shaders/core/cape_bloom.fsh";
    private static final String PACK_ID = "file/fx-probe";
    private static final String[] SCENES = {"pecho-dia", "ambos-noche-encantado", "espalda-con-elitros"};
    private static int step;
    private static long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(75);
    private static Path pack;
    private static CompletableFuture<?> pending;
    private static GlowProbe probe;
    private static BlockPos pane;
    private static int scene = -1;
    private static int framePasses;
    private static ItemStack rendered;
    private static int stableFrames;
    private static boolean captured;

    @SubscribeEvent
    public static void setup(FMLClientSetupEvent event) {
        event.enqueueWork(() -> {
            note("probe registrado (Curios=" + ModList.get().isLoaded("curios") + ")");
            resetDeadline();
            MinecraftForge.EVENT_BUS.addListener(CapeFxSmoke::tick);
            MinecraftForge.EVENT_BUS.addListener(CapeFxSmoke::afterArmor);
            MinecraftForge.EVENT_BUS.addListener(CapeFxSmoke::frame);
        });
    }

    private static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END || step < 0) return;
        Minecraft game = Minecraft.getInstance();
        try {
            if (System.nanoTime() - deadline > 0) {
                throw new AssertionError("stalled step " + step + ", scene " + scene + ", screen " + game.screen
                        + ", dayTime " + (game.level == null ? "no level" : game.level.getDayTime())
                        + ", pending " + (pending != null));
            }
            if (pending != null) {
                if (!pending.isDone()) return;
                pending.join();
                pending = null;
            }
            switch (step) {
                case 0 -> {
                    // A clean 1.20.1 install may stop at accessibility onboarding
                    // instead of TitleScreen. Neither screen needs interaction here.
                    if (game.getOverlay() != null || (!(game.screen instanceof TitleScreen)
                            && !(game.screen instanceof AccessibilityOnboardingScreen))) return;
                    expectMode(CapeBloom.Mode.HALO, "shader inicial compilado y enlazado");
                    probe = new GlowProbe();
                    probe.run(CapeBloom.Mode.HALO, true);
                    probe.run(CapeBloom.Mode.CORE, true);
                    probe.run(CapeBloom.Mode.OFF, false);
                    note("un fallo de halo baja a núcleo y uno de núcleo apaga sólo el pase; pila intacta");
                    pack = game.gameDirectory.toPath().resolve("resourcepacks/fx-probe");
                    write("pack.mcmeta", "{\"pack\":{\"description\":\"FX probe\",\"pack_format\":15}}");
                    write(ATLAS + "_halo.png", "not a PNG");
                    var repository = game.getResourcePackRepository();
                    List<String> selected = new ArrayList<>(repository.getSelectedIds());
                    repository.reload();
                    selected.add(PACK_ID);
                    repository.setSelected(selected);
                    check(repository.getSelectedIds().contains(PACK_ID), "test pack not found");
                    pending = game.reloadResourcePacks();
                }
                case 1 -> {
                    expectMode(CapeBloom.Mode.CORE, "PNG de halo corrupto: sólo núcleo");
                    probe.run(CapeBloom.Mode.CORE, false);
                    try (NativeImage wrongSize = new NativeImage(16, 16, true)) {
                        wrongSize.writeToFile(pack.resolve(ATLAS + "_halo.png"));
                    }
                    pending = game.reloadResourcePacks();
                }
                case 2 -> {
                    expectMode(CapeBloom.Mode.CORE, "atlas de halo de 16x16: sólo núcleo");
                    Files.delete(pack.resolve(ATLAS + "_halo.png"));
                    write(FRAGMENT, "#version 150\nthis is invalid GLSL\n");
                    pending = game.reloadResourcePacks();
                }
                case 3 -> {
                    expectMode(CapeBloom.Mode.CORE, "shader inválido: sólo núcleo");
                    Files.delete(pack.resolve(FRAGMENT));
                    write(ATLAS + "_glowmask.png", "not a PNG");
                    pending = game.reloadResourcePacks();
                }
                case 4 -> {
                    expectMode(CapeBloom.Mode.OFF, "núcleo corrupto: sólo paño base");
                    probe.run(CapeBloom.Mode.OFF, false);
                    Files.delete(pack.resolve(ATLAS + "_glowmask.png"));
                    System.setProperty("capa.sinHalo", "true");
                    pending = game.reloadResourcePacks();
                }
                case 5 -> {
                    expectMode(CapeBloom.Mode.CORE, "capa.sinHalo: sólo núcleo");
                    System.clearProperty("capa.sinHalo");
                    pending = game.reloadResourcePacks();
                }
                case 6 -> {
                    expectMode(CapeBloom.Mode.HALO, "recursos reparados: el halo vuelve en el mismo renderer");
                    probe.run(CapeBloom.Mode.HALO, false);
                    game.options.pauseOnLostFocus = false;
                    game.options.hideGui = true;
                    game.options.renderDistance().set(4);
                    game.options.simulationDistance().set(5);
                    game.options.framerateLimit().set(30);
                    game.options.setCameraType(CameraType.THIRD_PERSON_BACK);
                    GameRules rules = new GameRules();
                    rules.getRule(GameRules.RULE_DAYLIGHT).set(false, null);
                    rules.getRule(GameRules.RULE_DOMOBSPAWNING).set(false, null);
                    game.createWorldOpenFlows().createFreshLevel("fx-smoke", new LevelSettings(
                                    "FX smoke", GameType.CREATIVE, false, Difficulty.PEACEFUL, true,
                                    rules, WorldDataConfiguration.DEFAULT), new WorldOptions(27, false, false),
                            registries -> registries.registryOrThrow(Registries.WORLD_PRESET)
                                    .getHolderOrThrow(WorldPresets.FLAT).value().createWorldDimensions());
                }
                case 7 -> {
                    if (game.player == null || game.screen != null || game.getSingleplayerServer() == null) return;
                    var server = game.getSingleplayerServer();
                    var uuid = game.player.getUUID();
                    pending = server.submit(() -> {
                        ServerPlayer player = server.getPlayerList().getPlayer(uuid);
                        check(player != null, "server player missing");
                        testSlots(player);
                        pane = testBirth(player);
                    });
                }
                case 8 -> {
                    if (!game.level.getBlockState(pane).is(Blocks.GLASS_PANE)) return;
                    testFlight(game);
                    equipScene(game, 0);
                }
                case 9 -> {
                    if (!captured) return;
                    if (scene + 1 < SCENES.length) {
                        equipScene(game, scene + 1);
                        return;
                    }
                    note("PASS: recarga, oclusión y equipo en cliente Forge");
                    game.stop();
                }
                default -> { return; }
            }
            step++;
            resetDeadline();
        } catch (Exception | AssertionError error) {
            fail(game, error);
        }
    }

    private static void testSlots(ServerPlayer player) {
        ICurioStacksHandler back = backOf(player);
        ItemStack functional = mantle(), cosmetic = mantle();
        back.getStacks().setStackInSlot(0, functional);
        check(CuriosCompat.visibleBack(player).stack() == functional, "functional back not selected");
        back.getRenders().set(0, false);
        check(CuriosCompat.visibleBack(player) == null, "hidden mantle still selected");
        back.getRenders().set(0, true);
        back.getCosmeticStacks().setStackInSlot(0, new ItemStack(Items.PAPER));
        check(CuriosCompat.visibleBack(player) == null, "replaced mantle still selected");
        back.getCosmeticStacks().setStackInSlot(0, cosmetic);
        back.getRenders().set(0, false);
        var shown = CuriosCompat.visibleBack(player);
        check(shown.stack() == cosmetic && shown.matches(new SlotContext("back", player, 0, true, false)),
                "cosmetic not selected with functional slot hidden");
        player.setItemSlot(EquipmentSlot.CHEST, mantle());
        check(CuriosCompat.visibleBack(player) == null, "chest must win over cosmetic back");
        back.getCosmeticStacks().setStackInSlot(0, ItemStack.EMPTY);
        back.getRenders().set(0, true);
        back.getStacks().setStackInSlot(0, ItemStack.EMPTY);
        player.setItemSlot(EquipmentSlot.CHEST, ItemStack.EMPTY);
        note("Curios 5.14.1: visible, oculto, reemplazado, cosmético y prioridad de pecho");
    }

    private static BlockPos testBirth(ServerPlayer player) {
        var level = player.serverLevel();
        BlockPos panel = player.blockPosition().offset(3, 1, 0);
        level.setBlockAndUpdate(panel, Blocks.GLASS_PANE.defaultBlockState());
        BlockPos wall = panel.offset(0, 0, 2);
        level.setBlockAndUpdate(wall, Blocks.STONE.defaultBlockState());
        Vec3 start = Vec3.atLowerCornerOf(panel).add(.12, .36, .50);
        ArmorStand wearer = new ArmorStand(level, start.x, start.y, start.z);
        check(CapeSparkPath.clearBirth(level, wearer, start.add(.22, 0, 0)), "clear ray before pane blocked");
        check(!CapeSparkPath.clearBirth(level, wearer, start.add(.38, 0, 0)), "ray ended inside pane");
        check(!CapeSparkPath.clearBirth(level, wearer, start.add(.80, 0, 0)), "ray crossed thin pane");
        wearer.setPos(wall.getX() - .31, start.y, wall.getZ() + .5);
        check(!CapeSparkPath.clearBirth(level, wearer, new Vec3(wall.getX() + .2, start.y, wall.getZ() + .5)),
                "ray entered full block");
        note("nacimiento en aire y rechazo de panel fino o muro sólido");
        return panel;
    }

    private static void testFlight(Minecraft game) {
        for (int dz = 0; dz <= 1; dz++) {
            double x = pane.getX() + .12;
            Particle particle = game.particleEngine.createParticle(CapaParticles.CAPA_SPARK.get(),
                    x, pane.getY() + .36, pane.getZ() + .5 + dz, .04, .007, 0);
            check(particle instanceof CapaSparkParticle, "custom provider absent");
            for (int t = 0; t < 23; t++) particle.tick();
            double travel = particle.getPos().x - x;
            particle.remove();
            check(dz == 0 ? travel < .32 && travel > .15 : travel > .48,
                    "flight collision/impulse: dz=" + dz + ", travel=" + travel);
        }
        note("brasa real frenada por el panel; impulso libre intacto");
    }

    private static void resetDeadline() {
        deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(75);
    }

    private static void equipScene(Minecraft game, int index) {
        resetDeadline();
        scene = index;
        stableFrames = 0;
        captured = false;
        var server = game.getSingleplayerServer();
        var uuid = game.player.getUUID();
        pending = server.submit(() -> {
            ServerPlayer player = server.getPlayerList().getPlayer(uuid);
            player.serverLevel().setDayTime(index == 0 ? 6000 : 18000);
            ItemStack chest = index == 2 ? new ItemStack(Items.ELYTRA) : mantle();
            if (index == 1) chest.enchant(Enchantments.UNBREAKING, 1);
            player.setItemSlot(EquipmentSlot.CHEST, chest);
            backOf(player).getStacks().setStackInSlot(0, index == 0 ? ItemStack.EMPTY : mantle());
        });
    }

    private static void afterArmor(GeoRenderEvent.Armor.Post event) {
        if (scene < 0 || !(event.getRenderer() instanceof CapaArmorRenderer renderer)
                || renderer.getCurrentEntity() != Minecraft.getInstance().player) return;
        framePasses++;
        rendered = renderer.getCurrentStack();
    }

    private static void frame(TickEvent.RenderTickEvent event) {
        if (event.phase == TickEvent.Phase.START) {
            framePasses = 0;
            rendered = ItemStack.EMPTY;
            return;
        }
        if (scene < 0 || captured || pending != null) return;
        Minecraft game = Minecraft.getInstance();
        if (game.player == null || game.screen != null || !game.level.isLoaded(pane)
                || game.level.getDayTime() != (scene == 0 ? 6000 : 18000)) return;
        ItemStack chest = game.player.getItemBySlot(EquipmentSlot.CHEST);
        ItemStack back = backOf(game.player).getStacks().getStackInSlot(0);
        if (back.isEmpty() != (scene == 0) || (scene == 1 && !chest.hasFoil())
                || (scene == 2 ? !chest.is(Items.ELYTRA) : !chest.is(CapaTestMod.CAPA_DETERIORER.get()))) return;
        try {
            check(framePasses == 1 && rendered == (scene == 2 ? back : chest),
                    SCENES[scene] + ": incorrect worn draw count " + framePasses);
            if (++stableFrames < 18) return;
            Path shots = game.gameDirectory.toPath().resolve("fx-shots");
            Files.createDirectories(shots);
            try (NativeImage image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                image.writeToFile(shots.resolve(SCENES[scene] + ".png"));
            }
            note(SCENES[scene] + ": una sola capa en tercera persona trasera");
            captured = true;
        } catch (Exception | AssertionError error) {
            fail(game, error);
        }
    }

    private static ICurioStacksHandler backOf(net.minecraft.world.entity.LivingEntity player) {
        return CuriosApi.getCuriosInventory(player).resolve().orElseThrow().getStacksHandler("back").orElseThrow();
    }

    private static ItemStack mantle() {
        return new ItemStack(CapaTestMod.CAPA_DETERIORER.get());
    }

    private static void write(String relative, String contents) throws IOException {
        Path file = pack.resolve(relative);
        Files.createDirectories(file.getParent());
        Files.writeString(file, contents);
    }

    private static void expectMode(CapeBloom.Mode expected, String label) {
        check(CapeBloom.availableMode() == expected, label + ": got " + CapeBloom.availableMode());
        note(label);
    }

    private static void check(boolean test, String message) {
        if (!test) throw new AssertionError(message);
    }

    private static void note(String message) {
        CapaTestMod.LOGGER.info("FX smoke: {}", message);
    }

    private static void fail(Minecraft game, Throwable error) {
        step = -1;
        scene = -1;
        CapaTestMod.LOGGER.error("FX smoke: FAIL at client tick", error);
        game.stop();
    }

    private static final class GlowProbe extends CapaArmorRenderer {
        private final CapaGlowLayer layer = new CapaGlowLayer(this);
        private final CapaDeteriorerItem item = (CapaDeteriorerItem) mantle().getItem();
        private final PoseStack caller = new PoseStack();
        private final BufferBuilder sink = new BufferBuilder(256);
        private RenderType submitted;
        private boolean failing;

        GlowProbe() {
            caller.translate(.25, -.5, 1.75);
            caller.mulPose(Axis.XP.rotationDegrees(29));
        }

        void run(CapeBloom.Mode expected, boolean fail) {
            this.failing = fail;
            this.submitted = null;
            var before = new Matrix4f(caller.last().pose());
            var normal = new Matrix3f(caller.last().normal());
            BakedGeoModel model = getGeoModel().getBakedModel(getGeoModel().getModelResource(item, this));
            layer.render(caller, item, model, null, type -> sink, sink, 0, 0, 0);
            check(caller.clear() && caller.last().pose().equals(before) && caller.last().normal().equals(normal),
                    "glow mutated the caller's stack");
            check(submitted == (expected == CapeBloom.Mode.OFF ? null : CapeBloom.wornLight(expected)),
                    "unexpected light pass: expected " + expected + ", got " + submitted);
        }

        @Override
        public void reRender(BakedGeoModel model, PoseStack stack, MultiBufferSource buffers, CapaDeteriorerItem item,
                             RenderType type, VertexConsumer buffer, float partialTick, int light, int overlay,
                             float r, float g, float b, float a) {
            submitted = type;
            check(stack.last().pose().equals(caller.last().pose()) && stack.last().normal().equals(caller.last().normal()),
                    "emission transform differs from opaque transform");
            stack.pushPose();
            stack.translate(0, -2, 0);
            if (failing) throw new IllegalStateException("intentional FX smoke failure after GeckoLib push");
            stack.popPose();
        }
    }
}
