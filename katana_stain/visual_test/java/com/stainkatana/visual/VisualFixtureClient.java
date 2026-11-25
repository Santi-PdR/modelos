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
    private static long impactServerTick = -1;
    private static int impactCaptures;
    private static net.minecraft.world.item.ItemStack savedStack;
    private static int vanillaCueBeforeDisabled;
    private static float comboHealth;
    private static float firstComboDamage;
    private static java.util.UUID dragonId, finisherTarget;
    private static float finisherHealth, finisherSwordAttack;
    private static net.minecraft.world.phys.Vec3 dragonAnchor;
    /** Verify BC really resolved our four imported animation IDs, not merely that
     * the JSON files exist. Reflection keeps the fixture loadable without BC. */
    private static void verifyBetterCombatAnimations(Minecraft mc) {
        try {
            Class<?> registry = Class.forName("net.bettercombat.logic.WeaponRegistry");
            Object attrs = registry.getMethod("getAttributes", net.minecraft.world.item.ItemStack.class)
                    .invoke(null, mc.player.getMainHandItem());
            if (attrs == null) throw new IllegalStateException("No Better Combat katana attributes");
            Object[] attacks = (Object[]) attrs.getClass().getMethod("attacks").invoke(attrs);
            String[] expected = {"stainkatana:stain_serious_1", "stainkatana:stain_serious_2",
                    "stainkatana:stain_improved_3", "stainkatana:stain_improved_4"};
            if (attacks.length != expected.length) throw new IllegalStateException("Unexpected katana combo length");
            var animations = (java.util.Map<?, ?>) Class.forName("net.bettercombat.client.animation.AnimationRegistry")
                    .getField("animations").get(null);
            for (int i = 0; i < expected.length; i++) {
                Object id = attacks[i].getClass().getMethod("animation").invoke(attacks[i]);
                if (!expected[i].equals(id) || !animations.containsKey(id))
                    throw new IllegalStateException("Better Combat did not resolve imported attack " + i + ": " + id);
            }
            System.out.println("STAIN_BC_IMPORTED_COMBO_RESOLVED");
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("Cannot inspect Better Combat animation registry", e);
        }
    }
    private static final java.util.Set<String> bcHits = new java.util.HashSet<>();
    private static void observeBetterCombatCombo() {
        try {
            Class<?> events = Class.forName("net.bettercombat.api.client.BetterCombatClientEvents");
            Class<?> listener = Class.forName("net.bettercombat.api.client.BetterCombatClientEvents$PlayerAttackHit");
            Object callback = java.lang.reflect.Proxy.newProxyInstance(listener.getClassLoader(), new Class<?>[]{listener}, (proxy, method, args) -> {
                if (method.getDeclaringClass() == Object.class) {
                    if (method.getName().equals("toString")) return "KatanaComboFixture";
                    if (method.getName().equals("hashCode")) return System.identityHashCode(proxy);
                    if (method.getName().equals("equals")) return proxy == args[0];
                    return null;
                }
                if (args != null && args.length >= 3 && args[2] instanceof java.util.List<?> targets
                        && VisualFixtureServer.bcComboTarget != null
                        && targets.stream().anyMatch(e -> e instanceof net.minecraft.world.entity.Entity entity
                                && entity.getUUID().equals(VisualFixtureServer.bcComboTarget))) {
                    Object attack = args[1].getClass().getMethod("attack").invoke(args[1]);
                    String id = (String) attack.getClass().getMethod("animation").invoke(attack);
                    bcHits.add(id);
                }
                return null;
            });
            Object publisher = events.getField("ATTACK_HIT").get(null);
            publisher.getClass().getMethod("register", Object.class).invoke(publisher, callback);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("Cannot observe Better Combat attack events", e);
        }
    }
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null || mc.player.getMainHandItem().isEmpty()) return;
        // Do not advance the script while a requested frame is still pending.
        // On a busy software renderer several client ticks can run before the
        // next render; otherwise later cases overwrite captures or change hands
        // before the image is actually taken. Also avoid the loading overlay.
        if (capture != null || (tick == 0 && mc.screen != null)) return;
        var impact = VisualFixtureServer.confirmedImpacts.poll();
        if (impact != null) {
            impactServerTick = impact.serverTick();
            capture = String.format("confirmed_c_impact_%02d.png", impact.index());
            impactCaptures++;
            return;
        }
        tick++;
        if (tick == 1) {
            var id = new net.minecraft.resources.ResourceLocation("bettercombat", "attack_animations/two_handed_slash_vertical_right.json");
            System.out.println("STAIN_FIXTURE_BETTERCOMBAT=" + net.minecraftforge.fml.ModList.get().isLoaded("bettercombat"));
            System.out.println("STAIN_FIXTURE_CLIP=" + (mc.getResourceManager().getResource(id).isPresent() ? "bettercombat" : "fallback"));
            verifyAbilitySoundSelection(mc);
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
            case 19 -> mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT);
            case 20 -> capture = "00c_left_guard_front.png";
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
            case 205 -> {
                if (net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) {
                    if (com.stainkatana.katana.client.KatanaBetterCombatFx.cueCount() == 0)
                        throw new IllegalStateException("Better Combat attack did not trigger a katana cue");
                    verifyBetterCombatAnimations(mc);
                    System.out.println("STAIN_BC_ATTACK_FX_VERIFIED");
                }
            }
            // Animation preference must not silently disable the fallback
            // swing sound and particles. Better Combat owns its own cues.
            case 208 -> {
                if (!net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) {
                    vanillaCueBeforeDisabled = com.stainkatana.katana.client.KatanaVanillaSwings.cueCount();
                    com.stainkatana.katana.KatanaClientConfig.VANILLA_SWINGS.set(false);
                    mc.player.swing(net.minecraft.world.InteractionHand.MAIN_HAND);
                }
            }
            case 214 -> {
                if (!net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) {
                    if (com.stainkatana.katana.client.KatanaVanillaSwings.cueCount() <= vanillaCueBeforeDisabled)
                        throw new IllegalStateException("Disabling vanilla animation also suppressed its swing cue");
                    if (com.stainkatana.katana.client.KatanaAnimations.isPlaying(mc.player))
                        throw new IllegalStateException("Vanilla swing animation ignored disabled preference");
                    com.stainkatana.katana.KatanaClientConfig.VANILLA_SWINGS.set(true);
                    System.out.println("STAIN_VANILLA_CUE_WITHOUT_ANIMATION_VERIFIED");
                }
            }
            case 220 -> KatanaNetwork.CHANNEL.sendToServer(new KatanaNetwork.AbilityMessage(2));
            case 230 -> capture = "07_ultimate_start.png";
            // Sample additional real C strokes, not just the local animation preview.
            case 246 -> capture = "106_c_stroke_02.png";
            case 277 -> capture = "107_c_stroke_04.png";
            case 297 -> capture = "108_c_stroke_05.png";
            case 319 -> capture = "109_c_stroke_06.png";
            case 339 -> capture = "110_c_stroke_07.png";
            case 358 -> capture = "111_c_stroke_08.png";
            case 378 -> capture = "112_c_stroke_09.png";
            case 405 -> capture = "113_c_stroke_10.png";
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
                finisherSwordAttack = (float)player.getAttributeValue(net.minecraft.world.entity.ai.attributes.Attributes.ATTACK_DAMAGE);
                // Creative mode would make both protection checks vacuous.
                player.setGameMode(net.minecraft.world.level.GameType.SURVIVAL);
                player.invulnerableTime = 0;
                float originalHealth = player.getHealth();
                // The scene victim is paralyzed and cannot attack; use an independent, unbound source.
                var attacker = java.util.Objects.requireNonNull(net.minecraft.world.entity.EntityType.ZOMBIE.create(player.serverLevel()));
                if (!player.hurt(player.damageSources().mobAttack(attacker), 1))
                    throw new IllegalStateException("Control attack did not damage survival player");
                player.setHealth(originalHealth);
                player.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
                player.invulnerableTime = 0;
                com.stainkatana.katana.KatanaAbilities.activate(player, 0);
                if (player.getPersistentData().getCompound("StainKatanaAbilities").getInt("daggerCharges") != 0)
                    throw new IllegalStateException("Pressing Z did not start the finisher or consume charges");
                var fromTarget = player.position().subtract(victim.position()).multiply(1, 0, 1);
                var facing = victim.getLookAngle().multiply(1, 0, 1);
                if (fromTarget.lengthSqr() > 16 || fromTarget.dot(facing) >= 0)
                    throw new IllegalStateException("Finisher did not teleport behind its target");
                System.out.println("STAIN_FINISHER_VERIFIED");
                float casterHealth = player.getHealth();
                if (player.hurt(player.damageSources().mobAttack(attacker), 4) || player.getHealth() != casterHealth)
                    throw new IllegalStateException("Finisher did not protect its caster");
                player.setGameMode(net.minecraft.world.level.GameType.CREATIVE);
                savedStack = player.getMainHandItem();
                player.getInventory().setItem(player.getInventory().selected, new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.STICK));
                System.out.println("STAIN_FINISHER_ITEM_SWITCH_VERIFIED");
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
                        || finisherHealth - victim.getHealth() <= finisherSwordAttack)
                    throw new IllegalStateException("Finisher did not land stronger-than-normal, non-lethal damage");
                System.out.println("STAIN_FINISHER_DAMAGE_VERIFIED");
            });
            case 500 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                player.getInventory().setItem(player.getInventory().selected, savedStack);
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
                var damageBook = new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.ENCHANTED_BOOK);
                net.minecraft.world.item.EnchantedBookItem.addEnchantment(damageBook, new net.minecraft.world.item.enchantment.EnchantmentInstance(net.minecraft.world.item.enchantment.Enchantments.SHARPNESS, 1));
                var repairBook = new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.ENCHANTED_BOOK);
                net.minecraft.world.item.EnchantedBookItem.addEnchantment(repairBook, new net.minecraft.world.item.enchantment.EnchantmentInstance(net.minecraft.world.item.enchantment.Enchantments.MENDING, 1));
                if (!savedStack.getItem().isBookEnchantable(savedStack, damageBook) || savedStack.getItem().isBookEnchantable(savedStack, repairBook))
                    throw new IllegalStateException("Katana anvil enchantment policy is incorrect");
                player.setGameMode(net.minecraft.world.level.GameType.SURVIVAL);
                player.invulnerableTime = 0;
                float health = player.getHealth();
                var attacker = java.util.Objects.requireNonNull(net.minecraft.world.entity.EntityType.ZOMBIE.create(player.serverLevel()));
                boolean hurt = player.hurt(player.damageSources().mobAttack(attacker), 5);
                if (hurt || player.getHealth() != health)
                    throw new IllegalStateException("C did not protect the caster against entity damage");
                player.setGameMode(net.minecraft.world.level.GameType.CREATIVE);
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
            case 760 -> {
                mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT); mc.options.fov().set(35);
                com.stainkatana.katana.client.KatanaAnimations.swing(mc.player, 3);
            }
            case 764 -> capture = "28_fourth_cut.png";
            case 775 -> { mc.options.fov().set(70); mc.options.setCameraType(CameraType.THIRD_PERSON_BACK); }
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
                // Its autonomous flight and client rotation packets can move the
                // target or aim between the setup and activation. Establish the
                // test geometry on the server immediately before the request.
                boss.teleportTo(player.getX(), player.getY() + 3, player.getZ() + 12);
                boss.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
                for (var part : boss.getParts()) part.setPos(player.getX(), player.getEyeY() - .4, player.getZ() + 10);
                player.setYRot(0); player.setXRot(0);
                player.getPersistentData().getCompound("StainKatanaAbilities").remove("last");
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
                // Switching items is allowed; explicitly interrupt the scene before the next visual tests.
                player.addEffect(new net.minecraft.world.effect.MobEffectInstance(com.stainkatana.katana.KatanaEffects.PARALYSIS.get(), 100));
                System.out.println("STAIN_MULTIPART_RANGE_VERIFIED");
            });
            case 825 -> {
                mc.getSingleplayerServer().execute(() -> {
                    var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                    player.removeEffect(com.stainkatana.katana.KatanaEffects.PARALYSIS.get());
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
            case 872 -> com.stainkatana.katana.KatanaClientConfig.HUD_POSITION.set(com.stainkatana.katana.KatanaClientConfig.HudPosition.TOP_CENTER);
            case 875 -> capture = "29_hud_top_center.png";
            case 878 -> com.stainkatana.katana.KatanaClientConfig.HUD_POSITION.set(com.stainkatana.katana.KatanaClientConfig.HudPosition.RIGHT_MIDDLE);
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
            case 954 -> com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 1);
            case 959 -> capture = "30_slash_first_night.png";
            case 969 -> {
                mc.getSingleplayerServer().execute(() -> {
                    var world = mc.getSingleplayerServer().overworld();
                    world.setDayTime(6000);
                    var dragon = world.getEntity(dragonId);
                    if (dragon != null) dragon.discard();
                });
                mc.options.fov().set(70); mc.options.setCameraType(CameraType.FIRST_PERSON);
            }
            case 980 -> bloodSample(0, 0, 0);
            case 987 -> capture = "31_blood_base.png";
            case 1005 -> bloodSample(4, -4, 0);
            case 1012 -> capture = "32_blood_x4_y_minus4.png";
            case 1030 -> bloodSample(6, -6, 0);
            case 1037 -> capture = "33_blood_x6_y_minus6.png";
            case 1055 -> bloodSample(8, -6, 0);
            case 1062 -> capture = "34_blood_x8_y_minus6.png";
            case 1080 -> bloodSample(4, -8, 0);
            case 1087 -> capture = "35_blood_x4_y_minus8.png";
            case 1105 -> bloodSample(6, -6, 4);
            case 1112 -> capture = "36_blood_x6_y_minus6_z4.png";
            case 1130 -> bloodSample(6, -6, -4);
            case 1137 -> capture = "37_blood_x6_y_minus6_z_minus4.png";
            // Sample a full gesture for both handedness settings. A single frame
            // cannot establish hand-to-blade contact or catch mirroring errors.
            case 1155 -> {
                mc.getSingleplayerServer().execute(() -> {
                    var dragon = mc.getSingleplayerServer().overworld().getEntity(dragonId);
                    if (dragon != null) dragon.discard();
                });
                bloodSample(0, 0, 0);
            }
            case 1159 -> capture = "38_blood_right_reach.png";
            case 1162 -> capture = "39_blood_right_draw.png";
            case 1166 -> capture = "40_blood_right_face.png";
            case 1170 -> capture = "41_blood_right_recovery.png";
            case 1180 -> mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.LEFT);
            case 1195 -> {
                if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.LEFT)
                    throw new IllegalStateException("Left-handed blood fixture did not synchronize");
                bloodSample(0, 0, 0);
            }
            case 1199 -> capture = "42_blood_left_reach.png";
            case 1202 -> capture = "43_blood_left_draw.png";
            case 1206 -> capture = "44_blood_left_face.png";
            case 1210 -> capture = "45_blood_left_recovery.png";
            // The first-person world-model pass can hide an item outside the
            // camera. Compare the same clip in third person before diagnosing
            // that as an item-rendering or mirroring failure.
            case 1225 -> {
                if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.LEFT)
                    throw new IllegalStateException("Left hand changed before third-person blood sample");
                mc.options.fov().set(35); mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT); bloodSample(0, 0, 0);
            }
            case 1229 -> capture = "46_blood_left_third_reach.png";
            case 1232 -> capture = "47_blood_left_third_draw.png";
            case 1236 -> capture = "48_blood_left_third_face.png";
            case 1240 -> capture = "49_blood_left_third_recovery.png";
            case 1250 -> mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.RIGHT);
            case 1265 -> {
                if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.RIGHT)
                    throw new IllegalStateException("Right-handed blood fixture did not synchronize");
                bloodSample(0, 0, 0);
            }
            case 1269 -> capture = "50_blood_right_third_reach.png";
            case 1272 -> capture = "51_blood_right_third_draw.png";
            case 1276 -> capture = "52_blood_right_third_face.png";
            case 1280 -> capture = "53_blood_right_third_recovery.png";
            // Sample X first-person and C's forced cinematic view.
            // Local visual playback only: these frames do not verify server timing.
            case 1295 -> { mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.RIGHT);
                mc.options.setCameraType(CameraType.FIRST_PERSON); mc.options.fov().set(70); }
            case 1310 -> com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 1);
            case 1312 -> capture = "86_x_first_prepare.png";
            case 1315 -> capture = "87_x_first_windup.png";
            case 1317 -> capture = "88_x_first_impact.png";
            case 1320 -> capture = "89_x_first_follow.png";
            case 1323 -> capture = "90_x_first_recover.png";
            case 1340 -> com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 2);
            case 1342 -> capture = "91_c_cinematic_prepare.png";
            case 1345 -> capture = "92_c_cinematic_windup.png";
            case 1350 -> capture = "93_c_cinematic_impact.png";
            case 1353 -> capture = "94_c_cinematic_follow.png";
            case 1357 -> capture = "95_c_cinematic_recover.png";
            case 1370 -> { com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT); mc.options.fov().set(35); }
            case 1380 -> com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 2);
            case 1382 -> capture = "96_c_cinematic_repeat_prepare.png";
            case 1385 -> capture = "97_c_cinematic_repeat_windup.png";
            case 1390 -> capture = "98_c_cinematic_repeat_impact.png";
            case 1393 -> capture = "99_c_cinematic_repeat_follow.png";
            case 1397 -> capture = "100_c_cinematic_repeat_recover.png";
            case 1415 -> { com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                mc.options.setCameraType(CameraType.FIRST_PERSON); mc.options.fov().set(70);
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.LEFT); }
            case 1430 -> { if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.LEFT)
                    throw new IllegalStateException("Left hand not synchronized for X sample");
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 1); }
            case 1432 -> capture = "101_x_left_first_prepare.png";
            case 1435 -> capture = "102_x_left_first_windup.png";
            case 1437 -> capture = "103_x_left_first_impact.png";
            case 1440 -> capture = "104_x_left_first_follow.png";
            case 1443 -> capture = "105_x_left_first_recover.png";
            case 1460 -> {
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.RIGHT);
                mc.getSingleplayerServer().execute(() -> {
                    var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                    VisualFixtureServer.startWeakSequence(player);
                });
            }
            case 1690 -> mc.getSingleplayerServer().execute(VisualFixtureServer::verifyWeakSequence);
            case 1710 -> {
                if (!VisualFixtureServer.weakSequenceVerified)
                    throw new IllegalStateException("Low-health C sequence was not verified");
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.RIGHT);
                com.stainkatana.katana.KatanaClientConfig.BLOOD_HAND_X.set(0.0);
                com.stainkatana.katana.KatanaClientConfig.BLOOD_HAND_Y.set(0.0);
                com.stainkatana.katana.KatanaClientConfig.BLOOD_HAND_Z.set(0.0);
                mc.getSingleplayerServer().execute(() -> {
                    var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                    VisualFixtureServer.startWeakFinisher(player);
                });
            }
            case 1740 -> mc.getSingleplayerServer().execute(VisualFixtureServer::verifyWeakFinisher);
            case 1760 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                VisualFixtureServer.startRemarkDuringZ(player);
            });
            case 1790 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                VisualFixtureServer.verifyRemarkDuringZ(player);
            });
            case 1810 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                VisualFixtureServer.startXWallCheck(player);
            });
            case 1830 -> mc.getSingleplayerServer().execute(() -> {
                var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                VisualFixtureServer.verifyXWallCheck(player);
            });
            case 1840 -> {
                if (impactCaptures != com.stainkatana.katana.CombatTuning.ultimateStrikeCount())
                    throw new IllegalStateException("Expected ten confirmed C screenshots, got " + impactCaptures);
                System.out.println("STAIN_C_CONFIRMED_IMPACT_CAPTURES=" + impactCaptures);
                System.out.println("STAIN_EFFECT_SAMPLES_DONE");
                if (net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) {
                    observeBetterCombatCombo();
                    mc.getSingleplayerServer().execute(() -> {
                        var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                        VisualFixtureServer.startBetterCombatCombo(player);
                    });
                }
            }
            case 1860 -> {
                if (net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) {
                    mc.options.setCameraType(CameraType.THIRD_PERSON_BACK);
                    mc.player.setYRot(0); mc.player.setXRot(0);
                    mc.options.keyAttack.setDown(true);
                }
            }
            case 2010 -> {
                if (net.minecraftforge.fml.ModList.get().isLoaded("bettercombat")) {
                    mc.options.keyAttack.setDown(false);
                    String[] expected = {"stainkatana:stain_serious_1", "stainkatana:stain_serious_2",
                            "stainkatana:stain_improved_3", "stainkatana:stain_improved_4"};
                    for (String id : expected) if (!bcHits.contains(id))
                        throw new IllegalStateException("Better Combat did not attack target with " + id + ": " + bcHits);
                    System.out.println("STAIN_BC_FOUR_IMPORTED_ATTACKS_HIT_TARGET=" + bcHits);
                    mc.getSingleplayerServer().execute(VisualFixtureServer::verifyBetterCombatCombo);
                }
            }
            // Inspect the complete imported lateral stroke in isolation as well
            // as the server-confirmed impact frames above. These are local
            // playback samples, not proof of damage or exact network timing.
            case 2020 -> {
                mc.options.keyAttack.setDown(false);
                mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT);
                mc.options.fov().set(35);
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                // The BC combo target can stand directly between the front
                // camera and the player. Remove only fixture mobs after all
                // server assertions, before sampling the isolated animation.
                mc.getSingleplayerServer().execute(() -> {
                    var player = mc.getSingleplayerServer().getPlayerList().getPlayer(mc.player.getUUID());
                    for (var mob : player.serverLevel().getEntitiesOfClass(
                            net.minecraft.world.entity.Mob.class, player.getBoundingBox().inflate(20))) mob.discard();
                });
            }
            case 2028 -> com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 7);
            case 2030 -> capture = "114_c_lateral_prepare.png";
            case 2032 -> capture = "115_c_lateral_windup.png";
            case 2034 -> capture = "116_c_lateral_contact_estimate.png";
            case 2036 -> capture = "117_c_lateral_follow.png";
            case 2038 -> capture = "118_c_lateral_recover.png";
            case 2045 -> {
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.LEFT);
            }
            case 2056 -> {
                if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.LEFT)
                    throw new IllegalStateException("Left hand not synchronized for C lateral sample");
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 7);
            }
            case 2058 -> capture = "119_c_left_lateral_prepare.png";
            case 2060 -> capture = "120_c_left_lateral_windup.png";
            case 2062 -> capture = "121_c_left_lateral_contact_estimate.png";
            case 2064 -> capture = "122_c_left_lateral_follow.png";
            case 2066 -> capture = "123_c_left_lateral_recover.png";
            // Isolated phase samples for the other lateral variants. These are
            // local playback samples, not proof of damage or exact network timing.
            case 2068 -> {
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.RIGHT);
            }
            case 2070 -> com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 8);
            case 2072 -> capture = "124_c_trial2_prepare.png";
            case 2074 -> capture = "125_c_trial2_windup.png";
            case 2076 -> capture = "126_c_trial2_contact.png";
            case 2078 -> capture = "127_c_trial2_recover.png";
            case 2084 -> {
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 10);
            }
            case 2086 -> capture = "128_c_kelvin1_prepare.png";
            case 2088 -> capture = "129_c_kelvin1_windup.png";
            case 2090 -> capture = "130_c_kelvin1_contact.png";
            case 2092 -> capture = "131_c_kelvin1_recover.png";
            case 2098 -> {
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 11);
            }
            case 2100 -> capture = "132_c_kelvin2_prepare.png";
            case 2102 -> capture = "133_c_kelvin2_windup.png";
            case 2104 -> capture = "134_c_kelvin2_contact.png";
            case 2106 -> capture = "135_c_kelvin2_recover.png";
            case 2112 -> {
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.LEFT);
            }
            case 2114 -> {
                if (mc.player.getMainArm() != net.minecraft.world.entity.HumanoidArm.LEFT)
                    throw new IllegalStateException("Left hand not synchronized for Kelvin C sample");
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), 10);
            }
            case 2116 -> capture = "136_c_kelvin1_left_prepare.png";
            case 2118 -> capture = "137_c_kelvin1_left_windup.png";
            case 2120 -> capture = "138_c_kelvin1_left_contact.png";
            case 2122 -> capture = "139_c_kelvin1_left_recover.png";
            case 2124 -> {
                mc.options.mainHand().set(net.minecraft.world.entity.HumanoidArm.RIGHT);
                com.stainkatana.katana.client.KatanaAnimations.play(mc.player.getId(), -1);
                System.out.println("STAIN_VISUAL_FIXTURE_FINISHED"); mc.stop(); }
            default -> { }
        }
    }
    /** Verify actual registry selection, not whether an audio device produced sound. */
    private static void verifyAbilitySoundSelection(Minecraft mc) {
        boolean betterCombat = net.minecraftforge.fml.ModList.get().isLoaded("bettercombat");
        try {
            var swing = com.stainkatana.katana.KatanaAbilities.class.getDeclaredMethod("katanaSwingSound");
            var stab = com.stainkatana.katana.KatanaAbilities.class.getDeclaredMethod("betterCombatSound", String.class, net.minecraft.sounds.SoundEvent.class);
            swing.setAccessible(true); stab.setAccessible(true);
            var fallback = net.minecraft.sounds.SoundEvents.PLAYER_ATTACK_SWEEP;
            var actualSwing = (net.minecraft.sounds.SoundEvent) swing.invoke(null);
            var actualStab = (net.minecraft.sounds.SoundEvent) stab.invoke(null, "rapier_stab", fallback);
            var registry = net.minecraftforge.registries.ForgeRegistries.SOUND_EVENTS;
            for (String path : new String[]{"katana_slash", "rapier_stab"}) {
                var soundId = new net.minecraft.resources.ResourceLocation("bettercombat", path);
                var actual = path.equals("katana_slash") ? actualSwing : actualStab;
                if (betterCombat) {
                    if (!registry.containsKey(soundId) || actual != registry.getValue(soundId))
                        throw new IllegalStateException("Better Combat sound not selected: " + soundId);
                    var ogg = new net.minecraft.resources.ResourceLocation("bettercombat", "sounds/" + path + "-01.ogg");
                    if (mc.getResourceManager().getResource(ogg).isEmpty())
                        throw new IllegalStateException("Better Combat sound asset missing: " + ogg);
                } else if (actual != fallback) {
                    throw new IllegalStateException("Expected vanilla fallback for " + soundId);
                }
            }
            System.out.println("STAIN_ABILITY_SOUND_SELECTION_VERIFIED=" + (betterCombat ? "bettercombat" : "vanilla"));
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("Unable to inspect ability sound selection", e);
        }
    }
    private static void bloodSample(double x, double y, double z) {
        com.stainkatana.katana.KatanaClientConfig.BLOOD_HAND_X.set(x);
        com.stainkatana.katana.KatanaClientConfig.BLOOD_HAND_Y.set(y);
        com.stainkatana.katana.KatanaClientConfig.BLOOD_HAND_Z.set(z);
        var player = Minecraft.getInstance().player;
        if (player == null) throw new IllegalStateException("No player for blood gesture sample");
        com.stainkatana.katana.client.KatanaAnimations.play(player.getId(), 0);
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
            // A queued screenshot can be rendered after several game ticks on
            // the software renderer. Record the actual animation tick at the
            // rendered frame; the script tick alone is not its pose timestamp.
            var layer = dev.kosmx.playerAnim.minecraftApi.PlayerAnimationAccess
                    .getPlayerAssociatedData(mc.player).get(new net.minecraft.resources.ResourceLocation("stainkatana", "abilities"));
            dev.kosmx.playerAnim.api.layered.IAnimation animation = layer;
            while (animation instanceof dev.kosmx.playerAnim.api.layered.ModifierLayer<?> modifier)
                animation = modifier.getAnimation();
            int clipTick = animation instanceof dev.kosmx.playerAnim.api.layered.KeyframeAnimationPlayer player
                    ? player.getTick() : -1;
            String row = name + "\t" + tick + "\t" + clipTick + "\t"
                    + mc.player.getMainArm() + "\t" + mc.options.getCameraType() + "\t"
                    + impactServerTick + "\t" + mc.level.getGameTime() + "\n";
            impactServerTick = -1;
            java.nio.file.Files.writeString(new File(directory, "capture-timing.tsv").toPath(), row,
                    java.nio.file.StandardOpenOption.CREATE, java.nio.file.StandardOpenOption.APPEND);
            System.out.println("STAIN_VISUAL_CAPTURE " + name + " tick=" + tick + " clipTick=" + clipTick);
        } catch (Exception e) { throw new IllegalStateException("Screenshot failed: " + name, e); }
    }
}
