package com.capatest.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.core.particles.SimpleParticleType;

/**
 * Brasa del aura: tres sprites suaves (núcleo, destello, halo) con aparición
 * y desaparición graduales.
 *
 * v1.3.0 la hace deliberadamente tranquila: el constructor de Particle
 * inyecta velocidad aleatoria y +0.1 de impulso vertical, así que aquí se
 * sobreescribe con una deriva mínima, gravedad negativa casi nula y sin
 * colisiones. El alpha máximo baja de 0.92 a 0.52 y el tamaño se reduce.
 */
public class CapaEmberParticle extends TextureSheetParticle {
    private final SpriteSet sprites;
    private final float baseSize;

    protected CapaEmberParticle(ClientLevel level,
                                double x, double y, double z,
                                double dx, double dy, double dz,
                                SpriteSet sprites) {
        super(level, x, y, z, dx, dy, dz);
        this.sprites = sprites;

        this.lifetime = 24 + this.random.nextInt(9);
        this.rCol = 0.88F + this.random.nextFloat() * 0.10F;
        this.gCol = 0.34F + this.random.nextFloat() * 0.08F;
        this.bCol = 0.78F + this.random.nextFloat() * 0.14F;
        this.alpha = 0.0F;

        // Sin el movimiento aleatorio de Particle y sin dispersal por el cielo.
        this.hasPhysics = false;
        this.gravity = -0.018F;             // ascenso de ~0.0007 bloques/tick
        this.friction = 0.985F;
        this.setParticleSpeed(
                Math.copySign(Math.min(Math.abs(dx), 0.003D), dx),
                0.004D + Math.min(Math.abs(dy), 0.003D),
                Math.copySign(Math.min(Math.abs(dz), 0.003D), dz));

        this.scale(0.72F);
        this.baseSize = this.quadSize;
        this.pickSprite(sprites);
    }

    @Override
    public void tick() {
        super.tick();

        float progress = Math.min(1.0F, (float) this.age / (float) this.lifetime);
        float fadeIn = Math.min(1.0F, progress * 6.0F);
        float fadeOut = Math.min(1.0F, (1.0F - progress) * 3.5F);
        this.alpha = 0.52F * fadeIn * fadeOut;
        this.quadSize = this.baseSize * (1.0F - 0.35F * progress);
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
