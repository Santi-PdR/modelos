package dev.holorelic.client;

import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import dev.holorelic.RelicConfig;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.EntityModel;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.renderer.GeoObjectRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.client.renderer.texture.OverlayTexture;
import dev.holorelic.HoloRelic;
import top.theillusivec4.curios.api.SlotContext;
import top.theillusivec4.curios.api.client.ICurioRenderer;

public final class RelicRenderer extends GeoObjectRenderer<RelicVisual> implements ICurioRenderer {
    // Weak entity keys avoid retaining players after they leave tracking range; visuals hold no entity reference.
    private static final ResourceLocation GLOW_TEXTURE = new ResourceLocation(HoloRelic.ID, "textures/relic_hologram_glowing.png");
    private static final Map<LivingEntity, RelicVisual> VISUALS = new WeakHashMap<>();
    public RelicRenderer() {
        super(new RelicModel());
        addRenderLayer(new GeoRenderLayer<RelicVisual>(this) {
            @Override public void render(PoseStack pose, RelicVisual visual, BakedGeoModel model,
                    RenderType type, MultiBufferSource buffers, VertexConsumer buffer,
                    float partialTick, int light, int overlay) {
                if (!RelicConfig.GLOW.get()) return;
                // AutoGlowingTexture in 4.8.4 expects _glowmask and mutates the base texture.
                // An explicit emissive pass preserves both supplied PNGs and allows runtime disabling.
                RenderType glow = RenderType.entityTranslucentEmissive(GLOW_TEXTURE);
                getRenderer().reRender(model, pose, buffers, visual, glow, buffers.getBuffer(glow),
                        partialTick, LightTexture.FULL_BRIGHT, OverlayTexture.NO_OVERLAY, 1, 1, 1, 1);
            }
        });
    }
    static void forget(UUID id) { VISUALS.keySet().removeIf(e -> e.getUUID().equals(id)); }
    static void clear() { VISUALS.clear(); }
    @Override public long getInstanceId(RelicVisual visual) { return 0; } // Each visual owns an instanced cache.

    @Override public <T extends LivingEntity, M extends EntityModel<T>> void render(ItemStack stack,
            SlotContext context, PoseStack pose, RenderLayerParent<T, M> parent, MultiBufferSource buffers,
            int light, float limbSwing, float limbSwingAmount, float partialTick, float age,
            float headYaw, float headPitch) {
        var entity = context.entity();
        var mc = Minecraft.getInstance();
        if (entity.isInvisible() || (entity == mc.player && mc.options.getCameraType().isFirstPerson())) return;
        var visual = VISUALS.computeIfAbsent(entity, ignored -> new RelicVisual());
        visual.update(entity, partialTick, ClientState.get(entity.getUUID()));
        pose.pushPose();
        if (parent.getModel() instanceof HumanoidModel<?> humanoid) humanoid.body.translateAndRotate(pose);
        // Player layers use Y down, feet at Y=24px. GeckoLib geometry uses Y up and flips exported X.
        // Remove GeoObjectRenderer's block-center translation (see preRender), then anchor at the feet.
        pose.translate(RelicConfig.X.get(), 1.5 - RelicConfig.Y.get(), RelicConfig.Z.get());
        float scale = RelicConfig.SCALE.get().floatValue();
        float mirror = RelicConfig.SHOULDER.get() == RelicConfig.Shoulder.RIGHT ? -1 : 1;
        pose.scale(scale * mirror, -scale, scale);
        RenderType type = getGeoModel().getRenderType(visual, getTextureLocation(visual));
        // Pass the vertex consumer explicitly: GeoObjectRenderer otherwise substitutes the global buffer source.
        super.render(pose, visual, buffers, type, buffers.getBuffer(type), LightTexture.FULL_BRIGHT);
        pose.popPose();
    }
    @Override public void preRender(PoseStack pose, RelicVisual visual, BakedGeoModel model,
            MultiBufferSource buffers, VertexConsumer buffer, boolean rerender, float partialTick,
            int light, int overlay, float red, float green, float blue, float alpha) {
        // Body-space accessory, not a block: intentionally omit the default (0.5, 0.51, 0.5) translation.
        this.objectRenderTranslations = new org.joml.Matrix4f(pose.last().pose());
    }
}
