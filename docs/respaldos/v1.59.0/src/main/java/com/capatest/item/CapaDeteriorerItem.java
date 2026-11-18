package com.capatest.item;

import com.capatest.client.CapaArmorRenderer;
import com.capatest.particle.CapaParticles;
import net.minecraft.ChatFormatting;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
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
import java.util.EnumMap;
import java.util.Map;
import java.util.function.Consumer;

public class CapaDeteriorerItem extends ArmorItem implements GeoItem {
    private static final RawAnimation ITEM_ANIM = RawAnimation.begin().thenLoop("animation.item");
    private static final Map<CapeState, RawAnimation> WORN_ANIMATIONS = new EnumMap<>(CapeState.class);
    private static final int SPARK_INTERVAL_TICKS = 8;
    private static final int MAX_SPARKS_PER_TICK = 3;
    private static final String AURA_TICK = "capatest:aura_tick";

    static {
        for (CapeState mode : CapeState.values()) {
            WORN_ANIMATIONS.put(mode, RawAnimation.begin().thenLoop(mode.clip()));
        }
    }

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
            state.setAnimation(entity == null ? ITEM_ANIM :
                    WORN_ANIMATIONS.get(stateFor(entity, state.getData(DataTickets.ITEMSTACK))));
            return PlayState.CONTINUE;
        }));
    }

    public static CapeState stateFor(Entity entity, ItemStack equipped) {
        if (entity == null || entity instanceof ArmorStand) {
            return CapeState.IDLE;
        }
        Vec3 velocity = entity.getDeltaMovement();
        // Otros jugadores pueden estar interpolando la posición sin tener
        // su velocidad de locomoción local. Usar también el delta visible.
        double dx = entity.getX() - entity.xo;
        double dz = entity.getZ() - entity.zo;
        double horizontal = Math.max(velocity.horizontalDistanceSqr(), dx * dx + dz * dz);
        double dy = Math.min(velocity.y, entity.getY() - entity.yo);
        boolean elytra = false;
        float health = 1.0F;
        float maxHealth = 1.0F;
        if (entity instanceof LivingEntity living) {
            health = living.getHealth();
            maxHealth = living.getMaxHealth();
            elytra = living.isFallFlying();
        }
        int damage = equipped == null ? 0 : equipped.getDamageValue();
        int maxDamage = equipped == null ? 0 : equipped.getMaxDamage();
        boolean blight = CapeState.deteriorated(health, maxHealth, damage, maxDamage);
        return CapeState.select(blight, elytra, entity.isInWater(), !entity.onGround(),
                entity.isCrouching(), entity.isSprinting(), horizontal, dy);
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
        if (!level.isClientSide && entity instanceof Player player
                && player.getItemBySlot(EquipmentSlot.CHEST) == stack) {
            spawnAura(level, player, stack);
        }
    }

    /** FX del servidor, una sola emisión como máximo cada 8 ticks (hasta
     *  3 chispas). Los demás clientes ven el mismo impulso, sin geometría
     *  de partículas ni emisores en Blockbench. */
    public static void spawnAura(Level level, Player player, ItemStack equipped) {
        if (!(level instanceof ServerLevel server) || player.isSpectator()) {
            return;
        }
        int tick = player.tickCount;
        if (tick % SPARK_INTERVAL_TICKS != 0) {
            return;
        }
        CompoundTag data = player.getPersistentData();
        if (data.contains(AURA_TICK) && data.getInt(AURA_TICK) == tick) {
            return;
        }
        data.putInt(AURA_TICK, tick);

        CapeState mode = stateFor(player, equipped);
        int pulse = tick / SPARK_INTERVAL_TICKS + player.getId();
        boolean quiet = mode == CapeState.IDLE || mode == CapeState.SNEAK;
        if (quiet && (pulse & 1) != 0) {
            return;
        }
        CapeState.Aura aura = mode.aura();
        int count = Math.min(aura.count(), MAX_SPARKS_PER_TICK);
        // Yaw del cuerpo, no de la cámara/cabeza. El +Z del .geo es la
        // espalda; con yaw=0 (mira a +Z del mundo) nace hacia -Z.
        double yaw = Math.toRadians(player.yBodyRot);
        double backX = Math.sin(yaw), backZ = -Math.cos(yaw);
        double sideX = Math.cos(yaw), sideZ = Math.sin(yaw);
        RandomSource random = player.getRandom();
        double firstSide = ((pulse >>> (quiet ? 1 : 0)) & 1) == 0 ? -1.0D : 1.0D;
        for (int i = 0; i < count; i++) {
            boolean tip = i != 1;
            // En deterioro, dos puntas y un borde; nunca detrás de la nuca.
            double sign = i == 0 ? firstSide : -firstSide;
            double side = sign * ((tip ? 0.23D : 0.39D) + random.nextDouble() * 0.12D);
            double height = (tip ? 0.16D : 0.41D) + random.nextDouble() * 0.18D;
            double depth = aura.depth() + (random.nextDouble() - 0.5D) * 0.10D;
            double trail = aura.trail() * (0.75D + 0.35D * random.nextDouble());
            double outward = sign * aura.sideways() * (0.75D + 0.35D * random.nextDouble());
            // count=0 del protocolo de Minecraft: una partícula, impulso
            // exacto = (dx,dy,dz)*speed; count=1 lo volvía ruido gaussiano.
            server.sendParticles(CapaParticles.CAPA_SPARK.get(),
                    player.getX() + backX * depth + sideX * side,
                    player.getY() + height,
                    player.getZ() + backZ * depth + sideZ * side,
                    0, backX * trail + sideX * outward, aura.lift(),
                    backZ * trail + sideZ * outward, 1.0D);
        }
    }
}
