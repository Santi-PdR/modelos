package com.santipdr.holocore.client;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.santipdr.holocore.common.RelicAnimations;
import com.santipdr.holocore.common.RelicServer;
import com.santipdr.holocore.config.RelicConfig;
import com.santipdr.holocore.network.RelicActionPacket;
import com.santipdr.holocore.network.RelicNetwork;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
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
                                                    set(RelicConfig.OFFSET_X, "placement.offsetX", ctx.getArgument("x", Double.class));
                                                    set(RelicConfig.OFFSET_Y, "placement.offsetY", ctx.getArgument("y", Double.class));
                                                    set(RelicConfig.OFFSET_Z, "placement.offsetZ", ctx.getArgument("z", Double.class));
                                                    return info(ctx.getSource());
                                                })))))
                .then(Commands.literal("scale")
                        .then(Commands.argument("value", DoubleArgumentType.doubleArg(0.1, 4.0))
                                .executes(ctx -> {
                                    set(RelicConfig.SCALE, "placement.scale", ctx.getArgument("value", Double.class));
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
                                    markUnsaved("placement.shoulder");
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
                                    markUnsaved("visuals.quality");
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
                .then(Commands.literal("reset")
                        .executes(ctx -> reset(ctx.getSource()))
                        .then(Commands.argument("clave", StringArgumentType.word())
                                .suggests((ctx, builder) ->
                                        SharedSuggestionProvider.suggest(tweakKeys(), builder))
                                .executes(ctx -> resetOne(ctx.getSource(),
                                        StringArgumentType.getString(ctx, "clave")))))
                .then(Commands.literal("preview")
                        .executes(ctx -> preview(ctx.getSource(), null))
                        .then(Commands.argument("distancia", DoubleArgumentType.doubleArg(0.5D, 6.0D))
                                .executes(ctx -> preview(ctx.getSource(),
                                        ctx.getArgument("distancia", Double.class)))))
                .then(Commands.literal("save").executes(ctx -> save(ctx.getSource())))
                .then(Commands.literal("mood")
                        .executes(ctx -> moodShow(ctx.getSource()))
                        .then(Commands.argument("estado", StringArgumentType.word())
                                .suggests((ctx, builder) -> SharedSuggestionProvider.suggest(
                                        MOOD_NAMES, builder))
                                .executes(ctx -> moodSet(ctx.getSource(),
                                        StringArgumentType.getString(ctx, "estado")))))
                .then(Commands.literal("set")
                        .executes(ctx -> setList(ctx.getSource()))
                        .then(Commands.argument("clave", StringArgumentType.word())
                                .suggests((ctx, builder) ->
                                        SharedSuggestionProvider.suggest(tweakKeys(), builder))
                                .executes(ctx -> setShow(ctx.getSource(),
                                        StringArgumentType.getString(ctx, "clave")))
                                .then(Commands.argument("valor", StringArgumentType.word())
                                        .executes(ctx -> setApply(ctx.getSource(),
                                                StringArgumentType.getString(ctx, "clave"),
                                                StringArgumentType.getString(ctx, "valor"))))))
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
        // Locale.ROOT: con el idioma del juego en español String.format daria
        // "6,00" y esos numeros se copian al holocore-client.toml, donde la coma
        // rompe el valor. El resto de lineas ya lo hacia asi.
        Component message = Component.translatable("message.holocore.info",
                        String.format(Locale.ROOT, "%.2f", RelicConfig.OFFSET_X.get()),
                        String.format(Locale.ROOT, "%.2f", RelicConfig.OFFSET_Y.get()),
                        String.format(Locale.ROOT, "%.2f", RelicConfig.OFFSET_Z.get()),
                        String.format(Locale.ROOT, "%.2f", RelicConfig.SCALE.get()),
                        shoulder, quality)
                .withStyle(ChatFormatting.AQUA);
        source.sendSuccess(() -> message, false);
        source.sendSuccess(RelicClientCommands::diag, false);
        source.sendSuccess(RelicClientCommands::glowLine, false);
        RelicVisuals.RelicVisual actual = localVisual();
        if (actual != null && actual.animatable().mood() != RelicAnimatable.Mood.NEUTRAL) {
            // Los estados de brillo (herido, tormenta, resonancia) no se deducen
            // mirando: si el aura se ha puesto roja hay que saber por que.
            Component nombre = Component.translatable("message.holocore.state."
                    + actual.animatable().mood().name().toLowerCase(Locale.ROOT));
            source.sendSuccess(() -> Component.translatable("message.holocore.mood", nombre)
                    .withStyle(ChatFormatting.GOLD), false);
        }
        if (RelicClientEvents.previewEnabled()) {
            // Sin esto, la reliquia flotando delante de la camara parece un fallo
            // del mod hasta que uno se acuerda de que dejo /relic preview puesto.
            String distancia = String.format(Locale.ROOT, "%.2f",
                    RelicClientEvents.previewDistance());
            source.sendSuccess(() -> Component.translatable("message.holocore.preview_info",
                    distancia).withStyle(ChatFormatting.LIGHT_PURPLE), false);
        }
        if (!UNSAVED.isEmpty()) {
            int cambios = UNSAVED.size();
            source.sendSuccess(() -> Component.translatable("message.holocore.unsaved", cambios)
                    .withStyle(ChatFormatting.YELLOW), false);
        }
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
     * Claves cambiadas en memoria desde el ultimo {@code /relic save}. Sirve para
     * dos cosas: que {@code /relic info} avise de que hay valores que se perderan
     * al cerrar, y que {@code /relic save} sepa si hay algo que escribir.
     */
    private static final Set<String> UNSAVED = new LinkedHashSet<>();

    private static void markUnsaved(String clave) {
        UNSAVED.add(clave);
    }

    /**
     * Una clave ajustable en caliente con {@code /relic set}.
     *
     * <p>El tipo y el rango tienen que coincidir <b>exactamente</b> con
     * {@code RelicConfig}: el CI (paso {@code Validate config tweaks}) compara esta
     * tabla contra los {@code define}/{@code defineInRange} de la config, asi que
     * ni una clave olvidada ni un rango desincronizado pasan el build.</p>
     */
    private record Tweak(String key, Kind kind, ForgeConfigSpec.ConfigValue<?> value,
                         double min, double max, String defecto) {

        enum Kind { NUMBER, WHOLE, FLAG }

        static Tweak number(String key, ForgeConfigSpec.DoubleValue value, double min, double max,
                            double defecto) {
            return new Tweak(key, Kind.NUMBER, value, min, max, String.valueOf(defecto));
        }

        static Tweak whole(String key, ForgeConfigSpec.IntValue value, int min, int max, int defecto) {
            return new Tweak(key, Kind.WHOLE, value, min, max, String.valueOf(defecto));
        }

        static Tweak flag(String key, ForgeConfigSpec.BooleanValue value, boolean defecto) {
            return new Tweak(key, Kind.FLAG, value, 0.0D, 0.0D, String.valueOf(defecto));
        }

        /**
         * Vuelve al valor de fabrica (el que trae {@code RelicConfig}).
         *
         * @return {@code true} si el valor en memoria era otro y se ha cambiado.
         *         Se compara con {@link #current()}, o sea con lo que acaba de
         *         contestar el comando: si no cambia lo que se lee, no cambia nada.
         */
        boolean restoreDefault() {
            String antes = current();
            return apply(defecto) && !current().equals(antes);
        }

        String current() {
            return switch (kind) {
                case NUMBER -> String.format(Locale.ROOT, "%.2f", (Double) value.get());
                case WHOLE -> String.valueOf(value.get());
                case FLAG -> String.valueOf(value.get());
            };
        }

        /** @return {@code false} si el texto no es un valor valido para la clave */
        boolean apply(String raw) {
            switch (kind) {
                case FLAG -> {
                    String valor = raw.toLowerCase(Locale.ROOT);
                    if (valor.equals("true") || valor.equals("on")) {
                        ((ForgeConfigSpec.BooleanValue) value).set(true);
                        return true;
                    }
                    if (valor.equals("false") || valor.equals("off")) {
                        ((ForgeConfigSpec.BooleanValue) value).set(false);
                        return true;
                    }
                    return false;
                }
                case WHOLE, NUMBER -> {
                    double parsed;
                    try {
                        parsed = Double.parseDouble(raw);
                    } catch (NumberFormatException ex) {
                        return false;
                    }
                    if (Double.isNaN(parsed) || parsed < min || parsed > max) {
                        return false;
                    }
                    if (kind == Kind.WHOLE) {
                        ((ForgeConfigSpec.IntValue) value).set((int) Math.round(parsed));
                    } else {
                        ((ForgeConfigSpec.DoubleValue) value).set(parsed);
                    }
                    return true;
                }
            }
            return false;
        }
    }

    /**
     * Las 22 claves ajustables. Quedan fuera {@code placement.shoulder} y
     * {@code visuals.quality} porque ya tienen su propio comando ({@code /relic
     * side} y {@code /relic quality}), que ademas valida el texto.
     */
    private static final List<Tweak> TWEAKS = List.of(
            Tweak.number("placement.offsetX", RelicConfig.OFFSET_X, -32.0D, 32.0D, 6.0D),
            Tweak.number("placement.offsetY", RelicConfig.OFFSET_Y, -48.0D, 48.0D, -6.0D),
            Tweak.number("placement.offsetZ", RelicConfig.OFFSET_Z, -24.0D, 48.0D, 8.0D),
            Tweak.number("placement.scale", RelicConfig.SCALE, 0.1D, 4.0D, 1.0D),
            Tweak.flag("visuals.glowLayer", RelicConfig.GLOW_LAYER, true),
            Tweak.flag("visuals.glowHalo", RelicConfig.GLOW_HALO, true),
            Tweak.number("visuals.haloIntensity", RelicConfig.HALO_INTENSITY, 0.0D, 1.0D, 0.25D),
            Tweak.flag("visuals.glowAura", RelicConfig.GLOW_AURA, true),
            Tweak.number("visuals.auraIntensity", RelicConfig.AURA_INTENSITY, 0.0D, 1.0D, 0.32D),
            Tweak.flag("visuals.auraTint", RelicConfig.AURA_TINT, true),
            Tweak.flag("visuals.glowRing", RelicConfig.GLOW_RING, true),
            Tweak.number("visuals.ringIntensity", RelicConfig.RING_INTENSITY, 0.0D, 1.0D, 0.60D),
            Tweak.number("visuals.flashIntensity", RelicConfig.FLASH_INTENSITY, 0.0D, 2.0D, 1.0D),
            Tweak.flag("visuals.shaderGlow", RelicConfig.SHADER_GLOW, true),
            Tweak.number("visuals.shaderIntensity", RelicConfig.SHADER_INTENSITY, 0.0D, 1.0D, 0.35D),
            Tweak.flag("visuals.reducedEffects", RelicConfig.REDUCED_EFFECTS, false),
            Tweak.flag("visuals.idleVariations", RelicConfig.IDLE_VARIATIONS, true),
            Tweak.whole("visuals.maxRenderDistance", RelicConfig.MAX_RENDER_DISTANCE, 4, 128, 32),
            Tweak.whole("visuals.glitchMinSeconds", RelicConfig.GLITCH_MIN_SECONDS, 2, 600, 20),
            Tweak.whole("visuals.glitchMaxSeconds", RelicConfig.GLITCH_MAX_SECONDS, 2, 900, 60),
            Tweak.whole("visuals.alertRadius", RelicConfig.ALERT_RADIUS, 2, 48, 12),
            Tweak.whole("visuals.combatHoldTicks", RelicConfig.COMBAT_HOLD_TICKS, 10, 600, 80));

    private static String[] tweakKeys() {
        return TWEAKS.stream().map(Tweak::key).toArray(String[]::new);
    }

    /**
     * Busca una clave por su nombre completo ({@code visuals.auraIntensity})
     * <b>o</b> por el corto ({@code auraIntensity}), que es como se escriben en la
     * tabla del README. Solo se acepta el corto si no es ambiguo.
     */
    private static Tweak tweak(String clave) {
        String buscada = clave.toLowerCase(Locale.ROOT);
        for (Tweak tweak : TWEAKS) {
            if (tweak.key().toLowerCase(Locale.ROOT).equals(buscada)) {
                return tweak;
            }
        }
        Tweak unica = null;
        for (Tweak tweak : TWEAKS) {
            if (!tweak.key().toLowerCase(Locale.ROOT).endsWith("." + buscada)) {
                continue;
            }
            if (unica != null) {
                return null;
            }
            unica = tweak;
        }
        return unica;
    }

    /**
     * {@code /relic set} sin argumentos: todas las claves con su valor actual, en
     * tres lineas para que quepan en el chat.
     */
    private static int setList(CommandSourceStack source) {
        StringBuilder linea = new StringBuilder();
        int enLinea = 0;
        for (Tweak tweak : TWEAKS) {
            if (enLinea == 8) {
                String texto = linea.toString();
                source.sendSuccess(() -> Component.translatable("message.holocore.set_list", texto)
                        .withStyle(ChatFormatting.DARK_AQUA), false);
                linea.setLength(0);
                enLinea = 0;
            }
            if (enLinea > 0) {
                linea.append(" · ");
            }
            linea.append(tweak.key()).append('=').append(tweak.current());
            if (UNSAVED.contains(tweak.key())) {
                // Con un asterisco: asi se ve de un vistazo que se va a perder
                // al cerrar el juego, sin tener que ir clave por clave.
                linea.append('*');
            }
            enLinea++;
        }
        if (enLinea > 0) {
            String texto = linea.toString();
            source.sendSuccess(() -> Component.translatable("message.holocore.set_list", texto)
                    .withStyle(ChatFormatting.DARK_AQUA), false);
        }
        if (!UNSAVED.isEmpty()) {
            int pendientes = UNSAVED.size();
            source.sendSuccess(() -> Component.translatable("message.holocore.set_list_unsaved",
                    pendientes).withStyle(ChatFormatting.YELLOW), false);
        }
        source.sendSuccess(() -> Component.translatable("message.holocore.set_usage",
                String.format(Locale.ROOT, "%.2f", RelicConfig.AURA_INTENSITY.get()))
                .withStyle(ChatFormatting.GRAY), false);
        return TWEAKS.size();
    }

    private static int setShow(CommandSourceStack source, String clave) {
        Tweak tweak = tweak(clave);
        if (tweak == null) {
            source.sendFailure(Component.translatable("message.holocore.set_unknown", clave));
            return 0;
        }
        source.sendSuccess(() -> Component.translatable("message.holocore.set_value",
                tweak.key(), tweak.current()).withStyle(ChatFormatting.AQUA), false);
        return 1;
    }

    /**
     * Fija una clave <b>en memoria</b>, igual que {@code /relic offset}: el archivo
     * no se toca, para poder probar sobre la marcha y copiar despues el valor al
     * {@code holocore-client.toml}. Un valor fuera del rango de la config se
     * rechaza entero en vez de recortarse: asi lo que contesta el comando es
     * siempre lo que se aplico. El CI comprueba que los rangos coinciden.
     */
    private static int setApply(CommandSourceStack source, String clave, String valor) {
        Tweak tweak = tweak(clave);
        if (tweak == null) {
            source.sendFailure(Component.translatable("message.holocore.set_unknown", clave));
            return 0;
        }
        if (!tweak.apply(valor)) {
            source.sendFailure(Component.translatable("message.holocore.set_bad_value",
                    tweak.key(), tweak.current()));
            return 0;
        }
        markUnsaved(tweak.key());
        source.sendSuccess(() -> Component.translatable("message.holocore.set_value",
                tweak.key(), tweak.current()).withStyle(ChatFormatting.AQUA), false);
        return 1;
    }

    /** Nombres aceptados por {@code /relic mood}. {@code auto} = deteccion. */
    private static final String[] MOOD_NAMES = {"auto", "neutral", "dark", "rain", "storm",
            "wounded", "resonant"};

    /**
     * {@code /relic mood}: enseña el estado de brillo que manda ahora mismo (y si
     * esta forzado). Es lo que hay que mirar si el aura se ha puesto de un color
     * raro.
     */
    private static int moodShow(CommandSourceStack source) {
        RelicVisuals.RelicVisual actual = localVisual();
        RelicAnimatable.Mood forzado = RelicAnimatable.forcedMood();
        if (forzado != null) {
            Component nombre = Component.translatable("message.holocore.state."
                    + forzado.name().toLowerCase(Locale.ROOT));
            source.sendSuccess(() -> Component.translatable("message.holocore.mood_forced", nombre)
                    .withStyle(ChatFormatting.GOLD), false);
            return 1;
        }
        if (actual == null) {
            source.sendFailure(Component.translatable("message.holocore.not_equipped"));
            return 0;
        }
        Component nombre = Component.translatable("message.holocore.state."
                + actual.animatable().mood().name().toLowerCase(Locale.ROOT));
        source.sendSuccess(() -> Component.translatable("message.holocore.mood_show", nombre)
                .withStyle(ChatFormatting.AQUA), false);
        return 1;
    }

    /**
     * {@code /relic mood <estado>}: fuerza el estado de brillo, o vuelve a
     * automatico con {@code auto}. Sirve para ver tormenta, herido o resonancia sin
     * montar la escena — una tormenta de verdad, dos jugadores, poca vida.
     */
    private static int moodSet(CommandSourceStack source, String estado) {
        String buscado = estado.toLowerCase(Locale.ROOT);
        if (buscado.equals("auto")) {
            RelicAnimatable.forceMood(null);
            source.sendSuccess(() -> Component.translatable("message.holocore.mood_auto")
                    .withStyle(ChatFormatting.GRAY), false);
            return 1;
        }
        for (RelicAnimatable.Mood mood : RelicAnimatable.Mood.values()) {
            if (!mood.name().equalsIgnoreCase(buscado)) {
                continue;
            }
            RelicAnimatable.forceMood(mood);
            Component nombre = Component.translatable("message.holocore.state." + buscado);
            source.sendSuccess(() -> Component.translatable("message.holocore.mood_forced", nombre)
                    .withStyle(ChatFormatting.AQUA), false);
            return 1;
        }
        source.sendFailure(Component.translatable("message.holocore.set_unknown", estado));
        return 0;
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

    /** Atajo tipado de los comandos de colocacion: fija y marca como sin guardar. */
    private static void set(ForgeConfigSpec.DoubleValue value, String clave, double newValue) {
        value.set(newValue);
        markUnsaved(clave);
    }

    /**
     * {@code /relic reset}: vuelve a los valores de fabrica <b>en memoria</b>
     * (despues, {@code /relic save} los escribe). Se apoya en la misma tabla que
     * {@code /relic set}, asi que lo que se restaura es exactamente lo que la
     * config trae por defecto; el CI comprueba que coinciden.
     */
    private static int reset(CommandSourceStack source) {
        int cambios = 0;
        for (Tweak tweak : TWEAKS) {
            if (tweak.restoreDefault()) {
                markUnsaved(tweak.key());
                cambios++;
            }
        }
        // Las dos que no pasan por /relic set tambien se restauran, y solo se
        // marcan si de verdad estaban en otro valor: si no, un /relic reset sin
        // nada que deshacer dejaba 24 claves "sin guardar" que no habian cambiado
        // y el /relic save siguiente escribia el archivo para nada.
        if (RelicConfig.SHOULDER.get() != RelicConfig.Shoulder.RIGHT) {
            RelicConfig.SHOULDER.set(RelicConfig.Shoulder.RIGHT);
            markUnsaved("placement.shoulder");
            cambios++;
        }
        if (RelicConfig.QUALITY.get() != RelicConfig.Quality.FULL) {
            RelicConfig.QUALITY.set(RelicConfig.Quality.FULL);
            markUnsaved("visuals.quality");
            cambios++;
        }
        if (cambios == 0) {
            source.sendSuccess(() -> Component.translatable("message.holocore.reset_none")
                    .withStyle(ChatFormatting.GRAY), false);
            return 0;
        }
        int total = cambios;
        source.sendSuccess(() -> Component.translatable("message.holocore.reset", total)
                .withStyle(ChatFormatting.AQUA), false);
        return total;
    }

    /**
     * {@code /relic reset <clave>}: volver al defecto de <b>una</b> clave. Es el
     * deshacer de un experimento suelto sin tirar los otros veintitres ajustes.
     * Si la clave ya estaba en su defecto no se marca como sin guardar, igual
     * que en el reset completo.
     */
    private static int resetOne(CommandSourceStack source, String clave) {
        Tweak tweak = tweak(clave);
        if (tweak == null) {
            source.sendFailure(Component.translatable("message.holocore.set_unknown", clave));
            return 0;
        }
        if (!tweak.restoreDefault()) {
            source.sendSuccess(() -> Component.translatable("message.holocore.reset_one_none",
                    tweak.key()).withStyle(ChatFormatting.GRAY), false);
            return 0;
        }
        markUnsaved(tweak.key());
        source.sendSuccess(() -> Component.translatable("message.holocore.set_value",
                tweak.key(), tweak.current()).withStyle(ChatFormatting.AQUA), false);
        return 1;
    }

    /**
     * {@code /relic preview [distancia]}: dibuja la reliquia del jugador local
     * delante de la camara, con sus cuatro pases y su aura.
     *
     * <p>Existe para mirar el brillo siempre a la misma distancia y en cualquier
     * fondo —nieve, arena, cueva— sin depender de donde caiga el hombro ni de
     * ponerse en tercera persona. Sin argumento alterna; con argumento la enciende
     * a esa distancia.</p>
     */
    private static int preview(CommandSourceStack source, Double distancia) {
        Player player = Minecraft.getInstance().player;
        if (player == null || RelicServer.findRelic(player).isEmpty()) {
            source.sendFailure(Component.translatable("message.holocore.not_equipped"));
            return 0;
        }
        boolean encender = distancia != null || !RelicClientEvents.previewEnabled();
        float valor = distancia == null
                ? RelicClientEvents.previewDistance()
                : distancia.floatValue();
        RelicClientEvents.preview(encender, valor);
        if (!encender) {
            source.sendSuccess(() -> Component.translatable("message.holocore.preview_off")
                    .withStyle(ChatFormatting.GRAY), false);
            return 1;
        }
        String texto = String.format(Locale.ROOT, "%.2f", valor);
        source.sendSuccess(() -> Component.translatable("message.holocore.preview_on", texto)
                .withStyle(ChatFormatting.AQUA), false);
        return 1;
    }

    /**
     * {@code /relic save}: escribe en {@code config/holocore-client.toml} lo que
     * haya en memoria. Hasta 1.0.20 todo lo que se ajustaba con comandos moria al
     * cerrar el juego, asi que habia que copiar los numeros a mano.
     */
    private static int save(CommandSourceStack source) {
        if (UNSAVED.isEmpty()) {
            source.sendSuccess(() -> Component.translatable("message.holocore.save_none")
                    .withStyle(ChatFormatting.GRAY), false);
            return 0;
        }
        int cambios = UNSAVED.size();
        try {
            RelicConfig.SPEC.save();
        } catch (RuntimeException ex) {
            source.sendFailure(Component.translatable("message.holocore.save_error"));
            return 0;
        }
        UNSAVED.clear();
        source.sendSuccess(() -> Component.translatable("message.holocore.save", cambios)
                .withStyle(ChatFormatting.AQUA), false);
        return cambios;
    }
}
