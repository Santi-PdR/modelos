package com.santipdr.holocore.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.santipdr.holocore.config.RelicConfig;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import org.joml.Matrix4f;

/**
 * Aura y anillo de la reliquia: billboards aditivos que miran a camara.
 *
 * <p>Esto es el "bloom propio" que se puede hacer sin post-proceso: no se
 * desenfoca la pantalla, se <b>suma</b> una textura radial sobre lo ya dibujado,
 * que es exactamente como se ve un resplandor. Como es geometria normal, no
 * depende de shaders ni de que el jugador tenga un shaderpack, y se dibuja con
 * {@link RelicRenderTypes#ADDITIVE_GLOW}.</p>
 *
 * <p>El color y la intensidad salen del estado de la reliquia
 * ({@link RelicAnimatable#loopState()}), de modo que el aura sirve tambien para
 * saber que esta pasando sin mirar el modelo: azul en reposo, ambar cargada, rojo
 * en alerta y apagada en dormido. El anillo solo aparece en los estados que
 * importan, y gira en sentidos distintos segun cual sea.</p>
 *
 * <p>Los valores no se usan en crudo: {@link RelicGlowState} los interpola, asi
 * que un cambio de estado se ve como una transicion y no como un salto de color
 * en un frame.</p>
 *
 * <p>La posicion se toma de la traslacion de la matriz del {@code PoseStack} y la
 * escala de su primera columna; en el render de entidades el {@code PoseStack}
 * esta en coordenadas de mundo, asi que los vertices se emiten sin matriz.</p>
 */
public final class RelicAura {

    private static final ResourceLocation AURA_TEXTURE =
            new ResourceLocation("holocore", "textures/relic/relic_aura.png");
    private static final ResourceLocation RING_TEXTURE =
            new ResourceLocation("holocore", "textures/relic/relic_ring.png");

    /**
     * Diametro de cada capa del aura, en bloques (antes de la escala de la
     * config). El nucleo mide ~0.7 bloques: el aura solo tiene que rodearlo, no
     * cubrir la pantalla. Hasta 1.0.10 eran {1.05, 1.55, 2.10} y el resultado
     * era una nube blanca mas grande que el propio jugador.
     */
    private static final float[] DIAMETER = {0.62F, 0.85F, 1.10F};
    /** Cuanto aporta cada capa (0 = nada). La suma es lo que se ve sobre el fondo. */
    private static final float[] WEIGHT = {0.30F, 0.17F, 0.09F};
    /** Velocidad de giro de cada capa, en radianes por tick. Negativa = al reves. */
    private static final float[] SPIN = {0.035F, -0.022F, 0.010F};
    /**
     * Diametro del anillo de estado: por fuera del aura (1.10) con margen
     * suficiente para leerse como anillo y no como el borde del resplandor.
     */
    private static final float RING_DIAMETER = 1.35F;
    /**
     * Alpha de los quads del aura. Con blend aditivo el color final es
     * {@code rgb * alpha}, asi que esto es el mando global de cuanto suma el
     * aura: con 0.55 y los pesos de arriba el aporte maximo queda en ~0.31
     * (intensidad 1.0) en vez del 0.47 de 1.0.10, y sobre un fondo claro ya no
     * satura los tres canales.
     */
    private static final float AURA_ALPHA = 0.55F;
    /**
     * Cuanto mas cubre el pase de tinte que el aditivo.
     *
     * <p>Elegido con numeros, no a ojo: {@code tools/check_aura_math.py} compone
     * las dos pasadas sobre nieve, piedra y cueva. Con 1.6 sobre los mismos pesos,
     * sobre nieve el halo queda en (0.80, 0.94, 1.00) frente al fondo
     * (0.93, 0.95, 0.97): el tono cian sube +0.20 y la luminancia solo baja 0.03,
     * o sea que se tine sin parecer una sombra. Mas cobertura oscurece de mas;
     * menos, y el color se pierde.</p>
     */
    private static final float TINT_ALPHA_BOOST = 1.6F;

    /** Chispas en orbita alrededor del nucleo. */
    private static final int SPARK_COUNT = 5;
    /** Burbujas del estado bajo el agua: cuantas, tamano y lo rapido que suben. */
    private static final int BUBBLE_COUNT = 7;
    private static final float BUBBLE_SIZE = 0.055F;
    private static final float BUBBLE_SPEED = 0.28F;
    /** Gotas del estado de lluvia: caen, asi que van al reves que las burbujas. */
    private static final int DROP_COUNT = 6;
    private static final float DROP_SIZE = 0.045F;
    private static final float DROP_SPEED = 1.10F;
    /** Brasas del estado ardiendo: suben como las burbujas, pero rapido y calientes. */
    private static final int EMBER_COUNT = 6;
    private static final float EMBER_SIZE = 0.050F;
    private static final float EMBER_SPEED = 0.65F;
    /**
     * Onda de choque de los eventos: cuantas particulas, radio de salida y de
     * llegada, y tamano. Sale del destello, asi que no guarda estado.
     */
    /** Copos del estado de congelacion: caen despacio, giran y son diminutos. */
    /**
     * Motas del vacio (el End, 1.0.52): pocas, muy lentas y con un parpadeo largo.
     * No caen ni suben: giran en un plano algo inclinado y se apagan por el camino,
     * que es lo que hace el polvo de enderman cuando lo miras.
     */
    private static final int MOTE_COUNT = 9;
    /**
     * Pavesas (el Nether, 1.0.53): brasas que <b>salen disparadas y caen</b>. La
     * altura es una parabola ({@code 4t(1-t)}), no una subida: por eso no se
     * confunden con las brasas de ardiendo, que solo suben. El Nether no respira
     * fuego, lo escupe.
     */
    private static final int CINDER_COUNT = 8;
    private static final float CINDER_SIZE = 0.030F;
    private static final float CINDER_SPEED = 0.42F;
    private static final float CINDER_RISE = 0.34F;
    private static final float MOTE_SIZE = 0.034F;
    private static final float MOTE_SPEED = 0.10F;
    private static final float MOTE_RADIUS = 0.28F;
    private static final int FLAKE_COUNT = 7;
    private static final float FLAKE_SIZE = 0.038F;
    private static final float FLAKE_SPEED = 0.28F;
    /**
     * Eco en el suelo de los eventos: radio de salida y de llegada, en bloques, y a
     * que altura por debajo del nucleo se tumba (el hombro queda ~1,15 bloques por
     * encima de los pies).
     */
    private static final float GROUND_MIN_RADIUS = 0.32F;
    private static final float GROUND_MAX_RADIUS = 1.15F;
    private static final float GROUND_DROP = 1.15F;
    /**
     * El eco suma poco y tine mucho: sobre nieve el aditivo solo sube los tres
     * canales y con 0.42 el anillo salia blanco (lo dice tools/check_aura_math.py,
     * que compone las dos pasadas con estos mismos numeros). 0.12 de aditivo y
     * 3.0 de cobertura de tinte dan un anillo del color del estado sobre cualquier
     * fondo.
     */
    private static final float GROUND_TINT_BOOST = 3.0F;
    private static final float GROUND_ADDITIVE = 0.12F;
    /**
     * Lo mismo para los otros dos pases de evento: la onda (chispas que salen) y el
     * eco del anillo. Todos son aditivos que vuelan sobre el suelo, o sea que todos
     * se quemaban a blanco sobre nieve con los 0.55 de antes. Regla: tinte ×3 del
     * aditivo, y el aditivo entre 0.12 y 0.18. tools/check_aura_math.py compone los
     * tres sobre nieve, piedra y cueva.
     */
    private static final float SHOCK_TINT_BOOST = 3.0F;
    private static final float SHOCK_ADDITIVE = 0.16F;
    private static final float ECHO_TINT_BOOST = 3.0F;
    private static final float ECHO_ADDITIVE = 0.18F;
    /** Motas del vacio: la misma regla (tinte x3, aditivo pequeno). */
    private static final float MOTE_TINT_BOOST = 3.0F;
    private static final float MOTE_ADDITIVE = 0.16F;
    /** Pavesas del Nether: la misma regla. */
    private static final float CINDER_TINT_BOOST = 3.0F;
    private static final float CINDER_ADDITIVE = 0.16F;
    private static final int SHOCK_COUNT = 8;
    private static final float SHOCK_MIN = 0.16F;
    private static final float SHOCK_MAX = 0.62F;
    private static final float SHOCK_SIZE = 0.060F;
    private static final float SPARK_RADIUS = 0.42F;
    private static final float SPARK_SIZE = 0.075F;
    /**
     * Velocidad de la orbita de chispas, en <b>radianes por tick</b> (como
     * {@code SPIN}): 0.20 son 1,6 s por vuelta, que es lo que deja leer cinco
     * chispas orbitando. Con los 0.75 de hasta 1.0.45 daba 2,8 vueltas por segundo
     * y no se veian chispas, se veia un aro temblando. {@code visuals.sparkSpeed}
     * lo escala (0 = quietas, 3 = la velocidad vieja).
     */
    private static final float SPARK_SPEED = 0.20F;
    private static final float TWO_PI = 6.2831855F;

