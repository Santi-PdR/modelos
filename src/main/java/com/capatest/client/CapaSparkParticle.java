package com.capatest.client;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.Particle;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.ParticleRenderType;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.particle.TextureSheetParticle;
import net.minecraft.core.particles.SimpleParticleType;

/**
 * v1.23.0 — CHISPA EXCLUSIVA de la capa, con textura propia.
 *
 * El usuario pidió sustituir LAS PARTÍCULAS VANILLA por una partícula
 * personalizada: «chispas rectangulares pequeñas, verticales y
 * semitransparentes en color magenta/rosa neón con el centro brillante
 * (sin gravedad, flotando suavemente hacia arriba y desvaneciéndose),
 * generándose de forma sutil y dispersa alrededor de los bordes y las
 * puntas inferiores de la capa en lugar de acumularse detrás de la cabeza».
 *
 * El sprite (tools/texture_pipeline.py::build_spark_sprites) es una barra
 * de 6x12 texels con bordes translúcidos y centro casi blanco, sobre un
 * quad 16x16: se ve como un RECTÁNGULO VERTICAL, no como un cuadrado.
 * Tres frames dan un parpadeo suave. No hay gravedad, ni colisiones, ni
 * sonido, ni búsqueda de entidades. El presupuesto de emisión lo fija
 * CapaDeteriorerItem.spawnAura().
 */
public class CapaSparkParticle extends TextureSheetParticle {
    private final SpriteSet sprites;
    private final float baseSize;
    private final float drift;

    protected CapaSparkParticle(ClientLevel level,
                                double x, double y, double z,
                                double dx, double dy, double dz,
                                SpriteSet sprites) {
        super(level, x, y, z, dx, dy, dz);
        this.sprites = sprites;

        this.lifetime = 28 + this.random.nextInt(13);
        // El sprite ya lleva el color; no lo teñimos para conservar el
        // centro blanco y los bordes magenta semitransparentes.
        this.rCol = 1.0F;
        this.gCol = 1.0F;
        this.bCol = 1.0F;
        this.alpha = 0.0F;

        this.hasPhysics = false;
        this.gravity = 0.0F;                 // SIN gravedad
        this.friction = 0.96F;
        this.drift = (this.random.nextFloat() - 0.5F) * 0.0016F;
        // Sube suavemente; dx/dz son deriva mínima, no dispersión.
        this.setParticleSpeed(
                Math.copySign(Math.min(Math.abs(dx), 0.002D), dx),
                0.010D + Math.min(Math.abs(dy), 0.004D),
                Math.copySign(Math.min(Math.abs(dz), 0.002D), dz));

        this.scale(0.34F);
        this.baseSize = this.quadSize;
        this.pickSprite(sprites);
    }

    @Override
    public void tick() {
        super.tick();
        // Deriva lateral casi imperceptible, como una brasa flotando.
        this.xd += this.drift * Math.sin(this.age * 0.31F);
        float progress = Math.min(1.0F, (float) this.age / (float) this.lifetime);
        float fadeIn = Math.min(1.0F, progress * 7.0F);
        float fadeOut = Math.min(1.0F, (1.0F - progress) * 3.2F);
        // v1.29.0: PARPADEO (twinkle) de la chispa. Sobre el fadeIn/fadeOut
        // se suma un parpadeo rápido de alta frecuencia y baja amplitud,
        // para que no sea una partícula uniforme: parece una brasa viva
        // en vez de un cuadrado de alpha constante.
        // v1.31.0: se suma un SEGUNDO parpadeo a otra frecuencia y fase,
        // así el brillo de la brasa es irregular y vivo, no un seno
        // limpio y predecible.
        float twinkle = 0.18F * (float) Math.sin(this.age * 0.9F)
                + 0.08F * (float) Math.sin(this.age * 2.3F + 0.7F)
                // v1.32.0: TERCER parpadeo a frecuencia doble y muy baja
                // amplitud, con fase distinta: la brasa no es un seno
                // predecible, tiene el temblor irregular de una chispa viva.
                + 0.04F * (float) Math.sin(this.age * 4.1F + 2.3F);
        float cover = fadeIn * fadeOut;
        this.alpha = Math.min(1.0F, 0.72F * cover + twinkle * cover);   // semitransparente
        this.quadSize = this.baseSize * (1.0F - 0.22F * progress + 0.08F * twinkle);
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
            return new CapaSparkParticle(level, x, y, z, dx, dy, dz, this.sprites);
        }
    }
}
