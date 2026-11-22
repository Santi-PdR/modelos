package com.santipdr.holocore.client;

import com.santipdr.holocore.config.RelicConfig;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;

/**
 * Sonidos de la reliquia, con sonidos de <b>ametista de vanilla</b>: el mod no trae
 * ningun asset de audio.
 *
 * <p>Tres reglas, y las tres importan:</p>
 * <ul>
 *   <li>Solo suena la reliquia del <b>jugador local</b>. Las de otros portadores se
 *       ven, no se oyen: con cuatro jugadores cerca cada pulso seria un coro
 *       desafinado y sin forma de localizar de donde viene.</li>
 *   <li>Suena en la <b>cabeza del jugador</b> y no en la reliquia: el hombro esta a
 *       medio metro de la camara, y colocar el sonido ahi hace que el paneo salte al
 *       girar.</li>
 *   <li>Se apaga con {@code sound.events = false} o {@code sound.volume = 0}, y
 *       respeta el volumen de jugador porque va por {@link SoundSource#PLAYERS}.</li>
 * </ul>
 */
public final class RelicSounds {

    /** Despertar: la misma nota que el pulso, mas grave y mas larga. */
    private static final float AWAKE_PITCH = 1.00F;
    /** Dormir: bastante mas grave, se hunde. */
    private static final float SLEEP_PITCH = 0.55F;
    /** Pulso: agudo, corto, se oye por encima del combate. */
    private static final float PULSE_PITCH = 1.35F;

    private RelicSounds() {
    }

    static void awake(UUID wearer) {
        play(SoundEvents.AMETHYST_BLOCK_RESONATE, 0.90F, AWAKE_PITCH, wearer);
    }

    static void sleep(UUID wearer) {
        play(SoundEvents.AMETHYST_BLOCK_RESONATE, 0.70F, SLEEP_PITCH, wearer);
    }

    static void pulse(UUID wearer) {
        play(SoundEvents.AMETHYST_BLOCK_CHIME, 0.80F, PULSE_PITCH, wearer);
    }

    private static void play(SoundEvent sound, float gain, float pitch, UUID wearer) {
        if (!RelicConfig.EVENT_SOUND.get()) {
            return;
        }
        float volume = RelicConfig.SOUND_VOLUME.get().floatValue();
        if (volume <= 0.001F) {
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        LocalPlayer player = minecraft.player;
        if (player == null || minecraft.level == null || !player.getUUID().equals(wearer)) {
            return;
        }
        minecraft.level.playLocalSound(player.getX(), player.getEyeY(), player.getZ(), sound,
                SoundSource.PLAYERS, volume * gain, pitch, false);
    }
}
