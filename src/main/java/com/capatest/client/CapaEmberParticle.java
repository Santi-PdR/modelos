package com.capatest.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.core.particles.SimpleParticleType;

/** Partícula de aura: brasa magenta/violeta con 3 sprites animados y desvanecimiento. */
public class CapaEmberParticle extends TextureSheetParticle {
    private final SpriteSet sprites;

    protected CapaEmberParticle(ClientLevel level,
                                double x, double y, double z,
                                double dx, double dy, double dz,
                                SpriteSet sprites) {
        super(level, x, y, z, dx, dy, dz);
        this.sprites = sprites;
        this.lifetime = 26 + this.random.nextInt(16);
        this.rCol = 1.0F;
        this.gCol = 0.42F;
        this.bCol = 0.88F;
        this.alpha = 0.92F;
        this.scale(1.25F);
        this.pickSprite(sprites);
    }

    @Override
    public void tick() {
        super.tick();
        this.alpha = 0.92F * Math.max(0.0F, 1.0F - (float) this.age / (float) this.lifetime);
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
            return new CapaEmberParticle(level, x, y, z, dx, dy, dz, this.sprites);
        }
    }
}
