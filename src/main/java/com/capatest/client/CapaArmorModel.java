package com.capatest.client;

import com.capatest.item.CapaDeteriorerItem;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.state.BoneSnapshot;
import software.bernie.geckolib.model.DefaultedItemGeoModel;

import java.util.HashMap;
import java.util.Map;

/**
 * Modelo de la capa equipada v1.5.0.
 *
 * El geo aprobado sigue intacto: en runtime ocultamos SÓLO los cubos de los
 * tres huesos cape_top/mid/bottom y dejamos visibles todos sus hijos. Encima
 * aparece una superficie continua de 13×3 paneles v15_cloth_*, todavía
 * parentada a esos huesos, así que idle/moving/sprint/air siguen mandando.
 *
 * Referencias (ideas, no código portado):
 *  - tr7zw/WaveyCapes: una capa debe doblarse como una pieza flexible, con
 *    vaivén lateral y límites para evitar ángulos duros / clipping.
 *  - ismaildzf/finery: simulación de cuerda de 16 puntos, gravedad, inercia
 *    y un estado suavizado por portador.
 *  - ChimeraAnt-DEV/GlowberryClient #102: cadena segmentada, curva de
 *    amplitud creciente de hombros a dobladillo y retardo de fase; el giro del
 *    cuerpo se trata como una señal acotada.
 *  - FabricExtras/ArmorModelAPI: passes base/glow/trim sobre la misma malla.
 *  - Tutoriales de Blockbench/YouTube: una imagen de alta resolución bien
 *    mapeada y capas 3D delgadas se leen mucho mejor que cubos apilados.
 */
public class CapaArmorModel extends DefaultedItemGeoModel<CapaDeteriorerItem> {
    private static final String[] SECTIONS = {"cape_top", "cape_mid", "cape_bottom"};
    // Detalles de "cajas apiladas" del geo aprobado que ensuciaban la nueva
    // superficie continua. Se ocultan en runtime; el JSON sigue intacto.
    private static final String[] HIDDEN_DETAILS = {
            "mano_hombro_R", "mano_hombro_L", "mano_sigilo", "nucleo_sigilo",
            "espina_0", "espina_1", "espina_2",
            "cristal_top_L", "cristal_mid_R", "cristal_mid_L", "cristal_bot_R",
            "flujo_violeta_0", "flujo_violeta_1", "flujo_violeta_2",
            "flujo_violeta_3", "flujo_violeta_4",
            "esquirla_0", "esquirla_1", "esquirla_2", "esquirla_3",
            "esquirla_4", "esquirla_5", "esquirla_6", "esquirla_7"
    };
    private static final int COLUMNS = 13;
    private static final Map<Long, double[]> STATES = new HashMap<>();

    public CapaArmorModel(ResourceLocation assetSubpath) {
        super(assetSubpath);
    }

