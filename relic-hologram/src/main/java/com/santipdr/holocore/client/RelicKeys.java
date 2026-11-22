package com.santipdr.holocore.client;

import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.KeyMapping;
import net.minecraftforge.client.settings.KeyConflictContext;
import org.lwjgl.glfw.GLFW;

/**
 * Teclas del mod: G despierta/dorme, P pulsa y M pasa de un estado de brillo al
 * siguiente, lejos de las de vanilla.
 */
public final class RelicKeys {

    public static final String CATEGORY = "key.categories.holocore";

    public static final KeyMapping TOGGLE = new KeyMapping(
            "key.holocore.toggle",
            KeyConflictContext.IN_GAME,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_G,
            CATEGORY);

    public static final KeyMapping PULSE = new KeyMapping(
            "key.holocore.pulse",
            KeyConflictContext.IN_GAME,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_P,
            CATEGORY);

    public static final KeyMapping MOOD = new KeyMapping(
            "key.holocore.mood",
            KeyConflictContext.IN_GAME,
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_M,
            CATEGORY);

    private RelicKeys() {
    }
}