    private RelicAura() {
    }

    /** Solo se apaga si el jugador apaga las dos cosas: son cuatro quads en total. */
    static boolean enabled() {
        return RelicConfig.GLOW_AURA.get() || RelicConfig.GLOW_RING.get();
    }

    static void render(PoseStack poseStack, MultiBufferSource bufferSource, float partialTick,
                       RelicAnimatable.LoopState state, RelicGlowState glow, float fade,
                       RelicAnimatable.Mood mood, float motion, boolean onShoulder,
                       RelicAnimatable.Ground ground) {
        float time = time(partialTick);
        Frame frame = frame(poseStack);
        // Destello de evento: el anillo se enciende aunque el estado no lo tenga,
        // asi un pulso o un golpe se nota tambien en calma o dormida.
        float flash = glow.flashScaled();

        if (RelicConfig.GLOW_AURA.get()) {
            drawAura(bufferSource, frame, time, glow, flash, fade);
        }
        if (RelicConfig.GLOW_RING.get() && glow.ring() + flash * 0.8F > 0.01F) {
            drawRing(bufferSource, frame, time, state, glow, flash, fade, motion);
        }
        // Eco en el suelo: un anillo tumbado a los pies del portador, que se abre y
        // se apaga con el destello. Solo en el hombro: en la vista previa el "suelo"
        // seria la cara de la camara y quedaria una tarjeta flotando en el aire.
        if (onShoulder && RelicConfig.GROUND_ECHO.get() && flash > 0.04F) {
            drawGroundEcho(bufferSource, frame, flash, glow, fade, ground);
        }
        // Onda de choque: solo mientras dura el destello, o sea que en reposo no
        // cuesta ni un quad. Va detras del anillo para que el eco quede debajo.
        if (RelicConfig.GLOW_AURA.get() && sparksEnabled() && flash > 0.02F) {
            drawShockwave(bufferSource, frame, time, glow, flash, fade);
        }
        if (RelicConfig.GLOW_AURA.get() && sparksEnabled()) {
            // El estado forzado manda: con /relic mood storm las chispas se ponen
            // azules aunque el cielo este limpio, que es para lo que se fuerza.
            RelicAnimatable.Mood sparkMood = RelicAnimatable.forcedMood() != null
                    ? RelicAnimatable.forcedMood() : mood;
            drawSparks(bufferSource, frame, time, glow, fade, sparkMood, motion);
        }
    }

    // ------------------------------------------------------------------
    // Aura: tres capas girando a distinta velocidad
    // ------------------------------------------------------------------

    private static void drawAura(MultiBufferSource bufferSource, Frame frame, float time,
                                 RelicGlowState glow, float flash, float fade) {
        float intensity = RelicConfig.AURA_INTENSITY.get().floatValue() * glow.aura()
                * (1.0F + 0.35F * flash) * fade;
        // El destello abre el aura muy poco: el fogonazo lo da el anillo, que es
        // una linea y no una mancha.
        float spread = 1.0F + 0.10F * flash;
        if (intensity <= 0.001F) {
            return;
        }

        // 1) Tinte: mezcla normal con el color del estado tal cual. Es el unico
        //    pase que se ve de color sobre nieve/arena, porque mezclar hacia un
        //    cian claro quita rojo y verde sin apagar el azul (no oscurece: tine).
        //    Sobre fondo oscuro casi no se nota y manda el aditivo de abajo.
        if (RelicConfig.AURA_TINT.get()) {
            VertexConsumer tint = bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(AURA_TEXTURE));
            for (int layer = 0; layer < DIAMETER.length; layer++) {
                float coverage = Math.min(1.0F,
                        WEIGHT[layer] * pulseAt(time, layer) * intensity * TINT_ALPHA_BOOST);
                billboard(tint, frame, DIAMETER[layer] * spread, time * SPIN[layer],
                        glow.red(), glow.green(), glow.blue(), coverage);
            }
        }

