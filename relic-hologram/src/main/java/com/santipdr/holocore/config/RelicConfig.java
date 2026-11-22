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
    public static final ForgeConfigSpec.BooleanValue GLOW_AURA;
    public static final ForgeConfigSpec.DoubleValue AURA_INTENSITY;
    public static final ForgeConfigSpec.BooleanValue AURA_TINT;
    public static final ForgeConfigSpec.BooleanValue GLOW_RING;
    public static final ForgeConfigSpec.DoubleValue RING_INTENSITY;
    public static final ForgeConfigSpec.DoubleValue FLASH_INTENSITY;
    public static final ForgeConfigSpec.BooleanValue SHADER_GLOW;
    public static final ForgeConfigSpec.DoubleValue SHADER_INTENSITY;
    public static final ForgeConfigSpec.BooleanValue GROUND_ECHO;
    public static final ForgeConfigSpec.DoubleValue SPARK_SPEED_SCALE;
    public static final ForgeConfigSpec.DoubleValue ANIM_SPEED;
    public static final ForgeConfigSpec.BooleanValue REDUCED_EFFECTS;
    public static final ForgeConfigSpec.BooleanValue IDLE_VARIATIONS;
    public static final ForgeConfigSpec.IntValue MAX_RENDER_DISTANCE;
    public static final ForgeConfigSpec.IntValue GLITCH_MIN_SECONDS;
    public static final ForgeConfigSpec.IntValue GLITCH_MAX_SECONDS;
    public static final ForgeConfigSpec.IntValue ALERT_RADIUS;
    public static final ForgeConfigSpec.IntValue COMBAT_HOLD_TICKS;
    public static final ForgeConfigSpec.BooleanValue EVENT_SOUND;
    public static final ForgeConfigSpec.DoubleValue SOUND_VOLUME;

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
        HALO_INTENSITY = b.comment("Intensidad del halo aditivo (0 = nada, 1 = el maximo). 0.25 es lo que se ve bien;",
                        "mas de 0.4 empieza a verse como una mancha blanca sobre nieve o arena.")
                .defineInRange("haloIntensity", 0.25D, 0.0D, 1.0D);
        GLOW_AURA = b.comment("Aura de tres quads que miran a camara: es el 'bloom propio' sin post-proceso.",
                        "Funciona igual con y sin shaderpack, y cuesta tres quads.")
                .define("glowAura", true);
        AURA_INTENSITY = b.comment("Intensidad del aura (0 = invisible, 1 = muy marcada). El aura es aditiva:",
                        "sobre un fondo claro (nieve, desierto) sumar mucho termina viendose blanco.")
                .defineInRange("auraIntensity", 0.32D, 0.0D, 1.0D);
        AURA_TINT = b.comment("Segundo pase del aura con mezcla normal: tine en vez de sumar.",
                        "Es lo unico que da color sobre nieve o arena, donde un aditivo solo puede",
                        "blanquear. false = solo el brillo aditivo.")
                .define("auraTint", true);
        GLOW_RING = b.comment("Anillo de estado: gira y se tine segun idle/cargada/alerta. En calma y dormida no sale.")
                .define("glowRing", true);
        RING_INTENSITY = b.comment("Intensidad del anillo de estado (0 = invisible, 1 = muy marcado).")
                .defineInRange("ringIntensity", 0.60D, 0.0D, 1.0D);
        FLASH_INTENSITY = b.comment("Destello al ocurrir algo: pulso, liberacion, golpe recibido, subida de nivel",
                        "o despertar/dormir. Multiplica el pico del destello; 0 lo apaga del todo.")
                .defineInRange("flashIntensity", 1.0D, 0.0D, 2.0D);
        SHADER_GLOW = b.comment("Pase GLSL propio (borde de silueta + dos barridos) sobre la textura emisiva.",
                        "Se desactiva solo si hay shaderpack activo (Iris/Oculus/OptiFine), porque el pack",
                        "sustituye el programa y la reliquia podria quedar invisible. Su fuerza es shaderIntensity.")
                .define("shaderGlow", true);
        SHADER_INTENSITY = b.comment("Intensidad del pase GLSL (borde + barridos). Separada del halo",
                        "para poder bajar el borde sin apagar el brillo.")
                .defineInRange("shaderIntensity", 0.35D, 0.0D, 1.0D);
        GROUND_ECHO = b.comment("Eco en el suelo: en cada evento, un anillo tumbado a los pies del",
                        "portador se abre y se apaga. Solo se dibuja en tercera persona (en la vista",
                        "previa el suelo seria la cara de la camara). Un quad por evento.")
                .define("groundEcho", true);
        SPARK_SPEED_SCALE = b.comment("Multiplicador de la orbita de chispas. 1.0 es 1,6 s por vuelta",
                        "(se leen las cinco chispas); 3.0 es la velocidad de hasta 1.0.45, que",
                        "se veia como un aro temblando; 0 las deja quietas en su sitio.")
                .defineInRange("sparkSpeed", 1.0D, 0.0D, 3.0D);
        ANIM_SPEED = b.comment("Ritmo del bucle de animacion. 1.0 es el de las animaciones tal cual",
                        "estan hechas en el modelo (idle 48 s); 0.65 lo deja flotando, que es como",
                        "estaba pensado. El estado de brillo lo multiplica encima (herido 0.72,",
                        "tormenta 1.32, ardiendo 1.40): esto no cambia que animacion suena, solo",
                        "a que velocidad. Con 0.25 va a camara lenta y con 2.0 parece un tic.")
                .defineInRange("animSpeed", 0.65D, 0.25D, 2.0D);
        REDUCED_EFFECTS = b.comment("Usa idle_calm (sin rayos, cometas ni ondas) cuando el estado es normal.")
                .define("reducedEffects", false);
        IDLE_VARIATIONS = b.comment("La reliquia hace variaciones propias cada cierto tiempo en reposo",
                        "(temblor, glitch, pulso...). false = solo el glitch aleatorio de antes.")
                .define("idleVariations", true);
        MAX_RENDER_DISTANCE = b.comment("Distancia maxima (bloques) a la que se renderiza la reliquia de OTROS jugadores. El propio jugador siempre se renderiza.")
                .defineInRange("maxRenderDistance", 32, 4, 128);
        GLITCH_MIN_SECONDS = b.comment("Intervalo minimo entre variaciones de reposo (tambien glitches).")
                .defineInRange("glitchMinSeconds", 20, 2, 600);
        GLITCH_MAX_SECONDS = b.comment("Intervalo maximo entre variaciones de reposo.")
                .defineInRange("glitchMaxSeconds", 60, 2, 900);
        ALERT_RADIUS = b.comment("Radio (bloques) en el que un monstruo pone la reliquia en estado de alerta.")
                .defineInRange("alertRadius", 12, 2, 48);
        COMBAT_HOLD_TICKS = b.comment("Ticks que la reliquia sigue en estado cargado tras el ultimo golpe/ataque.")
                .defineInRange("combatHoldTicks", 80, 10, 600);
        b.pop();

        b.comment("Sonidos de la reliquia del jugador local.").push("sound");
        EVENT_SOUND = b.comment("Suena al despertar, dormir y pulsar. Solo la reliquia del jugador local:",
                        "las de otros jugadores no suenan, o con cuatro portadores cerca seria una orquesta.",
                        "Los sonidos son de ametista de vanilla: el mod no trae assets de audio.")
                .define("events", true);
        SOUND_VOLUME = b.comment("Volumen de esos sonidos (0 = apagados, 1 = los de vanilla tal cual).",
                        "0.45 es lo que se oye sin tapar los pasos ni la musica.")
                .defineInRange("volume", 0.45D, 0.0D, 1.0D);
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
