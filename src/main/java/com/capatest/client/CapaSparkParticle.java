package com.capatest.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.core.particles.SimpleParticleType;

/** Chispa rosa vertical que conserva la velocidad enviada por el servidor. */
public class CapaSparkParticle extends TextureSheetParticle {
    private final SpriteSet sprites;
    private final float baseSize;
    private final float streak;
    private final float phase;

    protected CapaSparkParticle(ClientLevel level,
                                double x, double y, double z,
                                double dx, double dy, double dz,
                                SpriteSet sprites) {
        super(level, x, y, z);
        this.sprites = sprites;
        double horizontal = Math.hypot(dx, dz);
        this.streak = (float) Math.min(1.0D, horizontal / 0.035D);
        double clamp = horizontal > 0.04D ? 0.04D / horizontal : 1.0D;
        this.setParticleSpeed(dx * clamp, Math.max(0.007D, Math.min(0.021D, dy)), dz * clamp);
        this.lifetime = 39 - Math.round(13 * this.streak) + this.random.nextInt(9);
        this.alpha = 0.0F;
        this.hasPhysics = false;
        this.gravity = 0.0F;
        this.friction = 0.94F;
        this.phase = this.random.nextFloat() * 3.14F;
        this.scale(0.28F + 0.10F * this.streak + 0.15F * this.random.nextFloat());
        this.baseSize = this.quadSize;
        this.setSprite(sprites.get(0, 2));
    }

    @Override
    public void tick() {
        super.tick();
        float p = Math.min(1.0F, (float) this.age / this.lifetime);
        float fade = Math.min(1.0F, p * 6.0F) * Math.min(1.0F, (1.0F - p) * 2.4F);
        float glint = 0.5F + 0.5F * (float) Math.sin(this.phase + p * 9.0F);
        this.alpha = (0.66F + 0.08F * glint + 0.09F * this.streak) * fade;
        this.quadSize = this.baseSize * (1.0F - 0.37F * p + 0.06F * glint);
        // La cara rosa pierde intensidad al envejecer, sin halo blanco.
        this.rCol = 1.0F - 0.19F * p;
        this.gCol = 0.98F - 0.22F * p;
        this.bCol = 1.0F;
        // Three equal phases; vanilla age interpolation hardly uses the last sprite.
        this.setSprite(this.sprites.get(Math.min(2, 3 * this.age / this.lifetime), 2));
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
