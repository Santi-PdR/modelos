package com.capatest.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.core.particles.SimpleParticleType;

/**
 * Mota fría de Blight Star (v1.9.0).
 *
 * Es deliberadamente más pequeña, lenta y azulada que {@link CapaEmberParticle}.
 * En vez de subir en línea recta, deriva en una órbita minúscula alrededor de
 * su punto de aparición: refuerza el motivo de estrella marchita sin llenar el
 * cielo de partículas. Usa tres sprites propios de 16x16 y un alpha bajo.
 */
public class CapaBlightParticle extends TextureSheetParticle {
    private final SpriteSet sprites;
    private final float baseSize;
    private final double orbit;

    protected CapaBlightParticle(ClientLevel level,
                                 double x, double y, double z,
                                 double dx, double dy, double dz,
                                 SpriteSet sprites) {
        super(level, x, y, z, dx, dy, dz);
        this.sprites = sprites;
        this.orbit = this.random.nextDouble() * Math.PI * 2.0D;

        this.lifetime = 30 + this.random.nextInt(11);
        this.rCol = 0.40F + this.random.nextFloat() * 0.12F;
        this.gCol = 0.82F + this.random.nextFloat() * 0.14F;
        this.bCol = 0.92F + this.random.nextFloat() * 0.08F;
        this.alpha = 0.0F;

        this.hasPhysics = false;
        this.gravity = -0.006F;
        this.friction = 0.992F;
        this.setParticleSpeed(0.0D, 0.0025D, 0.0D);

        this.scale(0.60F);
        this.baseSize = this.quadSize;
        this.pickSprite(sprites);
    }

    @Override
    public void tick() {
        super.tick();
        double phase = this.orbit + this.age * 0.16D;
        this.setParticleSpeed(Math.sin(phase) * 0.0018D, 0.0025D,
                Math.cos(phase) * 0.0018D);

        float progress = Math.min(1.0F, (float) this.age / (float) this.lifetime);
        float fadeIn = Math.min(1.0F, progress * 5.0F);
        float fadeOut = Math.min(1.0F, (1.0F - progress) * 3.0F);
        this.alpha = 0.46F * fadeIn * fadeOut;
        this.quadSize = this.baseSize * (1.0F - 0.28F * progress);
        this.setSpriteFromAge(this.sprites);
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
            return new CapaBlightParticle(level, x, y, z, dx, dy, dz, this.sprites);
        }
    }
}
