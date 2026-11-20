package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.compat.CuriosCompat;
import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeSparkPath;
import com.capatest.particle.CapaParticles;
import com.mojang.blaze3d.pipeline.TextureTarget;
import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.blaze3d.vertex.VertexSorting;
import com.mojang.math.Axis;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.AccessibilityOnboardingScreen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.protocol.game.ServerboundPlayerCommandPacket;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.Difficulty;
import net.minecraft.world.entity.Entity;
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
import net.minecraftforge.client.event.RegisterParticleProvidersEvent;
import net.minecraftforge.client.event.RenderPlayerEvent;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.GeckoLibCache;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.cache.object.GeoCube;
import software.bernie.geckolib.event.GeoRenderEvent;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.type.inventory.ICurioStacksHandler;

import java.io.IOException;
import java.lang.reflect.Field;
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
    private static final int HOTBAR_SLOT = 4, HOTBAR_SAMPLES = 34, HOTBAR_QUIET_TICKS = 52;
    // A real vanilla idle pose near zero arm pitch (sin(94*.067) ≈ 0).
    // Use the same phase for registered stills, not for any motion test.
    private static final int STILL_AGE = 94;
    // Negative controls run on the actual F5 camera. The older seating
    // stroke and the six v1.67.10 lining cubes are used only in this client.
    private static final Field SEATING = field(CapaArmorRenderer.class, "seating");
    private static final Field PLATE_FIT = field(CapaArmorRenderer.class, "plateFit");
    private static final Field TORSO_FIT = field(CapaArmorRenderer.class, "torsoFit");
    private static final Field BACKING = field(CapaArmorRenderer.class, "backing");
    private static final ResourceLocation LINING_V16710 = new ResourceLocation(CapaTestMod.MOD_ID, "geo/test/join_v16710.geo.json");
    private record Lining(GeoBone bone, List<GeoCube> cubes) {
        void restore() {
            bone.getCubes().clear();
            bone.getCubes().addAll(cubes);
        }
    }
    private static List<Lining> savedLining = List.of();
    private static final Field SKIN_MODEL = field(PlayerInfo.class, "skinModel");
    private static String savedModel;

    private static Field field(Class<?> owner, String name) {
        try {
            Field field = owner.getDeclaredField(name);
            field.setAccessible(true);
            return field;
        } catch (ReflectiveOperationException e) {
            throw new ExceptionInInitializerError(e);
        }
    }

    private enum Scene {
        CHEST("pecho-dia", 6000), NIGHT("pecho-noche", 18000), LAMP("pecho-noche-con-luz", 18000),
        BOTH("ambos-noche-encantado", 18000),
        TOP_BARE("cenital-sin-manto", 6000), TOP_OLD_JOIN("cenital-v16710", 6000),
        TOP_CHEST("cenital-pecho", 6000), TOP_BACK("cenital-curios", 6000),
        TURN_BARE("cenital-giro-sin-manto", 6000), TURN_CHEST("cenital-giro-pecho", 6000), TURN_BACK("cenital-giro-curios", 6000),
        OBLIQUE_BARE("oblicua-sin-manto", 6000), OBLIQUE_UNLINED("oblicua-sin-union", 6000),
        OBLIQUE_OLD_JOIN("oblicua-v16710", 6000), OBLIQUE_CHEST("oblicua-pecho", 6000), OBLIQUE_BACK("oblicua-curios", 6000),
        SIDE_BARE("perfil-sin-manto", 6000), SIDE_UNLINED("perfil-sin-union", 6000), SIDE_CHEST("perfil-pecho", 6000), SIDE_BACK("perfil-curios", 6000),
        FIT_BARE("ajuste-sin-manto", 6000), FIT_PREVIOUS("ajuste-v1678", 6000),
        FIT_CHEST("ajuste-pecho", 6000), FIT_BACK("ajuste-curios", 6000),
        FIT_SLIM_BARE("ajuste-fino-sin-manto", 6000), FIT_SLIM_PREVIOUS("ajuste-fino-v1678", 6000),
        FIT_SLIM_CHEST("ajuste-fino-pecho", 6000), FIT_SLIM_BACK("ajuste-fino-curios", 6000),
        MID_BARE("ajuste-medio-sin-manto", 6000), MID_PREVIOUS("ajuste-medio-v1679", 6000),
        MID_OLD_JOIN("ajuste-medio-v16710", 6000),
        MID_CHEST("ajuste-medio-pecho", 6000), MID_BACK("ajuste-medio-curios", 6000),
        PLATES_BARE("hombreras-sin-manto", 6000), PLATES_HIDDEN("hombreras-sin-placas", 6000),
        PLATES_PREVIOUS("hombreras-v16711", 6000),
        PLATES_CHEST("hombreras-pecho", 6000), PLATES_BACK("hombreras-curios", 6000),
        HISTORY_DIAG_BARE("historia-diagonal-sin-manto", 6000),
        HISTORY_DIAG_OLD_CHEST("historia-diagonal-pecho-v1280", 6000), HISTORY_DIAG_V16712_CHEST("historia-diagonal-pecho-v16712", 6000),
        HISTORY_DIAG_CHEST("historia-diagonal-pecho", 6000),
        HISTORY_DIAG_OLD_BACK("historia-diagonal-curios-v1280", 6000), HISTORY_DIAG_V16712_BACK("historia-diagonal-curios-v16712", 6000),
        HISTORY_DIAG_BACK("historia-diagonal-curios", 6000),
        HISTORY_MIRROR_BARE("historia-espejo-sin-manto", 6000),
        HISTORY_MIRROR_OLD_CHEST("historia-espejo-pecho-v1280", 6000), HISTORY_MIRROR_V16712_CHEST("historia-espejo-pecho-v16712", 6000),
        HISTORY_MIRROR_CHEST("historia-espejo-pecho", 6000),
        HISTORY_MIRROR_OLD_BACK("historia-espejo-curios-v1280", 6000), HISTORY_MIRROR_V16712_BACK("historia-espejo-curios-v16712", 6000),
        HISTORY_MIRROR_BACK("historia-espejo-curios", 6000),
        HISTORY_TOP_BARE("historia-cenital-sin-manto", 6000),
        HISTORY_TOP_OLD_CHEST("historia-cenital-pecho-v1280", 6000), HISTORY_TOP_V16712_CHEST("historia-cenital-pecho-v16712", 6000),
        HISTORY_TOP_CHEST("historia-cenital-pecho", 6000),
        HISTORY_TOP_OLD_BACK("historia-cenital-curios-v1280", 6000), HISTORY_TOP_V16712_BACK("historia-cenital-curios-v16712", 6000),
        HISTORY_TOP_BACK("historia-cenital-curios", 6000),
        LOOK_CHEST("mirada-pecho", 6000), LOOK_BACK("mirada-curios", 6000),
        WALK_CHEST("paso-pecho", 6000), WALK_BACK("paso-curios", 6000),
        HOTBAR_BARE("hotbar-vacia", 6000), HOTBAR("hotbar", 6000),
        STRAFE_LEFT("traslacion-izquierda", 18000), STRAFE_RIGHT("traslacion-derecha", 18000),
        WINGS("espalda-con-elitros", 18000),
        GLIDE("planeo-real", 6000), WADE("de-pie-en-agua", 6000), SWIM("nado-horizontal", 6000),
        SWIM_EXIT("fin-del-nado", 6000);

        final String file;
        final long dayTime;

        Scene(String file, long dayTime) {
            this.file = file;
            this.dayTime = dayTime;
        }

        boolean hotbar() { return this == HOTBAR_BARE || this == HOTBAR; }
        boolean elytra() { return this == WINGS || this == GLIDE; }
        boolean usesBack() { return this == TOP_BACK || this == TURN_BACK || this == OBLIQUE_BACK || this == SIDE_BACK || this == FIT_BACK || this == FIT_SLIM_BACK || this == MID_BACK || this == PLATES_BACK || this == LOOK_BACK || this == WALK_BACK || homeCompare() && file.contains("-curios") || elytra(); }
        boolean hasBack() { return this == BOTH || usesBack(); }
        boolean bare() { return this == TOP_BARE || this == TURN_BARE || this == OBLIQUE_BARE || this == SIDE_BARE || this == FIT_BARE || this == FIT_SLIM_BARE || this == MID_BARE || this == PLATES_BARE || homeCompare() && file.endsWith("sin-manto"); }
        boolean overhead() { return this == TOP_BARE || this == TOP_OLD_JOIN || this == TOP_CHEST || this == TOP_BACK || turned(); }
        boolean oldJoin() { return this == TOP_OLD_JOIN || this == OBLIQUE_OLD_JOIN || this == MID_OLD_JOIN; }
        boolean binding() { return oldJoin() || this == MID_CHEST || this == MID_BACK || this == TOP_CHEST
                || this == TOP_BACK || this == OBLIQUE_CHEST || this == OBLIQUE_BACK; }
        boolean turned() { return this == TURN_BARE || this == TURN_CHEST || this == TURN_BACK; }
        boolean unlined() { return this == OBLIQUE_UNLINED || this == SIDE_UNLINED; }
        boolean oblique() { return this == OBLIQUE_BARE || this == OBLIQUE_UNLINED || this == OBLIQUE_OLD_JOIN
                || this == OBLIQUE_CHEST || this == OBLIQUE_BACK; }
        boolean profile() { return this == SIDE_BARE || this == SIDE_UNLINED || this == SIDE_CHEST || this == SIDE_BACK; }
        boolean upperBack() { return oblique() || profile(); }
        boolean fit() { return ordinal() >= FIT_BARE.ordinal() && ordinal() <= MID_BACK.ordinal(); }
        boolean previousFit() { return this == FIT_PREVIOUS || this == FIT_SLIM_PREVIOUS || this == MID_PREVIOUS; }
        boolean slimFit() { return fit() && ordinal() >= FIT_SLIM_BARE.ordinal(); }
        boolean midFit() { return fit() && ordinal() >= MID_BARE.ordinal(); }
        boolean plates() { return ordinal() >= PLATES_BARE.ordinal() && ordinal() <= PLATES_BACK.ordinal(); }
        boolean homeCompare() { return ordinal() >= HISTORY_DIAG_BARE.ordinal() && ordinal() <= HISTORY_TOP_BACK.ordinal(); }
        boolean oldRig() { return homeCompare() && file.endsWith("-v1280"); }
        boolean publishedFit() { return homeCompare() && file.endsWith("-v16712"); }
        boolean sweep() { return this == LOOK_CHEST || this == LOOK_BACK; }
        boolean walk() { return this == WALK_CHEST || this == WALK_BACK; }
        boolean stillComparison() { return overhead() || upperBack() || fit() || plates() || homeCompare(); }
        boolean fixedCamera() { return stillComparison() || sweep(); }
        float yaw() {
            if (homeCompare()) return file.startsWith("historia-diagonal") ? 43 : file.startsWith("historia-espejo") ? -48 : 0;
            return fit() ? 3 : profile() ? 76 : turned() || oblique() || hotbar() ? 43 : 0;
        }
        float pitch() {
            if (homeCompare()) return file.startsWith("historia-diagonal") ? 58 : file.startsWith("historia-espejo") ? 48 : 89.5F;
            return plates() ? 89.5F : midFit() ? 58 : fit() ? 76 : profile() ? 21 : oblique() ? 58 : turned() || hotbar() ? 86 : 89;
        }
        boolean inspectBirths() { return this == GLIDE || this == WADE || this == SWIM; }
        boolean compareLight() { return this == CHEST || this == NIGHT || this == LAMP; }
        boolean strafe() { return this == STRAFE_LEFT || this == STRAFE_RIGHT; }
    }

    private static int step;
    private static long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(75);
    private static Path pack;
    private static CompletableFuture<?> pending;
    private static GlowProbe probe;
    private static BlockPos pane;
    private static BlockPos lamp;
    private static Scene scene;
    private static int framePasses;
    private static int frameLight;
    private static float framePartialTick;
    private static double frameTopDegrees, frameSeating, framePlateFit;
    private static CapeLookSweep lookSweep;
    private static CapeLookSweep.Draw seatDraw;
    private static CapeWalkProbe.Route walkRoute;
    private static CapeWalkProbe.Draw walkDraw;
    private static CapePlateProbe platesDraw;
    private static CapeHistoricFitProbe.Draw historyDraw;
    private static ItemStack rendered;
    private static Matrix4f playerPose, armorPose, upperBackProjection;
    private static Entity stillPlayer;
    private static int liveAge;
    private static int stableFrames;
    private static int observedBirths;
    private static boolean captured;
    private static int hotbarCount, lastHotbarTick, hotbarUnequippedTick;

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void observeParticles(RegisterParticleProvidersEvent event) {
        // Wrap the real provider only in the dev client to observe delivered births.
        event.registerSpriteSet(CapaParticles.CAPA_SPARK.get(), sprites -> {
            var provider = new CapaSparkParticle.Provider(sprites);
            return (type, level, x, y, z, dx, dy, dz) -> {
                var player = Minecraft.getInstance().player;
                if (scene != null && scene.inspectBirths() && pending == null && stableFrames >= 2
                        && player != null && player.distanceToSqr(x, y, z) < 9) {
                    double height = y - player.getY();
                    // The old short-hitbox rule would put these under .1 blocks.
                    if (scene == Scene.WADE ? height < .28 : height > .45) observedBirths++;
                }
                return provider.createParticle(type, level, x, y, z, dx, dy, dz);
            };
        });
    }

    @SubscribeEvent
    public static void setup(FMLClientSetupEvent event) {
        event.enqueueWork(() -> {
            note("probe registrado (Curios=" + ModList.get().isLoaded("curios") + ")");
            resetDeadline();
            MinecraftForge.EVENT_BUS.addListener(CapeFxSmoke::tick);
            MinecraftForge.EVENT_BUS.addListener(CapeFxSmoke::beforePlayer);
            MinecraftForge.EVENT_BUS.addListener(CapeFxSmoke::afterPlayer);
            MinecraftForge.EVENT_BUS.addListener(CapeFxSmoke::beforeArmor);
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
                        + ", pending " + (pending != null) + ", births " + observedBirths
                        + ", pose " + (game.player == null ? "no player" : game.player.getPose())
                        + ", swim " + (game.player == null ? 0 : game.player.getSwimAmount(1))
                        + ", stable frames " + stableFrames);
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
                    checkHaloBatch(game);
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
                    equipScene(game, Scene.CHEST);
                }
                case 9 -> {
                    driveScene(game);
                    if (!captured) return;
                    if (scene != Scene.SWIM_EXIT) {
                        Scene next = Scene.values()[scene.ordinal() + 1];
                        if (next.homeCompare() && !CapeHistoricFitProbe.ENABLED) next = Scene.LOOK_CHEST;
                        equipScene(game, next);
                        return;
                    }
                    if (game.player.getSwimAmount(1) > 0) return;
                    check(!CapaDeteriorerItem.auraFrame(game.player).posed(), "swim frame persisted after blend");
                    note("PASS: recarga, luz, oclusión, equipo, recorrido de mirada, hotbar, paso lateral, alas, planeo y nado en Forge");
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
        // The same-height ray used to start ABOVE this wall for a tilted
        // mantle with a high birth. The new ray must start inside the hitbox.
        wearer.setPos(wall.getX() - .3, wall.getY() - 1.4, wall.getZ() + .5);
        Vec3 high = new Vec3(wall.getX() + .8, wall.getY() + 1.1, wall.getZ() + .5);
        check(wearer.getBoundingBox().maxY < wall.getY() + 1, "high-birth fixture is not over the hitbox");
        check(!CapeSparkPath.clearBirth(level, wearer, high), "high birth skipped the top of the wall");
        wearer.setPos(wearer.getX(), wearer.getY(), wearer.getZ() + 1);
        check(CapeSparkPath.clearBirth(level, wearer, high.add(0, 0, 1)), "high birth in open air was rejected");
        note("nacimiento libre y rechazo de panel o muro, también por encima de la hitbox");
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

    private static void equipScene(Minecraft game, Scene next) {
        resetDeadline();
        scene = next;
        walkRoute = next.walk() ? new CapeWalkProbe.Route() : null;
        if (next == Scene.WALK_CHEST) game.options.framerateLimit().set(60);
        if (next == Scene.HOTBAR_BARE) game.options.framerateLimit().set(30);
        lookSweep = next.sweep() ? new CapeLookSweep() : null;
        stableFrames = observedBirths = 0;
        captured = false;
        if (next == Scene.TOP_BARE) game.options.fov().set(34);
        if (next == Scene.FIT_BARE || next == Scene.HISTORY_DIAG_BARE) game.options.fov().set(42);
        if (next == Scene.FIT_BARE || next == Scene.FIT_SLIM_BARE || next == Scene.HOTBAR_BARE) {
            // Select the actual vanilla player renderer by model, without
            // changing skin pixels, account, equipment, or the pose.
            var info = game.player.connection.getPlayerInfo(game.player.getUUID());
            check(info != null, "local player profile missing");
            try {
                if (next == Scene.FIT_BARE) savedModel = (String) SKIN_MODEL.get(info);
                SKIN_MODEL.set(info, next == Scene.HOTBAR_BARE ? savedModel : next.slimFit() ? "slim" : "default");
            } catch (IllegalAccessException e) {
                throw new AssertionError(e);
            }
        }
        if (next.hotbar()) {
            game.options.guiScale().set(2);
            game.options.hideGui = false;
            hotbarCount = 0;
            hotbarUnequippedTick = -1;
        }
        if (next == Scene.STRAFE_LEFT) {
            game.options.hideGui = true;
            game.options.fov().set(70);
        }
        game.options.keyLeft.setDown(false);
        if (next == Scene.HOTBAR_BARE || next == Scene.WALK_BACK) {
            game.options.keyUp.setDown(false);
            game.options.keySprint.setDown(false);
        }
        game.options.keyRight.setDown(false);
        if (next == Scene.SWIM) {
            game.options.keyUp.setDown(true);
            game.options.keySprint.setDown(true);
            return;
        }
        if (next == Scene.SWIM_EXIT) {
            game.options.keyUp.setDown(false);
            game.options.keySprint.setDown(false);
            game.player.setSprinting(false);
            return;
        }
        var server = game.getSingleplayerServer();
        var uuid = game.player.getUUID();
        pending = server.submit(() -> {
            ServerPlayer player = server.getPlayerList().getPlayer(uuid);
            var level = player.serverLevel();
            level.setDayTime(next.dayTime);
            if (next == Scene.LAMP) {
                lamp = BlockPos.containing(player.getX(), player.getEyeY(), player.getZ()).east();
                level.setBlockAndUpdate(lamp, Blocks.SEA_LANTERN.defaultBlockState());
            } else if (next == Scene.BOTH) {
                level.removeBlock(lamp, false);
            }
            // Keep the same displayed item, camera and unenchanted material
            // for the three lighting captures.
            if (next == Scene.NIGHT || next == Scene.LAMP) return;
            ItemStack chest = next.elytra() ? new ItemStack(Items.ELYTRA)
                    : next.bare() || next.usesBack() || next.hotbar() ? ItemStack.EMPTY : mantle();
            if (next == Scene.BOTH) chest.enchant(Enchantments.UNBREAKING, 1);
            player.setItemSlot(EquipmentSlot.CHEST, chest);
            backOf(player).getStacks().setStackInSlot(0, next.hasBack() ? mantle() : ItemStack.EMPTY);
            if (next.hotbar() || next == Scene.STRAFE_LEFT) {
                player.getInventory().setItem(HOTBAR_SLOT, next == Scene.HOTBAR ? mantle() : ItemStack.EMPTY);
                player.inventoryMenu.broadcastChanges();
            }
            if (next == Scene.TOP_BARE) {
                // Flat, high-contrast floor. All three images use the same
                // camera and body position, including the unequipped control.
                BlockPos floor = pane.offset(-6, -2, -6);
                for (int x = -3; x <= 3; x++) {
                    for (int z = -3; z <= 3; z++) {
                        level.setBlockAndUpdate(floor.offset(x, 0, z), Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState());
                    }
                }
                player.teleportTo(level, floor.getX() + .5, floor.getY() + 1, floor.getZ() + .5, 0, 89);
            } else if (next == Scene.FIT_BARE) {
                BlockPos floor = player.blockPosition().below();
                for (int x = -3; x <= 3; x++) {
                    for (int z = -3; z <= 3; z++) {
                        level.setBlockAndUpdate(floor.offset(x, 0, z), Blocks.BLUE_CONCRETE.defaultBlockState());
                    }
                }
            } else if (next == Scene.STRAFE_LEFT) {
                // An unobstructed strip beside the lamp/panel fixtures.
                player.teleportTo(level, pane.getX() - 6, player.getY(), pane.getZ() - 6, 0, 0);
            } else if (next == Scene.GLIDE) {
                player.getAbilities().flying = false;
                player.onUpdateAbilities();
                player.teleportTo(level, player.getX(), pane.getY() + 132, player.getZ(), 21, 18);
            } else if (next == Scene.WADE) {
                BlockPos pool = pane.offset(-3, 5, 11);
                for (int x = -5; x <= 5; x++) {
                    for (int z = -1; z <= 26; z++) {
                        for (int y = 0; y <= 3; y++) {
                            boolean border = Math.abs(x) == 5 || z == -1 || z == 26;
                            var block = y == 0 && z % 5 == 0 ? Blocks.SEA_LANTERN
                                    : y == 0 || border ? Blocks.PRISMARINE : Blocks.WATER;
                            level.setBlock(pool.offset(x, y, z), block.defaultBlockState(), 2);
                        }
                    }
                }
                player.stopFallFlying();
                player.setDeltaMovement(Vec3.ZERO);
                player.teleportTo(level, pool.getX() + .5, pool.getY() + 1.01, pool.getZ() + 6.5, 0, 0);
            }
        });
    }

    private static void driveScene(Minecraft game) {
        var player = game.player;
        if (scene.walk() && (scene.usesBack() ? !backOf(player).getStacks().getStackInSlot(0).isEmpty()
                : player.getItemBySlot(EquipmentSlot.CHEST).is(CapaTestMod.CAPA_DETERIORER.get()))) walkRoute.drive(game);
        if (scene.strafe()) {
            game.options.keyLeft.setDown(scene == Scene.STRAFE_LEFT);
            game.options.keyRight.setDown(scene == Scene.STRAFE_RIGHT);
        }
        if (scene == Scene.GLIDE && player != null && player.getY() > pane.getY() + 75
                && player.getDeltaMovement().y < -.08 && player.tryToStartFallFlying()) {
            // Start with a small lateral drift, so we test the vanilla
            // yaw correction too. Exact alignment can round the normalized
            // dot product above 1 in the renderer's unclamped acos.
            Vec3 look = player.getViewVector(1);
            player.setDeltaMovement(.42*look.x + .16*look.z, player.getDeltaMovement().y,
                    .42*look.z - .16*look.x);
            player.connection.send(new ServerboundPlayerCommandPacket(player,
                    ServerboundPlayerCommandPacket.Action.START_FALL_FLYING));
        }
    }

    private static void beforePlayer(RenderPlayerEvent.Pre event) {
        if (scene != null && event.getEntity() == Minecraft.getInstance().player) {
            playerPose = new Matrix4f(event.getPoseStack().last().pose());
            if (scene.stillComparison() && !captured && pending == null && stillPlayer == null) {
                // The shirt must not bob independently between the bare,
                // old and fitted images. Keep the vanilla setupAnim path;
                // only give it the same age during these test draws.
                stillPlayer = event.getEntity();
                liveAge = stillPlayer.tickCount;
                stillPlayer.tickCount = STILL_AGE;
            }
        }
    }

    private static void afterPlayer(RenderPlayerEvent.Post event) {
        if (event.getEntity() == stillPlayer) restoreAge();
    }

    private static void restoreAge() {
        if (stillPlayer != null) {
            stillPlayer.tickCount = liveAge;
            stillPlayer = null;
        }
    }

    private static void beforeArmor(GeoRenderEvent.Armor.Pre event) {
        if (scene == null || event.getEntity() != Minecraft.getInstance().player) return;
        if (scene.homeCompare()) {
            if (event.getRenderer() instanceof CapaArmorRenderer live) {
                if (scene.oldRig()) CapeHistoricFitProbe.substitute(event, live);
                else {
                    if (scene.publishedFit()) undoTorsoFit(live);
                    CapeHistoricFitProbe.arm(live);
                }
            } else if (CapeHistoricFitProbe.isLegacy(event.getRenderer())) {
                armHistory(event.getRenderer());
            }
            return;
        }
        if (!(event.getRenderer() instanceof CapaArmorRenderer renderer)) return;
        if (scene.sweep()) CapeLookSweep.Probe.arm(renderer);
        if (scene.walk()) CapeWalkProbe.arm(renderer);
        if (scene == Scene.PLATES_HIDDEN) CapePlateProbe.hide(renderer, true);
        else if (scene.plates()) CapePlateProbe.arm(renderer);
        if (scene.previousFit() || scene.oldJoin() || scene == Scene.PLATES_PREVIOUS) {
            undoTorsoFit(renderer);
            try {
                PLATE_FIT.setFloat(renderer, 0);
            } catch (IllegalAccessException e) {
                throw new AssertionError(e);
            }
        }
        if (scene.previousFit()) {
            // At 58° v1.67.9 was still fully open. The other controls
            // disable the complete original seating stroke from v1.67.9.
            try {
                SEATING.setFloat(renderer, 0);
            } catch (IllegalAccessException e) {
                throw new AssertionError(e);
            }
        }
        if (scene.oldJoin()) mountOldLining(renderer);
        if (scene.unlined()) {
            // Same pose, materials and item with only the two lining bones hidden.
            renderer.getGeoModel().getBone(CapeBacking.LEFT).orElseThrow().setHidden(true);
            renderer.getGeoModel().getBone(CapeBacking.RIGHT).orElseThrow().setHidden(true);
        }
    }

    private static void undoTorsoFit(CapaArmorRenderer renderer) {
        try {
            TORSO_FIT.set(renderer, CapeTorsoFit.NONE);
        } catch (IllegalAccessException e) {
            throw new AssertionError(e);
        }
    }

    @SuppressWarnings("unchecked")
    private static void armHistory(GeoArmorRenderer<?> renderer) {
        CapeHistoricFitProbe.arm((GeoArmorRenderer<CapaDeteriorerItem>) renderer);
    }

    private static void mountOldLining(CapaArmorRenderer renderer) {
        var control = GeckoLibCache.getBakedModels().get(LINING_V16710);
        check(control != null && control.topLevelBones().size() == 2 && savedLining.isEmpty(),
                "missing v1.67.10 lining fixture or overlapping control pass");
        savedLining = control.topLevelBones().stream().map(old -> {
            var bone = renderer.getGeoModel().getBone(old.getName()).orElseThrow();
            check(old.getCubes().size() == 3, "incorrect v1.67.10 lining cubes");
            var save = new Lining(bone, List.copyOf(bone.getCubes()));
            bone.getCubes().clear();
            bone.getCubes().addAll(old.getCubes());
            return save;
        }).toList();
        // v1.67.10 body-space profile, evaluated at the three fixed poses
        // (standing, arms settled): 89°/0°, 58°/3° and 58°/43°.
        double tilt = (58 - 48) / (76.0 - 48), turn = (43 - 13) / (47.0 - 13);
        double seat = scene.overhead() ? 1 : tilt * tilt * (3 - 2 * tilt);
        if (scene.oblique()) seat *= 1 - turn * turn * (3 - 2 * turn);
        try {
            SEATING.setFloat(renderer, (float) seat);
            BACKING.set(renderer, new CapeBacking.Shape(1, scene.oblique() ? .83430561F : 1, 1));
        } catch (IllegalAccessException e) {
            throw new AssertionError(e);
        }
    }

    private static void afterArmor(GeoRenderEvent.Armor.Post event) {
        if (scene == null || event.getEntity() != Minecraft.getInstance().player) return;
        if (scene.homeCompare() && (event.getRenderer() instanceof CapaArmorRenderer
                || CapeHistoricFitProbe.isLegacy(event.getRenderer()))) {
            framePasses++;
            rendered = event.getRenderer().getCurrentStack();
            framePartialTick = event.getPartialTick();
            historyDraw = CapeHistoricFitProbe.finish(event.getRenderer());
            return;
        }
        if (!(event.getRenderer() instanceof CapaArmorRenderer renderer)) return;
        framePasses++;
        rendered = renderer.getCurrentStack();
        armorPose = new Matrix4f(event.getPoseStack().last().pose());
        if (scene.oldJoin()) {
            savedLining.forEach(Lining::restore);
            savedLining = List.of();
        }
        if (scene.unlined()) {
            renderer.getGeoModel().getBone(CapeBacking.LEFT).orElseThrow().setHidden(false);
            renderer.getGeoModel().getBone(CapeBacking.RIGHT).orElseThrow().setHidden(false);
        }
        if (scene.upperBack() || scene.fit() || scene.overhead() || scene.plates()) {
            // Measure the seam under the same world projection used for
            // the current armor pass (neither debug pixels nor the visor).
            upperBackProjection = new Matrix4f(RenderSystem.getProjectionMatrix())
                    .mul(RenderSystem.getModelViewMatrix()).mul(armorPose).translate(0,1.5F,0).scale(-1,-1,1);
        }
        if (scene == Scene.PLATES_HIDDEN) CapePlateProbe.hide(renderer, false);
        else if (scene.plates()) platesDraw = CapePlateProbe.finish(renderer);
        if (scene.sweep()) seatDraw = CapeLookSweep.Probe.finish(renderer);
        if (scene.walk()) walkDraw = CapeWalkProbe.finish(renderer, event.getPartialTick());
        if (scene.fit() || scene.sweep() || scene.plates()) {
            try {
                frameSeating = SEATING.getFloat(renderer);
                framePlateFit = PLATE_FIT.getFloat(renderer);
            } catch (IllegalAccessException e) {
                throw new AssertionError(e);
            }
        }
        frameLight = event.getPackedLight();
        framePartialTick = event.getPartialTick();
        if (scene == Scene.WINGS) {
            frameTopDegrees = renderer.getGeoModel().getBone("cape_top")
                    .map(bone -> -Math.toDegrees(bone.getRotX())).orElse(Double.NaN);
        }
    }

    private static void frame(TickEvent.RenderTickEvent event) {
        if (event.phase == TickEvent.Phase.START) {
            framePasses = 0;
            frameTopDegrees = frameSeating = framePlateFit = Double.NaN;
            seatDraw = null;
            walkDraw = null;
            platesDraw = null;
            historyDraw = null;
            rendered = ItemStack.EMPTY;
            playerPose = armorPose = upperBackProjection = null;
            // Hold the camera/head yaw relative to the torso, like looking
            // around in F5 while the feet have not turned yet. Don't rotate
            // the mantle renderer independently of the vanilla player.
            var player = Minecraft.getInstance().player;
            if (player != null && scene != null && (scene.fixedCamera() || scene.hotbar())) {
                var look = scene.sweep() ? lookSweep.pose() : new CapeLookSweep.Pose(scene.pitch(), scene.yaw());
                float bodyYaw = scene.homeCompare() ? 31 : 0;
                float yaw = bodyYaw + look.yaw();
                float pitch = look.pitch();
                player.setYRot(yaw);
                player.yRotO = yaw;
                player.setXRot(pitch);
                player.xRotO = pitch;
                player.setYHeadRot(yaw);
                player.yHeadRotO = yaw;
                player.setYBodyRot(bodyYaw);
                player.yBodyRotO = bodyYaw;
            }
            return;
        }
        // Also restore the clock if another mod cancelled the player draw.
        restoreAge();
        if (scene == null || captured || pending != null) return;
        Minecraft game = Minecraft.getInstance();
        var player = game.player;
        if (player == null || game.screen != null || game.level.getDayTime() != scene.dayTime) return;
        ItemStack chest = player.getItemBySlot(EquipmentSlot.CHEST);
        ItemStack back = backOf(player).getStacks().getStackInSlot(0);
        boolean chestReady = scene.homeCompare() ? (scene.bare() || scene.usesBack() ? chest.isEmpty()
                : chest.is(CapaTestMod.CAPA_DETERIORER.get())) : switch (scene) {
            case TOP_BARE, TOP_BACK, TURN_BARE, TURN_BACK, OBLIQUE_BARE, OBLIQUE_BACK, SIDE_BARE, SIDE_BACK,
                    FIT_BARE, FIT_BACK, FIT_SLIM_BARE, FIT_SLIM_BACK, MID_BARE, MID_BACK,
                    PLATES_BARE, PLATES_BACK, LOOK_BACK, WALK_BACK, HOTBAR_BARE, HOTBAR -> chest.isEmpty();
            case WINGS, GLIDE -> chest.is(Items.ELYTRA);
            default -> chest.is(CapaTestMod.CAPA_DETERIORER.get());
        };
        if (back.isEmpty() == scene.hasBack() || (scene == Scene.BOTH && !chest.hasFoil()) || !chestReady) return;
        if (scene.hotbar()) {
            try {
                captureHotbar(game);
            } catch (Exception | AssertionError error) {
                fail(game, error);
            }
            return;
        }
        float swim = player.getSwimAmount(1);
        Vec3 velocity = player.getDeltaMovement();
        double bodyYaw = Mth.rotLerp(framePartialTick, player.yBodyRotO, player.yBodyRot);
        double lateral = scene.strafe() ? CapeTravel.measure(new CapeTravel.Step(velocity.x, velocity.y, velocity.z),
                new CapeTravel.Step(player.getX() - player.xo, player.getY() - player.yo, player.getZ() - player.zo),
                false, bodyYaw).side() : 0;
        boolean posed = scene.homeCompare() ? player.onGround() && !player.isCrouching()
                && Math.abs(player.getXRot() - scene.pitch()) < .05 && Math.abs(bodyYaw) < .05
                && Math.abs(player.getYHeadRot() - scene.yaw()) < .05 && velocity.horizontalDistanceSqr() < .0001
                : switch (scene) {
            case TOP_BARE, TOP_OLD_JOIN, TOP_CHEST, TOP_BACK, TURN_BARE, TURN_CHEST, TURN_BACK,
                    OBLIQUE_BARE, OBLIQUE_UNLINED, OBLIQUE_OLD_JOIN, OBLIQUE_CHEST, OBLIQUE_BACK,
                    SIDE_BARE, SIDE_UNLINED, SIDE_CHEST, SIDE_BACK,
                    FIT_BARE, FIT_PREVIOUS, FIT_CHEST, FIT_BACK,
                    FIT_SLIM_BARE, FIT_SLIM_PREVIOUS, FIT_SLIM_CHEST, FIT_SLIM_BACK,
                    MID_BARE, MID_PREVIOUS, MID_OLD_JOIN, MID_CHEST, MID_BACK,
                    PLATES_BARE, PLATES_HIDDEN, PLATES_PREVIOUS, PLATES_CHEST, PLATES_BACK -> player.onGround()
                    && !player.isCrouching() && Math.abs(player.getXRot()-scene.pitch()) < .05 && Math.abs(bodyYaw) < .05
                    && velocity.horizontalDistanceSqr() < .0001;
            case LOOK_CHEST, LOOK_BACK -> player.onGround() && !player.isCrouching()
                    && Math.abs(player.getXRot() - lookSweep.pose().pitch()) < .05
                    && Math.abs(player.getYHeadRot() - lookSweep.pose().yaw()) < .05
                    && Math.abs(bodyYaw) < .05 && velocity.horizontalDistanceSqr() < .0001;
            case STRAFE_LEFT -> player.onGround() && velocity.x > .045 && lateral > .015;
            case STRAFE_RIGHT -> player.onGround() && velocity.x < -.045 && lateral < -.015;
            case WINGS -> player.onGround() && !player.isCrouching() && velocity.horizontalDistanceSqr() < .0001
                    && Math.abs(Math.toDegrees(player.elytraRotZ) + 15) < .8;
            case GLIDE -> {
                Vec3 look = player.getViewVector(framePartialTick);
                double cross = velocity.x*look.z - velocity.z*look.x;
                yield player.isFallFlying() && player.getFallFlyingTicks() >= 12 && Math.abs(player.elytraRotZ) > .8F
                        && Math.abs(cross) > .001 * Math.sqrt(look.horizontalDistanceSqr()*velocity.horizontalDistanceSqr());
            }
            case WADE -> player.isInWater() && !player.isVisuallySwimming() && swim == 0;
            case SWIM -> player.isInWater() && player.isVisuallySwimming() && swim == 1;
            case SWIM_EXIT -> player.isInWater() && !player.isVisuallySwimming() && swim > .12F && swim < .9F;
            default -> !player.isFallFlying() && !player.isInWater();
        };
        if (!posed) {
            stableFrames = observedBirths = 0;
            return;
        }
        try {
            int expectedPasses = scene.bare() ? 0 : 1;
            if (scene.fixedCamera() && stableFrames < 6 && framePasses != expectedPasses) {
                stableFrames++;
                return;
            }
            check(framePasses == expectedPasses && (expectedPasses == 0 || rendered == (scene.usesBack() ? back : chest)),
                    scene.file + ": incorrect worn draw count " + framePasses);
            if (scene.walk()) {
                captured = walkRoute.capture(game, framePartialTick, walkDraw, shots(game), scene.file);
                return;
            }
            String exposure = "";
            if (scene.compareLight()) {
                int block = LightTexture.block(frameLight), sky = LightTexture.sky(frameLight);
                // Wait for the light engine to catch the lantern placement.
                if (sky < 14 || (scene == Scene.LAMP ? block < 13 : block > 2)) return;
                int payload = probe.wearerLight(player, rendered, framePartialTick, frameLight);
                double edge = (short) payload / 4096.0;
                double inner = (short) (payload >>> 16) / 4096.0;
                if (scene == Scene.NIGHT ? edge < 1.27 || inner < 1.12
                        : edge < .45 || inner < .45 || edge > .54 || inner > .54) {
                    check(stableFrames < 60, scene.file + ": unexpected worn halo " + edge + "/" + inner);
                    stableFrames++;
                    return;
                }
                exposure = "; UV2 borde=" + Math.round(100*edge) + "%, interior=" + Math.round(100*inner)
                        + "%, luz bloque/cielo=" + block + "/" + sky;
            }
            if (scene != Scene.SWIM_EXIT && ++stableFrames < 18) return;
            if (scene.sweep()) {
                captured = lookSweep.capture(game, shots(game), scene.file, frameSeating, seatDraw);
                if (captured) note("Recorrido de mirada " + scene.file + ": " + lookSweep.summary());
                return;
            }
            if (scene.inspectBirths() && observedBirths == 0) return;
            if (scene == Scene.WINGS) {
                check(frameTopDegrees > 24 && frameTopDegrees < 34,
                        "folded elytra guide not applied to cape_top: " + frameTopDegrees);
                exposure = "; bisagra del paño en reposo = " + Math.round(frameTopDegrees * 10) / 10.0 + "°";
            }
            double rootError = 0;
            if (scene.inspectBirths() || scene == Scene.SWIM_EXIT) {
                var frame = CapaDeteriorerItem.auraFrame(player);
                check(frame.posed() == (scene != Scene.WADE), scene.file + ": wrong emitter frame");
                if (scene == Scene.GLIDE || scene == Scene.SWIM) {
                    check(playerPose != null && armorPose != null, "missing renderer transform");
                    Matrix4f model = new Matrix4f(playerPose).invert().mul(armorPose)
                            .translate(0, 1.5F, 0).scale(-1, -1, 1);
                    // Compare tick-sampled points against the actual interpolated
                    // camera-relative root passed to GeckoLib, with a small margin.
                    for (float side : new float[]{-.50F, .42F}) {
                        Vector3f renderedPoint = model.transformPosition(-side, .82F, 1.1F, new Vector3f());
                        var birthFrame = frame.point(side, .82F, 1.1F);
                        rootError = Math.max(rootError, new Vec3(renderedPoint.x, renderedPoint.y, renderedPoint.z)
                                .distanceTo(new Vec3(birthFrame.x(), birthFrame.y(), birthFrame.z())));
                    }
                    check(rootError < .08, scene.file + ": emitter/render frame gap " + rootError);
                }
            }
            if (scene.fit() || scene.plates()) check(player.getModelName().equals(scene.slimFit() || scene.plates() ? "slim" : "default"),
                    scene.file + ": incorrect vanilla sleeve model");
            if (scene.fit() && !scene.bare()) {
                boolean seated = scene.oldJoin() ? Math.abs(frameSeating - .291545) < .001
                        : scene.midFit() ? frameSeating > .35 && frameSeating < .46 : frameSeating > .88;
                check(scene.previousFit() ? frameSeating == 0 : seated,
                        scene.file + ": incorrect fit control or live seating " + frameSeating);
                exposure = "; ajuste de la montura activa = " + Math.round(frameSeating * 100) + "%";
            }
            if (scene.plates() && !scene.bare()) {
                check(frameSeating > .96 && (scene == Scene.PLATES_PREVIOUS ? framePlateFit == 0 : framePlateFit > .94),
                        scene.file + ": invalid baseline or fitted pose " + frameSeating + "/" + framePlateFit);
            }
            Path shots = shots(game);
            try (NativeImage image = Screenshot.takeScreenshot(game.getMainRenderTarget())) {
                image.writeToFile(shots.resolve(scene.file + ".png"));
                if (scene.upperBack() && !scene.bare()) projectUpperBack(shots, image);
                if ((scene.fit() || scene.plates()) && !scene.bare()) projectFit(shots, image);
                if (scene.binding()) projectBinding(shots, image);
                if (scene.homeCompare() && !scene.bare()) {
                    check(historyDraw != null, "missing torso-space measurements of " + scene.file);
                    Files.writeString(shots.resolve(scene.file + ".tsv"), historyDraw.bounds());
                    Files.writeString(shots.resolve(scene.file + "-caras.tsv"), historyDraw.faces());
                    Files.writeString(shots.resolve(scene.file + "-camara.tsv"), historyDraw.camera());
                }
                if (scene.plates() && !scene.bare() && scene != Scene.PLATES_HIDDEN) {
                    check(platesDraw != null, "missing live plate pass");
                    platesDraw.write(shots.resolve(scene.file + "-caras.tsv"), image.getWidth(), image.getHeight());
                }
            }
            if (scene.strafe()) exposure = "; entrada lateral = " + Math.round(100 * lateral) + "%";
            note(scene.file + ": " + framePasses + " manto en F5" + (scene.inspectBirths()
                    ? "; nacimientos recibidos=" + observedBirths + ", diferencia de marco=" + Math.round(rootError * 1000) + " mm de bloque"
                    : exposure));
            captured = true;
        } catch (Exception | AssertionError error) {
            fail(game, error);
        }
    }

    private static Path shots(Minecraft game) throws IOException {
        return Files.createDirectories(game.gameDirectory.toPath().resolve("fx-shots"));
    }

    /** Registered model-space trim windows, measured in the F5 framebuffer. */
    private static void projectFit(Path shots, NativeImage image) throws IOException {
        check(upperBackProjection != null, "missing trim projection");
        StringBuilder data = new StringBuilder();
        for (float x : new float[]{-7.2F,0,5.8F}) {
            // Pad, center of the neck seam, opposite pad. The baseline's
            // visible upper surface is in these small windows (not the lining).
            float y = x == 0 ? 23.85F : 23F;
            float z = x == 0 ? 7.28F : 4.38F;
            for (float depth : new float[]{z, (float) (CapeFit.SEAT_PLANE
                    + (z-CapeFit.SEAT_PLANE)*CapeFit.seatDepthScale(1))}) {
                Vector3f pixel = upperBackProjection.transformProject(new Vector3f(x/16,y/16,depth/16));
                data.append((pixel.x()+1)*image.getWidth()/2).append('\t')
                        .append((1-pixel.y())*image.getHeight()/2).append('\t');
            }
            data.append('\n');
        }
        Files.writeString(shots.resolve(scene.file + ".tsv"), data.toString());
    }

    private static void projectBinding(Path shots, NativeImage image) throws IOException {
        StringBuilder out = new StringBuilder();
        // Points ON the vanilla jacket's top rear edge, not a projection
        // of the candidate cloth. Compare to a bare torso in the same pose.
        for (int u = -16; u <= 16; ++u) for (int v = 0; v < 6; ++v) {
            float x = u * .192F, z = 1.97F + .05F * v;
            var p = upperBackProjection.transformProject(new Vector3f(x/16,24.251F/16,z/16));
            out.append(u).append('\t').append(v).append('\t')
                    .append((int) ((1+p.x)*image.getWidth()*.5F)).append('\t')
                    .append((int) ((1-p.y)*image.getHeight()*.5F)).append('\n');
        }
        Files.writeString(shots.resolve(scene.file + "-borde.tsv"), out);
    }

    private static void projectUpperBack(Path shots, NativeImage image) throws IOException {
        check(upperBackProjection != null, "missing armor projection");
        StringBuilder points = new StringBuilder();
        // Oblique: exactly on the exposed upper back of the vanilla jersey.
        // Profile: a section through the high join, between shirt and collar.
        // At 76° the old collar projects over most of the jersey probe and
        // would conceal the open seam we need to test in that view.
        boolean side = scene.profile();
        for (int u = -15; u <= 15; u++) {
            float x = side ? 0 : u * .19F;
            float z = side ? 3.18F + .027F*u : 2.251F;
            for (int v = 0; v <= 7; v++) {
                float y = side ? 21.87F + .10F*v : 19.65F + .18F*v;
                Vector3f p = upperBackProjection.transformProject(new Vector3f(x/16,y/16,z/16));
                int px = (int) ((1+p.x)*image.getWidth()*.5F);
                int py = (int) ((1-p.y)*image.getHeight()*.5F);
                points.append(u).append('\t').append(v).append('\t')
                        .append(px).append('\t').append(py).append('\n');
            }
        }
        Files.writeString(shots.resolve(scene.file + ".tsv"), points);
    }

    private static void captureHotbar(Minecraft game) throws IOException {
        var player = game.player;
        var stack = player.getInventory().getItem(HOTBAR_SLOT);
        boolean empty = scene == Scene.HOTBAR_BARE;
        if ((empty ? !stack.isEmpty() : !stack.is(CapaTestMod.CAPA_DETERIORER.get()))
                || game.options.hideGui || ++stableFrames < 18) return;
        int tick = player.tickCount;
        // The previous fitting scene leaves real embers alive for up to 47
        // ticks. In a transparent hotbar they can change the pixels behind
        // an otherwise static slot. Wait from confirmed unequip, not FPS.
        if (empty) {
            if (hotbarUnequippedTick < 0) hotbarUnequippedTick = tick;
            if (tick - hotbarUnequippedTick < HOTBAR_QUIET_TICKS) return;
        }
        if (hotbarCount > 0 && tick == lastHotbarTick) return;
        check(framePasses == 0 && player.getInventory().selected != HOTBAR_SLOT,
                "hotbar fixture: worn or selected mantle");
        if (!empty && hotbarCount == 0) {
            check(!game.getItemRenderer().getModel(stack, game.level, player, 0).isCustomRenderer(),
                    "hotbar no longer uses the vanilla item model");
        }
        var window = game.getWindow();
        int guiWidth = window.getGuiScaledWidth(), guiHeight = window.getGuiScaledHeight();
        int startX = guiWidth/2 - 28, startY = guiHeight - 22;
        Path shots = shots(game);
        try (NativeImage image = Screenshot.takeScreenshot(game.getMainRenderTarget());
             NativeImage crop = new NativeImage(112, 44, false)) {
            // Exactly 3 neighboring slots, normalized to two physical
            // pixels per logical GUI pixel even if window dimensions round.
            for (int y = 0; y < crop.getHeight(); y++) {
                int iy = (int) ((startY + (y + .5)/2) * image.getHeight()/guiHeight);
                for (int x = 0; x < crop.getWidth(); x++) {
                    int ix = (int) ((startX + (x + .5)/2) * image.getWidth()/guiWidth);
                    crop.setPixelRGBA(x, y, image.getPixelRGBA(ix, iy));
                }
            }
            if (empty) {
                crop.writeToFile(shots.resolve("hotbar-vacia.png"));
                captured = true;
                return;
            }
            if (hotbarCount == 0) image.writeToFile(shots.resolve("hotbar-mundo.png"));
            crop.writeToFile(shots.resolve(String.format(java.util.Locale.ROOT, "hotbar-%02d.png", hotbarCount)));
        }
        lastHotbarTick = tick;
        if (++hotbarCount == HOTBAR_SAMPLES) {
            note(hotbarCount + " capturas de la ranura vanilla a lo largo de un ciclo del atlas");
            captured = true;
        }
    }

    private static void checkHaloBatch(Minecraft game) {
        // An actual NEW_ENTITY upload and the installed RenderType, not a
        // shader test that binds the attributes in its own order. Mix two
        // payloads in one batch and test the edge and lip independently.
        TextureTarget target = new TextureTarget(96, 16, true, Minecraft.ON_OSX);
        PoseStack view = RenderSystem.getModelViewStack();
        float start = RenderSystem.getShaderFogStart(), end = RenderSystem.getShaderFogEnd();
        float[] color = RenderSystem.getShaderColor().clone();
        RenderSystem.backupProjectionMatrix();
        view.pushPose();
        try {
            view.setIdentity();
            RenderSystem.applyModelViewMatrix();
            RenderSystem.setProjectionMatrix(new Matrix4f(), VertexSorting.ORTHOGRAPHIC_Z);
            RenderSystem.setShaderFogStart(2);
            RenderSystem.setShaderFogEnd(4);
            RenderSystem.setShaderColor(1, 1, 1, 1);
            RenderSystem.depthMask(true);
            target.setClearColor(22/255F, 16/255F, 28/255F, 128/255F);
            target.clear(Minecraft.ON_OSX);
            target.bindWrite(true);
            RenderSystem.enableScissor(64, 0, 16, 16);
            RenderSystem.clearDepth(.25);
            RenderSystem.clear(org.lwjgl.opengl.GL11.GL_DEPTH_BUFFER_BIT, Minecraft.ON_OSX);
            RenderSystem.disableScissor();
            RenderSystem.clearDepth(1);
            int edge = new CapeNocturne.Gains(1.5, .5).packed();
            int inner = new CapeNocturne.Gains(.5, 1.5).packed();
            MultiBufferSource.BufferSource buffers = MultiBufferSource.immediate(new BufferBuilder(1024));
            var type = CapeBloom.wornLight(CapeBloom.Mode.HALO);
            var vertices = buffers.getBuffer(type);
            probeQuad(vertices, 0, 251, 2, edge);
            probeQuad(vertices, 1, 251, 2, inner);
            probeQuad(vertices, 2, 259, 11, edge);
            probeQuad(vertices, 3, 259, 11, inner);
            probeQuad(vertices, 4, 259, 11, inner); // behind the depth-only occluder
            probeQuad(vertices, 5, 0, 0, edge);      // matte UV
            buffers.endBatch(type);
            int[] red = {37, 27, 79, 193, 22, 22};
            // Screenshot.takeScreenshot forces alpha to 255. Read the same
            // attachment here without that conversion to test the blend mask.
            try (NativeImage image = new NativeImage(target.width, target.height, false)) {
                RenderSystem.bindTexture(target.getColorTextureId());
                image.downloadTexture(0, false);
                for (int i = 0; i < red.length; i++) {
                    int rgba = image.getPixelRGBA(i * 16 + 8, 8);
                    check(Math.abs((rgba & 255) - red[i]) <= 1 && (rgba >>> 24) == 128,
                            "UV2/alpha/depth sample " + i + ": " + Integer.toHexString(rgba));
                }
            }
        } finally {
            RenderSystem.disableScissor();
            RenderSystem.clearDepth(1);
            target.destroyBuffers();
            game.getMainRenderTarget().bindWrite(true);
            RenderSystem.setShaderColor(color[0], color[1], color[2], color[3]);
            RenderSystem.setShaderFogStart(start);
            RenderSystem.setShaderFogEnd(end);
            RenderSystem.restoreProjectionMatrix();
            view.popPose();
            RenderSystem.applyModelViewMatrix();
        }
        note("NEW_ENTITY en GPU: dos intensidades UV2 en un lote, borde/interior, oclusión y alfa intacto");
    }

    private static void probeQuad(VertexConsumer vertices, int col, int x, int y, int light) {
        float left = col/3F - 1, right = (col+1)/3F - 1;
        float u = (x+.5F)/512, v = (y+.5F)/512;
        for (int i = 0; i < 4; i++)
            vertices.vertex(i < 2 ? left : right, i == 0 || i == 3 ? -1 : 1, 0,
                    1, 1, 1, 1, u, v, OverlayTexture.NO_OVERLAY, light, 0, 0, 1);
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
        CapaTestMod.LOGGER.error("FX smoke: FAIL at step " + step + ", scene " + scene + ": " + error.getMessage(), error);
        step = -1;
        scene = null;
        game.stop();
    }

    private static final class GlowProbe extends CapaArmorRenderer {
        private final CapaGlowLayer layer = new CapaGlowLayer(this);
        private final CapaDeteriorerItem item = (CapaDeteriorerItem) mantle().getItem();
        private final PoseStack caller = new PoseStack();
        private final BufferBuilder sink = new BufferBuilder(256);
        private RenderType submitted;
        private int submittedLight;
        private Entity sampleWearer;
        private ItemStack sampleStack;
        private boolean failing;

        GlowProbe() {
            caller.translate(.25, -.5, 1.75);
            caller.mulPose(Axis.XP.rotationDegrees(29));
        }

        void run(CapeBloom.Mode expected, boolean fail) {
            this.failing = fail;
            var before = new Matrix4f(caller.last().pose());
            var normal = new Matrix3f(caller.last().normal());
            submit(expected, 0, 0);
            check(caller.clear() && caller.last().pose().equals(before) && caller.last().normal().equals(normal),
                    "glow mutated the caller's stack");
            if (expected == CapeBloom.Mode.CORE)
                check(submittedLight == LightTexture.FULL_BRIGHT, "fallback received a halo payload");
        }

        int wearerLight(Entity wearer, ItemStack stack, float partialTick, int light) {
            // Replay just the actual layer's setup on the recorded world
            // inputs, with no extra vertex submission or animation advance.
            sampleWearer = wearer;
            sampleStack = stack;
            try {
                submit(CapeBloom.Mode.HALO, partialTick, light);
                return submittedLight;
            } finally {
                sampleWearer = null;
                sampleStack = null;
            }
        }

        @Override
        public Entity getCurrentEntity() {
            return sampleWearer != null ? sampleWearer : super.getCurrentEntity();
        }

        @Override
        public ItemStack getCurrentStack() {
            return sampleStack != null ? sampleStack : super.getCurrentStack();
        }

        private void submit(CapeBloom.Mode expected, float partialTick, int light) {
            submitted = null;
            BakedGeoModel model = getGeoModel().getBakedModel(getGeoModel().getModelResource(item, this));
            layer.render(caller, item, model, null, type -> sink, sink, partialTick, light, 0);
            check(submitted == (expected == CapeBloom.Mode.OFF ? null : CapeBloom.wornLight(expected)),
                    "unexpected light pass: expected " + expected + ", got " + submitted);
        }

        @Override
        public void reRender(BakedGeoModel model, PoseStack stack, MultiBufferSource buffers, CapaDeteriorerItem item,
                             RenderType type, VertexConsumer buffer, float partialTick, int light, int overlay,
                             float r, float g, float b, float a) {
            submitted = type;
            submittedLight = light;
            check(stack.last().pose().equals(caller.last().pose()) && stack.last().normal().equals(caller.last().normal()),
                    "emission transform differs from opaque transform");
            stack.pushPose();
            stack.translate(0, -2, 0);
            if (failing) throw new IllegalStateException("intentional FX smoke failure after GeckoLib push");
            stack.popPose();
        }
    }
}
