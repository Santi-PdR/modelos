package com.capatest.item;

import com.capatest.client.CapaArmorRenderer;
import com.capatest.client.CapaItemRenderer;
import com.capatest.particle.CapaParticles;
import net.minecraft.ChatFormatting;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
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
            private CapaItemRenderer itemRenderer;

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

            /** Modelo 3D real en inventario / mano / suelo (parent builtin/entity). */
            @Override
            public BlockEntityWithoutLevelRenderer getCustomRenderer() {
                if (this.itemRenderer == null) {
                    this.itemRenderer = new CapaItemRenderer();
                }
                return this.itemRenderer;
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

            // GeoArmorRenderer construye AnimationState con isMoving()=false y
            // limbSwing=0, así que usamos la velocidad real (estable por tick).
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
        spawnAura(level, player);
    }

    /**
     * Aura SERENA, emitida desde el servidor para que también la vean otros
     * jugadores. La llaman inventoryTick (slot de pecho) y CuriosCompat (slot
     * back de Curios). El sello por tick evita duplicar el efecto si ambos
     * caminos se ejecutan en el mismo tick con Curios instalado.
     *
     * v1.3.0 elimina PORTAL/CRIMSON_SPORE/SOUL_FIRE_FLAME: eran las motas que
     * llenaban el cielo en las capturas. Ahora queda una sola brasa propia,
     * dos por segundo, pegada a la espalda y con deriva casi nula.
     */
    public static void spawnAura(Level level, Player player) {
        if (level.isClientSide || !(level instanceof ServerLevel server)) {
            return;
        }
        if (player.tickCount % 10 != 0) {
            return;
        }

        CompoundTag data = player.getPersistentData();
        int tick = player.tickCount;
        if (data.getInt("capatest:aura_tick") == tick) {
            return;
        }
        data.putInt("capatest:aura_tick", tick);

        double yaw = Math.toRadians(player.getYRot());
        double x = player.getX() - Math.sin(yaw) * 0.30;   // detrás del jugador
        double z = player.getZ() + Math.cos(yaw) * 0.30;
        double y = player.getY() + 0.55 + ThreadLocalRandom.current().nextDouble() * 0.70;
        int count = player.isSprinting() ? 2 : 1;

        server.sendParticles(CapaParticles.CAPA_EMBER.get(), x, y, z,
                count, 0.07, 0.10, 0.07, 0.001);
    }
}
