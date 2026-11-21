package com.santipdr.holocore.client;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.santipdr.holocore.common.RelicAnimations;
import com.santipdr.holocore.common.RelicServer;
import com.santipdr.holocore.config.RelicConfig;
import com.santipdr.holocore.network.RelicActionPacket;
import com.santipdr.holocore.network.RelicNetwork;
import java.util.Locale;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.common.ForgeConfigSpec;

/**
 * Comandos de cliente {@code /relic ...}. Los de posicion tocan la config en
 * memoria (no la guardan) para poder afinar mirando el resultado y luego copiar
 * los numeros al archivo; los de accion mandan un paquete al servidor.
 */
public final class RelicClientCommands {

    /** Prefijo de todas las claves de animacion del modelo. */
    private static final String ANIM_PREFIX = "animation.relic.";

    private RelicClientCommands() {
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("relic")
                .then(Commands.literal("offset")
                        .then(Commands.argument("x", DoubleArgumentType.doubleArg(-32, 32))
                                .then(Commands.argument("y", DoubleArgumentType.doubleArg(-48, 48))
                                        .then(Commands.argument("z", DoubleArgumentType.doubleArg(-24, 48))
                                                .executes(ctx -> {
                                                    set(RelicConfig.OFFSET_X, ctx.getArgument("x", Double.class));
                                                    set(RelicConfig.OFFSET_Y, ctx.getArgument("y", Double.class));
                                                    set(RelicConfig.OFFSET_Z, ctx.getArgument("z", Double.class));
                                                    return info(ctx.getSource());
                                                })))))
                .then(Commands.literal("scale")
                        .then(Commands.argument("value", DoubleArgumentType.doubleArg(0.1, 4.0))
                                .executes(ctx -> {
                                    set(RelicConfig.SCALE, ctx.getArgument("value", Double.class));
                                    return info(ctx.getSource());
                                })))
                .then(Commands.literal("side")
                        .then(Commands.argument("side", StringArgumentType.word())
                                .suggests((ctx, builder) ->
                                        SharedSuggestionProvider.suggest(new String[]{"left", "right"}, builder))
                                .executes(ctx -> {
                                    String value = StringArgumentType.getString(ctx, "side");
                                    if (!value.equalsIgnoreCase("left") && !value.equalsIgnoreCase("right")) {
                                        ctx.getSource().sendFailure(Component.translatable("message.holocore.bad_side"));
                                        return 0;
                                    }
                                    RelicConfig.SHOULDER.set(value.equalsIgnoreCase("left")
                                            ? RelicConfig.Shoulder.LEFT
                                            : RelicConfig.Shoulder.RIGHT);
                                    return info(ctx.getSource());
                                })))
                .then(Commands.literal("quality")
                        .then(Commands.argument("quality", StringArgumentType.word())
                                .suggests((ctx, builder) ->
                                        SharedSuggestionProvider.suggest(new String[]{"full", "lite"}, builder))
                                .executes(ctx -> {
                                    String value = StringArgumentType.getString(ctx, "quality");
                                    if (!value.equalsIgnoreCase("full") && !value.equalsIgnoreCase("lite")) {
                                        ctx.getSource().sendFailure(Component.translatable("message.holocore.bad_quality"));
                                        return 0;
                                    }
                                    RelicConfig.QUALITY.set(value.equalsIgnoreCase("lite")
                                            ? RelicConfig.Quality.LITE
                                            : RelicConfig.Quality.FULL);
                                    return info(ctx.getSource());
                                })))
                .then(Commands.literal("toggle").executes(ctx -> action(ctx.getSource(),
                        RelicActionPacket.Action.TOGGLE)))
                .then(Commands.literal("pulse").executes(ctx -> action(ctx.getSource(),
                        RelicActionPacket.Action.PULSE)))
                .then(Commands.literal("release").executes(ctx -> action(ctx.getSource(),
                        RelicActionPacket.Action.RELEASE)))
                .then(Commands.literal("anim")
                        .executes(ctx -> animList(ctx.getSource()))
                        .then(Commands.argument("nombre", StringArgumentType.word())
                                .suggests((ctx, builder) ->
                                        SharedSuggestionProvider.suggest(shortNames(), builder))
                                .executes(ctx -> anim(ctx.getSource(),
                                        StringArgumentType.getString(ctx, "nombre")))))
                .then(Commands.literal("stats")
                        .executes(ctx -> stats(ctx.getSource()))
                        .then(Commands.literal("reset").executes(ctx -> statsReset(ctx.getSource()))))
                .then(Commands.literal("info").executes(ctx -> info(ctx.getSource()))));
    }

    private static int action(CommandSourceStack source, RelicActionPacket.Action action) {
        RelicNetwork.sendToServer(new RelicActionPacket(action));
        source.sendSuccess(() -> Component.translatable("message.holocore.sent",
                Component.translatable("message.holocore.action." + action.name().toLowerCase()))
                .withStyle(ChatFormatting.AQUA), false);
        return 1;
    }

    private static int info(CommandSourceStack source) {
        String shoulder = RelicConfig.SHOULDER.get() == RelicConfig.Shoulder.LEFT ? "left" : "right";
        String quality = RelicConfig.QUALITY.get() == RelicConfig.Quality.LITE ? "lite" : "full";
        Component message = Component.translatable("message.holocore.info",
                        String.format("%.2f", RelicConfig.OFFSET_X.get()),
                        String.format("%.2f", RelicConfig.OFFSET_Y.get()),
                        String.format("%.2f", RelicConfig.OFFSET_Z.get()),
                        String.format("%.2f", RelicConfig.SCALE.get()),
                        shoulder, quality)
                .withStyle(ChatFormatting.AQUA);
        source.sendSuccess(() -> message, false);
        source.sendSuccess(RelicClientCommands::diag, false);
        source.sendSuccess(RelicClientCommands::glowLine, false);
        return 1;
    }

    /**
     * Tercera linea de {@code /relic info}: las intensidades que estan mandando
     * ahora mismo. Sirve para afinar sin abrir el archivo de config.
     */
    private static Component glowLine() {
        String valores = String.format(Locale.ROOT, "aura %.2f · halo %.2f · glsl %.2f · anillo %.2f",
                RelicConfig.AURA_INTENSITY.get(), RelicConfig.HALO_INTENSITY.get(),
                RelicConfig.SHADER_INTENSITY.get(), RelicConfig.RING_INTENSITY.get());
        Component tinte = Component.translatable(RelicConfig.AURA_TINT.get()
                ? "message.holocore.on"
                : "message.holocore.off");
        return Component.translatable("message.holocore.glow", valores, tinte)
                .withStyle(ChatFormatting.DARK_AQUA);
    }

    /**
     * Segunda linea de {@code /relic info}: lo que no se puede adivinar mirando.
     * El estado en vivo sale del visual del jugador local (que existe desde el
     * primer tick con la reliquia puesta, se dibuje o no) y el GLSL dice <b>por
     * que</b> esta apagado cuando lo esta: config, shaderpack o compilacion
     * fallida.
     */
    private static Component diag() {
        String state = "-";
        String flash = "-";
        RelicVisuals.RelicVisual visual = localVisual();
        if (visual != null) {
            state = visual.animatable().loopState().name().toLowerCase(Locale.ROOT);
            flash = String.format(Locale.ROOT, "%.0f%%", visual.glow().flashScaled() * 100.0F);
        }
        return Component.translatable("message.holocore.diag", state, flash, glslStatus())
                .withStyle(ChatFormatting.DARK_AQUA);
    }

    private static Component glslStatus() {
        if (!RelicConfig.SHADER_GLOW.get()) {
            return Component.translatable("message.holocore.glsl.config");
        }
        if (RelicShaders.shaderPackActive()) {
            return Component.translatable("message.holocore.glsl.pack");
        }
        if (RelicShaders.shader() == null) {
            return Component.translatable("message.holocore.glsl.failed");
        }
        return Component.translatable("message.holocore.glsl.on");
    }

    /**
     * Visual del jugador local. Si no existe pero lleva la reliquia puesta, se
     * crea: el camino de tick lo hace en el primer tick con la reliquia encima,
     * asi que esto solo cubre el hueco de ese tick (y evita que {@code info} y
     * {@code anim} contesten "-" o "no equipada" por una carrera de un tick).
     */
    private static RelicVisuals.RelicVisual localVisual() {
        Player player = Minecraft.getInstance().player;
        if (player == null) {
            return null;
        }
        RelicVisuals.RelicVisual visual = RelicVisuals.existing(player);
        if (visual == null && RelicServer.findRelic(player).isPresent()) {
            visual = RelicVisuals.visual(player);
        }
        return visual;
    }

    /**
     * {@code /relic stats}: cuanto cuesta de verdad dibujar la reliquia.
     *
     * <p>Todo lo que cambio en 1.0.16 y 1.0.17 es invisible: el halo sigue
     * brillando igual. Estas cifras son la unica forma de ver el ahorro, y de
     * paso de comprobar que los pases que se dibujan son los que la config
     * permite (1 sin nada, 4 con base, emisivo, halo y GLSL).</p>
     */
    private static int stats(CommandSourceStack source) {
        long dibujos = RelicRenderStats.draws();
        double segundos = Math.max(0.001, RelicRenderStats.seconds());
        String porSegundo = dibujos == 0 ? "0" : String.format(Locale.ROOT, "%.0f", dibujos / segundos);
        String pases = dibujos == 0 ? "-" : String.format(Locale.ROOT, "%.2f",
                (double) RelicRenderStats.passes() / dibujos);
        String modelo = String.format(Locale.ROOT, "%.2f", RelicRenderStats.modelMillis());
        String aura = String.format(Locale.ROOT, "%.2f", RelicRenderStats.auraMillis());
        String ventana = String.format(Locale.ROOT, "%.1f", segundos);
        source.sendSuccess(() -> Component.translatable("message.holocore.stats",
                RelicVisuals.size(), porSegundo, pases).withStyle(ChatFormatting.AQUA), false);
        source.sendSuccess(() -> Component.translatable("message.holocore.stats_time",
                modelo, aura, dibujos, ventana).withStyle(ChatFormatting.DARK_AQUA), false);
        return 1;
    }

    private static int statsReset(CommandSourceStack source) {
        RelicRenderStats.reset();
        source.sendSuccess(() -> Component.translatable("message.holocore.stats_reset")
                .withStyle(ChatFormatting.AQUA), false);
        return 1;
    }

    /**
     * Nombres cortos (sin {@code animation.relic.}) para las sugerencias: son las
     * claves del JSON, que es lo que documenta el README.
     */
    private static String[] shortNames() {
        return RelicAnimations.ALL_NAMES.stream()
                .map(nombre -> nombre.startsWith(ANIM_PREFIX)
                        ? nombre.substring(ANIM_PREFIX.length())
                        : nombre)
                .toArray(String[]::new);
    }

    private static int anim(CommandSourceStack source, String nombre) {
        if (nombre.equalsIgnoreCase("list")) {
            return animList(source);
        }
        RelicVisuals.RelicVisual visual = localVisual();
        if (visual == null) {
            source.sendFailure(Component.translatable("message.holocore.not_equipped"));
            return 0;
        }
        String completo = nombre.startsWith(ANIM_PREFIX) ? nombre : ANIM_PREFIX + nombre;
        if (!visual.animatable().play(completo)) {
            source.sendFailure(Component.translatable("message.holocore.anim_unknown", nombre));
            return 0;
        }
        source.sendSuccess(() -> Component.translatable("message.holocore.anim", nombre)
                .withStyle(ChatFormatting.AQUA), false);
        return 1;
    }

    private static int animList(CommandSourceStack source) {
        String[] nombres = shortNames();
        // Dos lineas de diez: veinte nombres en una sola se cortan mal en el chat.
        for (int desde = 0; desde < nombres.length; desde += 10) {
            String trozo = String.join(", ",
                    java.util.Arrays.copyOfRange(nombres, desde, Math.min(desde + 10, nombres.length)));
            source.sendSuccess(() -> Component.translatable("message.holocore.anim_list", trozo)
                    .withStyle(ChatFormatting.DARK_AQUA), false);
        }
        return 1;
    }

    private static void set(ForgeConfigSpec.DoubleValue value, double newValue) {
        value.set(newValue);
    }
}
