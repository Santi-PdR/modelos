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
 * Modelo de la capa equipada v1.8.0.
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
    private float[] baseX;
    private float[] baseY;
    private float[] baseZ;
    private float[] hemBaseZ;
    private boolean clothReady;
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
                    "Manto de la Estrella Moribunda: animación de tela desactivada (la capa se muestra estática)", error);
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

        cachedRoot = root;
        panels = foundPanels;
        hems = foundHems;
        baseX = foundX;
        baseY = foundY;
        baseZ = foundZ;
        hemBaseZ = foundHemZ;
        clothReady = resolved > 0;
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
    }

    /** Si la animación cosmética falla, devolvemos la pose original del geo. */
    private void restoreBasePose() {
        if (panels == null)
            return;
        try {
            for (int i = 0; i < panels.length; i++) {
                GeoBone panel = panels[i];
                if (panel == null)
                    continue;
                panel.setRotX(baseX[i]);
                panel.setRotY(baseY[i]);
                panel.setRotZ(baseZ[i]);
            }
            if (hems != null) {
                for (int i = 0; i < hems.length; i++) {
                    if (hems[i] != null)
                        hems[i].setRotZ(hemBaseZ[i]);
                }
            }
        } catch (Exception ignored) {
            // La pose estática del geo sigue siendo válida sin este rescate.
        }
    }
}
