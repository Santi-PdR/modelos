package com.santipdr.holocore.config;

import net.minecraftforge.common.ForgeConfigSpec;

/**
 * Config de cliente. Es de cliente porque solo afecta a como se ve la reliquia:
 * posicion, escala y calidad de render no necesitan viajar al servidor ni
 * invalidar nada del mundo.
 *
 * <p>Los offsets se expresan en <b>pixeles de modelo</b> (1/16 de bloque) y en
 * el espacio del hueso {@code body} del jugador: X+ = lado izquierdo del
 * portador, Y+ = abajo, Z+ = espalda. Con {@code shoulder=right} se usa
 * {@code -offsetX}; para el otro hombro basta con cambiar ese valor.</p>
 */
public final class RelicConfig {

    public static final ForgeConfigSpec SPEC;

    public static final ForgeConfigSpec.EnumValue<Shoulder> SHOULDER;
    public static final ForgeConfigSpec.DoubleValue OFFSET_X;
    public static final ForgeConfigSpec.DoubleValue OFFSET_Y;
    public static final ForgeConfigSpec.DoubleValue OFFSET_Z;
    public static final ForgeConfigSpec.DoubleValue SCALE;
    public static final ForgeConfigSpec.EnumValue<Quality> QUALITY;
    public static final ForgeConfigSpec.BooleanValue GLOW_LAYER;
    public static final ForgeConfigSpec.BooleanValue GLOW_HALO;
    public static final ForgeConfigSpec.DoubleValue HALO_INTENSITY;
    public static final ForgeConfigSpec.BooleanValue REDUCED_EFFECTS;
    public static final ForgeConfigSpec.IntValue MAX_RENDER_DISTANCE;
    public static final ForgeConfigSpec.IntValue GLITCH_MIN_SECONDS;
    public static final ForgeConfigSpec.IntValue GLITCH_MAX_SECONDS;
    public static final ForgeConfigSpec.IntValue ALERT_RADIUS;
    public static final ForgeConfigSpec.IntValue COMBAT_HOLD_TICKS;

    static {
        ForgeConfigSpec.Builder b = new ForgeConfigSpec.Builder();

        b.comment("Donde se coloca el nucleo respecto al hombro del portador.").push("placement");
        SHOULDER = b.comment("Hombro por defecto. RIGHT es el del modelo anclado de Blockbench (x=-6 px).")
                .defineEnum("shoulder", Shoulder.RIGHT);
        OFFSET_X = b.comment("Desplazamiento lateral en pixeles de modelo (se espeja segun shoulder).")
                .defineInRange("offsetX", 6.0D, -32.0D, 32.0D);
        OFFSET_Y = b.comment("Desplazamiento vertical en pixeles de modelo. Y+ es ABAJO (convencion de las partes del jugador), asi que -6 sube 6 px.")
                .defineInRange("offsetY", -6.0D, -48.0D, 48.0D);
        OFFSET_Z = b.comment("Desplazamiento hacia atras en pixeles de modelo (Z+ = espalda).")
                .defineInRange("offsetZ", 8.0D, -24.0D, 48.0D);
        SCALE = b.comment("Escala global del modelo. 1.0 = tamano de Blockbench (~11 px de ancho).")
                .defineInRange("scale", 1.0D, 0.1D, 4.0D);
        b.pop();

        b.comment("Calidad y efectos.").push("visuals");
        QUALITY = b.comment("FULL: geometria de 977 cubos. LITE: variante de 751 cubos (mismos huesos y animaciones).")
                .defineEnum("quality", Quality.FULL);
        GLOW_LAYER = b.comment("Segundo pase emisivo con relic_hologram_glowing.png. Desactivalo en equipos lentos.")
                .define("glowLayer", true);
        GLOW_HALO = b.comment("Tercer pase con blend ADITIVO: suma luz y da el efecto de brillo acumulado sin shaders.",
                        "Solo se aplica con quality=FULL y reducedEffects=false; en LITE se omite por rendimiento.")
                .define("glowHalo", true);
        HALO_INTENSITY = b.comment("Intensidad del halo aditivo (0 = nada, 1 = el maximo). 0.35 es lo que se ve bien en el juego.")
                .defineInRange("haloIntensity", 0.35D, 0.0D, 1.0D);
        REDUCED_EFFECTS = b.comment("Usa idle_calm (sin rayos, cometas ni ondas) cuando el estado es normal.")
                .define("reducedEffects", false);
        MAX_RENDER_DISTANCE = b.comment("Distancia maxima (bloques) a la que se renderiza la reliquia de OTROS jugadores. El propio jugador siempre se renderiza.")
                .defineInRange("maxRenderDistance", 32, 4, 128);
        GLITCH_MIN_SECONDS = b.comment("Intervalo minimo entre glitches aleatorios (solo en idle).")
                .defineInRange("glitchMinSeconds", 20, 2, 600);
        GLITCH_MAX_SECONDS = b.comment("Intervalo maximo entre glitches aleatorios (solo en idle).")
                .defineInRange("glitchMaxSeconds", 60, 2, 900);
        ALERT_RADIUS = b.comment("Radio (bloques) en el que un monstruo pone la reliquia en estado de alerta.")
                .defineInRange("alertRadius", 12, 2, 48);
        COMBAT_HOLD_TICKS = b.comment("Ticks que la reliquia sigue en estado cargado tras el ultimo golpe/ataque.")
                .defineInRange("combatHoldTicks", 80, 10, 600);
        b.pop();

        SPEC = b.build();
    }

    private RelicConfig() {
    }

    public enum Shoulder {
        RIGHT,
        LEFT
    }

    public enum Quality {
        FULL,
        LITE
    }
}
