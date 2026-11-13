package com.capatest.item;

import com.capatest.client.CapaArmorRenderer;
import com.capatest.particle.CapaParticles;
import net.minecraft.ChatFormatting;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.core.particles.DustColorTransitionOptions;
import net.minecraft.core.particles.DustParticleOptions;
import org.joml.Vector3f;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.extensions.common.IClientItemExtensions;
import org.jetbrains.annotations.NotNull;
import software.bernie.geckolib.animatable.GeoItem;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.renderer.GeoArmorRenderer;
import software.bernie.geckolib.util.GeckoLibUtil;

import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.Consumer;

public class CapaDeteriorerItem extends ArmorItem implements GeoItem {
    // v1.22.0: UN CLIP POR ESTADO. Antes `animation.air` era un clon de
    // correr, así que saltar, caer y volar con elytra se movían igual que
    // esprintar en llano. Ahora hay 8 curvas distintas en cape_motion.py.
    private static final RawAnimation IDLE_ANIM = RawAnimation.begin().thenLoop("animation.idle");
    private static final RawAnimation MOVING_ANIM = RawAnimation.begin().thenLoop("animation.moving");
    private static final RawAnimation SPRINT_ANIM = RawAnimation.begin().thenLoop("animation.sprint");
    private static final RawAnimation FLY_ANIM = RawAnimation.begin().thenLoop("animation.air");
    private static final RawAnimation FALL_ANIM = RawAnimation.begin().thenLoop("animation.fall");
    private static final RawAnimation SNEAK_ANIM = RawAnimation.begin().thenLoop("animation.sneak");
    private static final RawAnimation SWIM_ANIM = RawAnimation.begin().thenLoop("animation.swim");
    private static final RawAnimation DETERIORO_ANIM = RawAnimation.begin().thenLoop("animation.deterioro");
    // v1.9.0: animación dedicada del bulto plegado en GUI/hotbar/mano.
    private static final RawAnimation ITEM_ANIM = RawAnimation.begin().thenLoop("animation.item");
    private static final int EMBER_INTERVAL_TICKS = 10;
    private static final int BLIGHT_INTERVAL_TICKS = 20;
    /** v1.22.0: TECHO DURO. Se emite 2 veces por segundo, como mucho 8
     *  partículas por tick de emisión: ~16/s y CERO geometría nueva. */
    private static final int MAX_AURA_PARTICLES_PER_TICK = 8;

    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public CapaDeteriorerItem(ArmorMaterial material, Type type, Properties properties) {
        super(material, type, properties);
    }

    @Override
    public void initializeClient(Consumer<IClientItemExtensions> consumer) {
        consumer.accept(new IClientItemExtensions() {
            private GeoArmorRenderer<?> renderer;

            @Override
            public @NotNull HumanoidModel<?> getHumanoidArmorModel(
                    LivingEntity livingEntity,
                    ItemStack itemStack,
                    EquipmentSlot equipmentSlot,
                    HumanoidModel<?> original
            ) {
                if (this.renderer == null) {
                    this.renderer = new CapaArmorRenderer();
                }

                this.renderer.prepForRender(livingEntity, itemStack, equipmentSlot, original);
                return this.renderer;
            }

            // v1.17.2: NO se registra BEWLR. El renderer 3D plegado
            // (builtin/entity) tapaba el icono 2D y el usuario no llegaba
            // a verlo nunca en el inventario. Ahora el item usa
            // minecraft:item/generated con layer0 = icono 16x16 -> 64x64.
        });
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        // 8 ticks de transición: al pasar de andar a correr o de correr a
        // volar la tela interpola, no pega un salto de pose.
        controllers.add(new AnimationController<>(this, "cape_controller", 8, state -> {
            Entity entity = state.getData(DataTickets.ENTITY);

            // Sin entidad = el ITEM 3D plegado en GUI/hotbar/mano.
            if (entity == null) {
                state.setAnimation(ITEM_ANIM);
                return PlayState.CONTINUE;
            }
            if (entity instanceof ArmorStand) {
                state.setAnimation(IDLE_ANIM);
                return PlayState.CONTINUE;
            }

            Vec3 motion = entity.getDeltaMovement();
            double horizontal = motion.x * motion.x + motion.z * motion.z;
            boolean moving = horizontal > 0.0009D;
            boolean living = entity instanceof LivingEntity;
            boolean flying = living && ((LivingEntity) entity).isFallFlying();
            boolean airborne = !entity.onGround();
            boolean falling = airborne && motion.y < -0.08D && !flying;
            boolean inWater = entity.isInWater();
            boolean crouching = entity.isCrouching();
            boolean sprinting = entity.isSprinting() && moving;
            boolean hurt = living && ((LivingEntity) entity).getHealth()
                    < ((LivingEntity) entity).getMaxHealth() * 0.5F;

            // Prioridad de estado: el que más cambia la silueta gana.
            if (hurt) {
                state.setAnimation(DETERIORO_ANIM);   // estremecimiento
            } else if (flying) {
                state.setAnimation(FLY_ANIM);         // elytra / planeo
            } else if (falling) {
                state.setAnimation(FALL_ANIM);        // caída libre
            } else if (inWater) {
                state.setAnimation(SWIM_ANIM);        // flote amortiguado
            } else if (crouching) {
                state.setAnimation(SNEAK_ANIM);       // capa recogida
            } else if (sprinting) {
                state.setAnimation(SPRINT_ANIM);      // barrida + estela
            } else if (airborne) {
                state.setAnimation(FLY_ANIM);         // salto
            } else if (moving) {
                state.setAnimation(MOVING_ANIM);      // vaivén de paso
            } else {
                state.setAnimation(IDLE_ANIM);        // respiración
            }
            return PlayState.CONTINUE;
        }));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return this.cache;
    }

