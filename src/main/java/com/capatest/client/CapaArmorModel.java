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

    /** Oculta las losas planas y el detalle boxy; se ejecuta una sola vez. */
    private void hideOriginalSlabs() {
        for (String section : SECTIONS) {
            GeoBone slab = getBone(section).orElse(null);
            if (slab != null) {
                // setHidden(true) pone childrenHidden=true; lo revertimos para
                // que los paneles v15_* (hijos) sigan renderizándose. En
                // GeckoLib 4.8.1 setChildrenHidden NO propaga a los hijos.
                slab.setHidden(true);
                slab.setChildrenHidden(false);
            }
        }
        for (String name : HIDDEN_DETAILS) {
            GeoBone detail = getBone(name).orElse(null);
            if (detail != null)
                detail.setHidden(true);   // oculta también a sus descendientes
        }
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
            chain.setRotZ(frontChainBaseZ[i] + (float) Math.toRadians(chainDeg));
        }

        animateDeterioro(time, speed, lift, turn, airborne, sprint, wind, seed, amplitude);
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
    /** Nombres generados por tools/armor_model_pipeline.py. Si cambias el
     *  geo, regenera esta lista; el resolvedor nunca inventa nombres y
     *  getBone() falla de forma silenciosa (null) si el modelo no está. */
    private static final String[] DETERIORO_NAMES = {
            "v15_cloth_cape_top_0", "v15_cloth_cape_top_1", "v15_cloth_cape_top_2", "v15_cloth_cape_top_3",
            "v15_cloth_cape_top_4", "v15_cloth_cape_top_5", "v15_cloth_cape_top_6", "v15_cloth_cape_top_7",
            "v15_cloth_cape_top_8", "v15_cloth_cape_mid_0", "v15_cloth_cape_mid_1", "v15_cloth_cape_mid_2",
            "v15_cloth_cape_mid_3", "v15_cloth_cape_mid_4", "v15_cloth_cape_mid_5", "v15_cloth_cape_mid_6",
            "v15_cloth_cape_mid_7", "v15_cloth_cape_mid_8", "v15_cloth_cape_bottom_0", "v15_cloth_cape_bottom_1",
            "v15_cloth_cape_bottom_2", "v15_cloth_cape_bottom_3", "v15_cloth_cape_bottom_4", "v15_cloth_cape_bottom_5",
            "v15_cloth_cape_bottom_6", "v15_cloth_cape_bottom_7", "v15_cloth_cape_bottom_8", "v17_cowl_front_0",
            "v17_cowl_tooth_0", "v17_cowl_front_1", "v17_cowl_tooth_1", "v17_cowl_front_2",
            "v17_cowl_tooth_2", "v17_cowl_front_3", "v17_cowl_tooth_3", "v17_cowl_front_4",
            "v17_cowl_tooth_4", "v17_cowl_front_5", "v17_cowl_tooth_5", "v17_cowl_front_6",
            "v17_cowl_tooth_6", "v17_cowl_front_7", "v17_cowl_tooth_7", "v17_cowl_front_8",
            "v17_cowl_tooth_8", "v17_cowl_back_0", "v17_cowl_back_1", "v17_cowl_back_2",
            "v17_cowl_back_3", "v17_cowl_back_4", "v17_yoke_0", "v17_yoke_1",
            "v17_yoke_2", "v17_yoke_3", "v17_yoke_4", "v17_yoke_5",
            "v17_ribbon_0_seg0", "v17_ribbon_0_seg1", "v17_ribbon_0_seg2", "v17_ribbon_0_seg3",
            "v17_ribbon_0_seg4", "v17_ribbon_0_seg5", "v17_ribbon_1_seg0", "v17_ribbon_1_seg1",
            "v17_ribbon_1_seg2", "v17_ribbon_1_seg3", "v17_ribbon_1_seg4", "v17_ribbon_1_seg5",
            "v17_ribbon_2_seg0", "v17_ribbon_2_seg1", "v17_ribbon_2_seg2", "v17_ribbon_2_seg3",
            "v17_ribbon_2_seg4", "v17_ribbon_2_seg5", "v17_ribbon_3_seg0", "v17_ribbon_3_seg1",
            "v17_ribbon_3_seg2", "v17_ribbon_3_seg3", "v17_ribbon_3_seg4", "v17_ribbon_3_seg5",
            "v17_ribbon_4_seg0", "v17_ribbon_4_seg1", "v17_ribbon_4_seg2", "v17_ribbon_4_seg3",
            "v17_ribbon_4_seg4", "v17_ribbon_4_seg5", "v17_ribbon_5_seg0", "v17_ribbon_5_seg1",
            "v17_ribbon_5_seg2", "v17_ribbon_5_seg3", "v17_ribbon_5_seg4", "v17_ribbon_5_seg5",
            "v17_ribbon_6_seg0", "v17_ribbon_6_seg1", "v17_ribbon_6_seg2", "v17_ribbon_6_seg3",
            "v17_ribbon_6_seg4", "v17_ribbon_6_seg5", "v17_ribbon_7_seg0", "v17_ribbon_7_seg1",
            "v17_ribbon_7_seg2", "v17_ribbon_7_seg3", "v17_ribbon_7_seg4", "v17_ribbon_7_seg5",
            "v17_ribbon_8_seg0", "v17_ribbon_8_seg1", "v17_ribbon_8_seg2", "v17_ribbon_8_seg3",
            "v17_ribbon_8_seg4", "v17_ribbon_8_seg5", "v17_ribbon_9_seg0", "v17_ribbon_9_seg1",
            "v17_ribbon_9_seg2", "v17_ribbon_9_seg3", "v17_ribbon_9_seg4", "v17_ribbon_9_seg5",
            "v17_ribbon_10_seg0", "v17_ribbon_10_seg1", "v17_ribbon_10_seg2", "v17_ribbon_10_seg3",
            "v17_ribbon_10_seg4", "v17_ribbon_10_seg5", "v17_ribbon_11_seg0", "v17_ribbon_11_seg1",
            "v17_ribbon_11_seg2", "v17_ribbon_11_seg3", "v17_ribbon_11_seg4", "v17_ribbon_11_seg5",
            "v17_ribbon_12_seg0", "v17_ribbon_12_seg1", "v17_ribbon_12_seg2", "v17_ribbon_12_seg3",
            "v17_ribbon_12_seg4", "v17_ribbon_12_seg5", "v17_ribbon_13_seg0", "v17_ribbon_13_seg1",
            "v17_ribbon_13_seg2", "v17_ribbon_13_seg3", "v17_ribbon_13_seg4", "v17_ribbon_13_seg5",
            "v17_ribbon_14_seg0", "v17_ribbon_14_seg1", "v17_ribbon_14_seg2", "v17_ribbon_14_seg3",
            "v17_ribbon_14_seg4", "v17_ribbon_14_seg5", "v17_ribbon_15_seg0", "v17_ribbon_15_seg1",
            "v17_ribbon_15_seg2", "v17_ribbon_15_seg3", "v17_ribbon_15_seg4", "v17_ribbon_15_seg5",
            "v17_ribbon_0_seg6", "v17_ribbon_1_seg6", "v17_ribbon_2_seg6", "v17_ribbon_3_seg6",
            "v17_ribbon_4_seg6", "v17_ribbon_5_seg6", "v17_ribbon_6_seg6", "v17_ribbon_7_seg6",
            "v17_ribbon_8_seg6", "v17_ribbon_9_seg6", "v17_ribbon_10_seg6", "v17_ribbon_11_seg6",
            "v17_ribbon_12_seg6", "v17_ribbon_13_seg6", "v17_ribbon_14_seg6", "v17_ribbon_15_seg6",
            "v17_shingle_0", "v17_shingle_1", "v17_shingle_2", "v17_shingle_3",
            "v17_shingle_4", "v17_shingle_5", "v17_shingle_6", "v17_shingle_7",
            "v17_shingle_8", "v17_shingle_9", "v17_mote_0", "v17_mote_1",
            "v17_mote_2", "v17_mote_3", "v17_mote_4", "v17_mote_5",
            "v17_mote_6", "v17_mote_7", "v17_mote_8", "v17_mote_9",
            "v17_mote_10", "v17_mote_11", "v17_mote_12", "v17_mote_13",
            "v17_mote_14", "v17_mote_15", "v17_mote_16", "v17_mote_17",
            "v17_mote_18", "v17_mote_19", "v17_mote_20", "v17_mote_21",
            "v17_mote_22", "v17_mote_23", "v17_mote_24", "v17_mote_25",
            "v17_vein_0", "v17_vein_1", "v17_vein_2", "v17_vein_3",
            "v17_vein_4", "v17_vein_5", "v17_vein_6", "v17_vein_7",
            "v17_vein_8", "v17_vein_9", "v17_ash_0", "v17_ash_1",
            "v17_ash_2", "v17_ash_3", "v17_ash_4", "v17_ash_5",
            "v17_ash_6", "v17_ash_7"
    };

    private void resolveDeterioro() {
        deterioroBones = new GeoBone[DETERIORO_NAMES.length];
        deterioroBase = new float[DETERIORO_NAMES.length][3];
        for (int i = 0; i < DETERIORO_NAMES.length; i++) {
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

    /** Flujo dinámico de la tela destrozada + deriva de las partículas.
     *  Todo en GRADOS convertido con Math.toRadians. Los microvóxeles
     *  tienen el pivote desplazado 0.6, así que al girar el hueso la
     *  partícula se DESPLAZA de verdad, sin mixins ni partículas externas. */
    private void animateDeterioro(double time, double speed, double lift,
                                  double turn, double airborne, double sprint,
                                  double wind, double seed, double amplitude) {
        if (deterioroBones == null)
            return;
        for (int i = 0; i < deterioroBones.length; i++) {
            GeoBone b = deterioroBones[i];
            if (b == null)
                continue;
            String n = DETERIORO_NAMES[i];
            double phase = time * 2.4D + i * 0.37D + wind * 0.6D;
            if (n.startsWith("v17_mote_") || n.startsWith("v17_ash_")) {
                double fall = Math.sin(phase * 1.7D + seed * 0.03D);
                double drift = Math.cos(phase * 0.9D + i);
                double amp = 7.0D + speed * 9.0D + airborne * 5.0D + sprint * 4.0D;
                b.setRotX(deterioroBase[i][0] + (float) Math.toRadians(
                        Mth.clamp(fall * amp, -18.0D, 18.0D)));
                b.setRotY(deterioroBase[i][1] + (float) Math.toRadians(
                        Mth.clamp(drift * amp * 0.70D, -14.0D, 14.0D)));
                b.setRotZ(deterioroBase[i][2] + (float) Math.toRadians(
                        Mth.clamp(Math.sin(phase) * amp * 0.50D, -12.0D, 12.0D)));
            } else if (n.startsWith("v17_cowl_tooth_")) {
                double flutter = Math.sin(phase * 2.7D + i * 0.8D)
                        * (1.8D + sprint * 1.6D);
                b.setRotX(deterioroBase[i][0] + (float) Math.toRadians(
                        Mth.clamp(flutter, -5.0D, 5.0D)));
                b.setRotZ(deterioroBase[i][2] + (float) Math.toRadians(
                        Mth.clamp(flutter * 0.75D, -4.0D, 4.0D)));
            } else if (n.startsWith("v17_cowl_") || n.startsWith("v17_yoke_")) {
                double breathe = Math.sin(phase * 0.8D) * (1.2D + sprint * 1.0D);
                b.setRotX(deterioroBase[i][0] + (float) Math.toRadians(
                        Mth.clamp(breathe + lift * 2.0D, -4.0D, 4.0D)));
                b.setRotZ(deterioroBase[i][2] + (float) Math.toRadians(
                        Mth.clamp(turn * 1.2D, -3.0D, 3.0D)));
            } else if (n.startsWith("v17_shingle_")) {
                double ripple = Math.sin(phase * 1.3D + i) * (1.6D + sprint * 2.0D);
                b.setRotX(deterioroBase[i][0] + (float) Math.toRadians(
                        Mth.clamp(ripple, -6.0D, 6.0D)));
                b.setRotZ(deterioroBase[i][2] + (float) Math.toRadians(
                        Mth.clamp(ripple * 0.55D, -4.0D, 4.0D)));
            } else if (n.startsWith("v17_vein_")) {
                double pulse = Math.sin(phase * 3.1D) * (1.1D + sprint * 1.4D)
                        + Math.sin(phase * 6.7D + i) * 0.5D;
                b.setRotZ(deterioroBase[i][2] + (float) Math.toRadians(
                        Mth.clamp(pulse * 2.4D, -7.0D, 7.0D)));
                b.setRotX(deterioroBase[i][0] + (float) Math.toRadians(
                        Mth.clamp(pulse * 0.7D, -3.0D, 3.0D)));
            } else if (n.startsWith("v17_ribbon_")) {
                int under = n.lastIndexOf('_');
                int segN = 0;
                if (under > 3 && n.substring(under + 1).startsWith("seg")) {
                    try {
                        segN = Integer.parseInt(n.substring(under + 4));
                    } catch (NumberFormatException ignored) {
                        segN = 0;
                    }
                }
                double seg = segN / 6.0D;
                double ph = phase - seg * 1.8D;
                double bend = amplitude * (0.30D + 0.70D * seg)
                        * (0.45D + 0.55D * Math.sin(ph));
                double sway = (turn * 2.2D + wind * 0.8D
                        + Math.sin(phase * 0.7D + i) * 1.1D)
                        * (0.30D + speed * 0.70D);
                double curl = Math.sin(phase * 0.6D + i)
                        * (1.2D + 2.6D * seg) + turn * 1.5D;
                // v1214: rafaga LENTA superpuesta, periodo ~10x el ondeo.
                // Da la sensacion de tela pesada que no vuelve a la misma
                // pose en cada ciclo, sin tocar los limites de seguridad.
                double gust = Math.sin(phase * 0.23D + i * 0.07D) * 1.3D;
                b.setRotX(deterioroBase[i][0] + (float) Math.toRadians(
                        Mth.clamp(bend, -14.0D, 14.0D)));
                b.setRotY(deterioroBase[i][1] + (float) Math.toRadians(
                        Mth.clamp(sway + gust * 0.5D, -9.0D, 9.0D)));
                b.setRotZ(deterioroBase[i][2] + (float) Math.toRadians(
                        Mth.clamp(curl + gust, -8.0D, 8.0D)));
            } else {
                double seg = (i % 6) / 6.0D;
                double wave = Math.sin(phase - seg * 1.8D);
                double bend = amplitude * (0.35D + 0.65D * seg) * (0.40D + 0.60D * wave);
                double sway = (turn * 2.2D + wind * 0.8D
                        + Math.sin(phase * 0.7D + i) * 1.1D) * (0.30D + speed * 0.70D);
                double curl = Math.sin(phase * 0.6D + i) * 3.0D + turn * 1.5D;
                b.setRotX(deterioroBase[i][0] + (float) Math.toRadians(
                        Mth.clamp(bend, -14.0D, 14.0D)));
                b.setRotY(deterioroBase[i][1] + (float) Math.toRadians(
                        Mth.clamp(sway, -9.0D, 9.0D)));
                b.setRotZ(deterioroBase[i][2] + (float) Math.toRadians(
                        Mth.clamp(curl, -8.0D, 8.0D)));
            }
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
