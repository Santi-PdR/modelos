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
    // v1.9.0: animación dedicada del bulto plegado en GUI/hotbar/mano.
    private static final RawAnimation ITEM_ANIM = RawAnimation.begin().thenLoop("animation.item");
    private static final int EMBER_INTERVAL_TICKS = 10;
    private static final int BLIGHT_INTERVAL_TICKS = 20;

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

            // v1.9.0: sin entidad es el ITEM 3D en GUI/hotbar/mano. Usa su
            // propia animación (bob, apertura de pliegues y broche), no el
            // idle de la armadura. Los ArmorStand sí siguen con idle.
            if (entity == null) {
                state.setAnimation(ITEM_ANIM);
                return PlayState.CONTINUE;
            }
            if (entity instanceof ArmorStand) {
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
        // v1220: el Effects track del .bbmodel distingue "rescoldo" en
        // reposo, "brasas" al correr y "deterioro". En Java/GeckoLib los
        // keyframes de particula NO se disparan solos: replicamos ese
        // estado aqui, desde el servidor, para que el efecto exista de
        // verdad en el juego y lo vean tambien los demas jugadores.
        boolean deterioro = stack.isDamaged()
                || player.getHealth() < player.getMaxHealth() * 0.5F;
        spawnAura(level, player, deterioro);
    }

    /** Compatibilidad con la llamada antigua (sin estado de deterioro). */
    public static void spawnAura(Level level, Player player) {
        spawnAura(level, player, false);
    }

    /**
     * Aura SERENA, emitida desde el servidor para que también la vean otros
     * jugadores. La llaman inventoryTick (slot de pecho) y CuriosCompat (slot
     * back de Curios). El sello por tick evita duplicar el efecto si ambos
     * caminos se ejecutan en el mismo tick con Curios instalado.
     *
     * v1.3.0 elimina PORTAL/CRIMSON_SPORE/SOUL_FIRE_FLAME: eran las motas que
     * llenaban el cielo en las capturas. Queda una brasa propia, dos por
     * segundo, pegada a la espalda y con deriva casi nula.
     *
     * v1.9.0 añade MOTAS FRÍAS de Blight Star: una cada dos segundos en idle
     * (dos al correr), en una órbita minúscula alrededor de la espalda. Es un
     * aura MUDA y de presupuesto fijo: no se registran SoundEvent ni se llama
     * a playSound, y el máximo son 7 partículas por tick de emisión.
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
        double x = player.getX() - Math.sin(yaw) * 0.30;   // detrás del jugador
        double z = player.getZ() + Math.cos(yaw) * 0.30;
        double y = player.getY() + 0.55 + ThreadLocalRandom.current().nextDouble() * 0.70;
        boolean sprint = player.isSprinting();
        int count = deterioro ? 3 : (sprint ? 2 : 1);
        double spread = deterioro ? 0.13 : 0.07;

        server.sendParticles(CapaParticles.CAPA_EMBER.get(), x, y, z,
                count, spread, 0.10, spread, deterioro ? 0.004 : 0.001);

        // Estela detrás del jugador al correr o deteriorarse: un punto
        // extra, dentro del presupuesto fijo de 7 particulas por tick.
        if (sprint || deterioro) {
            double sx = x - Math.sin(yaw) * 0.28D;
            double sz = z + Math.cos(yaw) * 0.28D;
            server.sendParticles(CapaParticles.CAPA_EMBER.get(), sx,
                    y + 0.12D, sz, 1, 0.05, 0.06, 0.05, 0.001);
        }

        // v1.9.0: mota cian en órbita lenta. Se emite con la mitad de
        // frecuencia que la brasa y siempre cerca del paño, nunca en el cielo.
        // Esquirlas: SOLO en deterioro. Suben un instante y caen, como
        // fragmentos de tela que se desprenden del dobladillo.
        if (deterioro) {
            server.sendParticles(CapaParticles.CAPA_SHARD.get(), x,
                    y + 0.25D, z, 1, 0.10, 0.16, 0.10, 0.002);
        }

        if (tick % BLIGHT_INTERVAL_TICKS == 0) {
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
        }
    }
}
