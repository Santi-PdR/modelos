package dev.holorelic;

import java.util.UUID;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;

public final class RelicNetwork {
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(HoloRelic.ID, "state"), () -> "1", "1"::equals, "1"::equals);

    public static void register() {
        CHANNEL.messageBuilder(Action.class, 0, NetworkDirection.PLAY_TO_SERVER)
                .encoder((p, b) -> b.writeBoolean(p.pulse))
                .decoder(b -> new Action(b.readBoolean()))
                .consumerMainThread((p, ctx) -> {
                    var player = ctx.get().getSender();
                    if (player != null) RelicServer.perform(player, p.pulse);
                    ctx.get().setPacketHandled(true);
                }).add();
        CHANNEL.messageBuilder(Snapshot.class, 1, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(Snapshot::encode).decoder(Snapshot::decode)
                .consumerMainThread(RelicNetwork::receive).add();
    }

    private static void receive(Snapshot packet, Supplier<NetworkEvent.Context> ctx) {
        // Client-only code is resolved exclusively on the physical client, safe on dedicated servers.
        DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                () -> () -> dev.holorelic.client.ClientState.receive(packet));
        ctx.get().setPacketHandled(true);
    }

    public record Action(boolean pulse) {}
    public record Snapshot(UUID wearer, boolean equipped, boolean active, long revision, int action, long actionUntil) {
        void encode(FriendlyByteBuf b) {
            b.writeUUID(wearer); b.writeBoolean(equipped); b.writeBoolean(active);
            b.writeLong(revision); b.writeVarInt(action); b.writeLong(actionUntil);
        }
        static Snapshot decode(FriendlyByteBuf b) {
            return new Snapshot(b.readUUID(), b.readBoolean(), b.readBoolean(), b.readLong(), b.readVarInt(), b.readLong());
        }
    }
    private RelicNetwork() {}
}
