package com.capatest.item;

import com.capatest.client.CapaArmorRenderer;
import com.capatest.particle.CapaParticles;
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
        CapePlayback playback = new CapePlayback();
        controllers.add(new AnimationController<>(this, "cape_controller", CapePlayback.FIRST_BLEND, state -> {
            Entity entity = state.getData(DataTickets.ENTITY);
            if (entity == null) {
                playback.reset();
                state.getController().transitionLength(CapePlayback.FIRST_BLEND);
                state.setAnimation(ITEM_ANIM);
            } else {
                CapeState pose = playback.sample(readWearer(entity, state.getData(DataTickets.ITEMSTACK)), entity.tickCount);
                state.getController().transitionLength(playback.blendTicks());
                state.setAnimation(WORN_ANIMATIONS.get(pose));
            }
            return PlayState.CONTINUE;
        }));
    }

    public static CapeState stateFor(Entity entity, ItemStack equipped) {
        return readWearer(entity, equipped).cosmeticState();
    }

    private static CapeState.Wearer readWearer(Entity entity, ItemStack equipped) {
        if (entity == null || entity instanceof ArmorStand) {
            return CapeState.Wearer.STILL;
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
        return new CapeState.Wearer(blight, elytra, entity.isInWater(), !entity.onGround(),
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

    // Do not force foil over the pixel-art star. Real enchantments keep
    // Minecraft's usual glint and all equipment/attribute lines stay intact.
    @Override
    public void appendHoverText(ItemStack stack, Level level, List<Component> tooltip, TooltipFlag flag) {
        super.appendHoverText(stack, level, tooltip, flag);
        tooltip.add(Component.translatable("item.capatest.capa_deteriorer_evilsaiyan.lore")
                .withStyle(style -> style.withColor(0xCA91C0).withItalic(true)));
    }

    @Override
    public void inventoryTick(ItemStack stack, Level level, Entity entity, int slotId, boolean isSelected) {
        if (!level.isClientSide && entity instanceof Player player
                && player.getItemBySlot(EquipmentSlot.CHEST) == stack) {
            spawnAura(level, player, stack);
        }
    }

    public static boolean isAuraTick(int tick) {
        return tick % SPARK_INTERVAL_TICKS == 0;
    }

    /** FX del servidor, una sola emisión como máximo cada 8 ticks (hasta
     *  3 chispas). Los demás clientes ven el mismo impulso, sin geometría
     *  de partículas ni emisores en Blockbench. */
    public static void spawnAura(Level level, Player player, ItemStack equipped) {
        if (!(level instanceof ServerLevel server) || player.isSpectator() || !isAuraTick(player.tickCount)) {
            return;
        }
        int tick = player.tickCount;
        CompoundTag data = player.getPersistentData();
        if (data.contains(AURA_TICK) && data.getInt(AURA_TICK) == tick) {
            return;
        }
        data.putInt(AURA_TICK, tick);

        CapeState mode = stateFor(player, equipped);
        int pulse = tick / SPARK_INTERVAL_TICKS + player.getId();
        boolean quiet = mode == CapeState.SNEAK;
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
        // Deterioro manda sobre el aura, pero una chispa de cuello no
        // debe aparecer pegada a la cara si el portador va en vuelo/agua.
        boolean collarAllowed = player.onGround() && !player.isFallFlying() && !player.isInWater();
        double stature = Math.max(.36D, Math.min(1.0D, player.getBbHeight() / 1.80D));
        for (int i = 0; i < count; i++) {
            CapeState.Spark spark = mode.spark(pulse, i, collarAllowed, random.nextDouble(),
                    random.nextDouble(), random.nextDouble());
            double side = spark.side();
            double height = spark.height() * stature;
            double depth = spark.depth();
            double trail = spark.collar() ? 0.005D : aura.trail() * (0.75D + 0.35D * random.nextDouble());
            double outward = Math.copySign(aura.sideways() * (0.75D + 0.35D * random.nextDouble()), side);
            Vec3 birth = new Vec3(player.getX() + backX * depth + sideX * side,
                    player.getY() + height, player.getZ() + backZ * depth + sideZ * side);
            // Do not spawn inside or across a block. No retry: keeping the
            // position of other sparks and the same per-wearer budget.
            if (!CapeSparkPath.clearBirth(server, player, birth)) {
                continue;
            }
            // count=0 del protocolo de Minecraft: una partícula, impulso
            // exacto = (dx,dy,dz)*speed; count=1 lo volvía ruido gaussiano.
            server.sendParticles(CapaParticles.CAPA_SPARK.get(), birth.x, birth.y, birth.z,
                    0, backX * trail + sideX * outward, aura.lift(),
                    backZ * trail + sideZ * outward, 1.0D);
        }
    }
}
