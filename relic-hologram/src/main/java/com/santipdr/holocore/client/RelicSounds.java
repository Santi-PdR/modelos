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
    /** Volumen de base del aviso de cambio de estado (1.0.58). */
    private static final float MOOD_GAIN = 0.55F;
    /** El pulso es el mismo tono del estado, una cuarta por encima (1.0.59). */
    private static final float PULSE_INTERVAL = 1.25F;
    /** Tope del pulso: por encima de 2.0 la ametista se convierte en un pitido. */
    private static final float PULSE_MAX = 2.0F;
    /** Bajo el agua el sonido se apaga, como se apaga la luz (1.0.59). */
    private static final float SUBMERGED_GAIN = 0.45F;
    private static final float SUBMERGED_PITCH = 0.85F;

    private RelicSounds() {
    }

    static void awake(UUID wearer) {
        play(SoundEvents.AMETHYST_BLOCK_RESONATE, 0.90F, AWAKE_PITCH, wearer);
    }

    static void sleep(UUID wearer) {
        play(SoundEvents.AMETHYST_BLOCK_RESONATE, 0.70F, SLEEP_PITCH, wearer);
    }

    /**
     * Pulso: el tono del estado, una cuarta por encima (1.0.59). Antes iba siempre
     * a 1.35 y sonaba igual ardiendo que en el vacio, que es justo lo que no debe
     * pasar cuando el color ya dice cual es cual.
     */
    static void pulse(UUID wearer, RelicAnimatable.Mood mood) {
        float pitch = Math.min(PULSE_MAX, pitchFor(mood) * PULSE_INTERVAL);
        applySubmerged(mood);
        play(SoundEvents.AMETHYST_BLOCK_CHIME, 0.80F, pitch, wearer);
    }

    /**
     * Bajo el agua el sonido se apaga, igual que el agua se lleva la luz del aura:
     * menos volumen y el tono un poco por debajo, que es lo que suena a "desde el
     * fondo". Se guarda en campos porque {@link #play} no recibe el estado.
     */
    private static float submergedGain = 1.0F;
    private static float submergedPitch = 1.0F;

    private static void applySubmerged(RelicAnimatable.Mood mood) {
        boolean water = mood == RelicAnimatable.Mood.SUBMERGED;
        submergedGain = water ? SUBMERGED_GAIN : 1.0F;
        submergedPitch = water ? SUBMERGED_PITCH : 1.0F;
    }

    /**
     * Cambio de estado de brillo: un tono distinto por estado (1.0.58). El color ya
     * cambia; el oido lo pilla antes que la vista, sobre todo con el estado en la
     * espalda, y es la forma de saber que paso algo sin girarse.
     *
     * <p>La tabla es de tono, no de melodia: ardiendo y el Nether van graves (peso),
     * herido tambien; el hielo y el End van agudos y finos. Los estados graves usan
     * la nota larga de ametista y los agudos el cascabel corto, asi que se distinguen
     * a la primera sin mirar.</p>
     */
    static void mood(UUID wearer, RelicAnimatable.Mood mood) {
        float pitch = pitchFor(mood);
        // Los graves resuenan; los agudos tintinean. El corte esta en 0.90, que es
        // donde la tabla deja de sonar a "pesado".
        SoundEvent sound = pitch < 0.90F
                ? SoundEvents.AMETHYST_BLOCK_RESONATE
                : SoundEvents.AMETHYST_BLOCK_CHIME;
        play(sound, MOOD_GAIN, pitch, wearer);
    }

    /** Tono de cada estado de brillo. Sin {@code default}: el CI exige los trece. */
    static float pitchFor(RelicAnimatable.Mood mood) {
        return switch (mood) {
            case NEUTRAL -> 1.00F;
            // Dos reliquias que se oyen: una quinta por encima, que suena a respuesta.
            case RESONANT -> 1.20F;
            case STORM -> 1.45F;
            // Herido y ardiendo son los dos estados de dano: graves y con peso.
            case WOUNDED -> 0.72F;
            case DARK -> 1.10F;
            case RAIN -> 0.95F;
            case NIGHT -> 0.85F;
            case SUBMERGED -> 0.66F;
            case PORTAL -> 1.28F;
            case BURNING -> 0.58F;
            // El frio es fino: el tono mas agudo fuera del End.
            case FREEZING -> 1.55F;
            // Alarma: agudo y cortante, por debajo del hielo.
            case HUNTED -> 1.34F;
            case NETHER -> 0.62F;
            case END -> 1.62F;
        };
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
                SoundSource.PLAYERS, volume * gain * submergedGain, pitch * submergedPitch, false);
    }
}
