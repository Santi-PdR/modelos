package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.state.BoneSnapshot;
import software.bernie.geckolib.model.DefaultedItemGeoModel;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Modelo de la capa equipada v1.14.0 (Deterioro / Evil Saiyan Rosé).
 *
 * <p>La capa es un mosaico 9×3 sobre UN rectángulo global: las 27 caras
 * comparten escala y el canvas 96×48 se lee como una sola ilustración. En
 * runtime se ocultan los 61 huesos originales con cubos que no pertenecen a
 * la cadena {@code chestplate → cape_top/mid/bottom}, pero se dejan vivos sus
 * hijos {@code v15_*}, que heredan las animaciones originales.</p>
 *
 * <p>v1.7.0 usa 3 pliegues anchos en lugar de 9 rayas finas: el relieve en Z
 * de la geometría y el sombreado del canvas muestrean la misma onda, así que
 * el retardo por columna se suaviza para que cada pliegue se mueva como un
 * bloque y no como un código de barras.</p>
 *
 * <p>v1.8.0 añade 5 estrellas 3D ({@code v15_star_*}) sobre la constelación
 * del canvas. Usan la zona emisiva ya existente, así que {@link CapaGlowLayer}
 * las hace latir sin cambiar la cobertura del glowmask.</p>
 *
 * <p>v1.9.0 añade 4 fragmentos orbitales ({@code v15_orbit_*}) alrededor del
 * medallón de Blight Star. Giran muy despacio en Z, con un poco más de energía
 * al correr; es animación cosmética y comparte el mismo fail-safe.</p>
 *
 * <p>También anima las 2 hombreras ({@code v15_pauldron_*}) y las 2 cadenas
 * delanteras ({@code v15_front_chain_*}): siguen el giro del cuerpo y el
 * sprint con amplitudes de 1–2°. Los nervios, drapeados y pesas cuelgan de
 * los paneles/hembras, así que heredan la onda sin coste extra de búsqueda.</p>
 *
 * <p>Corrección del crash de v1.5.0 (vigente): GeckoLib guarda las rotaciones
 * de los huesos en <b>radianes</b> (ver {@code BakedModelFactory.constructBone}:
 * {@code Math.toRadians(-rotation.x)}). v1.5.0 sumaba grados directamente,
 * así que un {@code bend} de 12 se convertía en 12 rad ≈ 687°: matrices
 * degeneradas por frame y culling/render inestable. Ahora todos los ángulos
 * se convierten con {@link Math#toRadians(double)}.</p>
 *
 * <p>También se elimina la consulta al modelo bakeado del hot path: puede
 * llamar a {@code AnimationProcessor.setActiveModel()} cuando cambia el modelo,
 * lo que vacía y vuelve a registrar los huesos (y por tanto reinicia los
 * {@link BoneSnapshot}) a mitad de frame. Los huesos se resuelven una sola vez
 * desde el {@code AnimationProcessor} que ya está activo, con un guardia de
 * identidad para sobrevivir a un resource reload.</p>
 *
 * <p>La onda de la tela es 100% cosmética. Si algo inesperado falla, se
 * desactiva una sola vez (con log) y la capa sigue renderizándose con la pose
 * estática del geo, en vez de tirar el juego.</p>
 *
 * <p>REV. B: NO hay motas ni ceniza en el modelo. Los 26 cubos sueltos
 * que aparecían flotando en Blockbench se eliminaron del geo; las
 * partículas las emite {@code CapaDeteriorerItem.spawnAura()} desde el
 * servidor cuando la capa está equipada. Además, la fase de la onda
 * dejó de ser {@code i * 0.37} (un índice global sin relación con la
 * tela) y ahora es {@code -0.62*tramo + columna*0.19}: el movimiento
 * BAJA por cada jirón. Curva y constantes compartidas con
 * {@code tools/cape_motion.py}, el {@code .bbmodel}, el
 * {@code animation.json} de GeckoLib y el visor.</p>
 *
 * <p>v1.21.0: Java NO vuelve a calcular esa onda. GeckoLib ya aplicó
 * {@code sample()} cuando se ejecuta {@code setCustomAnimations}; este
 * modelo sólo SUMA la respuesta al giro/salto/sprint del portador.
 * Antes las dos curvas se pisaban y la capa temblaba distinto en el
 * juego que en Blockbench.</p>
 *
 * Referencias (ideas, no código portado): tr7zw/WaveyCapes, ismaildzf/finery,
 * GlowberryClient #102/#106, FabricExtras/ArmorModelAPI y GeckoLib 1.20.1.
 */
public class CapaArmorModel extends DefaultedItemGeoModel<CapaDeteriorerItem> {
    private static final String[] SECTIONS = {"cape_top", "cape_mid", "cape_bottom"};
    /** v1.6.0: 9 columnas x 3 filas, mismo rectángulo global en el canvas. */
    private static final int COLUMNS = 9;
    /** v1.9.0: 4 fragmentos orbitando el núcleo de Blight Star. */
    private static final int ORBIT_SHARDS = 4;
    /** v1.9.0: arnés delantero animado con el giro/sprint del portador. */
    private static final int PAULDRONS = 2;
    private static final int FRONT_CHAINS = 2;

    /**
     * v1.6.0: los 61 huesos originales con cubos que NO son la cadena
     * chestplate -> cape_top/mid/bottom. Eran las placas, dedos, jirones,
     * hombreras y tiras que tapaban la superficie continua y daban el aspecto
     * de "cajas apiladas". Se ocultan en runtime; el geo prístino sigue intacto
     * y sus animaciones siguen accionando a los huesos padres.
     */
    private static final String[] HIDDEN_DETAILS = {
            "arnes_frontal", "collar_dentado", "yugo",
            "espina_0", "espina_1", "espina_2",
            "mano_hombro_R", "dedo_hR_0", "dedo_hR_1", "dedo_hR_2",
            "dedo_hR_3", "dedo_hR_4",
            "mano_hombro_L", "dedo_hL_0", "dedo_hL_1", "dedo_hL_2",
            "dedo_hL_3", "dedo_hL_4",
            "cristal_top_L", "flujo_violeta_0",
            "esquirla_0", "esquirla_1",
            "nucleo_sigilo", "mano_sigilo",
            "dedo_sigilo_0", "dedo_sigilo_1", "dedo_sigilo_2",
            "dedo_sigilo_3", "dedo_sigilo_4",
            "cinturon_oxidado", "lengueta", "colgajo_R", "colgajo_L",
            "cristal_mid_R", "cristal_mid_L",
            "flujo_violeta_1", "flujo_violeta_2", "esquirla_2", "esquirla_3",
            "jiron_0", "jiron_1", "jiron_2", "jiron_3", "jiron_4",
            "faldon_R", "faldon_R_tip", "faldon_L", "faldon_L_tip",
            "cristal_bot_R", "flujo_violeta_3", "flujo_violeta_4",
            "esquirla_4", "esquirla_5", "esquirla_6", "esquirla_7",
            "hombrera_der", "tira_der_0", "tira_der_1",
            "hombrera_izq", "tira_izq_0", "tira_izq_1"
    };

    /** Estado por portador; es una instancia del modelo, no un static global. */
    private final Map<Long, double[]> motion = new ConcurrentHashMap<>();

    // ------------------------------------------------------------------
    // v1.27.0 — CONTROLES DE VISIBILIDAD (diagnóstico y aislamiento).
    //
    // El usuario vio "motas" y "masas negras" en la parte alta de la
    // espalda y no sabía de dónde venían. Estos interruptores permiten
    // mirar POR PARTES lo que se dibuja: las anclas de la onda, la
    // hombrera o la cadena, por separado.
    //
    //   normal     : todo lo de siempre (anclas OCULTAS).
    //   anclas     : sólo las 27 anclas v15_cloth_* (el resto fuera).
    //   hombreras  : sólo las hombreras v18_pad_*.
    //   cadena     : sólo la cadena v18_chain_*.
    //
    // Se eligen con la propiedad del sistema `capa.visibilidad` y se
    // pueden cambiar en caliente con setVisibilidad(...).
    // ------------------------------------------------------------------
    public enum Visibilidad { NORMAL, ANCLAS, HOMBRERAS, CADENA }

    private static Visibilidad visibilidad = leerVisibilidad();

    /** Modo aplicado al modelo; si cambia, se vuelve a aplicar. */
    private Visibilidad visibilidadAplicada;

    private static Visibilidad leerVisibilidad() {
        String raw = System.getProperty("capa.visibilidad", "normal");
        for (Visibilidad v : Visibilidad.values()) {
            if (v.name().equalsIgnoreCase(raw))
                return v;
        }
        return Visibilidad.NORMAL;
    }

    /** Modo de visibilidad actual (diagnóstico). */
    public static Visibilidad getVisibilidad() {
        return visibilidad;
    }

    /** Cambia el modo en caliente; se aplica en el siguiente frame. */
    public static void setVisibilidad(Visibilidad modo) {
        if (modo != null)
            visibilidad = modo;
    }

    private GeoBone cachedRoot;
    private GeoBone[] panels;
    private GeoBone[] hems;
    private GeoBone[] orbitShards;
    private GeoBone[] pauldrons;
    private GeoBone[] frontChains;
    /** v1.13.0: hombreras TRASERAS animadas (las que se ven en F5). */
    private GeoBone[] rearPads;
    private float[] baseX;
    private float[] baseY;
    private float[] baseZ;
    private float[] hemBaseZ;
    private float[] orbitBaseZ;
    private float[] pauldronBaseZ;
    private float[] frontChainBaseZ;
    private float[] rearPadBaseX;
    private boolean clothReady;
    /** v1.14.0: collar, jirones, venas y microvóxeles de la piel nueva. */
    private GeoBone[] deterioroBones;
    private float[][] deterioroBase;
    /** rev. B: {familia, columna, tramo} REAL, no el indice del array. */
    private int[][] deterioroParts;
    /** Fail-safe cosmético: tras un error inesperado no se vuelve a intentar. */
    private boolean disabled;

    public CapaArmorModel(ResourceLocation assetSubpath) {
        super(assetSubpath);
    }

    @Override
    public void setCustomAnimations(CapaDeteriorerItem animatable, long instanceId,
                                    AnimationState<CapaDeteriorerItem> state) {
        if (disabled)
            return;
        try {
            resolveBones();
            // v1.27.0: si el interruptor de visibilidad cambió, se reaplica.
            applyVisibilidad();
            if (clothReady)
                applyClothWave(animatable, instanceId, state);
        } catch (Exception | LinkageError error) {
            disabled = true;
            CapaTestMod.LOGGER.error(
                    "Blight Star Mantle: animación de tela desactivada (la capa se muestra estática)", error);
            restoreBasePose();
        }
    }

    /**
     * Resuelve los huesos una vez. {@code getBone()} consulta el
     * AnimationProcessor ya activo: a diferencia de consultar el modelo bakeado no
     * puede lanzar GeckoLibException ni reiniciar los snapshots en mitad del
     * frame. Si el geo se recarga, cambia la identidad del hueso raíz y se
     * vuelve a inicializar.
     */
    private void resolveBones() {
        GeoBone root = getBone(SECTIONS[0]).orElse(null);
        if (root == null) {                 // modelo aún no bakeado
            clothReady = false;
            return;
        }
        if (clothReady && root == cachedRoot)
            return;

        GeoBone[] foundPanels = new GeoBone[SECTIONS.length * COLUMNS];
        float[] foundX = new float[foundPanels.length];
        float[] foundY = new float[foundPanels.length];
        float[] foundZ = new float[foundPanels.length];
        int resolved = 0;
        for (int section = 0; section < SECTIONS.length; section++) {
            for (int column = 0; column < COLUMNS; column++) {
                int i = section * COLUMNS + column;
                GeoBone bone = getBone("v15_cloth_" + SECTIONS[section] + "_" + column).orElse(null);
                if (bone == null)
                    continue;
                foundPanels[i] = bone;
                BoneSnapshot snapshot = bone.getInitialSnapshot();
                foundX[i] = snapshot == null ? bone.getRotX() : snapshot.getRotX();
                foundY[i] = snapshot == null ? bone.getRotY() : snapshot.getRotY();
                foundZ[i] = snapshot == null ? bone.getRotZ() : snapshot.getRotZ();
                resolved++;
            }
        }

        GeoBone[] foundHems = new GeoBone[COLUMNS];
        float[] foundHemZ = new float[COLUMNS];
        for (int column = 0; column < COLUMNS; column++) {
            GeoBone bone = getBone("v15_hem_" + column).orElse(null);
            if (bone == null)
                continue;
            foundHems[column] = bone;
            BoneSnapshot snapshot = bone.getInitialSnapshot();
            foundHemZ[column] = snapshot == null ? bone.getRotZ() : snapshot.getRotZ();
        }

        GeoBone[] foundOrbit = new GeoBone[ORBIT_SHARDS];
        float[] foundOrbitZ = new float[ORBIT_SHARDS];
        for (int i = 0; i < ORBIT_SHARDS; i++) {
            GeoBone bone = getBone("v15_orbit_" + i).orElse(null);
            if (bone == null)
                continue;
            foundOrbit[i] = bone;
            BoneSnapshot snapshot = bone.getInitialSnapshot();
            foundOrbitZ[i] = snapshot == null ? bone.getRotZ() : snapshot.getRotZ();
        }

        GeoBone[] foundPauldrons = new GeoBone[PAULDRONS];
        float[] foundPauldronZ = new float[PAULDRONS];
        for (int i = 0; i < PAULDRONS; i++) {
            GeoBone bone = getBone("v15_pauldron_" + (i == 0 ? "L" : "R")).orElse(null);
            if (bone == null)
                continue;
            foundPauldrons[i] = bone;
            BoneSnapshot snapshot = bone.getInitialSnapshot();
            foundPauldronZ[i] = snapshot == null ? bone.getRotZ() : snapshot.getRotZ();
        }

        GeoBone[] foundChains = new GeoBone[FRONT_CHAINS];
        float[] foundChainZ = new float[FRONT_CHAINS];
        for (int i = 0; i < FRONT_CHAINS; i++) {
            GeoBone bone = getBone("v15_front_chain_" + (i == 0 ? "L" : "R")).orElse(null);
            if (bone == null)
                continue;
            foundChains[i] = bone;
            BoneSnapshot snapshot = bone.getInitialSnapshot();
            foundChainZ[i] = snapshot == null ? bone.getRotZ() : snapshot.getRotZ();
        }

        // v1.13.0: las hombreras traseras se resuelven aparte para darles
        // su propio vaiven; no heredan la onda de los paneles de tela.
        GeoBone[] foundRear = new GeoBone[PAULDRONS];
        float[] foundRearBaseX = new float[PAULDRONS];
        for (int i = 0; i < PAULDRONS; i++) {
            GeoBone bone = getBone("v15_rear_pad_" + (i == 0 ? "L" : "R")).orElse(null);
            if (bone == null)
                continue;
            foundRear[i] = bone;
            BoneSnapshot snap = bone.getInitialSnapshot();
            foundRearBaseX[i] = snap == null ? bone.getRotX() : snap.getRotX();
        }

        cachedRoot = root;
        panels = foundPanels;
        hems = foundHems;
        orbitShards = foundOrbit;
        pauldrons = foundPauldrons;
        frontChains = foundChains;
        rearPads = foundRear;
        baseX = foundX;
        baseY = foundY;
        baseZ = foundZ;
        hemBaseZ = foundHemZ;
        orbitBaseZ = foundOrbitZ;
        pauldronBaseZ = foundPauldronZ;
        frontChainBaseZ = foundChainZ;
        rearPadBaseX = foundRearBaseX;
        clothReady = resolved > 0;
        resolveDeterioro();
        hideOriginalSlabs();
    }

    /**
     * v1.30.0: las 3 losas (cape_top/mid/bottom) ya NO se ocultan.
     *
     * Antes se llamaba a setHidden(true) para tapar la masa plana/boxy,
     * pero en tercera persona (F5) GeckoLib NO renderiza a los HIJOS de
     * un hueso oculto: al ocultar la losa, desaparecian también las tiras
     * v17_ribbon_* (sus hijas), y la capa se volvía invisible al mirarla
     * desde atrás.
     *
     * Ahora el geo ya no tiene cubos en las losas (armor_model_pipeline
     * los anuló), así que quedan visibles pero sin geometría: nada se
     * dibuja de ellas y, al NO estar ocultas, sus hijas (las tiras)
     * renderizan desde cualquier ángulo. Se setea visible explícitamente
     * para cubrir cualquier recarga del geo.
     */
    private void hideOriginalSlabs() {
        for (String section : SECTIONS) {
            GeoBone slab = getBone(section).orElse(null);
            if (slab != null) {
                slab.setHidden(false);
                slab.setChildrenHidden(false);
            }
        }
        for (String name : HIDDEN_DETAILS) {
            GeoBone detail = getBone(name).orElse(null);
            if (detail != null)
                detail.setHidden(true);   // oculta también a sus descendientes
        }
        // v1.27.0: las 27 ANCLAS `v15_cloth_*` son cubos de 0.16 que
        // existen SÓLO para dar pose a la onda (los usa panels[] y la
        // animación). No se dibujan: se ocultan SIN borrar el hueso, la
        // jerarquía ni ninguna pista del animation.json.
        hideClothAnchors(false);
        // Los huesos se acaban de resolver otra vez: hay que reaplicar el
        // modo de visibilidad (puede que el geo se haya recargado y los
        // huesos sean objetos nuevos, sin el estado de `hidden`).
        visibilidadAplicada = null;
    }

    /**
     * v1.27.0: las 27 anclas {@code v15_cloth_*} son cubos de 0.16 que
     * existen SÓLO para dar pose a la onda (los usa {@code panels[]} y el
     * animation.json). Se OCULTAN sin borrar el hueso, la jerarquía ni
     * ninguna pista: el modelo sigue moviéndose igual, pero el cuello no
     * tiene motas negras.
     *
     * @param visible true sólo para el modo de diagnóstico ANCLAS.
     */
    private void hideClothAnchors(boolean visible) {
        for (String section : SECTIONS) {
            for (int column = 0; column < COLUMNS; column++) {
                GeoBone anchor = getBone("v15_cloth_" + section + "_" + column).orElse(null);
                if (anchor != null)
                    anchor.setHidden(!visible);
            }
        }
    }

    /**
     * v1.27.0: aplica el modo de visibilidad (normal / anclas /
     * hombreras / cadena). Se llama al resolver los huesos y cada vez
     * que el interruptor cambia, para poder aislar una pieza y ver de
     * verdad qué pinta en el juego.
     */
    private void applyVisibilidad() {
        if (visibilidadAplicada == visibilidad && clothReady)
            return;
        // 1) Punto de partida: se restablece todo lo gestionado.
        // v1.30.0: las losas ya NO se ocultan (ver hideOriginalSlabs):
        // ocultarlas volvía invisible a las tiras v17_ribbon_* en F5.
        for (String section : SECTIONS) {
            GeoBone slab = getBone(section).orElse(null);
            if (slab != null) {
                slab.setHidden(false);
                slab.setChildrenHidden(false);
            }
        }
        for (String name : HIDDEN_DETAILS) {
            GeoBone detail = getBone(name).orElse(null);
            if (detail != null)
                detail.setHidden(true);
        }
        for (String name : DETERIORO_NAMES) {
            GeoBone bone = getBone(name).orElse(null);
            if (bone != null) {
                bone.setHidden(false);
                bone.setChildrenHidden(false);
            }
        }
        // 2) Las anclas se ocultan siempre (salvo en modo ANCLAS): son
        //    referencias de pose, no piezas visibles.
        hideClothAnchors(visibilidad == Visibilidad.ANCLAS);
        // 3) Aislamiento: fuera todo lo que no sea la familia elegida.
        String familia = null;
        if (visibilidad == Visibilidad.HOMBRERAS)
            familia = "v18_pad_";
        else if (visibilidad == Visibilidad.CADENA)
            familia = "v18_chain_";
        if (visibilidad == Visibilidad.ANCLAS)
            familia = "v15_cloth_";
        if (familia != null) {
            for (String name : DETERIORO_NAMES) {
                if (name.startsWith(familia))
                    continue;
                GeoBone bone = getBone(name).orElse(null);
                if (bone != null) {
                    bone.setHidden(true);
                    bone.setChildrenHidden(true);
                }
            }
        }
        visibilidadAplicada = visibilidad;
    }

    private void applyClothWave(CapaDeteriorerItem animatable, long instanceId,
                                AnimationState<CapaDeteriorerItem> state) {
        Object rawEntity = state.getData(DataTickets.ENTITY);
        Entity entity = rawEntity instanceof Entity e ? e : null;
        Vec3 velocity = entity == null ? Vec3.ZERO : entity.getDeltaMovement();

        double targetSpeed = Mth.clamp(velocity.horizontalDistance() * 2.2D, 0.0D, 1.0D);
        double targetLift = entity == null ? 0.0D : Mth.clamp(-velocity.y * 1.3D, -0.45D, 1.0D);
        float turnTarget = 0.0F;
        if (entity instanceof LivingEntity living) {
            float delta = (living.yBodyRot - living.yBodyRotO + 540.0F) % 360.0F - 180.0F;
            turnTarget = Mth.clamp(delta / 14.0F, -1.0F, 1.0F);
        }
        double targetSneak = entity != null && entity.isCrouching() ? 1.0D : 0.0D;
        double targetWater = entity != null && entity.isInWater() ? 1.0D : 0.0D;
        double targetAir = entity != null && !entity.onGround() ? 1.0D : 0.0D;
        double targetSprint = entity != null && entity.isSprinting() ? 1.0D : 0.0D;

        if (motion.size() > 128)
            motion.clear();

        double[] m = motion.computeIfAbsent(instanceId, key -> new double[7]);
        m[0] = Mth.lerp(m[0], targetSpeed, 0.14D);
        m[1] = Mth.lerp(m[1], targetLift, 0.10D);
        m[2] = Mth.lerp(m[2], turnTarget, 0.12D);
        m[3] = Mth.lerp(m[3], targetSneak, 0.12D);
        m[4] = Mth.lerp(m[4], targetWater, 0.06D);
        m[5] = Mth.lerp(m[5], targetAir, 0.12D);
        m[6] = Mth.lerp(m[6], targetSprint, 0.14D);

        double time = entity == null
                ? state.getAnimationTick() / 20.0D
                : (entity.tickCount + state.getPartialTick()) / 20.0D;
        double seed = entity == null ? instanceId : entity.getId();
        double wind = Math.sin(time * 1.31D + seed * 0.37D) * 0.65D
                + Math.sin(time * 2.73D + seed * 0.11D) * 0.35D;

        double speed = m[0];
        double lift = m[1];
        double turn = m[2];
        double sneak = m[3];
        double water = m[4];
        double airborne = m[5];
        double sprint = m[6];
        double amplitude = Math.max(0.10D, 0.55D + speed * 3.4D + lift
                + airborne * 1.7D + sprint * 0.8D + sneak * 0.5D + water * 0.6D);

        for (int section = 0; section < SECTIONS.length; section++) {
            double share = 0.30D + 0.35D * section;   // hombros -> dobladillo
            for (int column = 0; column < COLUMNS; column++) {
                int i = section * COLUMNS + column;
                GeoBone panel = panels[i];
                if (panel == null)
                    continue;

                // v1.7.0: retardo por columna más suave. Con 3 pliegues
                // anchos (3 columnas por pliegue) un retardo fuerte por
                // columna descompone cada pliegue en tiras que se mueven
                // independientes; queremos que ondeen como una sola tela.
                double phase = time * (4.4D + speed * 2.2D)
                        - section * 0.55D - column * 0.030D;
                double wave = Math.sin(phase + wind * 0.8D);
                double ripple = Math.sin(time * 2.3D - section * 0.7D
                        + column * 0.42D + wind * 0.5D);
                double lateral = (column - (COLUMNS - 1) / 2.0D) / ((COLUMNS - 1) / 2.0D);

                // Todo en GRADOS, convertido a radianes justo antes de setRot*.
                double bendDeg = Mth.clamp(amplitude * share * (0.55D + 0.45D * wave), 0.0D, 12.0D);
                double swayDeg = Mth.clamp((turn * 3.0D + wind * 0.75D
                        + ripple * 0.65D) * share * (0.25D + speed * 0.75D), -8.0D, 8.0D);
                double curlDeg = Mth.clamp((lateral * 2.1D + ripple * 0.85D)
                        * (0.35D + speed * 1.1D), -6.0D, 6.0D);

                panel.setRotX(baseX[i] - (float) Math.toRadians(bendDeg));
                panel.setRotY(baseY[i] + (float) Math.toRadians(
                        swayDeg * (0.30D + 0.70D * Math.abs(lateral))));
                panel.setRotZ(baseZ[i] + (float) Math.toRadians(curlDeg));
            }
        }

        for (int column = 0; column < COLUMNS; column++) {
            GeoBone hem = hems[column];
            if (hem == null)
                continue;
            double flutterDeg = Math.sin(time * 5.1D - column * 0.55D + wind * 0.7D)
                    * (0.7D + speed * 2.4D + airborne * 1.2D);
            // v1.47.0: SEGUNDO armónico del flutter (amplitud 0.4 grados,
            // frecuencia mayor, fase distinta por columna): el dobladillo
            // tiene el temblor fino del borde del tejido, no un vaivén
            // simple. Es ROTACIÓN (RotZ) pura: no toca la posición del
            // paño ni puede empujarlo al cuerpo.
            flutterDeg += 0.4D * Math.sin(time * 9.2D - column * 1.1D + wind * 0.3D);
            hem.setRotZ(hemBaseZ[column]
                    + (float) Math.toRadians(Mth.clamp(flutterDeg, -5.0D, 5.0D)));
        }

        // v1.9.0: los 4 fragmentos de Blight Star giran como un halo lento.
        // Sólo se toca RotZ: el hueso padre (panel de tela) ya aporta la onda.
        for (int i = 0; i < ORBIT_SHARDS; i++) {
            GeoBone shard = orbitShards[i];
            if (shard == null)
                continue;
            double spinDeg = Math.sin(time * (0.85D + speed * 0.65D)
                    + i * Math.PI / 2.0D + seed * 0.09D)
                    * (1.4D + sprint * 1.2D);
            // v1.44.0: se suma un segundo armónico de ROTACIÓN (amplitud
            // 0.25°, fase distinta) para que el halo no gire como un
            // motor regular: tiene el temblor de los fragmentos
            // flotando. Sólo se toca RotZ: es rotación pura, no toca
            // la posición del paño ni puede empujarlo al cuerpo.
            spinDeg += 0.25D * Math.sin(time * 2.4D + i * 1.7D + seed * 0.05D);
            // v1.49.0: TERCER armónico de ROTACIÓN (0.10°, fase distinta):
            // el halo lee el temblor fino de los fragmentos flotando, no
            // un vaivén de dos frecuencias. Sólo RotZ: rotación pura,
            // sin tocar la posición del paño ni empujarlo al cuerpo.
            spinDeg += 0.10D * Math.sin(time * 4.1D + i * 2.6D + seed * 0.04D);
            shard.setRotZ(orbitBaseZ[i] + (float) Math.toRadians(spinDeg));
        }

        // Arnés delantero: acompaña el giro y el sprint sin competir con la
        // onda principal. Las cadenas tienen un vaivén corto y silencioso.
        for (int i = 0; i < PAULDRONS; i++) {
            GeoBone pad = pauldrons[i];
            if (pad == null)
                continue;
            double padDeg = turn * 1.2D + sprint * 0.8D
                    + Math.sin(time * 1.7D + i * 1.9D + wind * 0.2D) * 0.45D;
            // v1.46.0: se suma un segundo armónico de ROTACIÓN (amplitud
            // 0.15 grados, fase distinta) para que la hombrera no cole
            // con un vaivén regular: tiene el temblor de la pieza
            // flotando. Sólo se toca RotZ: es rotación pura, no toca
            // la posición del paño ni puede empujarlo al cuerpo.
            padDeg += 0.15D * Math.sin(time * 2.9D + i * 2.3D);
            // v1.49.0: TERCER armónico de ROTACIÓN (0.08°, fase distinta):
            // la hombrera delantera lee el temblor fino de la pieza
            // flotando, no un vaivén de dos frecuencias. Sólo RotZ:
            // rotación pura, sin tocar la posición del paño.
            padDeg += 0.08D * Math.sin(time * 4.3D + i * 2.7D);
            pad.setRotZ(pauldronBaseZ[i] + (float) Math.toRadians(padDeg));
        }
        // v1.13.0: ANIMACION de las hombreras traseras. RotX con retardo
        // por lado + un pequeno giro en Z con el giro del cuerpo. Todo en
        // grados convertido a radianes, como el resto del modelo.
        if (rearPads != null) {
            for (int i = 0; i < rearPads.length; i++) {
                GeoBone pad = rearPads[i];
                if (pad == null)
                    continue;
                double phase = time * (2.6D + speed * 2.0D) + i * 1.7D + wind * 0.4D;
                double liftDeg = Math.sin(phase) * (0.8D + speed * 2.2D
                        + airborne * 1.6D + sprint * 1.1D);
                double tiltDeg = turn * 1.6D + Math.sin(phase * 0.7D) * 0.6D;
                // v1.47.0: SEGUNDOS armónicos de ROTACIÓN para la leva
                // (RotX, 0.3 grados) y la inclinación (RotZ, 0.2 grados),
                // con fase distinta: la hombrera trasera tiene el
                // temblor fino de la pieza flotando, no un vaivén simple.
                // Es rotación pura: no toca la posición del paño.
                liftDeg += 0.3D * Math.sin(phase * 1.9D + i * 2.2D);
                tiltDeg += 0.2D * Math.sin(phase * 2.3D + i * 1.5D);
                // v1.49.0: TERCER armónico de ROTACIÓN para la leva
                // (RotX, 0.12 grados) y la inclinación (RotZ, 0.10
                // grados), con fase distinta: la hombrera trasera lee el
                // temblor ultrafino de la pieza flotando, no un vaivén de
                // dos frecuencias. Es rotación pura: no toca la posición
                // del paño ni puede empujarlo al cuerpo.
                liftDeg += 0.12D * Math.sin(phase * 2.7D + i * 2.9D);
                tiltDeg += 0.10D * Math.sin(phase * 3.1D + i * 2.5D);
                pad.setRotX(rearPadBaseX[i] + (float) Math.toRadians(
                        Mth.clamp(liftDeg, -6.0D, 6.0D)));
                pad.setRotZ((float) Math.toRadians(
                        Mth.clamp(tiltDeg, -4.0D, 4.0D)));
            }
        }
        for (int i = 0; i < FRONT_CHAINS; i++) {
            GeoBone chain = frontChains[i];
            if (chain == null)
                continue;
            double chainDeg = Math.sin(time * 2.1D + i * 1.3D + wind * 0.35D)
                    * (0.6D + speed * 1.0D + sprint * 0.5D);
            // v1.45.0: se suma un segundo armónico de ROTACIÓN (amplitud
            // 0.2 grados, fase distinta) para que la cadena no collogue
            // con un vaivén regular: tiene el temblor de los eslabones
            // flotando. Sólo se toca RotZ: es rotación pura, no toca
            // la posición del paño ni puede empujarlo al cuerpo.
            chainDeg += 0.2D * Math.sin(time * 3.3D + i * 2.1D);
            // v1.48.0: TERCER armónico de ROTACIÓN (0.12 grados, fase
            // distinta): el vaivén de la cadena lee el temblor fino de
            // los eslabones. Sólo RotZ: rotación pura, sin tocar la
            // posición del paño.
            chainDeg += 0.12D * Math.sin(time * 4.7D + i * 2.9D);
            chain.setRotZ(frontChainBaseZ[i] + (float) Math.toRadians(chainDeg));
        }

        animateDeterioro(time, speed, lift, turn, airborne, sprint, sneak, water, wind, seed);
    }

    /** Si la animación cosmética falla, devolvemos la pose original del geo. */
    private void restoreBasePose() {
        if (panels == null && deterioroBones == null)
            return;
        try {
            restoreDeterioro();
            // v1.14.0: deterioroBones puede estar resuelto antes de que
            // panels exista; sin este guardia panels.length lanzaba NPE
            // justo en el fail-safe (dentro de un catch silencioso).
            if (panels != null && baseX != null && baseY != null && baseZ != null) {
                for (int i = 0; i < panels.length; i++) {
                    GeoBone panel = panels[i];
                    if (panel == null)
                        continue;
                    panel.setRotX(baseX[i]);
                    panel.setRotY(baseY[i]);
                    panel.setRotZ(baseZ[i]);
                }
            }
            if (hems != null && hemBaseZ != null) {
                for (int i = 0; i < hems.length; i++) {
                    if (hems[i] != null)
                        hems[i].setRotZ(hemBaseZ[i]);
                }
            }
            if (orbitShards != null && orbitBaseZ != null) {
                for (int i = 0; i < orbitShards.length; i++) {
                    if (orbitShards[i] != null)
                        orbitShards[i].setRotZ(orbitBaseZ[i]);
                }
            }
            if (pauldrons != null && pauldronBaseZ != null) {
                for (int i = 0; i < pauldrons.length; i++) {
                    if (pauldrons[i] != null)
                        pauldrons[i].setRotZ(pauldronBaseZ[i]);
                }
            }
            if (frontChains != null && frontChainBaseZ != null) {
                for (int i = 0; i < frontChains.length; i++) {
                    if (frontChains[i] != null)
                        frontChains[i].setRotZ(frontChainBaseZ[i]);
                }
            }
            if (rearPads != null && rearPadBaseX != null) {
                for (int i = 0; i < rearPads.length; i++) {
                    if (rearPads[i] != null) {
                        rearPads[i].setRotX(rearPadBaseX[i]);
                        rearPads[i].setRotZ(0.0F);
                    }
                }
            }
        } catch (Exception ignored) {
            // La pose estática del geo sigue siendo válida sin este rescate.
        }
    }

    // ------------------------------------------------------------------
    // v1.14.0 — DETERIORO / EVIL SAIYAN ROSÉ
    // ------------------------------------------------------------------
    /** v1.26.0: EXACTAMENTE los 150 huesos de tela del geo.
     *
     * <p>Antes arrastraba 42 nombres que ya NO existen en el geo (cuatro
     * mechones de más, diez tejas y cuatro piezas de capucha) y le
     * faltaban los diez {@code v18_chain_*} / {@code v18_pad_*}: las
     * hombreras y la cadena NO recibían la respuesta del portador.
     * tools/audit_model.py comprueba que esta lista y el geo digan lo
     * MISMO, para que la lista no vuelva a quedarse vieja.
     *
     * <p>Si cambias el geo, regenera esta lista: el resolvedor nunca
     * inventa nombres y {@code getBone()} falla de forma silenciosa
     * (null) si el modelo no está.
     */
    private static final String[] DETERIORO_NAMES = {
            // 27: 9 columnas x 3 tramos del pano legacy
            "v15_cloth_cape_bottom_0", "v15_cloth_cape_bottom_1", "v15_cloth_cape_bottom_2", "v15_cloth_cape_bottom_3",
            "v15_cloth_cape_bottom_4", "v15_cloth_cape_bottom_5", "v15_cloth_cape_bottom_6", "v15_cloth_cape_bottom_7",
            "v15_cloth_cape_bottom_8", "v15_cloth_cape_mid_0", "v15_cloth_cape_mid_1", "v15_cloth_cape_mid_2",
            "v15_cloth_cape_mid_3", "v15_cloth_cape_mid_4", "v15_cloth_cape_mid_5", "v15_cloth_cape_mid_6",
            "v15_cloth_cape_mid_7", "v15_cloth_cape_mid_8", "v15_cloth_cape_top_0", "v15_cloth_cape_top_1",
            "v15_cloth_cape_top_2", "v15_cloth_cape_top_3", "v15_cloth_cape_top_4", "v15_cloth_cape_top_5",
            "v15_cloth_cape_top_6", "v15_cloth_cape_top_7", "v15_cloth_cape_top_8",
            // 84: 12 mechones x 7 tramos (la superficie articulada)
            "v17_ribbon_0_seg0", "v17_ribbon_0_seg1", "v17_ribbon_0_seg2", "v17_ribbon_0_seg3",
            "v17_ribbon_0_seg4", "v17_ribbon_0_seg5", "v17_ribbon_0_seg6", "v17_ribbon_1_seg0",
            "v17_ribbon_1_seg1", "v17_ribbon_1_seg2", "v17_ribbon_1_seg3", "v17_ribbon_1_seg4",
            "v17_ribbon_1_seg5", "v17_ribbon_1_seg6", "v17_ribbon_2_seg0", "v17_ribbon_2_seg1",
            "v17_ribbon_2_seg2", "v17_ribbon_2_seg3", "v17_ribbon_2_seg4", "v17_ribbon_2_seg5",
            "v17_ribbon_2_seg6", "v17_ribbon_3_seg0", "v17_ribbon_3_seg1", "v17_ribbon_3_seg2",
            "v17_ribbon_3_seg3", "v17_ribbon_3_seg4", "v17_ribbon_3_seg5", "v17_ribbon_3_seg6",
            "v17_ribbon_4_seg0", "v17_ribbon_4_seg1", "v17_ribbon_4_seg2", "v17_ribbon_4_seg3",
            "v17_ribbon_4_seg4", "v17_ribbon_4_seg5", "v17_ribbon_4_seg6", "v17_ribbon_5_seg0",
            "v17_ribbon_5_seg1", "v17_ribbon_5_seg2", "v17_ribbon_5_seg3", "v17_ribbon_5_seg4",
            "v17_ribbon_5_seg5", "v17_ribbon_5_seg6", "v17_ribbon_6_seg0", "v17_ribbon_6_seg1",
            "v17_ribbon_6_seg2", "v17_ribbon_6_seg3", "v17_ribbon_6_seg4", "v17_ribbon_6_seg5",
            "v17_ribbon_6_seg6", "v17_ribbon_7_seg0", "v17_ribbon_7_seg1", "v17_ribbon_7_seg2",
            "v17_ribbon_7_seg3", "v17_ribbon_7_seg4", "v17_ribbon_7_seg5", "v17_ribbon_7_seg6",
            "v17_ribbon_8_seg0", "v17_ribbon_8_seg1", "v17_ribbon_8_seg2", "v17_ribbon_8_seg3",
            "v17_ribbon_8_seg4", "v17_ribbon_8_seg5", "v17_ribbon_8_seg6", "v17_ribbon_9_seg0",
            "v17_ribbon_9_seg1", "v17_ribbon_9_seg2", "v17_ribbon_9_seg3", "v17_ribbon_9_seg4",
            "v17_ribbon_9_seg5", "v17_ribbon_9_seg6", "v17_ribbon_10_seg0", "v17_ribbon_10_seg1",
            "v17_ribbon_10_seg2", "v17_ribbon_10_seg3", "v17_ribbon_10_seg4", "v17_ribbon_10_seg5",
            "v17_ribbon_10_seg6", "v17_ribbon_11_seg0", "v17_ribbon_11_seg1", "v17_ribbon_11_seg2",
            "v17_ribbon_11_seg3", "v17_ribbon_11_seg4", "v17_ribbon_11_seg5", "v17_ribbon_11_seg6",
            // 19: collar (7 front + 7 tooth + 5 back)
            "v17_cowl_back_0", "v17_cowl_back_1", "v17_cowl_back_2", "v17_cowl_back_3",
            "v17_cowl_back_4", "v17_cowl_front_0", "v17_cowl_front_1", "v17_cowl_front_2",
            "v17_cowl_front_3", "v17_cowl_front_4", "v17_cowl_front_5", "v17_cowl_front_6",
            "v17_cowl_tooth_0", "v17_cowl_tooth_1", "v17_cowl_tooth_2", "v17_cowl_tooth_3",
            "v17_cowl_tooth_4", "v17_cowl_tooth_5", "v17_cowl_tooth_6",
            // 10: grietas NEON
            "v17_vein_0", "v17_vein_1", "v17_vein_2", "v17_vein_3",
            "v17_vein_4", "v17_vein_5", "v17_vein_6", "v17_vein_7",
            "v17_vein_8", "v17_vein_9",
            // 10: hombreras y cadena (v1.26.0: antes NO recibían respuesta)
            "v18_chain_0", "v18_chain_1", "v18_chain_2", "v18_chain_3",
            "v18_chain_4", "v18_chain_5", "v18_chain_6", "v18_chain_7",
            "v18_pad_0", "v18_pad_1"
    };

    /** Espejo de `tools/cape_motion.py::parts()`: familia 0=tela,
     *  1=capucha, 2=vena. Sin esto la onda usaba el índice del
     *  array y dos jirones vecinos podían moverse en contrafase. */
    private static int[] motionParts(String name) {
        try {
            int last = name.lastIndexOf('_');
            String tail = last >= 0 ? name.substring(last + 1) : "0";
            int col = 0;
            if (name.startsWith("v17_ribbon_") && tail.startsWith("seg")) {
                String[] parts = name.split("_");
                return new int[]{0, Integer.parseInt(parts[2]),
                        Integer.parseInt(tail.substring(3))};
            }
            if (name.startsWith("v15_cloth_cape_")) {
                col = Integer.parseInt(tail);
                int seg = name.contains("cape_mid_") ? 3
                        : (name.contains("cape_bottom_") ? 6 : 0);
                return new int[]{0, col, seg};
            }
            if (name.startsWith("v15_hem_"))
                return new int[]{0, Integer.parseInt(tail), 6};
            if (name.startsWith("v17_vein_"))
                return new int[]{2, Integer.parseInt(tail), 0};
            if (name.startsWith("v17_cowl_") || name.startsWith("v17_yoke_")
                    || name.startsWith("v18_pad_") || name.startsWith("v18_chain_"))
                return new int[]{1, Integer.parseInt(tail), 0};
            return new int[]{0, Integer.parseInt(tail), 0};
        } catch (RuntimeException ignored) {
            return new int[]{0, 0, 0};
        }
    }

    /** v1.26.0: EJE DE SIMETRÍA POR FAMILIA = (columnas - 1) / 2.
     *
     * <p>Antes TODO usaba {@code (col - 7.5) / 7.5}, un 7.5 heredado
     * de las 16 tiras de la élitra. Con 12 mechones eso iba de -1.0 a
     * +0.47 y con 9 columnas de paño de -1.0 a +0.07: la capa se
     * inclinaba SIEMPRE hacia el mismo lado y el paño izquierdo
     * ondeaba el doble que el derecho. Los ejes se midieron sobre los
     * pivotes X del geo real (simétricos respecto a 0).
     *
     * <p>Espejo exacto de {@code tools/cape_motion.py::axis_of()} y de
     * {@code preview/app.js::motionAxis()}; la CI compara los tres
     * ficheros número a número.
     */
    private static final double RIBBON_AXIS = 5.5D;      // 12 mechones
    private static final double CLOTH_AXIS = 4.0D;        // 9 columnas de pano
    private static final double VEIN_AXIS = 4.5D;         // 10 grietas
    private static final double COWL_AXIS = 3.0D;         // 7 piezas de capucha
    private static final double COWL_BACK_AXIS = 2.0D;    // 5 piezas del cuello
    private static final double CHAIN_AXIS = 3.5D;        // 8 eslabones
    private static final double PAD_AXIS = 0.5D;          // 2 hombreras
    private static final double DEFAULT_AXIS = 5.5D;      // sin anatomia

    private static double motionAxis(String name) {
        if (name.startsWith("v17_ribbon_"))
            return RIBBON_AXIS;
        if (name.startsWith("v15_cloth_cape_") || name.startsWith("v15_hem_"))
            return CLOTH_AXIS;
        if (name.startsWith("v17_vein_"))
            return VEIN_AXIS;
        if (name.startsWith("v18_chain_"))
            return CHAIN_AXIS;
        if (name.startsWith("v18_pad_"))
            return PAD_AXIS;
        if (name.startsWith("v17_cowl_back_"))
            return COWL_BACK_AXIS;
        if (name.startsWith("v17_cowl_") || name.startsWith("v17_yoke_"))
            return COWL_AXIS;
        return DEFAULT_AXIS;
    }

    private void resolveDeterioro() {
        deterioroBones = new GeoBone[DETERIORO_NAMES.length];
        deterioroBase = new float[DETERIORO_NAMES.length][3];
        deterioroParts = new int[DETERIORO_NAMES.length][3];
        for (int i = 0; i < DETERIORO_NAMES.length; i++) {
            deterioroParts[i] = motionParts(DETERIORO_NAMES[i]);
            GeoBone bone = getBone(DETERIORO_NAMES[i]).orElse(null);
            if (bone == null)
                continue;
            deterioroBones[i] = bone;
            BoneSnapshot snap = bone.getInitialSnapshot();
            deterioroBase[i][0] = snap == null ? bone.getRotX() : snap.getRotX();
            deterioroBase[i][1] = snap == null ? bone.getRotY() : snap.getRotY();
            deterioroBase[i][2] = snap == null ? bone.getRotZ() : snap.getRotZ();
        }
    }

    /** v1.21.0: Java YA NO reimplementa la onda.
     *  GeckoLib aplica {@code cape_motion.sample()} (la MISMA curva que
     *  el {@code .bbmodel} y el visor) antes de este callback. Antes este
     *  método calculaba otra onda con fase 0.45 y SOBRESCRIBÍA las
     *  rotaciones: en Minecraft la capa se movía distinto que en
     *  Blockbench, y las dos curvas sumadas daban un temblor. Ahora sólo
     *  se SUMAN offsets de respuesta al portador, leyendo la rotación ya
     *  animada de cada hueso. El retardo {@code -0.62*tramo} se conserva
     *  en el offset para que la respuesta también baje por la tela. */
    private void animateDeterioro(double time, double speed, double lift,
                                  double turn, double airborne, double sprint,
                                  double sneak, double water, double wind,
                                  double seed) {
        if (deterioroBones == null || deterioroParts == null)
            return;
        double gust = Math.sin(time * 0.23D + seed * 0.07D);
        double sweep = Math.sin(time * 0.41D + seed * 0.11D);
        for (int i = 0; i < deterioroBones.length; i++) {
            GeoBone b = deterioroBones[i];
            if (b == null)
                continue;
            int family = deterioroParts[i][0];
            int col = deterioroParts[i][1];
            int seg = deterioroParts[i][2];
            double segF = Math.min(1.0D, seg / 6.0D);
            // v1.26.0: el eje sale de la anatomía de la familia, no de
            // un 7.5 global (ver motionAxis).
            double axis = motionAxis(DETERIORO_NAMES[i]);
            double lateral = (col - axis) / axis;
            // TRAVEL = 0.62 rad/tramo: la onda llega retardada desde
            // GeckoLib; el offset se propaga con el MISMO retardo.
            double lag = 0.62D * seg;
            double response = 0.35D + 0.65D * segF;
            double ripple = Math.sin(time * 1.7D - lag + seed * 0.05D)
                    * 0.50D * response;
            double offX = Mth.clamp(-(sprint * 2.2D + airborne * 1.6D
                    + lift * 0.9D + speed * 0.6D) * response
                    + (sneak + water) * 1.0D * response, -6.0D, 6.0D);
            double offY = Mth.clamp(turn * 2.6D * response * lateral
                    + wind * 0.55D * response + sweep * 0.45D * response,
                    -5.0D, 5.0D);
            double offZ = Mth.clamp((gust * 0.9D + wind * 0.35D) * response
                    * (0.6D + 0.4D * Math.abs(lateral))
                    + ripple + turn * 1.2D * lateral, -5.0D, 5.0D);
            if (family == 1) {          // capuchón: casi rígido
                offX *= 0.35D;
                offY = 0.0D;
                offZ *= 0.45D;
            } else if (family == 2) {  // venas: siguen el estremecimiento
                offZ *= 1.35D;
            }
            b.setRotX(b.getRotX() + (float) Math.toRadians(offX));
            b.setRotY(b.getRotY() + (float) Math.toRadians(offY));
            b.setRotZ(b.getRotZ() + (float) Math.toRadians(offZ));
        }
    }

    private void restoreDeterioro() {
        if (deterioroBones == null)
            return;
        for (int i = 0; i < deterioroBones.length; i++) {
            GeoBone b = deterioroBones[i];
            if (b == null)
                continue;
            b.setRotX(deterioroBase[i][0]);
            b.setRotY(deterioroBase[i][1]);
            b.setRotZ(deterioroBase[i][2]);
        }
    }
}
