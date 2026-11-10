package com.capatest.item;

import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.crafting.Ingredient;

public class CapaArmorMaterial implements ArmorMaterial {
    public static final CapaArmorMaterial INSTANCE = new CapaArmorMaterial();

    @Override
    public int getDurabilityForType(ArmorItem.Type type) {
        // Antes devolvía 600 para los 4 tipos. Ahora es coherente por pieza.
        return switch (type) {
            case HELMET -> 260;
            case CHESTPLATE -> 900;
            case LEGGINGS -> 720;
            case BOOTS -> 320;
        };
    }

    @Override
    public int getDefenseForType(ArmorItem.Type type) {
        return type == ArmorItem.Type.CHESTPLATE ? 9 : 0;
    }

    @Override
    public int getEnchantmentValue() {
        return 20;
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
        // BUG FIX: antes era "capatest:capa_deteriorer_evilsaiyan". Forge interpreta
        // los ':' de este nombre como separador de namespace al construir la textura
        // vanilla de armadura. Con el override de getArmorTexture() en el item esto
        // ya no se usa, pero el nombre debe ser un id simple y válido.
        return "capa_deteriorer_evilsaiyan";
    }

    @Override
    public float getToughness() {
        return 3.0F;
    }

    @Override
    public float getKnockbackResistance() {
        return 0.15F;
    }
}
