package com.capatest.client;

import com.capatest.CapaTestMod;
import com.capatest.compat.CuriosCompat;
import com.capatest.item.CapaDeteriorerItem;
import com.capatest.item.CapeState;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.blaze3d.vertex.VertexMultiConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.item.ItemStack;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import top.theillusivec4.curios.api.CuriosApi;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;
import java.util.concurrent.CompletableFuture;

/** Real equipment packets and input keys; observe vertices without drawing a second cape. */
final class CapeTransferProbe {
    private static final int CROUCH = 10, JUMP = 24, STAND = 44, END = 59;
    private final StringBuilder trace = new StringBuilder("tramo\ttick\tranura\tdibujos\tvertices_halo\tborde\tinterior\t"
            + "r\tg\tb\tblight\tsuelo\tagachado\taltura\tnuca_x\tnuca_y\tnuca_z\tpaso_nuca\tpaso_control_32\tpaso_punta\n");
    private CompletableFuture<?> request;
    private int stage, start = -1;
    private double floor, maxLive, maxControl;
    private boolean lifted, landed, onGround;
    private Vector3f standingHood, priorHood, priorControl, priorTip;
    private CapaArmorRenderer chest, back;
    private double lastTime, lastEdge, lastInner;
    private Sample sample;

    private record Sample(CapaArmorRenderer renderer, int count, int light, int rgba) {}

    void beginFrame() { sample = null; }

    void arm(CapaArmorRenderer renderer) {
        var layers = renderer.getRenderLayers();
        for (int i = 0; i < layers.size(); i++) {
            if (layers.get(i) instanceof Emission layer && layer.owner == this) return;
            if (layers.get(i) instanceof CapaGlowLayer original) {
                layers.set(i, new Emission(this, renderer, original));
                return;
            }
        }
        throw new AssertionError("actual glow layer missing from equipment renderer");
    }

    void drive(Minecraft game) {
        if (request != null && request.isDone()) {
            request.join();
            request = null;
        }
        if (start < 0 || stage == 2) return;
        int t = game.player.tickCount - start;
        game.options.keyShift.setDown(t >= CROUCH && t < STAND);
        game.options.keyJump.setDown(t >= JUMP && t < JUMP + 2);
        if (t < END) return;
        require(lifted && landed, "crouched jump did not take off and land in " + slot(stage));
        require(maxControl > 2.4 && maxLive < .48, "nape snap in " + slot(stage) + ": " + maxLive + " / " + maxControl);
        CapaTestMod.LOGGER.info("FX smoke: nuca en salto {}: pico {}u / control misma pose .32 {}u",
                slot(stage), String.format(Locale.ROOT, "%.3f", maxLive), String.format(Locale.ROOT, "%.3f", maxControl));
        stage++;
        start = -1;
        lifted = landed = false;
        maxLive = maxControl = 0;
        priorHood = priorControl = null;
        // Leave the visible back piece equipped throughout the transfer. Only
        // the chest packet changes priority, so there is no synthetic empty gap.
        boolean takeOff = stage == 1;
        var server = game.getSingleplayerServer();
        var uuid = game.player.getUUID();
        request = server.submit(() -> {
            var player = server.getPlayerList().getPlayer(uuid);
            player.setItemSlot(EquipmentSlot.CHEST, takeOff ? ItemStack.EMPTY : new ItemStack(CapaTestMod.CAPA_DETERIORER.get()));
        });
    }

