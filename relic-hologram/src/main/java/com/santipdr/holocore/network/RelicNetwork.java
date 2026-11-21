package com.santipdr.holocore.network;

import com.santipdr.holocore.HoloCore;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.network.simple.SimpleChannel;

/**
 * Canal minimo: solo viaja el estado de la reliquia (activa/dormida y sellos de
 * tiempo de los eventos) y las acciones del jugador. Nada por tick.
 */
public final class RelicNetwork {

    private static final String PROTOCOL = "1";

    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(HoloCore.MOD_ID, "main"),
            () -> PROTOCOL,
            PROTOCOL::equals,
            PROTOCOL::equals);

    private RelicNetwork() {
    }

    public static void register() {
        int id = 0;
        CHANNEL.messageBuilder(RelicActionPacket.class, id++, NetworkDirection.PLAY_TO_SERVER)
                .encoder(RelicActionPacket::encode)
                .decoder(RelicActionPacket::decode)
                .consumerMainThread(RelicActionPacket::handle)
                .add();

        CHANNEL.messageBuilder(RelicStatePacket.class, id++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(RelicStatePacket::encode)
                .decoder(RelicStatePacket::decode)
                .consumerMainThread(RelicStatePacket::handle)
                .add();
    }

    public static void sendToServer(Object message) {
        CHANNEL.sendToServer(message);
    }

    public static void toAll(Object message) {
        CHANNEL.send(PacketDistributor.ALL.noArg(), message);
    }

    public static void toPlayer(ServerPlayer player, Object message) {
        CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), message);
    }
}