        // 2) Aditivo: el brillo.
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        for (int layer = 0; layer < DIAMETER.length; layer++) {
            float weight = WEIGHT[layer] * pulseAt(time, layer) * intensity;
            billboard(buffer, frame, DIAMETER[layer] * spread, time * SPIN[layer],
                    glow.red() * weight, glow.green() * weight, glow.blue() * weight, AURA_ALPHA);
        }
    }

    /**
     * Eco en el suelo: el anillo del estado tumbado en el plano horizontal del
     * portador, un poco por debajo del nucleo, abriendose mientras el destello se
     * apaga.
     *
     * <p>Usa los ejes X y Z de la matriz de pose (los del portador) en vez de los de
     * la camara: billboardeado seria otro aro mirandote de frente, y lo que hace que
     * un golpe se sienta es que la onda <b>golpee el suelo</b>. La altura baja por el
     * eje Y del portador, no por el de la pantalla.</p>
     */
    private static void drawGroundEcho(MultiBufferSource bufferSource, Frame frame, float flash,
                                       RelicGlowState glow, float fade, RelicAnimatable.Ground ground) {
        float t = 1.0F - Math.min(1.0F, flash);
        float radius = GROUND_MIN_RADIUS + (GROUND_MAX_RADIUS - GROUND_MIN_RADIUS) * t;
        float alpha = flash * GROUND_ADDITIVE * fade;
        if (alpha <= 0.01F) {
            return;
        }
        // El suelo cambia la forma del eco (1.0.55), no su brillo: el presupuesto
        // de luz es el mismo, asi que la regla de "tinte debajo, aditivo pequeno"
        // se cumple igual en los cuatro casos.
        float spread = switch (ground) {
            // En el agua el eco es un rizo: mas ancho y mas tenue. El agua se lleva
            // parte de la luz, como en el estado sumergido.
            case WATER -> 1.35F;
            // Arena, tierra, nieve: el suelo cede, el eco se abre y se apaga antes.
            case LOOSE -> 1.12F;
            // Piedra y metal: el eco se cierra sobre si mismo.
            case HARD -> 0.88F;
            case OTHER -> 1.0F;
        };
        float gain = switch (ground) {
            case WATER -> 0.70F;
            case LOOSE -> 0.88F;
            case HARD -> 1.0F;
            case OTHER -> 1.0F;
        };
        echoRing(bufferSource, frame, glow, radius * spread, alpha * gain);
        if (ground == RelicAnimatable.Ground.HARD) {
            // Rebote: el segundo anillo, mas pequeno y mas flojo, sale con el mismo
            // destello pero cerrado sobre el primero. Es lo que hace una piedra.
            echoRing(bufferSource, frame, glow, radius * spread * 0.55F, alpha * gain * 0.55F);
        }
    }

    /**
     * Un anillo tumbado: tinte con cobertura {@code alpha x GROUND_TINT_BOOST} y
     * aditivo {@code alpha} encima. Sobre nieve o arena el aditivo solo sube los
     * tres canales y la onda se queda blanca (fue el fallo de 1.0.9-1.0.10 con el
     * aura); el tinte la mantiene del color del estado y el aditivo la hace brillar.
     */
    private static void echoRing(MultiBufferSource bufferSource, Frame frame,
                                 RelicGlowState glow, float radius, float alpha) {
        float cx = frame.originX - frame.skyX * GROUND_DROP;
        float cy = frame.originY - frame.skyY * GROUND_DROP;
        float cz = frame.originZ - frame.skyZ * GROUND_DROP;
        float rx = frame.rightX * radius;
        float ry = frame.rightY * radius;
        float rz = frame.rightZ * radius;
        float bx = frame.backX * radius;
        float by = frame.backY * radius;
        float bz = frame.backZ * radius;
        if (RelicConfig.AURA_TINT.get()) {
            VertexConsumer tint = bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(RING_TEXTURE));
            float coverage = Math.min(1.0F, alpha * GROUND_TINT_BOOST);
            quad(tint,
                    cx - rx - bx, cy - ry - by, cz - rz - bz,
                    cx - rx + bx, cy - ry + by, cz - rz + bz,
                    cx + rx + bx, cy + ry + by, cz + rz + bz,
                    cx + rx - bx, cy + ry - by, cz + rz - bz,
                    glow.red(), glow.green(), glow.blue(), coverage);
        }
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(RING_TEXTURE));
        quad(buffer,
                cx - rx - bx, cy - ry - by, cz - rz - bz,
                cx - rx + bx, cy - ry + by, cz - rz + bz,
                cx + rx + bx, cy + ry + by, cz + rz + bz,
                cx + rx - bx, cy + ry - by, cz + rz - bz,
                glow.red() * alpha, glow.green() * alpha, glow.blue() * alpha, 1.0F);
    }

    /**
     * Onda de choque de un evento (pulso, golpe, liberacion, subida de nivel).
     *
     * <p><b>Sin estado</b>: el reloj es el propio destello, que ya existe y se apaga
     * solo. {@code flash} alto = radio minimo y brillo alto; segun baja, la onda se
     * abre y se apaga. Con eso el mismo codigo sirve para cualquier evento y no hay
     * lista de particulas que mantener, ni objetos que crear en el render.</p>
     */
    private static void drawShockwave(MultiBufferSource bufferSource, Frame frame, float time,
                                      RelicGlowState glow, float flash, float fade) {
        float t = 1.0F - Math.min(1.0F, flash);
        float radius = SHOCK_MIN + (SHOCK_MAX - SHOCK_MIN) * t;
        float weight = flash * SHOCK_ADDITIVE * fade;
        if (weight <= 0.01F) {
            return;
        }
        // Tinte debajo (ver SHOCK_ADDITIVE): si no, sobre nieve la onda es un
        // fogonazo blanco y deja de ser del color del estado.
        if (RelicConfig.AURA_TINT.get()) {
            VertexConsumer tint = bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(AURA_TEXTURE));
            float coverage = Math.min(1.0F, weight * SHOCK_TINT_BOOST);
            drawShockRing(tint, frame, time, radius, t, coverage,
                    glow.red(), glow.green(), glow.blue());
        }
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        float red = glow.red();
        float green = glow.green();
        float blue = glow.blue();
        // Gira un poco mientras se abre: una onda perfectamente radial parece un
        // anillo estatico que solo escala.
        drawShockRing(buffer, frame, time, radius, t, 1.0F,
                red * weight, green * weight, blue * weight);
    }

    /**
     * Las ocho particulas de la onda. Se dibuja dos veces (tinte y aditivo) con los
     * mismos numeros; el color ya viene multiplicado por quien llama.
     */
    private static void drawShockRing(VertexConsumer buffer, Frame frame, float time,
                                      float radius, float t, float alpha,
                                      float red, float green, float blue) {
        // Gira un poco mientras se abre: una onda perfectamente radial parece un
        // anillo estatico que solo escala.
        float turn = seconds(time) * 0.35F;
        float size = SHOCK_SIZE * (1.0F - 0.45F * t);
        for (int i = 0; i < SHOCK_COUNT; i++) {
            float angle = turn + i * (TWO_PI / SHOCK_COUNT);
            float left = cos(angle) * radius;
            float up = sin(angle) * radius * 0.8F;
            float cx = frame.originX + frame.leftX * left + frame.upX * up;
            float cy = frame.originY + frame.leftY * left + frame.upY * up;
            float cz = frame.originZ + frame.leftZ * left + frame.upZ * up;
            billboardAt(buffer, frame, cx, cy, cz, size, angle * 1.5F,
                    red, green, blue, alpha);
        }
    }

    // ------------------------------------------------------------------
    // Anillo: uno solo, girando segun el estado
    // ------------------------------------------------------------------

    private static void drawRing(MultiBufferSource bufferSource, Frame frame, float time,
                                 RelicAnimatable.LoopState state, RelicGlowState glow, float flash,
                                 float fade, float motion) {
        float weight = RelicConfig.RING_INTENSITY.get().floatValue()
                * (glow.ring() + 0.7F * flash) * fade;
        if (weight <= 0.001F) {
            return;
        }

        // En alerta el anillo late como un aviso; en los demas estados, respira. Y
        // late mas rapido si el portador va corriendo: el anillo es lo unico que se
        // ve de frente, asi que ahi es donde se nota el ritmo.
        boolean alert = state == RelicAnimatable.LoopState.ALERT;
        float beatSpeed = (alert ? 0.45F : 0.15F) * (1.0F + 0.70F * motion);
        float beat = 0.72F + 0.28F * (0.5F + 0.5F * sin(time * beatSpeed));
        float size = RING_DIAMETER * (1.0F + 0.25F * flash)
                * (alert ? 1.0F + 0.03F * sin(time * beatSpeed) : 1.0F);
        float amount = weight * beat;

        float angle = time * glow.spin();

        // El anillo tambien lleva tinte: sobre nieve el aditivo lo dejaba en
        // blanco y se perdia. El tinte lo mantiene del color del estado.
        if (RelicConfig.AURA_TINT.get()) {
            VertexConsumer tint = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(RING_TEXTURE));
            float coverage = Math.min(1.0F, amount * 0.9F);
            billboard(tint, frame, size, angle,
                    glow.red(), glow.green(), glow.blue(), coverage);
        }

        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(RING_TEXTURE));
        billboard(buffer, frame, size, angle,
                glow.red() * amount, glow.green() * amount, glow.blue() * amount, 1.0F);

        // Eco del anillo en los eventos (pulso, golpe, liberacion, cambio de
        // estado): un anillo mas grande que se abre y se apaga con el destello.
        // Es lo que convierte un fogonazo en una onda. Un quad, mismo lote.
        if (flash > 0.05F) {
            float echoSize = RING_DIAMETER * (1.0F + 2.4F * flash);
            float echo = weight * flash * ECHO_ADDITIVE;
            // Tinte debajo, como el eco del suelo: el eco del anillo tambien vuela
            // sobre el suelo y con solo aditivo se quedaba blanco sobre nieve.
            if (RelicConfig.AURA_TINT.get()) {
                VertexConsumer echoTint =
                        bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(RING_TEXTURE));
                billboard(echoTint, frame, echoSize, -angle * 0.6F,
                        glow.red(), glow.green(), glow.blue(),
                        Math.min(1.0F, echo * ECHO_TINT_BOOST));
            }
            billboard(buffer, frame, echoSize, -angle * 0.6F,
                    glow.red() * echo, glow.green() * echo, glow.blue() * echo, 1.0F);
        }
    }

    /**
     * Chispas en orbita: cinco quads aditivos del mismo tipo que el aura, o sea
     * que suman al lote que ya esta abierto. Giran en el plano de la camara, con
     * radio y altura distintos por chispa para que no se lean como un anillo
     * plano, y el giro hereda el del estado ({@code glow.spin()}): en alerta van
     * al reves que en calma.
     */
    private static void drawSparks(MultiBufferSource bufferSource, Frame frame, float time,
                                   RelicGlowState glow, float fade, RelicAnimatable.Mood mood,
                                   float motion) {
        float amount = fade * (0.55F + 0.45F * glow.aura()) * (1.0F + 0.6F * glow.flashScaled());
        if (amount <= 0.01F) {
            return;
        }
        if (mood == RelicAnimatable.Mood.SUBMERGED) {
            // Bajo el agua no hay chispas en orbita: hay burbujas subiendo.
            drawBubbles(bufferSource, frame, time, glow, amount, motion);
            return;
        }
        if (mood == RelicAnimatable.Mood.FREEZING) {
            // Congelandose: copos que bajan y se mecen. Es el unico VFX que va
            // *mas* lento que la lluvia: el frio congela hasta el movimiento.
            drawFlakes(bufferSource, frame, time, glow, amount, motion);
            return;
        }
        if (mood == RelicAnimatable.Mood.BURNING) {
            // Ardiendo: brasas subiendo, con parpadeo. Se ve aunque el jugador este
            // quieto, que es justo cuando mas falta hace saber que sigues en fuego.
            drawEmbers(bufferSource, frame, time, glow, amount, motion);
            return;
        }
        if (mood == RelicAnimatable.Mood.NETHER) {
            // En el Nether, pavesas: brasas que salen y caen (1.0.53). Hasta 1.0.52
            // reciclaba las de ardiendo, y solo se distinguian por el color.
            drawCinders(bufferSource, frame, time, glow, amount, motion);
            return;
        }
        if (mood == RelicAnimatable.Mood.END) {
            // En el End, motas del vacio: giran despacio y se apagan por el camino
            // (1.0.52). Antes se reciclaban los copos del hielo, y se notaba: los
            // copos caen, y en el End no cae nada.
            drawMotes(bufferSource, frame, time, glow, amount, motion);
            return;
        }
        if (mood == RelicAnimatable.Mood.RAIN) {
            // Con lluvia, gotas cayendo alrededor: el mismo truco que las burbujas,
            // al reves. Es el estado que mas tiempo se pasa encendido, y con chispas
            // en orbita se confundia con el reposo.
            drawDrops(bufferSource, frame, time, glow, amount, motion);
            return;
        }
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        boolean storm = mood == RelicAnimatable.Mood.STORM;
        // De noche las brasas flotan: la mitad de velocidad, la mitad de densidad
        // y mas frias. Es lo que distingue "noche despejada" de "no pasa nada"
        // sin tocar el color del aura ni el del modelo.
        boolean night = mood == RelicAnimatable.Mood.NIGHT;
        // Con un portal cerca las chispas se estiran hacia arriba y giran mas rapido:
        // es lo que hace el borde de un portal del Nether con las particulas.
        boolean portal = mood == RelicAnimatable.Mood.PORTAL;
        // Correr acelera la orbita: con el portador esprintando las chispas barren
        // mas rapido y el aura parece viva sin cambiar un solo pixel de textura.
        float orbit = time * SPARK_SPEED * RelicConfig.SPARK_SPEED_SCALE.get().floatValue()
                * (1.0F + 6.0F * Math.abs(glow.spin()))
                * (night ? 0.45F : portal ? 1.5F : 1.0F) * (1.0F + 0.45F * motion);
        // Con tormenta las chispas tiran a azul electrico: el color del estado es
        // casi blanco y sin esto se perderia el "hay truenos" en el aura.
        float redTint = glow.red();
        float greenTint = glow.green();
        float blueTint = glow.blue();
        if (storm) {
            redTint = redTint * 0.55F + 0.35F * 0.45F;
            greenTint = greenTint * 0.55F + 0.85F * 0.45F;
            blueTint = blueTint * 0.55F + 1.00F * 0.45F;
        } else if (portal) {
            // Violeta: el color del portal, mezclado con el del estado.
            redTint = redTint * 0.40F + 0.78F * 0.60F;
            greenTint = greenTint * 0.30F + 0.42F * 0.70F;
            blueTint = blueTint * 0.85F + 1.00F * 0.15F;
        } else if (night) {
            // Palido y frio, como el hielo: menos rojo, el verde y el azul intactos.
            redTint = redTint * 0.65F + 0.45F * 0.35F;
            greenTint = greenTint * 0.85F + 0.70F * 0.15F;
            blueTint = blueTint * 0.95F + 1.00F * 0.05F;
        }
        for (int i = 0; i < SPARK_COUNT; i++) {
            float phase = orbit + i * (TWO_PI / SPARK_COUNT);
            if (night && (i & 1) == 1) {
                // En la noche la mitad de las chispas se apagan: menos densidad.
                continue;
            }
            float radius = SPARK_RADIUS * (0.72F + 0.28F * sin(phase * 2.0F + i));
            float lift = sin(phase * 3.0F + i * 1.7F) * (portal ? 0.30F : 0.16F);
            float offset = cos(phase) * radius;
            float height = sin(phase) * radius * 0.8F + lift;
            float cx = frame.originX + frame.leftX * offset + frame.upX * height;
            float cy = frame.originY + frame.leftY * offset + frame.upY * height;
            float cz = frame.originZ + frame.leftZ * offset + frame.upZ * height;
            float weight = amount * (0.35F + 0.25F * sin(phase * 4.0F + i));
            billboardAt(buffer, frame, cx, cy, cz, SPARK_SIZE,
                    phase * 2.0F, redTint * weight, greenTint * weight, blueTint * weight, 1.0F);
            // Estela: si el portador se mueve, cada chispa deja una copia un poco
            // atras en su orbita, mas apagada y mas pequena. Dos quads por chispa y
            // solo con motion alto: parado no cuesta nada.
            if (motion > 0.35F) {
                float tail = phase - 0.22F * motion;
                float tailRadius = SPARK_RADIUS * (0.72F + 0.28F * sin(tail * 2.0F + i));
                float tailOffset = cos(tail) * tailRadius;
                float tailHeight = sin(tail) * tailRadius * 0.8F
                        + sin(tail * 3.0F + i * 1.7F) * (portal ? 0.30F : 0.16F);
                float tx = frame.originX + frame.leftX * tailOffset + frame.upX * tailHeight;
                float ty = frame.originY + frame.leftY * tailOffset + frame.upY * tailHeight;
                float tz = frame.originZ + frame.leftZ * tailOffset + frame.upZ * tailHeight;
                float tailWeight = weight * 0.42F * motion;
                billboardAt(buffer, frame, tx, ty, tz, SPARK_SIZE * 0.72F, tail * 2.0F,
                        redTint * tailWeight, greenTint * tailWeight, blueTint * tailWeight, 1.0F);
            }
        }
    }

    /**
     * Burbujas: suben desde debajo de la reliquia, se hinchan un poco y se apagan
     * al llegar arriba. Es el unico estado con VFX propio; el resto reutiliza la
     * orbita de chispas cambiando color y densidad, porque una orbita que sube en
     * vertical dejaria de leerse como orbita.
     */
    private static void drawBubbles(MultiBufferSource bufferSource, Frame frame, float time,
                                    RelicGlowState glow, float amount, float motion) {
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        // Verde azulado de fondo de rio, mezclado con el color del estado.
        float redTint = glow.red() * 0.35F + 0.45F * 0.65F;
        float greenTint = glow.green() * 0.45F + 0.92F * 0.55F;
        float blueTint = glow.blue() * 0.55F + 1.00F * 0.45F;
        for (int i = 0; i < BUBBLE_COUNT; i++) {
            // rise va de 0 (abajo) a 1 (arriba) y vuelve a empezar: es el ciclo de
            // una burbuja, desfasado por indice para que no suban en bloque.
            // Nadar acelera las burbujas: es lo que se ve al cruzar un rio a nado.
            float rise = fract(seconds(time) * BUBBLE_SPEED * (1.0F + 0.50F * motion)
                    + i * (1.0F / BUBBLE_COUNT));
            float offset = sin(seconds(time) * 1.3F + i * 2.1F) * 0.10F;
            float height = -0.32F + rise * 0.72F;
            float cx = frame.originX + frame.leftX * offset + frame.upX * height;
            float cy = frame.originY + frame.leftY * offset + frame.upY * height;
            float cz = frame.originZ + frame.leftZ * offset + frame.upZ * height;
            // Se apagan al final del recorrido y crecen un poco: asi se leen como
            // burbujas que se van y no como puntos que se caen.
            float weight = amount * (1.0F - rise) * 0.55F;
            float size = BUBBLE_SIZE * (0.6F + 0.6F * rise);
            billboardAt(buffer, frame, cx, cy, cz, size, seconds(time) * 0.6F + i,
                    redTint * weight, greenTint * weight, blueTint * weight, 1.0F);
        }
    }

    /**
     * Gotas de lluvia: caen de arriba abajo, se apagan al llegar abajo y llevan un
     * poco de viento lateral (cada una con su fase) para que no caigan en columna.
     * Misma textura y mismo lote que las chispas: cero draws nuevos.
     */
    private static void drawDrops(MultiBufferSource bufferSource, Frame frame, float time,
                                  RelicGlowState glow, float amount, float motion) {
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        // Azul de agua mezclado con el color del estado (que en lluvia ya es profundo).
        float redTint = glow.red() * 0.55F + 0.62F * 0.45F;
        float greenTint = glow.green() * 0.75F + 0.82F * 0.25F;
        float blueTint = glow.blue() * 0.95F + 1.00F * 0.05F;
        // Correr acelera la caida: es la sensacion de que la lluvia te llega de lado.
        float speed = DROP_SPEED * (1.0F + 0.40F * motion);
        for (int i = 0; i < DROP_COUNT; i++) {
            // fall va de 0 (arriba) a 1 (abajo), desfasado por indice.
            float fall = fract(seconds(time) * speed + i * (1.0F / DROP_COUNT));
            float wind = sin(seconds(time) * 0.9F + i * 1.9F) * 0.07F;
            float offset = wind;
            float height = 0.40F - fall * 0.72F;
            float cx = frame.originX + frame.leftX * offset + frame.upX * height;
            float cy = frame.originY + frame.leftY * offset + frame.upY * height;
            float cz = frame.originZ + frame.leftZ * offset + frame.upZ * height;
            // Se ven al entrar arriba y se apagan al llegar abajo: una gota que
            // parpadea en el sitio se lee como un pixel roto, no como lluvia.
            float weight = amount * (0.25F + 0.75F * fall) * 0.60F;
            billboardAt(buffer, frame, cx, cy, cz, DROP_SIZE, seconds(time) * 0.8F + i,
                    redTint * weight, greenTint * weight, blueTint * weight, 1.0F);
        }
    }

    /**
     * Copos: caen muy despacio (un cruce cada ~3,5 s), se mecen de lado con un
     * giro propio y son mas pequenos que las gotas. Blanco azulado del estado, y
     * correr los arrastra sin acelerarlos mucho: el hielo no reacciona rapido.
     */
    /**
     * Pavesas: {@code CINDER_COUNT} granos que suben y vuelven a caer. La altura es
     * {@code 4t(1-t)} (cero al salir, uno en el punto alto, cero al llegar al
     * suelo), asi que su vuelo se ve entero; el tamano encoge en la bajada y el
     * brillo se apaga al final. Tinte debajo, aditivo pequeno.
     */
    private static void drawCinders(MultiBufferSource bufferSource, Frame frame, float time,
                                    RelicGlowState glow, float amount, float motion) {
        VertexConsumer tint = RelicConfig.AURA_TINT.get()
                ? bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(AURA_TEXTURE))
                : null;
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        float speed = CINDER_SPEED * (1.0F + 0.45F * motion);
        for (int i = 0; i < CINDER_COUNT; i++) {
            // Cada pavesa sale desfasada: van saltando de una en una, no todas a la vez.
            float t = fract(seconds(time) * speed + i * (1.0F / CINDER_COUNT));
            float height = CINDER_RISE * 4.0F * t * (1.0F - t);
            // Deriva lateral: la pavesa no sube recta, se abre al salir.
            float drift = sin(seconds(time) * 0.9F + i * 2.3F) * 0.07F * t;
            float cx = frame.originX + frame.leftX * drift + frame.upX * height;
            float cy = frame.originY + frame.leftY * drift + frame.upY * height;
            float cz = frame.originZ + frame.leftZ * drift + frame.upZ * height;
            float weight = amount * (1.0F - 0.75F * t) * CINDER_ADDITIVE;
            if (weight <= 0.002F) {
                continue;
            }
            float size = CINDER_SIZE * (1.0F - 0.45F * t);
            if (tint != null) {
                billboardAt(tint, frame, cx, cy, cz, size, t * 3.0F + i,
                        glow.red(), glow.green(), glow.blue(),
                        Math.min(1.0F, weight * CINDER_TINT_BOOST));
            }
            billboardAt(buffer, frame, cx, cy, cz, size, t * 3.0F + i,
                    glow.red() * weight, glow.green() * weight, glow.blue() * weight, 1.0F);
        }
    }

    /**
     * Motas del vacio: {@code MOTE_COUNT} granos que giran en un plano inclinado y
     * se encienden y apagan con un ciclo largo ({@code sin(life * PI)}: cero, uno,
     * cero). Tinte debajo y aditivo pequeno, como todos los pases de evento.
     */
    private static void drawMotes(MultiBufferSource bufferSource, Frame frame, float time,
                                  RelicGlowState glow, float amount, float motion) {
        VertexConsumer tint = RelicConfig.AURA_TINT.get()
                ? bufferSource.getBuffer(RelicRenderTypes.TINT_GLOW.apply(AURA_TEXTURE))
                : null;
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        // Muy lentas y apenas aceleran al correr: el End no se inmuta.
        float orbit = seconds(time) * MOTE_SPEED * (1.0F + 0.25F * motion);
        for (int i = 0; i < MOTE_COUNT; i++) {
            float phase = orbit * TWO_PI + i * (TWO_PI / MOTE_COUNT);
            float life = fract(orbit * 0.5F + i * (1.0F / MOTE_COUNT));
            float blink = sin(life * (float) Math.PI);
            float weight = amount * blink * MOTE_ADDITIVE;
            if (weight <= 0.002F) {
                continue;
            }
            float radius = MOTE_RADIUS * (0.72F + 0.36F * fract(i * 0.37F));
            float left = cos(phase) * radius;
            float up = sin(phase) * radius * 0.55F + 0.06F * sin(phase * 2.1F + i);
            float cx = frame.originX + frame.leftX * left + frame.upX * up;
            float cy = frame.originY + frame.leftY * left + frame.upY * up;
            float cz = frame.originZ + frame.leftZ * left + frame.upZ * up;
            if (tint != null) {
                billboardAt(tint, frame, cx, cy, cz, MOTE_SIZE, phase,
                        glow.red(), glow.green(), glow.blue(),
                        Math.min(1.0F, weight * MOTE_TINT_BOOST));
            }
            billboardAt(buffer, frame, cx, cy, cz, MOTE_SIZE, phase,
                    glow.red() * weight, glow.green() * weight, glow.blue() * weight, 1.0F);
        }
    }

    private static void drawFlakes(MultiBufferSource bufferSource, Frame frame, float time,
                                   RelicGlowState glow, float amount, float motion) {
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        float redTint = glow.red() * 0.45F + 0.88F * 0.55F;
        float greenTint = glow.green() * 0.60F + 0.96F * 0.40F;
        float blueTint = glow.blue() * 0.75F + 1.00F * 0.25F;
        float speed = FLAKE_SPEED * (1.0F + 0.30F * motion);
        for (int i = 0; i < FLAKE_COUNT; i++) {
            float fall = fract(seconds(time) * speed + i * (1.0F / FLAKE_COUNT));
            // El mecido es lo que distingue un copo de una gota: baja en zigzag.
            float sway = sin(seconds(time) * 1.1F + i * 2.6F) * 0.09F;
            float height = 0.42F - fall * 0.78F;
            float cx = frame.originX + frame.leftX * sway + frame.upX * height;
            float cy = frame.originY + frame.leftY * sway + frame.upY * height;
            float cz = frame.originZ + frame.leftZ * sway + frame.upZ * height;
            // Entran apagados y se encienden al llegar abajo, como un copo que se
            // posa: al reves que las gotas, que se apagan al caer.
            float weight = amount * (0.35F + 0.45F * fall) * 0.55F;
            billboardAt(buffer, frame, cx, cy, cz, FLAKE_SIZE, seconds(time) * 0.35F + i,
                    redTint * weight, greenTint * weight, blueTint * weight, 1.0F);
        }
    }

    /**
     * Brasas: suben, se mecen poco y <b>parpadean</b> (cada una con su fase), que es
     * lo que separa una brasa de una burbuja caliente. Naranja casi puro encima del
     * color del estado, y correr las aviva: es el mismo truco de lotes que las
     * burbujas y las gotas, sin draws nuevos.
     */
    private static void drawEmbers(MultiBufferSource bufferSource, Frame frame, float time,
                                   RelicGlowState glow, float amount, float motion) {
        VertexConsumer buffer = bufferSource.getBuffer(RelicRenderTypes.ADDITIVE_GLOW.apply(AURA_TEXTURE));
        float redTint = glow.red() * 0.70F + 1.00F * 0.30F;
        float greenTint = glow.green() * 0.55F + 0.55F * 0.45F;
        float blueTint = glow.blue() * 0.25F + 0.18F * 0.75F;
        float speed = EMBER_SPEED * (1.0F + 0.45F * motion);
        for (int i = 0; i < EMBER_COUNT; i++) {
            float rise = fract(seconds(time) * speed + i * (1.0F / EMBER_COUNT));
            float sway = sin(seconds(time) * 1.7F + i * 2.3F) * 0.06F;
            float height = -0.30F + rise * 0.70F;
            float cx = frame.originX + frame.leftX * sway + frame.upX * height;
            float cy = frame.originY + frame.leftY * sway + frame.upY * height;
            float cz = frame.originZ + frame.leftZ * sway + frame.upZ * height;
            // Parpadeo: la brasa se enciende y se apaga dos veces por ciclo. Sin esto
            // sube como una burbuja naranja y no se lee como fuego.
            float flicker = 0.55F + 0.45F * sin(seconds(time) * 9.0F + i * 2.7F);
            float weight = amount * flicker * (1.0F - 0.45F * rise) * 0.75F;
            float size = EMBER_SIZE * (1.0F - 0.35F * rise);
            billboardAt(buffer, frame, cx, cy, cz, size, seconds(time) * 0.9F + i,
                    redTint * weight, greenTint * weight, blueTint * weight, 1.0F);
        }
    }

    /** Parte decimal de un numero, sin asignar nada (Math.floor devuelve double). */
    private static float fract(float value) {
        return value - (float) Math.floor(value);
    }

    /** Las chispas se saltan en LITE y con los efectos reducidos, como el halo. */
    private static boolean sparksEnabled() {
        return RelicConfig.QUALITY.get() == RelicConfig.Quality.FULL
                && !RelicConfig.REDUCED_EFFECTS.get();
    }

    /** Latido lento de cada capa del aura: 0.82 .. 1.0, desfasado entre capas. */
    private static float pulseAt(float time, int layer) {
        return 0.82F + 0.18F * sin(time * 0.08F + layer * 1.7F);
    }

    // ------------------------------------------------------------------
    // Geometria
    // ------------------------------------------------------------------

    /**
     * Origen, escala y ejes de camara de este frame.
     *
     * <p>Es una instancia <b>reutilizada</b>, no un {@code record}: el render corre
     * en el hilo de render, un portador detras de otro, asi que no hay dos frames
     * a la vez. Antes cada frame creaba un {@code record} y, por cada billboard,
     * cuatro {@code Vector3f} para girar los ejes: del orden de 35 objetos por
     * portador y frame, que a 240 FPS y diez reliquias en pantalla son ~88 000
     * objetos por segundo solo de basura para el recolector.</p>
     */
    private static final class Frame {
        private float originX;
        private float originY;
        private float originZ;
        private float scale;
        private float leftX;
        private float leftY;
        private float leftZ;
        private float upX;
        private float upY;
        private float upZ;
        /** Eje X del modelo (derecha del portador) en espacio de vista, normalizado. */
        private float rightX;
        private float rightY;
        private float rightZ;
        /** Eje Z del modelo (hacia delante del portador) en espacio de vista. */
        private float backX;
        private float backY;
        private float backZ;
        /** Eje Y del modelo (arriba del portador): la normal del plano del suelo. */
        private float skyX;
        private float skyY;
        private float skyZ;
    }

    /** Unico frame vivo: se rellena en {@link #frame} y se lee en {@link #billboard}. */
    private static final Frame FRAME = new Frame();

    private static Frame frame(PoseStack poseStack) {
        Matrix4f matrix = poseStack.last().pose();
        Frame frame = FRAME;
        frame.originX = matrix.m30();
        frame.originY = matrix.m31();
        frame.originZ = matrix.m32();
        // Escala uniforme aproximada: longitud de la primera columna.
        float scale = (float) Math.sqrt(
                matrix.m00() * matrix.m00() + matrix.m01() * matrix.m01() + matrix.m02() * matrix.m02());
        frame.scale = (scale > 0.0F) && !Float.isNaN(scale) ? scale : 1.0F;

        // Ejes del modelo, normalizados: son los del portador, no los de la camara.
        // El eco en el suelo los necesita para tumbarse en el plano horizontal de
        // quien lleva la reliquia (y para bajar por su Y en vez de por la pantalla).
        float lenZ = (float) Math.sqrt(
                matrix.m20() * matrix.m20() + matrix.m21() * matrix.m21() + matrix.m22() * matrix.m22());
        float lenY = (float) Math.sqrt(
                matrix.m10() * matrix.m10() + matrix.m11() * matrix.m11() + matrix.m12() * matrix.m12());
        float invZ = lenZ > 1.0E-6F ? 1.0F / lenZ : 0.0F;
        float invY = lenY > 1.0E-6F ? 1.0F / lenY : 0.0F;
        float invX = 1.0F / frame.scale;
        frame.rightX = matrix.m00() * invX;
        frame.rightY = matrix.m01() * invX;
        frame.rightZ = matrix.m02() * invX;
        frame.backX = matrix.m20() * invZ;
        frame.backY = matrix.m21() * invZ;
        frame.backZ = matrix.m22() * invZ;
        frame.skyX = matrix.m10() * invY;
        frame.skyY = matrix.m11() * invY;
        frame.skyZ = matrix.m12() * invY;

        // Ejes de la camara tal cual: se leen sus componentes en el acto, sin
        // copiarlos a ningun vector propio.
        Camera camera = Minecraft.getInstance().gameRenderer.getMainCamera();
        frame.leftX = camera.getLeftVector().x();
        frame.leftY = camera.getLeftVector().y();
        frame.leftZ = camera.getLeftVector().z();
        frame.upX = camera.getUpVector().x();
        frame.upY = camera.getUpVector().y();
        frame.upZ = camera.getUpVector().z();
        return frame;
    }

    /**
     * Emite un quad que mira a camara, centrado en el origen del frame y girado
     * {@code angle} radianes alrededor del eje de vision.
     */
    private static void billboard(VertexConsumer buffer, Frame frame, float diameter, float angle,
                                  float red, float green, float blue, float alpha) {
        billboardAt(buffer, frame, frame.originX, frame.originY, frame.originZ,
                diameter, angle, red, green, blue, alpha);
    }

    /** Igual que {@link #billboard} pero centrado en un punto cualquiera. */
    private static void billboardAt(VertexConsumer buffer, Frame frame, float centerX, float centerY,
                                    float centerZ, float diameter, float angle,
                                    float red, float green, float blue, float alpha) {
        float cos = (float) Math.cos(angle);
        float sin = (float) Math.sin(angle);

        // Ejes del quad girados alrededor del eje de vision: una combinacion
        // lineal de los ejes de la camara, sin asignar nada.
        float axX = frame.leftX * cos + frame.upX * sin;
        float axY = frame.leftY * cos + frame.upY * sin;
        float axZ = frame.leftZ * cos + frame.upZ * sin;
        float ayX = frame.upX * cos - frame.leftX * sin;
        float ayY = frame.upY * cos - frame.leftY * sin;
        float ayZ = frame.upZ * cos - frame.leftZ * sin;

        float half = diameter * 0.5F * frame.scale;
        float x = half * axX;
        float y = half * axY;
        float z = half * axZ;
        float ux = half * ayX;
        float uy = half * ayY;
        float uz = half * ayZ;

        float ox = centerX;
        float oy = centerY;
        float oz = centerZ;

        quad(buffer,
                ox - x - ux, oy - y - uy, oz - z - uz,
                ox - x + ux, oy - y + uy, oz - z + uz,
                ox + x + ux, oy + y + uy, oz + z + uz,
                ox + x - ux, oy + y - uy, oz + z - uz,
                red, green, blue, alpha);
    }

    private static void quad(VertexConsumer buffer,
                             float x0, float y0, float z0,
                             float x1, float y1, float z1,
                             float x2, float y2, float z2,
                             float x3, float y3, float z3,
                             float red, float green, float blue, float alpha) {
        vertex(buffer, x0, y0, z0, 0.0F, 0.0F, red, green, blue, alpha);
        vertex(buffer, x1, y1, z1, 0.0F, 1.0F, red, green, blue, alpha);
        vertex(buffer, x2, y2, z2, 1.0F, 1.0F, red, green, blue, alpha);
        vertex(buffer, x3, y3, z3, 1.0F, 0.0F, red, green, blue, alpha);
    }

    /**
     * El RenderType aditivo usa el mismo formato de vertice que las entidades
     * ({@code NEW_ENTITY}), asi que hay que rellenar color, UV, overlay,
     * lightmap y normal en ese orden aunque aqui solo usemos la UV. En 1.20.1 el
     * metodo del overlay se llama {@code overlayCoords}, no {@code overlay}.
     */
    private static void vertex(VertexConsumer buffer, float x, float y, float z,
                               float u, float v, float red, float green, float blue, float alpha) {
        buffer.vertex(x, y, z)
                .color(red, green, blue, alpha)
                .uv(u, v)
                .overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT)
                .normal(0.0F, 1.0F, 0.0F)
                .endVertex();
    }

    /**
     * Movimiento propio del objeto, aplicado al {@code PoseStack} <b>antes</b> del
     * modelo y del aura: los dos lean la matriz, asi que se mueven juntos.
     *
     * <p>Hasta 1.0.30 la reliquia estaba clavada al hombro: la animacion movia
     * huesos, pero el conjunto no respiraba. Aqui hay dos cosas:</p>
     * <ul>
     *   <li><b>flotar</b>: 0.022 bloques de vaiven lento, con la amplitud segun el
     *       estado de brillo (tormenta 1.5x, herido 0.6x);</li>
     *   <li><b>asentarse</b>: en un evento el conjunto se achata un 4% y se ensancha
     *       un 5%, que es lo que da sensacion de golpe frente a solo cambiar de
     *       color.</li>
     * </ul>
     *
     * <p>{@code yDown} existe porque el render de la entidad hereda la convencion
     * del modelo del jugador (Y+ hacia abajo) y la vista previa esta en
     * coordenadas de mundo (Y+ hacia arriba): el vaiven tiene que ir al reves.</p>
     */
    static void applyAliveMotion(PoseStack poseStack, float partialTick, float flash,
                                 RelicAnimatable.Mood mood, boolean yDown, float motion) {
        float time = time(partialTick);
        float energy = switch (mood) {
            case STORM -> 1.5F;
            case RESONANT -> 1.2F;
            case DARK -> 0.9F;
            case RAIN -> 0.8F;
            case WOUNDED -> 0.6F;
            // De noche flota poco y muy despacio: el estado es "quieta y palida".
            case NIGHT -> 0.75F;
            // Bajo el agua el vaiven es el mas corto: el agua frena todo.
            case SUBMERGED -> 0.50F;
            // Un portal tira de ella: flota un poco mas que en reposo.
            case PORTAL -> 1.10F;
            // Ardiendo vibra: el vaiven mas amplio despues de la tormenta.
            case BURNING -> 1.35F;
            // Congelandose apenas se mueve: el frio entumece.
            case FREEZING -> 0.55F;
            // El Nether vibra mas que el reposo pero menos que ardiendo; en el End
            // no hay nada que empuje, asi que flota por debajo.
            case NETHER -> 1.25F;
            case END -> 0.70F;
            case NEUTRAL -> 1.0F;
        };
        // Correr suma un 60% de vaiven y agacharse lo recorta: es la diferencia
        // entre una reliquia que te sigue y una que se queda quieta contigo.
        energy *= 1.0F + 0.60F * motion;
        // En segundos, no en ticks: con ticks esto daba 5,4 Hz, o sea un temblor
        // de cinco veces por segundo con el que la reliquia "saltaba" en el sitio.
        float elapsed = seconds(time);
        float lift = 0.022F * energy * sin(elapsed * 1.7F);
        poseStack.translate(0.0D, yDown ? -lift : lift, 0.0D);
        // Un grado escaso de ladeo, desfasado del vaiven: si no, parece un pez.
        // Se rota la matriz en el sitio: pasar un eje a mulPose crea un Quaternionf
        // por reliquia y frame, y el camino de render no asigna nada.
        poseStack.last().pose().rotateY((float) Math.toRadians(1.1F * sin(elapsed * 0.7F)));
        if (flash > 0.01F) {
            float squeeze = Math.min(1.0F, flash);
            poseStack.scale(1.0F + 0.05F * squeeze, 1.0F - 0.04F * squeeze, 1.0F + 0.05F * squeeze);
        }
    }

    private static float sin(float value) {
        return (float) Math.sin(value);
    }

    private static float cos(float value) {
        return (float) Math.cos(value);
    }

    /**
     * Segundos de juego a partir de los ticks de {@link #time(float)}.
     *
     * <p>Todos estos efectos estan pensados en "por segundo" (una gota tarda ~1 s
     * en caer, una brasa parpadea ~1,4 veces por segundo), pero el reloj de la
     * reliquia son ticks: 20 por segundo. Hasta 1.0.42 las gotas, las brasas y el
     * vaiven usaban el numero tal cual y salian <b>veinte veces</b> mas rapidos —
     * las gotas cambiaban de sitio 22 veces por segundo y el vaiven era un
     * temblor de 5 Hz. Esto es lo que separa "flota" de "salta".</p>
     */
    private static float seconds(float ticks) {
        return ticks / 20.0F;
    }

    private static float time(float partialTick) {
        Minecraft minecraft = Minecraft.getInstance();
        return (minecraft.level == null ? 0.0F : minecraft.level.getGameTime()) + partialTick;
    }
}
