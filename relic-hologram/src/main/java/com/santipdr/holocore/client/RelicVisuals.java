package com.santipdr.holocore.client;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.world.entity.player.Player;

/**
 * Un juego modelo+renderer+animatable por portador.
 *
 * <p>Es importante que el {@link software.bernie.geckolib.model.GeoModel} no se
 * comparta: GeckoLib guarda en el modelo el acumulador de tiempo de animacion
 * ({@code animTime}), y con varios jugadores renderizados en el mismo frame cada
 * uno reescribiria el reloj del otro. Con una instancia por portador cada
 * reliquia mantiene su fase.</p>
 */
public final class RelicVisuals {

    /** Ticks sin renderizarse antes de liberar el modelo (re-equipar reinicia). */
    private static final int IDLE_EXPIRY_TICKS = 40;

    private static final Map<UUID, RelicVisual> VISUALS = new HashMap<>();

    private RelicVisuals() {
    }

    /** Modelo, renderer y estado de brillo (aura/anillo interpolados) del portador. */
    public record RelicVisual(RelicAnimatable animatable, RelicGeoRenderer renderer, RelicGlowState glow) {
    }

    public static RelicVisual visual(Player player) {
        return VISUALS.computeIfAbsent(player.getUUID(),
                uuid -> new RelicVisual(new RelicAnimatable(uuid),
                        new RelicGeoRenderer(new RelicGeoModel()),
                        new RelicGlowState()));
    }

    /**
     * Visual ya existente, sin crear nada: lo usa {@code /relic info} para
     * diagnosticar sin instanciar medio renderer si el jugador no lleva reliquia.
     */
    public static RelicVisual existing(Player player) {
        return VISUALS.get(player.getUUID());
    }

    public static void prune(long gameTime) {
        VISUALS.entrySet().removeIf(entry ->
                gameTime - entry.getValue().animatable().lastRenderTick() > IDLE_EXPIRY_TICKS);
    }

    public static void clear() {
        VISUALS.clear();
    }

    public static int size() {
        return VISUALS.size();
    }
}
