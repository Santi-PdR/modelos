package com.santipdr.holocore.network;

import com.santipdr.holocore.common.RelicServer;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkEvent;

/** Acciones que el cliente puede pedir al servidor (tecla o comando). */
public record RelicActionPacket(Action action) {

    public enum Action {
        TOGGLE,
        PULSE,
        RELEASE
    }

    public void encode(FriendlyByteBuf buf) {
        buf.writeEnum(action);
    }

    public static RelicActionPacket decode(FriendlyByteBuf buf) {
        return new RelicActionPacket(buf.readEnum(Action.class));
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier) {
        NetworkEvent.Context context = contextSupplier.get();
        context.enqueueWork(() -> {
            ServerPlayer sender = context.getSender();
            if (sender == null) {
                return;
            }
            switch (action) {
                case TOGGLE -> RelicServer.toggle(sender);
                case PULSE -> RelicServer.pulse(sender);
                case RELEASE -> RelicServer.release(sender);
            }
        });
        context.setPacketHandled(true);
    }
}
