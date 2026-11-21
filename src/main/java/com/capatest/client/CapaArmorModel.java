package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
import com.google.gson.JsonParseException;
import net.minecraft.client.player.RemotePlayer;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.model.DefaultedItemGeoModel;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.WeakHashMap;

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
    // Render-thread state shared across chest and Curios. A weak wearer key
    // survives an equipment change but never reuses another entity's clock.
    private static final Map<LivingEntity, CapeWornMotion> MOTION = new WeakHashMap<>();
    private final List<GeoBone> animated = new ArrayList<>();
    private CapeWornClips wornClips;
    private boolean useDefaultSampler;
    private GeoBone clothTop;
    private GeoBone clothMid;
    private double armBack;
    private double legBack;
    private double bodyPitch;
    private double wingGoal;
    private CapeHood.Pose hood = CapeHood.REST;
    private double sprintEdge;
    private boolean disabled;

    CapeHood.Pose hood() { return hood; }
    double sprintEdge() { return sprintEdge; }

    void setClearancePose(double arm, double leg, double pitch, double wingGoal) {
        this.armBack = arm;
        this.legBack = leg;
        this.bodyPitch = pitch;
        this.wingGoal = wingGoal;
    }

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
    public void handleAnimations(CapaDeteriorerItem item, long instanceId, AnimationState<CapaDeteriorerItem> state) {
        // No fit from a previous wearer if this rig or clip is unsupported.
        sprintEdge = 0;
        if (!(state.getData(DataTickets.ENTITY) instanceof LivingEntity wearer) || !resolveRig()) {
            super.handleAnimations(item, instanceId, state);
            return;
        }
        if (wornClips == null && !useDefaultSampler) {
            try {
                wornClips = new CapeWornClips(getAnimationResource(item), animated);
            } catch (IOException | IllegalArgumentException | IllegalStateException | JsonParseException customAsset) {
                useDefaultSampler = true;
                CapaTestMod.LOGGER.warn("Blight Star Mantle: se usa el muestreador de GeckoLib para el recurso equipado", customAsset);
            }
        }
        if (useDefaultSampler) {
            super.handleAnimations(item, instanceId, state);
            return;
        }
        var motion = sampleMotion(wearer, state);
        wornClips.apply(motion);
        applyFit(wearer, motion, true);
    }

    @Override
    public void setCustomAnimations(CapaDeteriorerItem animatable, long instanceId,
                                    AnimationState<CapaDeteriorerItem> state) {
        // Resource packs may supply non-linear or Molang-driven tracks. In
        // that case leave authored motion to GeckoLib rather than flatten it.
        if (resolveRig() && state.getData(DataTickets.ENTITY) instanceof LivingEntity wearer)
            applyFit(wearer, sampleMotion(wearer, state), false);
    }

    static CapeWornMotion wornMotion(LivingEntity wearer) {
        return MOTION.get(wearer);
    }

    private static CapeWornMotion sampleMotion(LivingEntity wearer, AnimationState<CapaDeteriorerItem> state) {
        var motion = MOTION.computeIfAbsent(wearer, key -> new CapeWornMotion());
        var walk = wearer.walkAnimation;
        int limbScale = wearer.isBaby() ? 3 : 1;
        boolean moves = !wearer.isPassenger() && wearer.isAlive();
        boolean swimPose = moves && !wearer.isAutoSpinAttack();
        motion.sample(CapaDeteriorerItem.readClothWearer(wearer, state.getData(DataTickets.ITEMSTACK)),
                wearer.tickCount, state.getPartialTick(), walk.position(0) * limbScale, walk.position(1) * limbScale,
                moves ? walk.speed(0) : 0, moves ? walk.speed(1) : 0,
                swimPose ? wearer.getSwimAmount(0) : 0, swimPose ? wearer.getSwimAmount(1) : 0);
        return motion;
    }

    private void applyFit(LivingEntity wearer, CapeWornMotion motion, boolean coordinated) {
        applyVisibilidad();
        hood = CapeHood.REST;
        if (disabled) return;
        try {
            applyClothResponse(wearer, motion.partial(), motion);
            var response = motion.response;
            if (coordinated) hood = CapeHood.pose(motion.time(), motion.stride(), motion.amplitude() * motion.ground(),
                    response.turnAt(.16), response.sideAt(.12), wearer.getId());
            applyClearance(coordinated ? motion : null);
            // Same continuous blend as the authored sprint, including starts
            // and stops. Do not push the cloth with each immediate arm swing.
            if (coordinated) sprintEdge = motion.weight(CapeState.SPRINT);
        } catch (Exception | LinkageError error) {
            disabled = true;
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
        clothTop = root;
        clothMid = getBone(SECTIONS[1]).orElse(null);
        wornClips = null;
        useDefaultSampler = false;
        disabled = false;
        animated.clear();
        cloth.clear();
        details.clear();
        anchors.clear();
        for (String name : HIDDEN_DETAILS)
            getBone(name).ifPresent(bone -> bone.setHidden(true));
        for (String section : SECTIONS) {
            getBone(section).ifPresent(bone -> {
                animated.add(bone);
                bone.setHidden(false);
                bone.setChildrenHidden(false);
            });
            collectFamily("v15_cloth_" + section + "_", COLUMNS, anchors);
        }
        for (int col=0; col<RIBBONS; col++) {
            for (int seg=0; seg<=LAST_SEGMENT; seg++) {
                GeoBone b = getBone("v17_ribbon_" + col + "_seg" + seg).orElse(null);
                if (b != null) {
                    if (seg > 0) animated.add(b);
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
        for (String name : new String[]{"v20_mount_seat", CapeFit.GUSSET_BONE, "v20_mount_saddle",
                CapeFit.SHOULDERS_BONE, CapeFit.UNDER_YOKE_BONE, CapeBacking.LEFT, CapeBacking.RIGHT})
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

    private void applyClearance(CapeWornMotion motion) {
        double arm = armBack, leg = legBack;
        if (motion != null && wingGoal > 0) {
            arm = CapeStride.walkEnvelope(arm, motion.stride(), motion.limbAmplitude(), motion.ground(), 1);
            leg = CapeStride.walkEnvelope(leg, motion.stride(), motion.limbAmplitude(), motion.ground(), 1.4);
        } else if (motion != null) {
            arm = CapeStride.groundedEnvelope(arm, motion.stride(), motion.amplitude(), motion.limbAmplitude(), motion.strideSupport(), 1);
            leg = CapeStride.groundedEnvelope(leg, motion.stride(), motion.amplitude(), motion.limbAmplitude(), motion.strideSupport(), 1.4);
        }
        double armGoal = CapeStride.armGoal(arm, bodyPitch, 0);
        double legGoal = CapeStride.legGoal(leg, bodyPitch, 0);
        if (clothTop == null || clothMid == null || (armGoal <= 0 && legGoal <= 0 && wingGoal <= 0))
            return;
        // GeckoLib's baked X is the negative of the authored GEO pitch.
        // Take the greater clearance, not the sum. The existing hinge below
        // the collar carries its seam; the seat, fit and atlas stay unchanged.
        double top = -Math.toDegrees(clothTop.getRotX());
        double mid = -Math.toDegrees(clothMid.getRotX());
        double topLift = Math.max(CapeStride.topLift(top, armGoal, legGoal), CapeWingFit.topLift(top, wingGoal));
        double midLift = CapeStride.midLift(top + topLift, mid, legGoal);
        if (topLift > 0)
            clothTop.setRotX(clothTop.getRotX() - (float) Math.toRadians(topLift));
        if (midLift > 0)
            clothMid.setRotX(clothMid.getRotX() - (float) Math.toRadians(midLift));
    }

    private void applyClothResponse(LivingEntity wearer, float partial, CapeWornMotion motion) {
        Vec3 velocity = wearer.getDeltaMovement();
        CapeTravel.Motion travel = CapeTravel.measure(new CapeTravel.Step(velocity.x, velocity.y, velocity.z),
                new CapeTravel.Step(wearer.getX() - wearer.xo, wearer.getY() - wearer.yo, wearer.getZ() - wearer.zo),
                wearer instanceof RemotePlayer, Mth.rotLerp(partial, wearer.yBodyRotO, wearer.yBodyRot));
        double time = motion.time() / 20.0D;
        double turnTarget = travel.cut() ? 0
                : Mth.clamp(Mth.wrapDegrees(wearer.yBodyRot - wearer.yBodyRotO) / 14.0F, -1.0F, 1.0F);
        // Flight and rides have their own body frames. Fade with the actual
        // swim blend; standing in water only damps the response.
        double lateralFreedom = wearer.isFallFlying() || wearer.isPassenger() || wearer.isAutoSpinAttack()
                ? 0 : 1 - Mth.clamp(wearer.getSwimAmount(partial), 0, 1);
        CapeResponse response = motion.response;
        if (travel.cut()) response.reset();
        response.sample(time, travel.speed(), travel.lift(), turnTarget,
                wearer.isCrouching() ? 1 : 0, wearer.isInWater() ? 1 : 0,
                wearer.onGround() ? 0 : 1, wearer.isSprinting() ? 1 : 0,
                lateralFreedom > 0 ? travel.side() : 0);
        double seed = wearer.getId();
        double wind = Math.sin(time * 1.31D + seed * 0.37D) * 0.65D
                + Math.sin(time * 2.73D + seed * 0.11D) * 0.35D;
        double gust = Math.sin(time * 0.23D + seed * 0.07D);
        double sweep = Math.sin(time * 0.41D + seed * 0.11D);
        // Only the cloth below the seam reacts to gait and wind.
        for (Cloth piece : cloth) {
            GeoBone b = piece.bone();
            int seg = piece.segment();
            if (seg == 0)
                continue; // the sewn root only follows its section hinge
            double axis = (RIBBONS - 1) / 2.0D;
            double lateral = (piece.column() - axis) / axis;
            double lag = 0.62D * seg;
            double weight = CapeResponse.weightAt(seg, LAST_SEGMENT);
            double ripple = Math.sin(time * 1.7D - lag + seed * 0.05D) * 0.44D;
            double turn = response.turnAt(weight);
            double side = lateralFreedom * response.sideAt(weight);
            double offY = turn * 1.84D * lateral + wind * 0.38D + sweep * 0.35D;
            double offZ = (gust * 0.68D + wind * 0.24D) * (0.6D + 0.4D * Math.abs(lateral))
                    + ripple + turn * 0.86D * lateral;
            b.setRotX(b.getRotX() + (float) Math.toRadians(response.pitchAt(weight)));
            b.setRotY(b.getRotY() + (float) Math.toRadians(CapeResponse.sideYaw(offY, side, weight)));
            b.setRotZ(b.getRotZ() + (float) Math.toRadians(CapeResponse.sideRoll(offZ, side, weight)));
        }
    }
}
