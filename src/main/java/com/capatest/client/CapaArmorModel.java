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
import software.bernie.geckolib.model.DefaultedItemGeoModel;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Eight authored clips plus a bounded, rotational response on visible cloth. */
public class CapaArmorModel extends DefaultedItemGeoModel<CapaDeteriorerItem> {
    private static final String[] SECTIONS = {"cape_top", "cape_mid", "cape_bottom"};
    private static final int COLUMNS = 9;    // diagnostic anchors per section
    private static final int RIBBONS = 12;
    private static final int LAST_SEGMENT = 4; // the next two cubes share this pivot

    // Conceal legacy geometry but keep the original bones and track identifiers.
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

    public enum Visibilidad { NORMAL, ANCLAS, HOMBRERAS, CADENA }

    private static Visibilidad visibilidad = initialVisibility();
    private Visibilidad visibilidadAplicada;
    private GeoBone cachedRoot;
    private final List<GeoBone> anchors = new ArrayList<>(27);
    private final List<GeoBone> details = new ArrayList<>();
    private final List<Cloth> cloth = new ArrayList<>(RIBBONS * (LAST_SEGMENT + 1));
    // This is render-thread state. Evict only the least recently used wearer.
    private final Map<Long, CapeResponse> motion = new LinkedHashMap<>(32, .75F, true);
    private boolean disabled;

    private record Cloth(GeoBone bone, int column, int segment) {}

    public CapaArmorModel(ResourceLocation assetSubpath) {
        super(assetSubpath);
    }

