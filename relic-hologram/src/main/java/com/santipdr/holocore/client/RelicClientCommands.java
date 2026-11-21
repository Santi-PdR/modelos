package com.santipdr.holocore.client;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.santipdr.holocore.config.RelicConfig;
import com.santipdr.holocore.network.RelicActionPacket;
import com.santipdr.holocore.network.RelicNetwork;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.network.chat.Component;
import net.minecraftforge.common.ForgeConfigSpec;

/**
 * Comandos de cliente {@code /relic ...}. Los de posicion tocan la config en
 * memoria (no la guardan) para poder afinar mirando el resultado y luego copiar
 * los numeros al archivo; los de accion mandan un paquete al servidor.
 */
public final class RelicClientCommands {

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
        return 1;
    }

    private static void set(ForgeConfigSpec.DoubleValue value, double newValue) {
        value.set(newValue);
    }
}
