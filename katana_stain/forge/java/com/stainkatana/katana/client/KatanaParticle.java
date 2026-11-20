package com.stainkatana.katana.client;

import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Camera;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Vector4f;

/**
 * Oriented double-sided slash quad adapted from Better Combat Particle's
 * BotSlashParticle180 by Malfu; original sprites and MIT notice are included.
 * The small impact glyph (style 1) remains a camera-facing particle.
 */
public final class KatanaParticle extends TextureSheetParticle {
    private final SpriteSet sprites;
    private final int style;
    private final float yawAngle, pitchAngle, rollAngle;

    private KatanaParticle(ClientLevel level, double x, double y, double z,
                           double yaw, double pitch, double angle, SpriteSet sprites, int style) {
        super(level, x, y, z, 0, 0, 0);
        this.sprites = sprites; this.style = style;
        this.yawAngle = (float) yaw; this.pitchAngle = (float) pitch; this.rollAngle = (float) angle;
        this.hasPhysics = false;
        this.lifetime = style == 0 ? 8 : style == 1 ? 7 : 10;
        this.quadSize = style == 0 ? 1.35F : style == 1 ? 0.32F : 1.45F;
        this.xd = this.yd = this.zd = 0;
        if (style == 0) this.setColor(1.0F, .65F, .65F);
        else this.setColor(.82F, .13F, .16F);
        this.alpha = style == 0 ? .85F : .80F;
        this.setSpriteFromAge(sprites);
    }

    @Override public void tick() {
        super.tick();
        if (!this.removed) this.setSpriteFromAge(this.sprites);
    }
    @Override public ParticleRenderType getRenderType() { return ParticleRenderType.PARTICLE_SHEET_TRANSLUCENT; }

    @Override public void render(VertexConsumer out, Camera camera, float partialTick) {
        if (style == 1) {
            super.render(out, camera, partialTick);
            return;
        }
        // Malfu's world-oriented XZ plane, translated to Mojmap and supplied by our impact packet.
        Vec3 cameraPos = camera.getPosition();
        float x = (float)(Mth.lerp(partialTick, this.xo, this.x) - cameraPos.x());
        float y = (float)(Mth.lerp(partialTick, this.yo, this.y) - cameraPos.y());
        float z = (float)(Mth.lerp(partialTick, this.zo, this.z) - cameraPos.z());
        float size = this.getQuadSize(partialTick);
        Matrix4f rotation = new Matrix4f().rotateY((float)Math.toRadians(-yawAngle))
                .rotateX((float)Math.toRadians(pitchAngle)).rotateZ((float)Math.toRadians(rollAngle));
        Vector4f[] corners = {new Vector4f(-size, 0, -size, 1), new Vector4f(-size, 0, size, 1),
                new Vector4f(size, 0, size, 1), new Vector4f(size, 0, -size, 1)};
        for (Vector4f corner : corners) { rotation.transform(corner); corner.add(x, y, z, 0); }
        float[] u = {getU1(), getU1(), getU0(), getU0()};
        float[] v = {getV1(), getV0(), getV0(), getV1()};
        int light = getLightColor(partialTick);
        for (int i = 0; i < 8; i++) {
            int n = i < 4 ? i : 7 - i;
            out.vertex(corners[n].x(), corners[n].y(), corners[n].z()).uv(u[n], v[n])
                    .color(rCol, gCol, bCol, alpha).uv2(light).endVertex();
        }
    }

    public static final class SlashProvider implements ParticleProvider<SimpleParticleType> {
        private final SpriteSet sprites; public SlashProvider(SpriteSet sprites) { this.sprites = sprites; }
        public Particle createParticle(SimpleParticleType type, ClientLevel level, double x, double y, double z, double dx, double dy, double dz) {
            return new KatanaParticle(level, x, y, z, dx, dy, dz, sprites, 0);
        }
    }
    public static final class ShardProvider implements ParticleProvider<SimpleParticleType> {
        private final SpriteSet sprites; public ShardProvider(SpriteSet sprites) { this.sprites = sprites; }
        public Particle createParticle(SimpleParticleType type, ClientLevel level, double x, double y, double z, double dx, double dy, double dz) {
            return new KatanaParticle(level, x, y, z, dx, dy, dz, sprites, 1);
        }
    }
    public static final class PulseProvider implements ParticleProvider<SimpleParticleType> {
        private final SpriteSet sprites; public PulseProvider(SpriteSet sprites) { this.sprites = sprites; }
        public Particle createParticle(SimpleParticleType type, ClientLevel level, double x, double y, double z, double dx, double dy, double dz) {
            return new KatanaParticle(level, x, y, z, dx, dy, dz, sprites, 2);
        }
    }
}