    boolean capture(Minecraft game, Path dir, int draws, ItemStack drawn, float partial, CapeWalkProbe.Draw pose) throws IOException {
        var player = game.player;
        var functional = CuriosApi.getCuriosInventory(player).resolve().orElseThrow()
                .getStacksHandler("back").orElseThrow().getStacks().getStackInSlot(0);
        ItemStack armor = player.getItemBySlot(EquipmentSlot.CHEST);
        if (stage == 0 && start < 0 && (!functional.isDamaged() || armor.isEmpty() || !player.onGround())) return false;
        require(functional.is(CapaTestMod.CAPA_DETERIORER.get()) && functional.isDamaged(), "missing worn Curios fixture");
        boolean curios = armor.isEmpty();
        require(draws == 1 && drawn == (curios ? functional : armor) && pose != null,
                "equipment transfer did not draw exactly one winning cape (" + draws + ")");
        require((CuriosCompat.visibleBack(player) != null) == curios, "rendered winner disagrees with display priority");
        require(sample != null && sample.count > 0 && (sample.rgba & 255) == 255, "halo not actually submitted");
        var renderer = sample.renderer;
        var motion = CapaArmorModel.wornMotion(player);
        double blight = motion.weight(CapeState.BLIGHT);
        double now = player.tickCount + (double) partial;
        double edge = (short) sample.light / 4096.0, inner = (short) (sample.light >>> 16) / 4096.0;
        // .39's base halo plus a bounded, halo-only wake (< .55).
        require(edge >= .459 && edge <= 2.181 && inner >= .459 && inner <= 1.971, "invalid halo gains in real equipment render");
        double tipStep = priorTip == null ? 0 : priorTip.distance(pose.tip());
        boolean expected = curios == (stage == 1);
        if (start < 0 && expected) {
            if (stage == 0) chest = renderer;
            else {
                require(player.onGround() && !player.isCrouching(), "transfer fixture not standing");
                require(stage == 1 ? renderer != chest : renderer == chest && renderer != back, "did not switch real renderers");
                if (stage == 1) back = renderer;
                CapeState from = stage == 1 ? CapeState.IDLE : CapeState.BLIGHT;
                require(colorError(sample.rgba, from.glow(now / 20)) <= 1, "visible tint reset when changing equipment");
                require(stage == 1 ? blight < .08 : blight > .92, "cloth blend restarted at the new equipment endpoint");
                double dt = now - lastTime;
                require(dt >= 0 && dt <= 4 && tipStep < 1.2, "free end snapped at equipment transfer: " + tipStep);
                require(Math.max(Math.abs(edge - lastEdge), Math.abs(inner - lastInner)) < .06 + .02 * dt,
                        "halo snapped at equipment transfer");
                CapaTestMod.LOGGER.info("FX smoke: traspaso real a {}: un manto, UV2 continuo, tinte previo y paño mezclado", slot(stage));
            }
            start = player.tickCount;
            floor = player.getY();
        }
        lastTime = now;
        lastEdge = edge;
        lastInner = inner;
        priorTip = pose.tip();
        double t = start < 0 ? -1 : now - start;
        double height = player.getY() - floor;
        boolean ground = player.onGround();
        if (t >= 0 && t < CROUCH) standingHood = pose.hood();
        if (t >= 8 && t < CROUCH) {
            CapeState target = curios ? CapeState.BLIGHT : CapeState.IDLE;
            require(colorError(sample.rgba, target.glow(now / 20)) <= 1 && (curios ? blight > .999 : blight < .001),
                    "visible cape did not finish its fade");
        }
        double hoodStep = 0, controlStep = 0;
        if (stage < 2 && t >= 19 && t < STAND) {
            // FALL can contribute during the hop; the vanilla torso, not
            // a full-weight SNEAK clip, defines the tested clearance.
            require(player.getPose() == Pose.CROUCHING && pose.sneak() > 0, "did not hold Shift through the jump");
            require(Math.abs(player.getXRot()) < .05 && Math.abs(player.getYHeadRot() - player.yBodyRot) < .1,
                    "jump control needs a centered head");
            var hood = pose.hood();
            require(standingHood != null && hood.distance(standingHood) > 2, "nape lost its crouched clearance");
            var control = new Vector3f(hood);
            if (!ground) {
                // Same vertices/pose, only undo .33's airborne translation:
                // mount and seat axes here coincide with chestplate axes.
                var shift = CapeHood.nape(0, 0, 28.64789, pose.sneak()).forBone(CapeWalkProbe.HOOD);
                control.sub((float) shift.x(), (float) shift.y(), (float) shift.z());
                if (height > .5) lifted = true;
            }
            if (priorHood != null) {
                hoodStep = hood.distance(priorHood);
                controlStep = control.distance(priorControl);
                if (onGround != ground) {
                    maxLive = Math.max(maxLive, hoodStep);
                    maxControl = Math.max(maxControl, controlStep);
                    if (ground && lifted) landed = true;
                }
            }
            priorHood = hood;
            priorControl = control;
            onGround = ground;
        }
        trace.append(stage).append('\t').append(t).append('\t').append(curios ? "curios" : "pecho").append('\t')
                .append(draws).append('\t').append(sample.count).append('\t').append(edge).append('\t').append(inner).append('\t')
                .append(sample.rgba >>> 24).append('\t').append((sample.rgba >>> 16) & 255).append('\t').append((sample.rgba >>> 8) & 255)
                .append('\t').append(blight).append('\t').append(ground ? 1 : 0).append('\t').append(player.isCrouching() ? 1 : 0)
                .append('\t').append(height).append('\t').append(pose.hood().x()).append('\t').append(pose.hood().y())
                .append('\t').append(pose.hood().z()).append('\t').append(hoodStep).append('\t').append(controlStep)
                .append('\t').append(tipStep).append('\n');
        if (stage != 2 || t < 10) return false;
        require(blight < .001 && colorError(sample.rgba, CapeState.IDLE.glow(now / 20)) <= 1, "healthy chest did not finish its fade");
        save(dir, "traspaso-forge.tsv");
        restore(chest);
        restore(back);
        return true;
    }

