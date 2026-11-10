package com.capatest.item;

import com.capatest.CapaTestMod;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.crafting.Ingredient;

public class CapaArmorMaterial implements ArmorMaterial {
    public static final CapaArmorMaterial INSTANCE = new CapaArmorMaterial();

    @Override
    public int getDurabilityForType(ArmorItem.Type type) {
        return 600;
    }

    @Override
    public int getDefenseForType(ArmorItem.Type type) {
        return type == ArmorItem.Type.CHESTPLATE ? 8 : 0;
    }

    @Override
    public int getEnchantmentValue() {
        return 18;
    }

    @Override
    public SoundEvent getEquipSound() {
        return SoundEvents.ARMOR_EQUIP_NETHERITE;
    }

    @Override
    public Ingredient getRepairIngredient() {
        return Ingredient.EMPTY;
    }

    @Override
    public String getName() {
        return CapaTestMod.MOD_ID + ":capa_deteriorer_evilsaiyan";
    }

    @Override
    public float getToughness() {
        return 2.5F;
    }

    @Override
    public float getKnockbackResistance() {
        return 0.1F;
    }
}