    /**
     * Sin este override Forge buscaba
     * capatest:textures/models/armor/capa_deteriorer_evilsaiyan_layer_1.png,
     * que no existe (el mod usa el atlas de GeckoLib).
     */
    @Override
    public String getArmorTexture(ItemStack stack, Entity entity, EquipmentSlot slot, String type) {
        return "capatest:textures/item/armor/capa_deteriorer_evilsaiyan.png";
    }

    /** Brillo de encantamiento permanente en inventario / mano. */
    @Override
    public boolean isFoil(ItemStack stack) {
        return true;
    }

    @Override
    public void appendHoverText(ItemStack stack, Level level, List<Component> tooltip, TooltipFlag flag) {
        tooltip.add(Component.translatable("item.capatest.capa_deteriorer_evilsaiyan.lore1")
                .withStyle(ChatFormatting.DARK_PURPLE));
        tooltip.add(Component.translatable("item.capatest.capa_deteriorer_evilsaiyan.lore2")
                .withStyle(ChatFormatting.GRAY));
        tooltip.add(Component.translatable("item.capatest.capa_deteriorer_evilsaiyan.lore3")
                .withStyle(ChatFormatting.DARK_PURPLE, ChatFormatting.ITALIC));
        super.appendHoverText(stack, level, tooltip, flag);
    }

    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity entity, int slotId, boolean isSelected) {
        if (level.isClientSide || !(entity instanceof Player player)) {
            return;
        }
        if (player.getItemBySlot(EquipmentSlot.CHEST).isEmpty()
                || player.getItemBySlot(EquipmentSlot.CHEST).getItem() != this) {
            return;
        }
        // rev. B: NO hay Effects track ni motas 3D. Las partículas se
        // generan AQUI, desde el servidor, sólo mientras la capa está
        // equipada; así las ven también los demás jugadores y el
        // .bbmodel no busca JSONs de partículas que no existen.
        boolean deterioro = stack.isDamaged()
                || player.getHealth() < player.getMaxHealth() * 0.5F;
        spawnAura(level, player, deterioro);
    }

    /** Compatibilidad con la llamada antigua (sin estado de deterioro). */
    public static void spawnAura(Level level, Player player) {
        spawnAura(level, player, false);
    }

    /**
     * Aura emitida desde el servidor para que también la vean otros
     * jugadores. La llaman inventoryTick (slot de pecho) y CuriosCompat
     * (slot back). El sello por tick evita duplicar el efecto.
     *
     * <p>v1.22.0: las motas de 3x3 casi no se veían. Ahora hay un AURA de
     * polvo con ESCALA real (1.8), un HALO de cuello con transición de
     * color (2.2) y una ESTELA al correr/volar/caer, repartidos por las
     * tres alturas del paño. Sigue siendo MUDA y de presupuesto FIJO:
     * {@code MAX_AURA_PARTICLES_PER_TICK = 8}, 2 emisiones por segundo,
     * sin geometría, sin sonidos y sin búsqueda de entidades. Las
     * partículas NO son geometría: se generan al llevar la capa puesta.
     */
    public static void spawnAura(Level level, Player player, boolean deterioro) {
        if (level.isClientSide || !(level instanceof ServerLevel server)) {
            return;
        }
        if (player.tickCount % EMBER_INTERVAL_TICKS != 0) {
            return;
        }

        CompoundTag data = player.getPersistentData();
        int tick = player.tickCount;
        if (data.getInt("capatest:aura_tick") == tick) {
            return;
        }
        data.putInt("capatest:aura_tick", tick);

        double yaw = Math.toRadians(player.getYRot());
        double backX = -Math.sin(yaw), backZ = Math.cos(yaw);
        double sideX = Math.cos(yaw), sideZ = Math.sin(yaw);
        double x = player.getX() + backX * 0.30D;   // detrás del jugador
        double z = player.getZ() + backZ * 0.30D;

        boolean sprint = player.isSprinting();
        boolean flying = player.isFallFlying();
        boolean falling = !player.onGround() && player.getDeltaMovement().y < -0.08D;
        boolean inWater = player.isInWater();
        double drift = inWater ? 0.02D : 0.07D;
        int budget = MAX_AURA_PARTICLES_PER_TICK;

        // v1.22.0: antes las motas eran sprites minúsculos de 3x3 que no
        // se veían. `DustParticleOptions` / `DustColorTransitionOptions`
        // permiten ESCALA REAL en el mundo (1.8 / 2.2): el aura se lee
        // claramente con 1 sola partícula por punto, sin llenar el cielo.
        DustParticleOptions glow = new DustParticleOptions(
                new Vector3f(0.86F, 0.16F, 0.52F), 1.8F);
        DustColorTransitionOptions halo = new DustColorTransitionOptions(
                new Vector3f(0.95F, 0.22F, 0.62F),
                new Vector3f(0.36F, 0.12F, 0.68F), 2.2F);

        // 1) AURA por TODA la capa: tres alturas y ambos lados, como las
        //    motas de la referencia (antes sólo y=0.55..1.15).
        double[] heights = {0.42D, 0.98D, 1.54D};
        for (int i = 0; i < heights.length && budget > 0; i++) {
            double side = (i % 2 == 0 ? -1.0D : 1.0D) * (0.28D + 0.06D * i);
            double hy = heights[i] + 0.05D * Math.sin(tick * 0.17D + i);
            server.sendParticles(glow,
                    x + sideX * side, player.getY() + hy, z + sideZ * side,
                    1, 0.05D, drift, 0.05D, 0.0D);
            budget--;
        }

        // 2) HALO DE CUELLO: dos destellos grandes a la altura de los
        //    hombros. Es el FX que más se nota de lejos.
        if (budget >= 2) {
            for (int side = -1; side <= 1; side += 2) {
                server.sendParticles(halo,
                        x + sideX * (side * 0.34D), player.getY() + 1.42D,
                        z + sideZ * (side * 0.34D),
                        1, 0.03D, 0.04D, 0.03D, 0.0D);
                budget--;
            }
        }

        // 3) BRASAS propias y esquirlas: se reparten por todo el paño.
        int embers = deterioro ? 2 : (sprint || flying || falling ? 2 : 1);
        for (int i = 0; i < embers && budget > 0; i++) {
            double side = (i - (embers - 1) * 0.5D) * 0.30D;
            double height = 0.35D + 1.25D * ThreadLocalRandom.current().nextDouble();
            server.sendParticles(CapaParticles.CAPA_EMBER.get(),
                    x + sideX * side, player.getY() + height, z + sideZ * side,
                    1, 0.09D, 0.12D, 0.09D, 0.001D);
            budget--;
        }

        // 4) ESTELA DE MOVIMIENTO: dos puntos detrás al correr, volar o
        //    caer. Se lee como un rastro, no como confeti.
        if ((sprint || flying || falling) && budget >= 2) {
            for (int i = 0; i < 2; i++) {
                double d = 0.35D + i * 0.30D;
                server.sendParticles(glow,
                        x + backX * d, player.getY() + 0.75D + i * 0.22D,
                        z + backZ * d, 1, 0.04D, 0.05D, 0.04D, 0.0D);
                budget--;
            }
        }

        // 5) MOTAS FRÍAS de Blight Star: órbita mínima, cada 20 ticks.
        if (tick % BLIGHT_INTERVAL_TICKS == 0 && budget > 0) {
            double angle = tick * 0.11D;
            double side = Math.cos(angle) * 0.20D;
            double depth = Math.sin(angle) * 0.07D;
            double ox = x + Math.cos(yaw) * side - Math.sin(yaw) * depth;
            double oz = z + Math.sin(yaw) * side + Math.cos(yaw) * depth;
            double oy = player.getY() + 0.88D
                    + ThreadLocalRandom.current().nextDouble() * 0.44D;
            int motes = deterioro ? 2 : 1;
            server.sendParticles(CapaParticles.CAPA_BLIGHT_MOTE.get(), ox, oy, oz,
                    motes, 0.025, 0.035, 0.025, 0.001);
            budget -= motes;
        }

        // 6) ESQUIRLAS: SOLO en deterioro, dentro del presupuesto.
        if (deterioro && budget > 0) {
            server.sendParticles(CapaParticles.CAPA_SHARD.get(), x,
                    player.getY() + 0.40D, z, 1, 0.10D, 0.16D, 0.10D, 0.002D);
        }
        // Las partículas NO son geometría: el .bbmodel no lleva ni un cubo
        // suelto ni pista `effects`. Todo se genera aquí, en runtime.
    }

}
