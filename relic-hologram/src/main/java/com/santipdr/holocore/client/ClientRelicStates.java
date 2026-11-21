package com.santipdr.holocore.client;

import com.santipdr.holocore.network.RelicStatePacket;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Ultimo estado recibido del servidor para cada portador. */
public final class ClientRelicStates {

    /**
     * @param active reliquia despierta
     * @param hit    gameTime del ultimo golpe
     * @param pulse  gameTime del ultimo pulso
     * @param release gameTime de la ultima liberacion
     * @param bump   gameTime de la ultima subida de nivel
     */
    public record Snapshot(boolean active, long hit, long pulse, long release, long bump) {
        /** Antes de recibir nada se asume activa: es el estado de una reliquia nueva. */
        public static final Snapshot DEFAULT = new Snapshot(true, 0L, 0L, 0L, 0L);
    }

    private static final Map<UUID, Snapshot> STATES = new ConcurrentHashMap<>();

    private ClientRelicStates() {
    }

    public static void accept(RelicStatePacket packet) {
        STATES.put(packet.player(),
                new Snapshot(packet.active(), packet.hit(), packet.pulse(), packet.release(), packet.bump()));
    }

    public static Snapshot get(UUID player) {
        return STATES.getOrDefault(player, Snapshot.DEFAULT);
    }

    public static void clear() {
        STATES.clear();
    }
}
