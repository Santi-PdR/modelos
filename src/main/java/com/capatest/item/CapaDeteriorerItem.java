package com.capatest.item;

import com.capatest.client.CapaArmorRenderer;
import com.capatest.particle.CapaParticles;
import net.minecraft.ChatFormatting;
import net.minecraft.client.model.HumanoidModel;
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
    /** v1.23.0: chispas SUTILES. Un tick de emisión cada 6 (~3.3/s) y
     *  como mucho 4 chispas en ese tick: 3-13 partículas por segundo,
     *  SIN geometría, SIN sonidos y SIN búsqueda de entidades. */
    private static final int SPARK_INTERVAL_TICKS = 6;
    private static final int MAX_SPARKS_PER_TICK = 4;

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
     * Chispas emitidas desde el servidor para que también las vean otros
     * jugadores. La llaman inventoryTick (slot de pecho) y CuriosCompat
     * (slot back). El sello por tick evita duplicar el efecto.
     *
     * <p>v1.23.0: UNA partícula exclusiva ({@code capa_spark}) con textura
     * propia, en vez de partículas vanilla. Chispas rectangulares,
     * verticales, semitransparentes y con centro brillante; SIN gravedad,
     * suben suavemente y se desvanecen. Nacen dispersas en los BORDES y
     * las PUNTAS INFERIORES de la capa, no detrás de la cabeza. Presupuesto
     * fijo de {@code MAX_SPARKS_PER_TICK = 4}, 1 emisión cada 6 ticks.
     * Las partículas NO son geometría: se generan al llevar la capa puesta.
     */
    public static void spawnAura(Level level, Player player, boolean deterioro) {
        if (level.isClientSide || !(level instanceof ServerLevel server)) {
            return;
        }
        if (player.tickCount % SPARK_INTERVAL_TICKS != 0) {
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

        boolean sprint = player.isSprinting();
        boolean flying = player.isFallFlying();
        boolean falling = !player.onGround() && player.getDeltaMovement().y < -0.08D;
        int count = deterioro ? 3 : ((sprint || flying || falling) ? 2 : 1);
        count = Math.min(count, MAX_SPARKS_PER_TICK);

        // v1.23.0: las chispas nacen en los BORDES y en las PUNTAS
        // INFERIORES del paño (y=0.12..0.95), NUNCA detrás de la cabeza.
        // Antes el aura de polvo vanilla se acumulaba en y=1.4 y tapaba
        // la cabeza del jugador en las capturas.
        for (int i = 0; i < count; i++) {
            boolean tip = i % 2 == 0;
            double rnd = ThreadLocalRandom.current().nextDouble();
            double height = tip
                    ? 0.12D + 0.30D * rnd            // puntas inferiores
                    : 0.42D + 0.53D * rnd;           // bordes del paño
            double side = (i % 2 == 0 ? -1.0D : 1.0D) * (0.34D + 0.12D * rnd);
            double depth = 0.42D + (tip ? 0.24D : 0.06D) + 0.06D * rnd;
            double x = player.getX() + backX * depth + sideX * side;
            double z = player.getZ() + backZ * depth + sideZ * side;
            server.sendParticles(CapaParticles.CAPA_SPARK.get(),
                    x, player.getY() + height, z,
                    1, 0.018D, 0.010D, 0.018D, 0.0D);
        }
        // Las partículas NO son geometría: el .bbmodel no lleva ni un cubo
        // suelto ni pista `effects`. Todo se genera aquí, en runtime.
    }

}
