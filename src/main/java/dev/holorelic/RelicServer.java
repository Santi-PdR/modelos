package dev.holorelic;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;
import top.theillusivec4.curios.api.CuriosApi;

@Mod.EventBusSubscriber(modid = HoloRelic.ID)
public final class RelicServer {
    // Server-owned state and rate limit. Clients cannot name a target or fabricate animation events.
    private static final Map<UUID, State> STATES = new HashMap<>();
    private static long nextRevision;
    private static final String DORMANT = "holorelicDormant";
    private static final class State {
        boolean active;
        ItemStack stack;
        long revision, busyUntil, glitchAt;
        int action;
    }
    private static ItemStack equipped(ServerPlayer p) {
        return CuriosApi.getCuriosInventory(p).resolve()
                .flatMap(h -> h.findFirstCurio(HoloRelic.CORE.get()))
                .map(r -> r.stack()).orElse(ItemStack.EMPTY);
    }
    private static long nextGlitch(ServerPlayer p, long now) {
        int min = RelicConfig.GLITCH_MIN.get();
        int max = Math.max(min, RelicConfig.GLITCH_MAX.get());
        return now + 20L * (min + p.getRandom().nextInt(max - min + 1));
    }
    private static RelicNetwork.Snapshot snapshot(ServerPlayer p, State s) {
        return new RelicNetwork.Snapshot(p.getUUID(), s != null, s != null && s.active,
                s == null ? 0 : s.revision,
                s == null || p.level().getGameTime() >= s.busyUntil ? 0 : s.action, s == null ? 0 : s.busyUntil);
    }
    private static void broadcast(ServerPlayer p, State s) {
        RelicNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> p), snapshot(p, s));
    }
    private static void animate(ServerPlayer p, State s, int action, int duration) {
        long now = p.level().getGameTime();
        s.action = action; s.revision = ++nextRevision; s.busyUntil = now + duration;
        s.glitchAt = nextGlitch(p, s.busyUntil);
        broadcast(p, s);
    }
    public static boolean perform(ServerPlayer p, boolean pulse) {
        var stack = equipped(p);
        State s = STATES.get(p.getUUID());
        if (stack.isEmpty() || s == null || p.level().getGameTime() < s.busyUntil || (pulse && !s.active)) return false;
        if (pulse) animate(p, s, 3, 50);
        else {
            s.active = !s.active;
            stack.getOrCreateTag().putBoolean(DORMANT, !s.active);
            animate(p, s, s.active ? 1 : 2, s.active ? 62 : 46);
        }
        return true;
    }
    @SubscribeEvent public static void tick(TickEvent.PlayerTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.player instanceof ServerPlayer p)) return;
        var stack = equipped(p);
        State s = STATES.get(p.getUUID());
        if (stack.isEmpty()) {
            if (STATES.remove(p.getUUID()) != null) broadcast(p, null);
            return;
        }
        long now = p.level().getGameTime();
        if (s == null || s.stack != stack) {
            s = new State(); s.stack = stack; s.active = !stack.getOrCreateTag().getBoolean(DORMANT);
            STATES.put(p.getUUID(), s);
            animate(p, s, s.active ? 1 : 2, s.active ? 62 : 46);
        } else if (s.active && now >= s.busyUntil && now >= s.glitchAt) animate(p, s, 4, 22);
    }
    @SubscribeEvent public static void tracking(PlayerEvent.StartTracking e) {
        if (e.getEntity() instanceof ServerPlayer viewer && e.getTarget() instanceof ServerPlayer wearer) {
            RelicNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> viewer), snapshot(wearer, STATES.get(wearer.getUUID())));
        }
    }
    @SubscribeEvent public static void logout(PlayerEvent.PlayerLoggedOutEvent e) { STATES.remove(e.getEntity().getUUID()); }
    @SubscribeEvent public static void clonePlayer(PlayerEvent.Clone e) { STATES.remove(e.getEntity().getUUID()); }
    @SubscribeEvent public static void dimension(PlayerEvent.PlayerChangedDimensionEvent e) { STATES.remove(e.getEntity().getUUID()); }
    @SubscribeEvent public static void stopped(ServerStoppedEvent e) { STATES.clear(); }
    @SubscribeEvent public static void commands(RegisterCommandsEvent e) {
        var root = Commands.literal("relic");
        for (String name : new String[]{"toggle", "pulse"}) {
            root.then(Commands.literal(name).executes(ctx -> {
                var p = ctx.getSource().getPlayerOrException();
                if (perform(p, name.equals("pulse"))) return 1;
                ctx.getSource().sendFailure(Component.translatable("message.holorelic.unavailable"));
                return 0;
            }));
        }
        e.getDispatcher().register(root);
    }
    private RelicServer() {}
}