    @Override
    public void setCustomAnimations(CapaDeteriorerItem animatable, long instanceId,
                                    AnimationState<CapaDeteriorerItem> state) {
        BakedGeoModel baked = getBakedModel(getModelResource(animatable));
        hideOriginalSlabs(baked);

        Entity entity = state.getData(DataTickets.ENTITY);
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

        if (STATES.size() > 128)
            STATES.clear();

        double[] motion = STATES.computeIfAbsent(instanceId, key -> new double[7]);
        motion[0] = Mth.lerp(motion[0], targetSpeed, 0.14D);
        motion[1] = Mth.lerp(motion[1], targetLift, 0.10D);
        motion[2] = Mth.lerp(motion[2], turnTarget, 0.12D);
        motion[3] = Mth.lerp(motion[3], targetSneak, 0.12D);
        motion[4] = Mth.lerp(motion[4], targetWater, 0.06D);
        motion[5] = Mth.lerp(motion[5], targetAir, 0.12D);
        motion[6] = Mth.lerp(motion[6], targetSprint, 0.14D);

        double time = entity == null
                ? state.getAnimationTick() / 20.0D
                : (entity.tickCount + state.getPartialTick()) / 20.0D;
        double seed = entity == null ? instanceId : entity.getId();
        double wind = Math.sin(time * 1.31D + seed * 0.37D) * 0.65D
                + Math.sin(time * 2.73D + seed * 0.11D) * 0.35D;

        double speed = motion[0];
        double lift = motion[1];
        double turn = motion[2];
        double sneak = motion[3];
        double water = motion[4];
        double airborne = motion[5];
        double sprint = motion[6];
        float amplitude = (float) Math.max(0.10D, 0.55D + speed * 3.4D + lift
                + airborne * 1.7D + sprint * 0.8D + sneak * 0.5D + water * 0.6D);

        for (int section = 0; section < SECTIONS.length; section++) {
            double share = 0.30D + 0.35D * section; // hombros -> dobladillo
            for (int column = 0; column < COLUMNS; column++) {
                GeoBone panel = baked.getBone(
                        "v15_cloth_" + SECTIONS[section] + "_" + column).orElse(null);
                if (panel == null)
                    continue;

                double phase = time * (4.4D + speed * 2.2D)
                        - section * 0.55D - column * 0.045D;
                float wave = (float) Math.sin(phase + wind * 0.8D);
                float ripple = (float) Math.sin(time * 2.3D - section * 0.7D
                        + column * 0.62D + wind * 0.5D);
                double lateral = (column - (COLUMNS - 1) / 2.0D) / ((COLUMNS - 1) / 2.0D);

                float bend = Mth.clamp(amplitude * (float) share * (0.55F + 0.45F * wave),
                        0.0F, 12.0F);
                float sway = Mth.clamp((float) ((turn * 3.0D + wind * 0.75D
                        + ripple * 0.65D) * share * (0.25D + speed * 0.75D)), -8.0F, 8.0F);
                float curl = Mth.clamp((float) ((lateral * 2.1D + ripple * 0.85D)
                        * (0.35D + speed * 1.1D)), -6.0F, 6.0F);

                BoneSnapshot initial = panel.getInitialSnapshot();
                float baseX = initial == null ? 0.0F : initial.getRotX();
                float baseY = initial == null ? 0.0F : initial.getRotY();
                float baseZ = initial == null ? 0.0F : initial.getRotZ();
                // Rotación absoluta, no acumulativa: GeckoLib limpia los
                // marcadores de transformación al final de cada frame.
                panel.setRotX(baseX - bend);
                panel.setRotY(baseY + sway * (0.30F + 0.70F * (float) Math.abs(lateral)));
                panel.setRotZ(baseZ + curl);
            }
        }

        // Las puntas del dobladillo tienen su propio temblor, siempre acotado.
        for (int column = 0; column < COLUMNS; column++) {
            GeoBone hem = baked.getBone("v15_hem_" + column).orElse(null);
            if (hem == null)
                continue;
            BoneSnapshot initial = hem.getInitialSnapshot();
            float baseZ = initial == null ? 0.0F : initial.getRotZ();
            float flutter = (float) (Math.sin(time * 5.1D - column * 0.55D + wind * 0.7D)
                    * (0.7D + speed * 2.4D + airborne * 1.2D));
            hem.setRotZ(baseZ + Mth.clamp(flutter, -5.0F, 5.0F));
        }
    }

    /** Limpia la silueta sin editar el geo: oculta losas y detalle boxy. */
    private static void hideOriginalSlabs(BakedGeoModel baked) {
        for (String section : SECTIONS) {
            GeoBone slab = baked.getBone(section).orElse(null);
            if (slab != null) {
                // Sus cubos desaparecen, pero los hijos (incluidos los nuevos
                // paneles v15_*) siguen renderizándose y heredando animación.
                slab.setHidden(true);
                slab.setChildrenHidden(false);
            }
        }
        for (String name : HIDDEN_DETAILS) {
            GeoBone detail = baked.getBone(name).orElse(null);
            if (detail != null)
                detail.setHidden(true); // también oculta dedos/cristalillos hijos
        }
    }
}
