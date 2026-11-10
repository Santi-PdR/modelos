package com.capatest.item;

import com.capatest.client.CapaArmorRenderer;
import net.minecraft.ChatFormatting;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.core.particles.ParticleTypes;
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
    // idle y moving son las animaciones originales hechas a mano: no se tocan.
    private static final RawAnimation IDLE_ANIM = RawAnimation.begin().thenLoop("animation.idle");
    private static final RawAnimation MOVING_ANIM = RawAnimation.begin().thenLoop("animation.moving");
    // sprint/air se derivan de moving con tools/animation_pipeline.py
    private static final RawAnimation SPRINT_ANIM = RawAnimation.begin().thenLoop("animation.sprint");
    private static final RawAnimation AIR_ANIM = RawAnimation.begin().thenLoop("animation.air");

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
        });
    }

    @Override
    public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
        controllers.add(new AnimationController<>(this, "cape_controller", 4, state -> {
            Entity entity = state.getData(DataTickets.ENTITY);

            // En inventario / GUI no hay entidad; los ArmorStand always idle.
            if (entity == null || entity instanceof ArmorStand) {
                state.setAnimation(IDLE_ANIM);
                return PlayState.CONTINUE;
            }

            // BUG FIX: GeoArmorRenderer construye AnimationState con
            // isMoving()=false y limbSwing=0, así que state.isMoving() no sirve.
            // Además entity.xo/zo es la posición del tick anterior: al renderizar
            // varios frames por tick producía parpadeos entre idle y moving.
            // Usamos la velocidad real, que es estable durante todo el tick.
            Vec3 motion = entity.getDeltaMovement();
            double horizontal = motion.x * motion.x + motion.z * motion.z;
            boolean moving = horizontal > 0.0009D;

            if (!entity.onGround()) {
                state.setAnimation(AIR_ANIM);          // salto / caída / elytra
            } else if (entity.isSprinting() && moving) {
                state.setAnimation(SPRINT_ANIM);       // capa más abierta y rápida
            } else if (moving) {
                state.setAnimation(MOVING_ANIM);
            } else {
                state.setAnimation(IDLE_ANIM);
            }
            return PlayState.CONTINUE;
        }));
    }

    @Override
    public AnimatableInstanceCache getAnimatableInstanceCache() {
        return this.cache;
    }

    /**
     * BUG FIX: sin este override Forge buscaba
     * capatest:textures/models/armor/capa_deteriorer_evilsaiyan_layer_1.png,
     * que no existe (el mod usa el atlas de GeckoLib). Ahora se enlaza la
     * textura correcta y desaparece el recurso perdido.
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
        super.appendHoverText(stack, level, tooltip, flag);
    }

    /**
     * Aura de partículas. Se emite desde el servidor (integrado o dedicado) para
     * que también la vean otros jugadores; en cliente no hacemos nada y así
     * evitamos duplicados y trabajo innecesario.
     */
    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity entity, int slotId, boolean isSelected) {
        if (level.isClientSide || !(entity instanceof Player player)) {
            return;
        }
        if (player.getItemBySlot(EquipmentSlot.CHEST).isEmpty()
                || player.getItemBySlot(EquipmentSlot.CHEST).getItem() != this) {
            return;
        }
        if (player.tickCount % 4 != 0 || !(level instanceof ServerLevel server)) {
            return;
        }

        double yaw = Math.toRadians(player.getYRot());
        double x = player.getX() - Math.sin(yaw) * 0.38;   // detrás del jugador
        double z = player.getZ() + Math.cos(yaw) * 0.38;
        double y = player.getY() + 0.85 + ThreadLocalRandom.current().nextDouble() * 0.9;
        boolean fast = player.isSprinting();

        server.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, x, y, z,
                fast ? 3 : 1, 0.12, 0.18, 0.12, 0.01);
        if (player.tickCount % 8 == 0) {
            server.sendParticles(ParticleTypes.PORTAL, x, y + 0.2, z,
                    fast ? 3 : 2, 0.28, 0.35, 0.28, 0.02);
        }
        if (player.tickCount % 12 == 0) {
            server.sendParticles(ParticleTypes.CRIMSON_SPORE, x, y + 0.4, z,
                    1, 0.25, 0.10, 0.25, 0.005);
        }
    }
}
