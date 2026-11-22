package com.capatest.client;

import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Camera;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.util.Mth;
import org.joml.Vector3f;

/** Chispa rosa que conserva la velocidad enviada por el servidor. */
public class CapaSparkParticle extends TextureSheetParticle {
    private final SpriteSet sprites;
    private final int spriteEnd;
    private final float baseSize;
    private final float streak;
    private final float phase;
    private double previousDriftX, previousDriftZ, driftX, driftZ;

    protected CapaSparkParticle(ClientLevel level,
                                double x, double y, double z,
                                double dx, double dy, double dz,
                                SpriteSet sprites) {
        super(level, x, y, z);
        this.sprites = sprites;
        // Older resource packs may still list only the three key sprites.
        // SpriteSet scales its index to the list, so they repeat at 0 and 1.
        this.spriteEnd = sprites.get(0, CapeEmber.LAST_SPRITE) == sprites.get(1, CapeEmber.LAST_SPRITE)
                ? 2 : CapeEmber.LAST_SPRITE;
        double horizontal = Math.hypot(dx, dz);
        this.streak = (float) Math.min(1.0D, horizontal / 0.035D);
        double clamp = horizontal > 0.04D ? 0.04D / horizontal : 1.0D;
        this.setParticleSpeed(dx * clamp, Math.max(0.007D, Math.min(0.021D, dy)), dz * clamp);
        this.lifetime = 39 - Math.round(13 * this.streak) + this.random.nextInt(9);
        this.alpha = 0.0F;
        // Stop at block shapes (including panes and slabs). This does not
        // change the free-air impulse or add gravity/bounces.
        this.hasPhysics = true;
        this.gravity = 0.0F;
        this.friction = 0.94F;
        this.phase = this.random.nextFloat() * 3.14F;
        this.scale(0.28F + 0.10F * this.streak + 0.15F * this.random.nextFloat());
        this.baseSize = this.quadSize;
        this.setSprite(sprites.get(0, spriteEnd));
    }

    @Override
    public void tick() {
        previousDriftX = driftX;
        previousDriftZ = driftZ;
        super.tick();
        // Use movement actually allowed by collision, not a launch vector
        // that would keep the sprite banked after it stops at a pane.
        driftX = this.x - this.xo;
        driftZ = this.z - this.zo;
    }

    @Override
    public void render(VertexConsumer vertices, Camera camera, float partialTick) {
        float partial = CapeEmber.renderFraction(partialTick);
        double progress = CapeEmber.renderProgress(this.age, this.lifetime, partial);
        if (progress <= 0 || progress >= 1) return;
        CapeEmber.Look look = CapeEmber.look(progress, this.streak, this.phase);
        this.alpha = (float) look.alpha();
        this.quadSize = this.baseSize * (float) look.scale();
        this.rCol = (float) look.red();
        this.gCol = (float) look.green();
        this.bCol = (float) look.blue();
        int frame = spriteEnd == 2 ? look.frame() : CapeEmber.spriteIndex(progress, this.lifetime);
        this.setSprite(this.sprites.get(frame, spriteEnd));
        double dx = Mth.lerp((double) partial, previousDriftX, driftX);
        double dz = Mth.lerp((double) partial, previousDriftZ, driftZ);
        // Camera-local X in world space. Do not mutate the camera's quaternion.
        var right = camera.rotation().transform(new Vector3f(1, 0, 0));
        float bank = (float) CapeEmber.bank(progress, dx * right.x() + dz * right.z());
        // Vanilla's one fullbright quad: same UV, scale, centre and depth test.
        // This value belongs only to this view, never to the simulation tick.
        float savedRoll = this.roll, savedPreviousRoll = this.oRoll;
        this.roll = this.oRoll = bank;
        try {
            super.render(vertices, camera, partial);
        } finally {
            this.roll = savedRoll;
            this.oRoll = savedPreviousRoll;
        }
    }

    @Override
    protected int getLightColor(float partialTick) {
        return LightTexture.FULL_BRIGHT;
    }

    @Override
    public ParticleRenderType getRenderType() {
        return ParticleRenderType.PARTICLE_SHEET_TRANSLUCENT;
    }

    public static class Provider implements ParticleProvider<SimpleParticleType> {
        private final SpriteSet sprites;

        public Provider(SpriteSet sprites) {
            this.sprites = sprites;
        }

        @Override
        public Particle createParticle(SimpleParticleType type, ClientLevel level,
                                       double x, double y, double z,
                                       double dx, double dy, double dz) {
            return new CapaSparkParticle(level, x, y, z, dx, dy, dz, this.sprites);
        }
    }
}
