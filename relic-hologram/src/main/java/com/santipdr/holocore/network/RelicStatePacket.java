package com.santipdr.holocore.network;

import java.util.UUID;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;

/**
 * Estado autoritativo del servidor para un portador concreto.
 *
 * @param active  reliquia despierta (true) o dormida (false)
 * @param hit     gameTime del ultimo golpe recibido
 * @param pulse   gameTime del ultimo energy_pulse pedido
 * @param release gameTime de la ultima liberacion
 * @param bump    gameTime de la ultima subida de nivel
 */
public record RelicStatePacket(UUID player, boolean active, long hit, long pulse, long release, long bump) {

    public void encode(FriendlyByteBuf buf) {
        buf.writeUUID(player);
        buf.writeBoolean(active);
        buf.writeLong(hit);
        buf.writeLong(pulse);
        buf.writeLong(release);
        buf.writeLong(bump);
    }

    public static RelicStatePacket decode(FriendlyByteBuf buf) {
        return new RelicStatePacket(buf.readUUID(), buf.readBoolean(),
                buf.readLong(), buf.readLong(), buf.readLong(), buf.readLong());
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier) {
        NetworkEvent.Context context = contextSupplier.get();
        context.enqueueWork(() ->
                // DistExecutor evita que el servidor dedicado intente resolver
                // clases de cliente al verificar esta clase.
                DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                        () -> () -> com.santipdr.holocore.client.ClientRelicStates.accept(this)));
        context.setPacketHandled(true);
    }
}