    void save(Path dir, String file) throws IOException {
        Files.writeString(dir.resolve(file), trace);
    }

    private void restore(CapaArmorRenderer renderer) {
        var layers = renderer.getRenderLayers();
        layers.replaceAll(layer -> layer instanceof Emission observed && observed.owner == this ? observed.original : layer);
    }

    private static String slot(int stage) { return stage == 1 ? "curios" : "pecho"; }

    private static int colorError(int rgba, CapeState.Glow glow) {
        return Math.max(Math.abs((rgba >>> 24) - (int)(255 * glow.red())),
                Math.max(Math.abs(((rgba >>> 16) & 255) - (int)(255 * glow.green())),
                         Math.abs(((rgba >>> 8) & 255) - (int)(255 * glow.blue()))));
    }

    private static void require(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }

    private static final class Emission extends GeoRenderLayer<CapaDeteriorerItem> {
        private final CapeTransferProbe owner;
        private final CapaArmorRenderer renderer;
        private final CapaGlowLayer original;

        Emission(CapeTransferProbe owner, CapaArmorRenderer renderer, CapaGlowLayer original) {
            super(renderer);
            this.owner = owner;
            this.renderer = renderer;
            this.original = original;
        }

        @Override
        public void render(PoseStack pose, CapaDeteriorerItem item, BakedGeoModel geometry, RenderType type,
                           MultiBufferSource buffers, VertexConsumer vertices, float partial, int light, int overlay) {
            var player = Minecraft.getInstance().player;
            if (renderer.getCurrentEntity() != player) {
                original.render(pose, item, geometry, type, buffers, vertices, partial, light, overlay);
                return;
            }
            var trace = new CapeVertexProbe();
            original.render(pose, item, geometry, type, target -> {
                require(target == CapeBloom.wornLight(CapeBloom.Mode.HALO), "unexpected real glow render type");
                return VertexMultiConsumer.create(buffers.getBuffer(target), trace);
            }, vertices, partial, light, overlay);
            owner.sample = new Sample(renderer, trace.count, trace.light, trace.rgba);
        }
    }
}
