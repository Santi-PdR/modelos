package com.stainkatana.visual;

import com.stainkatana.StainKatanaMod;
import com.stainkatana.katana.KatanaNetwork;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.io.File;

/** Deterministic graphical smoke fixture. Only present in the CI client. */
@Mod.EventBusSubscriber(modid = StainKatanaMod.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class VisualFixtureClient {
    private static int tick;
    private static String capture;
    private static net.minecraft.world.item.ItemStack savedStack;
    private static float comboHealth;
    private static float firstComboDamage;
    private static java.util.UUID dragonId, finisherTarget;
    private static float finisherHealth;
    private static net.minecraft.world.phys.Vec3 dragonAnchor;
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || mc.player.getMainHandItem().isEmpty()) return;
        tick++;
        if (tick == 1) {
            var id = new net.minecraft.resources.ResourceLocation("bettercombat", "attack_animations/two_handed_slash_vertical_right.json");
            System.out.println("STAIN_FIXTURE_BETTERCOMBAT=" + net.minecraftforge.fml.ModList.get().isLoaded("bettercombat"));
            System.out.println("STAIN_FIXTURE_CLIP=" + (mc.getResourceManager().getResource(id).isPresent() ? "bettercombat" : "fallback"));
        }
        switch (tick) {
            case 5 -> {
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.LEFT);
                mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
                mc.options.fov().set(35);
            }
            case 18 -> {
                if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.LEFT)
                    throw new IllegalStateException("Left-handed fixture did not synchronize");
                capture = "00a_left_third.png";
            }
            case 21 -> mc.options.setCameraType(CameraType.FIRST_PERSON);
            case 26 -> capture = "00b_left_first.png";
            case 29 -> {
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.RIGHT);
                mc.options.fov().set(70);
            }
            case 35 -> mc.setScreen(new InventoryScreen(mc.player));
            case 40 -> capture = "01_inventory.png";
            case 48 -> mc.setScreen(null);
            case 58 -> {
                if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.RIGHT)
                    throw new IllegalStateException("Right-handed fixture did not synchronize");
                mc.options.setCameraType(CameraType.FIRST_PERSON); capture = "02_first_person.png";
            }
            case 70 -> { mc.options.setCameraType(CameraType.THIRD_PERSON_BACK); mc.options.fov().set(35); capture = "03_third_back.png"; }
            case 82 -> { mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT); capture = "04_third_front.png"; }
            case 95 -> { mc.options.fov().set(70); mc.options.setCameraType(CameraType.THIRD_PERSON_BACK); }
            case 105 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(1));
            case 111 -> capture = "05_slash_windup.png";
            case 113 -> capture = "06a_slash_impact.png";
            case 114 -> capture = "06b_slash_impact.png";
            case 115 -> capture = "06c_slash_impact.png";
            case 116 -> capture = "06d_slash_impact.png";
            case 140 -> { mc.options.setCameraType(CameraType.FIRST_PERSON); KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(0)); }
            case 144 -> capture = "10a_blood_reach.png";
            case 147 -> capture = "10b_blood_draw.png";
            case 151 -> capture = "10_paralysis.png";
            case 153 -> capture = "11_blood_feedback.png";
            case 155 -> capture = "11a_blood_recovery.png";
            case 180 -> {
                mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
                if (net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) mc.options.keyAttack.setDown(true);
                else mc.player.swing(net.minecraft.world.InteractionHand.MAIN_HAND);
            }
            case 183 -> {
                if (!net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) {
                    if (!com.stainkatana.katana.client.KatanaAnimations.isPlaying(mc.player))
                        throw new IllegalStateException("Vanilla swing animation did not start");
                    System.out.println("STAIN_VANILLA_SWING_PLAYING");
                }
                capture = "12_normal_attack.png";
            }
            case 186 -> capture = "13_normal_attack.png";
            case 190 -> mc.options.keyAttack.setDown(false);
            case 220 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(2));
            case 230 -> capture = "07_ultimate_start.png";
            case 260 -> {
                if (!com.stainkatana.katana.client.KatanaScene.cameraApplied())
                    throw new IllegalStateException("Cinematic orbit never applied");
                System.out.println("STAIN_CAMERA_VERIFIED");
                capture = "08_ultimate_2s.png";
            }
            case 300 -> capture = "09_ultimate_4s.png";
            case 340 -> capture = "14_ultimate_6s.png";
            case 380 -> capture = "15_ultimate_8s.png";
            case 430 -> capture = "16_ultimate_end.png";
            case 440 -> {
                mc.options.fov().set(35); mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT);
                // Move the marked fixture mob aside so it cannot obscure the player's gesture.
                mc.getSingleplayerServer().execute(() -> {
                    var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                    var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(8));
                    if (!mobs.isEmpty()) mobs.get(0).teleportTo(player.getX() + 3, player.getY(), player.getZ() + 1);
                });
            }
            case 445 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(0));
            case 449 -> capture = "17a_blood_third_reach.png";
            case 453 -> capture = "17b_blood_third_draw.png";
            case 457 -> capture = "17c_blood_third_face.png";
            case 459 -> capture = "17d_blood_third_recovery.png";
            case 460 -> { mc.options.fov().set(70); mc.options.setCameraType(CameraType.THIRD_PERSON_BACK); }
            case 479 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(8));
                if (mobs.isEmpty() || player.getPersistentData().getCompound("StainKatanaAbilities").getInt("daggerCharges") != 2)
                    throw new IllegalStateException("Two successful Zs did not charge the finisher");
                var victim = mobs.get(0);
                finisherTarget = victim.getUUID(); finisherHealth = victim.getHealth();
                com.stainkatana.katana.KatanaAbilities.activate(player, 0);
                if (player.getPersistentData().getCompound("StainKatanaAbilities").getInt("daggerCharges") != 0)
                    throw new IllegalStateException("Pressing Z did not start the finisher or consume charges");
                var fromTarget = player.position().subtract(victim.position()).multiply(1, 0, 1);
                var facing = victim.getLookAngle().multiply(1, 0, 1);
                if (fromTarget.lengthSqr() > 16 || fromTarget.dot(facing) >= 0)
                    throw new IllegalStateException("Finisher did not teleport behind its target");
                System.out.println("STAIN_FINISHER_VERIFIED");
            });
            case 491 -> {
                if (!com.stainkatana.katana.client.KatanaScene.cameraApplied())
                    throw new IllegalStateException("Finisher camera did not acquire a target");
                System.out.println("STAIN_FINISHER_CAMERA_VERIFIED");
                capture = "18_finisher.png";
            }
            case 495 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var target = player.serverLevel().getEntity(finisherTarget);
                if (!(target instanceof net.minecraft.world.entity.LivingEntity victim) || !victim.isAlive()
                        || finisherHealth - victim.getHealth() <= player.getAttributeValue(net.minecraft.world.entity.ai.attributes.Attributes.ATTACK_DAMAGE))
                    throw new IllegalStateException("Finisher did not land stronger-than-normal, non-lethal damage");
                System.out.println("STAIN_FINISHER_DAMAGE_VERIFIED");
            });
            case 503 -> capture = "19_finisher_end.png";
            case 550 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                player.setYRot(180);
                long now = player.getServer().overworld().getGameTime();
                com.stainkatana.katana.KatanaAbilities.activate(player, 1);
                if (player.getPersistentData().getCompound("StainKatanaAbilities").getLong("next1") <= now)
                    throw new IllegalStateException("X did not activate facing empty space");
                player.setYRot(0);
                System.out.println("STAIN_EMPTY_X_VERIFIED");
            });
            case 590 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(20));
                if (mobs.isEmpty()) throw new IllegalStateException("No fixture mob");
                mobs.get(0).teleportTo(player.getX(), player.getY(), player.getZ() + 14);
                player.setYRot(0);
                long now = player.getServer().overworld().getGameTime();
                com.stainkatana.katana.KatanaAbilities.activate(player, 2);
                if (player.getPersistentData().getCompound("StainKatanaAbilities").getLong("next2") <= now)
                    throw new IllegalStateException("C failed at 14 blocks");
                System.out.println("STAIN_LONG_RANGE_C_VERIFIED");
            });
            case 600 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(20));
                if (mobs.isEmpty() || !mobs.get(0).hasEffect(com.stainkatana.katana.KatanaEffects.CINEMATIC_BIND.get()))
                    throw new IllegalStateException("Long range C did not bind mob");
                savedStack = player.getMainHandItem();
                if (savedStack.isDamageableItem() || !savedStack.getItem().isEnchantable(savedStack))
                    throw new IllegalStateException("Katana durability or enchantability is incorrect");
                float health = player.getHealth();
                boolean hurt = player.hurt(player.damageSources().mobAttack(mobs.get(0)), 5);
                if (hurt || player.getHealth() != health)
                    throw new IllegalStateException("C did not protect the caster against entity damage");
                player.getInventory().setItem(player.getInventory().selected, new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.STICK));
                System.out.println("STAIN_CASTER_PROTECTION_VERIFIED");
            });
            case 605 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(20));
                if (mobs.isEmpty() || !com.stainkatana.katana.KatanaAbilities.isCinematicallyBound(mobs.get(0)))
                    throw new IllegalStateException("C stopped after changing items");
                player.addEffect(new net.minecraft.world.effect.MobEffectInstance(com.stainkatana.katana.KatanaEffects.PARALYSIS.get(), 100));
            });
            case 610 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(20));
                if (mobs.isEmpty() || com.stainkatana.katana.KatanaAbilities.isCinematicallyBound(mobs.get(0)))
                    throw new IllegalStateException("C cancellation did not release mob");
                player.removeEffect(com.stainkatana.katana.KatanaEffects.PARALYSIS.get());
                player.getInventory().setItem(player.getInventory().selected, savedStack);
                System.out.println("STAIN_CANCELLATION_VERIFIED");
            });
            case 620 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(20));
                if (mobs.isEmpty()) throw new IllegalStateException("No fixture mob for Z");
                var mob = mobs.get(0);
                // Exercise the normal hit-marking method, then separate the mob.
                player.getMainHandItem().hurtEnemy(mob, player);
                mob.teleportTo(player.getX(), player.getY(), player.getZ() + 20);
                com.stainkatana.katana.KatanaAbilities.activate(player, 0);
            });
            case 640 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(24));
                if (mobs.isEmpty() || !mobs.get(0).hasEffect(com.stainkatana.katana.KatanaEffects.PARALYSIS.get()))
                    throw new IllegalStateException("Z did not paralyze target at 20 blocks");
                System.out.println("STAIN_LONG_RANGE_Z_VERIFIED");
            });
            case 670 -> mc.getSingleplayerServer().execute(() -> {
                if (net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) return;
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(24));
                if (mobs.isEmpty()) throw new IllegalStateException("No mob for combo");
                var mob = mobs.get(0);
                mob.teleportTo(player.getX(), player.getY(), player.getZ() + 2);
                mob.setHealth(mob.getMaxHealth());
                player.getPersistentData().getCompound("StainKatanaAbilities").putInt("daggerCharges", 0);
                comboHealth = mob.getHealth();
            });
            case 690, 710, 730, 750 -> mc.getSingleplayerServer().execute(() -> {
                if (net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) return;
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var mobs = player.serverLevel().getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(5));
                if (mobs.isEmpty()) throw new IllegalStateException("Combo target missing");
                var mob = mobs.get(0);
                float before = mob.getHealth();
                player.attack(mob);
                float damage = before - mob.getHealth();
                if (damage <= 0) throw new IllegalStateException("Combo attack caused no damage");
                if (firstComboDamage == 0) firstComboDamage = damage;
                if (tick >= 750) {
                    if (damage < firstComboDamage * 1.4F) throw new IllegalStateException("Fourth hit was not heavier: " + damage + " vs " + firstComboDamage);
                    System.out.println("STAIN_VANILLA_COMBO_VERIFIED " + firstComboDamage + " " + damage);
                }
            });
            case 780 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var world = player.serverLevel();
                world.getEntitiesOfClass(net.minecraft.world.entity.monster.Zombie.class, player.getBoundingBox().inflate(30))
                        .forEach(mob -> mob.teleportTo(player.getX() + 40, player.getY(), player.getZ()));
                world.getGameRules().getRule(net.minecraft.world.level.GameRules.RULE_MOBGRIEFING).set(false, world.getServer());
                var dragon = net.minecraft.world.entity.EntityType.ENDER_DRAGON.create(world);
                if (dragon == null) throw new IllegalStateException("Could not create Ender Dragon");
                dragon.moveTo(player.getX(), player.getY() + 3, player.getZ() + 12, 180, 0);
                world.addFreshEntity(dragon);
                dragonId = dragon.getUUID();
                player.setYRot(0); player.setXRot(0);
                player.getPersistentData().getCompound("StainKatanaAbilities").putLong("next2", 0);
            });
            case 790 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var dragon = player.serverLevel().getEntity(dragonId);
                if (!(dragon instanceof net.minecraft.world.entity.boss.enderdragon.EnderDragon boss)) throw new IllegalStateException("Dragon missing");
                com.stainkatana.katana.KatanaAbilities.activate(player, 2);
                if (!com.stainkatana.katana.KatanaAbilities.isCinematicallyBound(boss))
                    throw new IllegalStateException("C failed to select Ender Dragon");
                dragonAnchor = boss.position();
                System.out.println("STAIN_DRAGON_SELECTED");
            });
            case 810 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var dragon = player.serverLevel().getEntity(dragonId);
                if (!(dragon instanceof net.minecraft.world.entity.LivingEntity living)
                        || !com.stainkatana.katana.KatanaAbilities.isCinematicallyBound(living)
                        || living.position().distanceToSqr(dragonAnchor) > .25)
                    throw new IllegalStateException("Ender Dragon not held at cinematic anchor");
                player.addEffect(new net.minecraft.world.effect.MobEffectInstance(com.stainkatana.katana.KatanaEffects.PARALYSIS.get(), 100));
                System.out.println("STAIN_DRAGON_HELD");
            });
            case 815 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var dragon = player.serverLevel().getEntity(dragonId);
                if (dragon instanceof net.minecraft.world.entity.LivingEntity living
                        && com.stainkatana.katana.KatanaAbilities.isCinematicallyBound(living))
                    throw new IllegalStateException("Ender Dragon not released after cancellation");
                player.removeEffect(com.stainkatana.katana.KatanaEffects.PARALYSIS.get());
                System.out.println("STAIN_DRAGON_RELEASED");
            });
            case 820 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                var boss = player.serverLevel().getEntity(dragonId);
                if (!(boss instanceof net.minecraft.world.entity.boss.enderdragon.EnderDragon dragon))
                    throw new IllegalStateException("Dragon missing for multipart range fixture");
                player.getInventory().setItem(player.getInventory().selected, savedStack);
                dragon.teleportTo(player.getX(), player.getY() + 3, player.getZ() + 30);
                // Move all other parts with the parent; otherwise stale hitboxes
                // from its previous location can be closer than the test part.
                for (var other : dragon.getParts()) other.setPos(dragon.getX(), dragon.getY(), dragon.getZ());
                var part = dragon.getParts()[0];
                part.setPos(player.getX(), player.getEyeY() - .4, player.getZ() + 8);
                if (dragon.getBoundingBox().intersects(player.getBoundingBox().inflate(15)))
                    throw new IllegalStateException("Multipart parent must be outside the normal search box");
                player.setYRot(0); player.setXRot(0);
                player.getPersistentData().getCompound("StainKatanaAbilities").putLong("next2", 0);
                // Client fixture ticks and server ticks can drift under software rendering.
                // Reset the anti-spam timestamp so this tests hitbox selection, not timing.
                player.getPersistentData().getCompound("StainKatanaAbilities").remove("last");
                System.out.println("STAIN_MULTIPART_DIAG registered=" + player.serverLevel().getPartEntities().contains(part)
                        + " partAlive=" + part.isAlive() + " partBox=" + part.getBoundingBox()
                        + " eye=" + player.getEyePosition() + " look=" + player.getLookAngle()
                        + " sword=" + player.getMainHandItem() + " data=" + player.getPersistentData().getCompound("StainKatanaAbilities"));
                com.stainkatana.katana.KatanaAbilities.activate(player, 2);
                if (!com.stainkatana.katana.KatanaAbilities.isCinematicallyBound(dragon))
                    throw new IllegalStateException("C did not find a dragon part with its parent out of range");
                // Cancel on the next server tick, then restore the sword in case 825.
                player.getInventory().setItem(player.getInventory().selected, new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.STICK));
                System.out.println("STAIN_MULTIPART_RANGE_VERIFIED");
            });
            case 825 -> {
                mc.getSingleplayerServer().execute(() -> {
                    var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                    player.getInventory().setItem(player.getInventory().selected, savedStack);
                });
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.LEFT);
                mc.options.fov().set(35);
                mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT);
            }
            case 845 -> {
                if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.LEFT
                        || mc.player.getMainHandItem().getItem() != StainKatanaMod.KATANA_STAIN.get())
                    throw new IllegalStateException("Left-handed grip fixture not ready");
                capture = "20_left_hand_front.png";
            }
            case 850 -> mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
            case 855 -> capture = "21_left_hand_back.png";
            case 860 -> { mc.options.fov().set(70); mc.options.setCameraType(CameraType.FIRST_PERSON); }
            case 865 -> capture = "22_left_hand_first.png";
            case 870 -> { mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.RIGHT); mc.options.setCameraType(CameraType.THIRD_PERSON_BACK); }
            case 880 -> effectSample(com.stainkatana.katana.KatanaVisualStyle.SWING);
            case 884 -> capture = "23_fx_swing.png";
            case 892 -> effectSample(com.stainkatana.katana.KatanaVisualStyle.BLOOD_BIND);
            case 896 -> capture = "24_fx_blood_bind.png";
            case 904 -> effectSample(com.stainkatana.katana.KatanaVisualStyle.FINISHER);
            case 908 -> capture = "25_fx_finisher.png";
            case 916 -> effectSample(com.stainkatana.katana.KatanaVisualStyle.ULTIMATE_FINAL);
            case 920 -> capture = "26_fx_final.png";
            case 928 -> {
                mc.options.setCameraType(CameraType.FIRST_PERSON);
                mc.getSingleplayerServer().execute(() -> mc.getSingleplayerServer().overworld().setDayTime(18000));
            }
            case 940 -> effectSample(com.stainkatana.katana.KatanaVisualStyle.FINISHER);
            case 944 -> capture = "27_fx_first_night.png";
            case 954 -> { System.out.println("STAIN_EFFECT_SAMPLES_DONE"); System.out.println("STAIN_VISUAL_FIXTURE_FINISHED"); mc.stop(); }
            default -> { }
        }
    }
    private static void effectSample(int style) {
        var player = Minecraft.getInstance().player;
        if (player == null) throw new IllegalStateException("No player for FX sample");
        var forward = player.getLookAngle().multiply(1, 0, 1).normalize();
        // Offset the third-person sample so the caster does not occlude the effect.
        var side = new net.minecraft.world.phys.Vec3(forward.z, 0, -forward.x);
        double lateral = Minecraft.getInstance().options.getCameraType().isFirstPerson() ? 0 : 1.4;
        var point = player.position().add(forward.scale(2.5)).add(side.scale(lateral)).add(0, 1.1, 0);
        com.stainkatana.katana.client.KatanaVisuals.spawn(player.getId(), point.x, point.y, point.z,
                player.getYRot(), style, player.getMainArm() == net.minecraft.world.entity.HumanoidArm.LEFT);
    }
    @SubscribeEvent public static void render(TickEvent.RenderTickEvent event) {
        if (event.phase != TickEvent.Phase.END || capture == null) return;
        String name = capture; capture = null;
        Minecraft mc = Minecraft.getInstance();
        try (var image = Screenshot.takeScreenshot(mc.getMainRenderTarget())) {
            File directory = new File(mc.gameDirectory, "stain-visual-test");
            if (!directory.isDirectory() && !directory.mkdirs()) throw new IllegalStateException("Cannot create screenshots folder");
            image.writeToFile(new File(directory, name));
            System.out.println("STAIN_VISUAL_CAPTURE " + name + " tick=" + tick);
        } catch (Exception e) { throw new IllegalStateException("Screenshot failed: " + name, e); }
    }
}
