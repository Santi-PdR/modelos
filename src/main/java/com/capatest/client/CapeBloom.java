package com.capatest.client;

import com.capatest.CapaTestMod;
import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.VertexFormat;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.ShaderInstance;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceProvider;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RegisterShadersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.opengl.GL20;

import java.io.IOException;

/** Local bloom on the posed cloth. No framebuffer, global shader override or extra mesh pass. */
@Mod.EventBusSubscriber(modid = CapaTestMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class CapeBloom extends RenderType {
    private static final ResourceLocation PROGRAM = new ResourceLocation(CapaTestMod.MOD_ID, "cape_bloom");
    private static final ResourceLocation EMISSION = new ResourceLocation(CapaTestMod.MOD_ID,
            "textures/item/armor/capa_deteriorer_evilsaiyan_glowmask.png");
    private static final ResourceLocation HALO = new ResourceLocation(CapaTestMod.MOD_ID,
            "textures/item/armor/capa_deteriorer_evilsaiyan_halo.png");
    private static final int ATLAS_SIDE = 512;
    // Only read or changed on the render thread. A reload can both add and
    // remove resources; never keep a reference to the old closed program.
    private static int generation;
    private static boolean coreReady;
    private static ShaderInstance shader;

    enum Mode { OFF, CORE, HALO }

    private CapeBloom() {
        super("capatest_cape_bloom", DefaultVertexFormat.NEW_ENTITY, VertexFormat.Mode.QUADS,
                1536, false, true, () -> {}, () -> {});
    }

    @SubscribeEvent
    public static void registerShader(RegisterShadersEvent event) {
        generation++;
        shader = null;
        coreReady = false;
        ResourceProvider resources = event.getResourceProvider();
        try {
            validateAtlas(resources, EMISSION, true);
            coreReady = true;
        } catch (IOException | RuntimeException | LinkageError error) {
            CapaTestMod.LOGGER.warn("Blight Star Mantle: núcleo no disponible; se conserva el paño opaco", error);
            return;
        }
        if (Boolean.getBoolean("capa.sinHalo")) return;
        try {
            validateAtlas(resources, HALO, false);
            ShaderInstance candidate = new ShaderInstance(resources, PROGRAM,
                    DefaultVertexFormat.NEW_ENTITY);
            // ShaderInstance throws on compilation failure, but link errors can just log.
            if (GlStateManager.glGetProgrami(candidate.getId(), GL20.GL_LINK_STATUS) == 0) {
                candidate.close();
                throw new IOException("Could not link " + PROGRAM);
            }
            event.registerShader(candidate, loaded -> {
                shader = loaded;
                CapaTestMod.LOGGER.info("Blight Star Mantle: halo de grietas listo");
            });
        } catch (IOException | RuntimeException | LinkageError error) {
            CapaTestMod.LOGGER.warn("Blight Star Mantle: sin halo, se usa la emisión estándar", error);
        }
    }

    private static void validateAtlas(ResourceProvider resources, ResourceLocation texture,
                                      boolean needsAlpha) throws IOException {
        // Decode, not just exists(): TextureManager silently substitutes the
        // missing-texture checkerboard on a bad PNG. Keep it out of this pass.
        try (NativeImage image = NativeImage.read(null, resources.open(texture))) {
            int size = image.getWidth();
            if (size < ATLAS_SIDE || size != image.getHeight() || size % ATLAS_SIDE != 0
                    || size > RenderSystem.maxSupportedTextureSize()) {
                throw new IOException(texture + ": incompatible atlas " + size + "x" + image.getHeight());
            }
            if (needsAlpha && !image.format().hasAlpha()) {
                throw new IOException(texture + ": emission atlas needs an alpha channel");
            }
        }
    }

    static int generation() {
        return generation;
    }

    static Mode availableMode() {
        return !coreReady ? Mode.OFF : shader == null ? Mode.CORE : Mode.HALO;
    }

    static RenderType wornLight(Mode mode) {
        return switch (mode) {
            case HALO -> Type.BLOOM;
            case CORE -> RenderType.entityTranslucentEmissive(EMISSION, false);
            case OFF -> throw new IllegalArgumentException("No light pass");
        };
    }

    private static final class Type {
        // Match the blend in cape_bloom.json. Preserve the destination alpha:
        // RGB = old*(1-coreCoverage) + premultiplied core + additive spill.
        private static final TransparencyStateShard BLEND = new TransparencyStateShard("capatest_bloom", () -> {
            RenderSystem.enableBlend();
            RenderSystem.blendFuncSeparate(GlStateManager.SourceFactor.ONE,
                    GlStateManager.DestFactor.ONE_MINUS_SRC_ALPHA,
                    GlStateManager.SourceFactor.ZERO, GlStateManager.DestFactor.ONE);
        }, () -> {
            RenderSystem.disableBlend();
            RenderSystem.defaultBlendFunc();
        });
        private static final RenderType BLOOM = create("capatest_cape_bloom", DefaultVertexFormat.NEW_ENTITY,
                VertexFormat.Mode.QUADS, 1536, false, true, CompositeState.builder()
                        .setShaderState(new ShaderStateShard(() -> shader))
                        .setTextureState(MultiTextureStateShard.builder()
                                .add(EMISSION, false, false) // crisp core, as in the fallback
                                .add(HALO, true, false)     // smooth spill within each UV card, no mip bleed
                                .build())
                        .setTransparencyState(BLEND)
                        .setCullState(NO_CULL)
                        .setDepthTestState(LEQUAL_DEPTH_TEST)
                        .setWriteMaskState(COLOR_WRITE)
                        .createCompositeState(false));
    }
}
