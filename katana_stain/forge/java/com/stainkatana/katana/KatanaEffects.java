package com.stainkatana.katana;

import com.stainkatana.StainKatanaMod;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public final class KatanaEffects {
    private static final DeferredRegister<MobEffect> EFFECTS = DeferredRegister.create(ForgeRegistries.MOB_EFFECTS, StainKatanaMod.MOD_ID);
    public static final RegistryObject<MobEffect> PARALYSIS = EFFECTS.register("blood_paralysis", BloodParalysis::new);
    // Separate effect permits the cinematic to release its own immobilization safely.
    public static final RegistryObject<MobEffect> CINEMATIC_BIND = EFFECTS.register("cinematic_bind", BloodParalysis::new);
    public static boolean immobilized(net.minecraft.world.entity.LivingEntity entity) {
        return entity.hasEffect(PARALYSIS.get()) || entity.hasEffect(CINEMATIC_BIND.get());
    }
    private KatanaEffects() { }
    public static void register(IEventBus bus) { EFFECTS.register(bus); }
    private static final class BloodParalysis extends MobEffect {
        private BloodParalysis() {
            super(MobEffectCategory.HARMFUL, 0x7B0A18);
            addAttributeModifier(Attributes.MOVEMENT_SPEED, "4f48fd63-8d16-46c6-97e3-9177156dc910", -1.0D, AttributeModifier.Operation.MULTIPLY_TOTAL);
        }
    }
}
