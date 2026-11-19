package com.stainkatana.katana;

import java.util.List;
import java.util.function.Consumer;

import net.minecraft.ChatFormatting;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.SwordItem;
import net.minecraft.world.item.Tiers;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraftforge.client.extensions.common.IClientItemExtensions;
import org.jetbrains.annotations.Nullable;
import org.joml.Vector3f;
import software.bernie.geckolib.animatable.GeoItem;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.util.GeckoLibUtil;

/** Primer prototipo jugable. La marca y su aplicación son autoritativas en servidor. */
public class StainKatanaItem extends SwordItem implements GeoItem {
    static final String MARK = "StainBloodMark";
    private static final int MARK_TICKS = 200;
    private static final DustParticleOptions BLOOD = new DustParticleOptions(new Vector3f(0.55F, 0.025F, 0.035F), 0.8F);
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public StainKatanaItem() {
        super(Tiers.IRON, 3, -2.4F, new Properties().stacksTo(1));
    }

    @Override
    public void initializeClient(Consumer<IClientItemExtensions> consumer) {
        consumer.accept(new IClientItemExtensions() {
            private KatanaRenderer renderer;
            @Override public BlockEntityWithoutLevelRenderer getCustomRenderer() {
                if (renderer == null) renderer = new KatanaRenderer();
                return renderer;
            }
        });
    }

    @Override public void registerControllers(AnimatableManager.ControllerRegistrar controllers) { }
    @Override public AnimatableInstanceCache getAnimatableInstanceCache() { return cache; }

    @Override
    public boolean hurtEnemy(ItemStack stack, LivingEntity target, LivingEntity attacker) {
        if (attacker instanceof Player && target.isAlive() && target.level() instanceof ServerLevel level) {
            CompoundTag mark = new CompoundTag();
            mark.putUUID("Target", target.getUUID());
            mark.putString("Dimension", level.dimension().location().toString());
            mark.putLong("Expires", level.getGameTime() + MARK_TICKS);
            stack.getOrCreateTag().put(MARK, mark);
            level.sendParticles(BLOOD, target.getX(), target.getY(0.55), target.getZ(), 8, 0.22, 0.25, 0.22, 0.015);
        }
        return super.hurtEnemy(stack, target, attacker);
    }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> lines, TooltipFlag flag) {
        lines.add(Component.translatable("item.stainkatana.katana_stain.lore").withStyle(ChatFormatting.DARK_RED));
        lines.add(Component.translatable("item.stainkatana.katana_stain.hint").withStyle(ChatFormatting.GRAY));
    }
}
