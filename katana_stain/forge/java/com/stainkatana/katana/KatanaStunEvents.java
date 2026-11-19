package com.stainkatana.katana;

import com.stainkatana.StainKatanaMod;
import net.minecraft.world.entity.LivingEntity;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.event.entity.player.AttackEntityEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** El stun no pausa el mundo: bloquea ataques/interacciones y el salto en servidor. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class KatanaStunEvents {
    private KatanaStunEvents() { }
    @SubscribeEvent public static void jump(LivingEvent.LivingJumpEvent event) {
        LivingEntity entity = event.getEntity();
        if (!entity.level().isClientSide && entity.hasEffect(KatanaEffects.PARALYSIS.get())) {
            var v = entity.getDeltaMovement();
            entity.setDeltaMovement(v.x, Math.min(0, v.y), v.z);
            entity.hurtMarked = true;
        }
    }
    @SubscribeEvent public static void attack(AttackEntityEvent event) {
        if (!event.getEntity().level().isClientSide && event.getEntity().hasEffect(KatanaEffects.PARALYSIS.get())) event.setCanceled(true);
    }
    @SubscribeEvent public static void damage(LivingAttackEvent event) {
        if (!event.getEntity().level().isClientSide && event.getSource().getEntity() instanceof LivingEntity attacker
                && attacker.hasEffect(KatanaEffects.PARALYSIS.get())) event.setCanceled(true);
    }
    @SubscribeEvent public static void interact(PlayerInteractEvent event) {
        if (!event.getEntity().level().isClientSide && event.isCancelable()
                && event.getEntity().hasEffect(KatanaEffects.PARALYSIS.get())) event.setCanceled(true);
    }
}
