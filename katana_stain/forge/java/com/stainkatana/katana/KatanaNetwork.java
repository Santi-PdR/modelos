package com.stainkatana.katana;

import com.stainkatana.StainKatanaMod;
import java.util.Optional;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;

/** Solo acepta un identificador de habilidad, nunca blancos ni daño enviados por el cliente. */
public final class KatanaNetwork {
    private static final String VERSION = "6";
    public static final SimpleChannel CHANNEL = NetworkRegistry.ChannelBuilder
            .named(new ResourceLocation(StainKatanaMod.MOD_ID, "abilities"))
            .networkProtocolVersion(() -> VERSION).clientAcceptedVersions(VERSION::equals)
            .serverAcceptedVersions(VERSION::equals).simpleChannel();
    private KatanaNetwork() { }
    public static void init() {
        CHANNEL.registerMessage(0, AbilityMessage.class, AbilityMessage::encode,
                AbilityMessage::decode, AbilityMessage::handle, Optional.of(NetworkDirection.PLAY_TO_SERVER));
        CHANNEL.registerMessage(1, AnimationMessage.class, AnimationMessage::encode,
                AnimationMessage::decode, AnimationMessage::handle, Optional.of(NetworkDirection.PLAY_TO_CLIENT));
        CHANNEL.registerMessage(2, VisualMessage.class, VisualMessage::encode,
                VisualMessage::decode, VisualMessage::handle, Optional.of(NetworkDirection.PLAY_TO_CLIENT));
    }
    public record AbilityMessage(int ability) {
        public static void encode(AbilityMessage msg, FriendlyByteBuf buf) { buf.writeVarInt(msg.ability); }
        public static AbilityMessage decode(FriendlyByteBuf buf) { return new AbilityMessage(buf.readVarInt()); }
        public static void handle(AbilityMessage msg, Supplier<NetworkEvent.Context> supplier) {
            NetworkEvent.Context context = supplier.get();
            context.enqueueWork(() -> {
                ServerPlayer player = context.getSender();
                if (player != null && msg.ability >= 0 && msg.ability < 3)
                    KatanaAbilities.activate(player, msg.ability);
            });
            context.setPacketHandled(true);
        }
    }
    public static void broadcastAnimation(ServerPlayer player, int ability) {
        CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> player),
                new AnimationMessage(player.getId(), ability));
    }
    public record AnimationMessage(int entityId, int ability) {
        public static void encode(AnimationMessage msg, FriendlyByteBuf buf) {
            buf.writeVarInt(msg.entityId); buf.writeVarInt(msg.ability);
        }
        public static AnimationMessage decode(FriendlyByteBuf buf) {
            return new AnimationMessage(buf.readVarInt(), buf.readVarInt());
        }
        public static void handle(AnimationMessage msg, Supplier<NetworkEvent.Context> supplier) {
            NetworkEvent.Context context = supplier.get();
            context.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                    () -> () -> com.stainkatana.katana.client.KatanaAnimations.play(msg.entityId, msg.ability)));
            context.setPacketHandled(true);
        }
    }
    public static void broadcastVisual(ServerPlayer player, double x, double y, double z, int style) {
        CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> player),
                new VisualMessage(player.getId(), x, y, z, player.getYRot(), style, player.getMainArm() == net.minecraft.world.entity.HumanoidArm.LEFT));
    }
    public record VisualMessage(int entityId, double x, double y, double z, float yaw, int style, boolean leftHanded) {
        public static void encode(VisualMessage msg, FriendlyByteBuf buf) {
            buf.writeVarInt(msg.entityId); buf.writeDouble(msg.x); buf.writeDouble(msg.y); buf.writeDouble(msg.z);
            buf.writeFloat(msg.yaw); buf.writeVarInt(msg.style); buf.writeBoolean(msg.leftHanded);
        }
        public static VisualMessage decode(FriendlyByteBuf buf) {
            return new VisualMessage(buf.readVarInt(), buf.readDouble(), buf.readDouble(), buf.readDouble(), buf.readFloat(), buf.readVarInt(), buf.readBoolean());
        }
        public static void handle(VisualMessage msg, Supplier<NetworkEvent.Context> supplier) {
            NetworkEvent.Context context = supplier.get();
            context.enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                    () -> () -> com.stainkatana.katana.client.KatanaVisuals.spawn(msg.entityId, msg.x, msg.y, msg.z, msg.yaw, msg.style, msg.leftHanded)));
            context.setPacketHandled(true);
        }
    }
}
