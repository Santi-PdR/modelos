package com.santipdr.holocore.client;

import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.KeyMapping;
import net.minecraftforge.client.settings.KeyConflictContext;
import org.lwjgl.glfw.GLFW;

/** Teclas del mod. G por defecto para no chocar con las de vanilla. */
public final class RelicKeys {

    public static final String CATEGORY = "key.categories.holocore";

    public static final KeyMapping TOGGLE = new KeyMapping(
            "key.holocore.toggle",
            KeyConflictContext.IN_GAME,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_G,
            CATEGORY);

    private RelicKeys() {
    }
}
