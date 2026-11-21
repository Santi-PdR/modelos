package com.stainkatana.katana;

import java.util.List;
import java.util.function.Consumer;

import net.minecraft.ChatFormatting;
import net.minecraft.client.renderer.BlockEntityWithoutLevelRenderer;
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
import software.bernie.geckolib.animatable.GeoItem;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.util.GeckoLibUtil;

/** Primer prototipo jugable. La marca y su aplicación son autoritativas en servidor. */
public class StainKatanaItem extends SwordItem implements GeoItem {
    static final String MARK = "StainBloodMark";
    private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);

    public StainKatanaItem() {
        super(Tiers.NETHERITE, 6, -2.0F, new Properties().stacksTo(1));
    }

    // Keep the blade permanent even if a mod attempts to apply durability damage.
    @Override public boolean isDamageable(ItemStack stack) { return false; }
    @Override public int getMaxDamage(ItemStack stack) { return 0; }
    @Override public void setDamage(ItemStack stack, int damage) { super.setDamage(stack, 0); }
    @Override public boolean isEnchantable(ItemStack stack) { return stack.getCount() == 1; }
    @Override public boolean canApplyAtEnchantingTable(ItemStack stack, net.minecraft.world.item.enchantment.Enchantment enchantment) {
        return enchantment.category == net.minecraft.world.item.enchantment.EnchantmentCategory.WEAPON;
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
        if (attacker instanceof net.minecraft.server.level.ServerPlayer player
                && target.level() instanceof ServerLevel level) {
            if (target.isAlive()) markTarget(stack, target, level);
            // Normal katana hits also have visible feedback, not only abilities.
            KatanaNetwork.broadcastVisual(player, target.getX(), target.getY(.55), target.getZ(), KatanaVisualStyle.HIT);
            level.sendParticles(KatanaParticles.SHARD.get(), target.getX(), target.getY(.55), target.getZ(),
                    5, .18, .2, .18, .025);
        }
        return super.hurtEnemy(stack, target, attacker);
    }

    static void markTarget(ItemStack stack, LivingEntity target, ServerLevel level) {
        CompoundTag mark = new CompoundTag();
        mark.putUUID("Target", target.getUUID());
        mark.putString("Dimension", level.dimension().location().toString());
        mark.putLong("Expires", level.getGameTime() + CombatTuning.MARK_TICKS);
        stack.getOrCreateTag().put(MARK, mark);
    }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> lines, TooltipFlag flag) {
        lines.add(Component.translatable("item.stainkatana.katana_stain.lore").withStyle(ChatFormatting.DARK_RED, ChatFormatting.ITALIC));
        lines.add(Component.translatable("item.stainkatana.katana_stain.flavour").withStyle(ChatFormatting.GRAY, ChatFormatting.ITALIC));
    }
}
