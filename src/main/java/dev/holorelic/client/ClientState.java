package dev.holorelic.client;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import dev.holorelic.RelicNetwork;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = "holorelic", value = Dist.CLIENT)
public final class ClientState {
    private static final Map<UUID, RelicNetwork.Snapshot> STATES = new HashMap<>();
    public static RelicNetwork.Snapshot get(UUID id) { return STATES.get(id); }
    public static void receive(RelicNetwork.Snapshot packet) {
        if (packet.equipped()) STATES.put(packet.wearer(), packet);
        else { STATES.remove(packet.wearer()); RelicRenderer.forget(packet.wearer()); }
    }
    @SubscribeEvent public static void logout(ClientPlayerNetworkEvent.LoggingOut e) {
        STATES.clear(); RelicRenderer.clear();
    }
    private ClientState() {}
}