    private static Visibilidad initialVisibility() {
        try {
            return Visibilidad.valueOf(System.getProperty("capa.visibilidad", "normal").toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ignored) {
            return Visibilidad.NORMAL;
        }
    }

    public static Visibilidad getVisibilidad() {
        return visibilidad;
    }

    public static void setVisibilidad(Visibilidad modo) {
        if (modo != null)
            visibilidad = modo;
    }

    @Override
    public void setCustomAnimations(CapaDeteriorerItem animatable, long instanceId,
                                    AnimationState<CapaDeteriorerItem> state) {
        if (!resolveRig())
            return;
        applyVisibilidad();
        if (disabled)
            return;
        try {
            applyClothResponse(instanceId, state);
        } catch (Exception | LinkageError error) {
            disabled = true;
            motion.clear();
            CapaTestMod.LOGGER.error("Blight Star Mantle: respuesta del paño desactivada; se conservan los clips", error);
        }
    }

    /** Resolve against the active baked model; a resource reload changes its identity. */
    private boolean resolveRig() {
        GeoBone root = getBone(SECTIONS[0]).orElse(null);
        if (root == null)
            return false;
        if (root == cachedRoot)
            return true;
        cachedRoot = root;
        motion.clear();
        cloth.clear();
        details.clear();
        anchors.clear();
        for (String name : HIDDEN_DETAILS)
            getBone(name).ifPresent(bone -> bone.setHidden(true));
        for (String section : SECTIONS) {
            getBone(section).ifPresent(bone -> {
                bone.setHidden(false);
                bone.setChildrenHidden(false);
            });
            collectFamily("v15_cloth_" + section + "_", COLUMNS, anchors);
        }
        for (int col=0; col<RIBBONS; col++) {
            for (int seg=0; seg<=LAST_SEGMENT; seg++) {
                GeoBone b = getBone("v17_ribbon_" + col + "_seg" + seg).orElse(null);
                if (b != null) {
                    cloth.add(new Cloth(b, col, seg));
                    details.add(b);
                }
            }
        }
        collectFamily("v17_cowl_front_", 7, details);
        collectFamily("v17_cowl_tooth_", 7, details);
        collectFamily("v17_cowl_back_", 5, details);
        getBone("v17_cowl_return").ifPresent(details::add);
        collectFamily("v19_cuellito_", 3, details);
        collectFamily("v17_vein_", 10, details);
        collectFamily("v18_pad_", 2, details);
        collectFamily("v18_chain_", 8, details);
        for (String name : new String[]{"v20_mount_seat", CapeFit.GUSSET_BONE, "v20_mount_saddle"})
            getBone(name).ifPresent(details::add);
        visibilidadAplicada = null;
        return true;
    }

    private void collectFamily(String prefix, int size, List<GeoBone> into) {
        for (int i=0; i<size; i++)
            getBone(prefix + i).ifPresent(into::add);
    }

    private void hideClothAnchors(boolean visible) {
        for (GeoBone anchor : anchors)
            anchor.setHidden(!visible);
    }

    private void applyVisibilidad() {
        if (visibilidadAplicada == visibilidad)
            return;
        hideClothAnchors(visibilidad == Visibilidad.ANCLAS);
        for (GeoBone b : details) {
            boolean visible = switch (visibilidad) {
                case NORMAL -> true;
                case ANCLAS -> false;
                case HOMBRERAS -> b.getName().startsWith("v18_pad_");
                case CADENA -> b.getName().startsWith("v18_chain_");
            };
            b.setHidden(!visible);
            b.setChildrenHidden(!visible);
        }
        visibilidadAplicada = visibilidad;
    }

    private void applyClothResponse(long instanceId, AnimationState<CapaDeteriorerItem> state) {
        if (!(state.getData(DataTickets.ENTITY) instanceof LivingEntity wearer))
            return;
        Vec3 velocity = wearer.getDeltaMovement();
        double time = (wearer.tickCount + (double) state.getPartialTick()) / 20.0D;
        double turnTarget = Mth.clamp(Mth.wrapDegrees(wearer.yBodyRot - wearer.yBodyRotO) / 14.0F, -1.0F, 1.0F);
        CapeResponse response = motion.computeIfAbsent(instanceId, key -> new CapeResponse());
        if (motion.size() > 128)
            motion.remove(motion.keySet().iterator().next());
        double[] m = response.sample(time,
                Mth.clamp(velocity.horizontalDistance() * 2.2D, 0.0D, 1.0D),
                Mth.clamp(-velocity.y * 1.3D, -0.45D, 1.0D), turnTarget,
                wearer.isCrouching() ? 1 : 0, wearer.isInWater() ? 1 : 0,
                wearer.onGround() ? 0 : 1, wearer.isSprinting() ? 1 : 0);
        double seed = wearer.getId();
        double wind = Math.sin(time * 1.31D + seed * 0.37D) * 0.65D
                + Math.sin(time * 2.73D + seed * 0.11D) * 0.35D;
        double gust = Math.sin(time * 0.23D + seed * 0.07D);
        double sweep = Math.sin(time * 0.41D + seed * 0.11D);
        double offX = Mth.clamp(-(m[6] * 1.3D + m[5] * 0.9D + m[1] * 0.65D + m[0] * 0.62D)
                + (m[3] + m[4]) * 0.72D, -CapeResponse.MAX_BACK, CapeResponse.MAX_IN);
        // Only the cloth below the seam reacts to gait and wind.
        for (Cloth piece : cloth) {
            GeoBone b = piece.bone();
            int seg = piece.segment();
            if (seg == 0)
                continue; // the sewn root only follows its section hinge
            double axis = (RIBBONS - 1) / 2.0D;
            double lateral = (piece.column() - axis) / axis;
            double lag = 0.62D * seg;
            double weight = Math.pow(seg / (double) LAST_SEGMENT, 1.45D);
            double ripple = Math.sin(time * 1.7D - lag + seed * 0.05D) * 0.44D;
            double turn = response.turnAt(weight);
            double offY = Mth.clamp(turn * 1.84D * lateral + wind * 0.38D + sweep * 0.35D,
                    -CapeResponse.MAX_YAW, CapeResponse.MAX_YAW);
            double offZ = Mth.clamp((gust * 0.68D + wind * 0.24D) * (0.6D + 0.4D * Math.abs(lateral))
                    + ripple + turn * 0.86D * lateral, -CapeResponse.MAX_ROLL, CapeResponse.MAX_ROLL);
            b.setRotX(b.getRotX() + (float) Math.toRadians(offX * weight));
            b.setRotY(b.getRotY() + (float) Math.toRadians(offY * weight));
            b.setRotZ(b.getRotZ() + (float) Math.toRadians(offZ * weight));
        }
    }
}
