package com.santipdr.holocore.client;

import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.santipdr.holocore.HoloCore;
import com.santipdr.holocore.config.RelicConfig;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.ShaderInstance;
import net.minecraft.server.packs.resources.PreparableReloadListener;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.util.profiling.ProfilerFiller;
import net.minecraftforge.client.event.RegisterClientReloadListenersEvent;
import net.minecraftforge.fml.ModList;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

/**
 * Shader propio de la reliquia: fresnel en el borde + linea de barrido.
 *
 * <p>El juego solo precompila sus propios core shaders, asi que este se monta a
 * mano desde un listener de recarga de recursos (asi se recompila al cambiar de
 * pack de recursos) y se tira el anterior. Los ficheros viven en
 * {@code assets/minecraft/shaders/core/holocore_relic_glow.*} porque
 * {@link ShaderInstance} arma la ruta como {@code shaders/core/<nombre>.json} y
 * el nombre no admite namespace.</p>
 *
 * <p><b>Con shaderpack activo no se usa.</b> Iris/Oculus/OptiFine sustituyen el
 * pipeline: un programa que el pack no conoce acaba en su fallback o invisible
 * (le paso a Forge con su shader "unlit", Oculus #630). En ese caso el mod se
 * queda con los tres pases de siempre, que el pack si entiende.</p>
 */
public final class RelicShaders {

    /** Nombre del programa; tiene que coincidir con los ficheros de resources. */
    public static final String PROGRAM = "holocore_relic_glow";

    /** Cada cuanto se vuelve a mirar si hay pack activo (ms). */
    private static final long PACK_CHECK_MS = 5_000L;

    private static volatile ShaderInstance shader;
    private static boolean shaderPackActive;
    private static long nextPackCheck;

    private RelicShaders() {
    }

    public static void register(RegisterClientReloadListenersEvent event) {
        event.registerReloadListener(new Reload());
    }

    /** Shader compilado, o {@code null} si fallo la compilacion. */
    public static ShaderInstance shader() {
        return shader;
    }

    /**
     * Se puede usar el pase GLSL: configurado, compilado y sin shaderpack que lo
     * vaya a sustituir.
     */
    public static boolean ready() {
        return RelicConfig.SHADER_GLOW.get() && shader != null && !shaderPackActive();
    }

    /** Tiempo en segundos, para el uniform del barrido. */
    public static float timeSeconds(float partialTick) {
        Minecraft minecraft = Minecraft.getInstance();
        float ticks = (minecraft.level == null ? 0L : minecraft.level.getGameTime()) + partialTick;
        return ticks / 20.0F;
    }

    /**
     * Oculus/OptiFine presentes. Si la API de Iris esta disponible se le pregunta
     * de verdad si hay pack en uso; si no, se asume que si (mejor perder el
     * fresnel que dejar la reliquia invisible).
     */
    public static boolean shaderPackActive() {
        long now = System.currentTimeMillis();
        if (now >= nextPackCheck) {
            nextPackCheck = now + PACK_CHECK_MS;
            shaderPackActive = detectShaderPack();
        }
        return shaderPackActive;
    }

    private static boolean detectShaderPack() {
        boolean irisFamily = ModList.get().isLoaded("oculus") || ModList.get().isLoaded("iris");
        if (irisFamily) {
            try {
                Class<?> api = Class.forName("net.irisshaders.iris.api.v0.IrisApi");
                Object instance = api.getMethod("getInstance").invoke(null);
                Object inUse = api.getMethod("isShaderPackInUse").invoke(instance);
                if (inUse instanceof Boolean active) {
                    return active;
                }
            } catch (Throwable ignored) {
                // Version de Oculus sin esa API: se asume activo.
            }
            return true;
        }
        if (ModList.get().isLoaded("optifine")) {
            return true;
        }
        try {
            Class.forName("optifine.Installer");
            return true;
        } catch (Throwable ignored) {
            return false;
        }
    }

    private static void install(ShaderInstance loaded) {
        if (loaded == null) {
            // Si esta recarga fallo (pack de recursos roto, GLSL tocado en un
            // resource pack...) se conserva el programa anterior: peor es dejar
            // el RenderType con un shader nulo y petar en el primer dibujo.
            if (shader == null) {
                HoloCore.LOGGER.warn("Sin shader {}: el pase GLSL queda desactivado", PROGRAM);
            }
            return;
        }
        ShaderInstance previous = shader;
        shader = loaded;
        if (previous != null) {
            previous.close();
        }
        // Marcador que el smoke test del CI busca en el log: si el GLSL no
        // compila, esta linea no aparece y el CI falla.
        HoloCore.LOGGER.info("Shader del aura compilado ({})", PROGRAM);
    }

    private static ShaderInstance build(ResourceManager manager) {
        try {
            return new ShaderInstance(manager, PROGRAM, DefaultVertexFormat.NEW_ENTITY);
        } catch (Exception e) {
            HoloCore.LOGGER.error("No se pudo compilar el shader {}: {}", PROGRAM, e.toString());
            return null;
        }
    }

    private static final class Reload implements PreparableReloadListener {

        /**
         * La compilacion va en el ejecutor del juego, no en el de fondo: crear un
         * programa GL requiere el contexto de OpenGL, que solo existe en el hilo
         * de render. Ahi tambien corre GameRenderer.reloadShaders.
         */
        @Override
        public CompletableFuture<Void> reload(PreparationBarrier barrier, ResourceManager manager,
                                              ProfilerFiller prepProfiler, ProfilerFiller reloadProfiler,
                                              Executor backgroundExecutor, Executor gameExecutor) {
            return CompletableFuture.completedFuture(null)
                    .thenCompose(barrier::wait)
                    .thenRunAsync(() -> install(build(manager)), gameExecutor);
        }
    }
}
