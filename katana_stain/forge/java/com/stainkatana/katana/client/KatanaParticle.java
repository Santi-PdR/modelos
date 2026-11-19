package com.stainkatana.katana.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.core.particles.SimpleParticleType;

/** Sprites propios animados; sin física de bloques y con presupuestos acotados. */
public final class KatanaParticle extends TextureSheetParticle {
    private final SpriteSet sprites;
    private final int style;
    private final float initialSize;
    private KatanaParticle(ClientLevel level, double x, double y, double z,
                           double dx, double dy, double dz, SpriteSet sprites, int style) {
        super(level, x, y, z, dx, dy, dz);
        this.sprites = sprites; this.style = style;
        this.hasPhysics = false;
        this.lifetime = style == 0 ? 8 : style == 1 ? 15 : 12;
        this.quadSize = style == 0 ? 1.2F : style == 1 ? 0.12F + this.random.nextFloat() * 0.10F : 1.15F;
        this.initialSize = this.quadSize;
        this.gravity = style == 1 ? 0.12F : 0;
        this.friction = 0.93F;
        if (style == 1) {
            this.xd = dx + (this.random.nextDouble() - 0.5) * 0.06;
            this.yd = dy + this.random.nextDouble() * 0.06;
            this.zd = dz + (this.random.nextDouble() - 0.5) * 0.06;
            this.roll = this.random.nextFloat() * 6.28F;
            this.oRoll = this.roll;
        } else {
            this.xd = 0; this.yd = 0; this.zd = 0;
        }
        this.setSpriteFromAge(sprites);
    }
    @Override public void tick() {
        super.tick();
        if (this.removed) return;
        float progress = (float)this.age / this.lifetime;
        this.alpha = Math.min(1F, (1F-progress)*4F);
        if (style == 1) {
            this.oRoll = this.roll;
            this.roll += 0.07F;
            this.quadSize = this.initialSize * (1F-0.35F*progress);
        }
        this.setSpriteFromAge(this.sprites);
    }
    @Override public ParticleRenderType getRenderType() { return ParticleRenderType.PARTICLE_SHEET_TRANSLUCENT; }

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
