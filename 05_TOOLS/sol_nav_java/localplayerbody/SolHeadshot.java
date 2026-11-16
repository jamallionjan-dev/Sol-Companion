package localplayerbody;

import java.util.ArrayDeque;
import java.util.Deque;

import me.zed_0xff.zombie_buddy.Exposer;
import me.zed_0xff.zombie_buddy.Patch;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.characters.BodyDamage.BodyPartType;
import zombie.characters.IsoGameCharacter;
import zombie.characters.IsoZombie;
import zombie.CombatManager;
import zombie.combat.HitReaction;
import zombie.combat.ShotDirection;
import zombie.core.physics.BallisticsController;
import zombie.core.physics.RagdollBodyPart;
import zombie.inventory.types.HandWeapon;

/** Optional Sol-only native firearm hit-part routing for the isolated lab. */
@Exposer.LuaClass
public final class SolHeadshot {
    private static volatile boolean enabled;
    private static volatile boolean oneShotKills;
    private static volatile String requestedFireMode = "single";
    private static final ThreadLocal<Deque<HitContext>> CONTEXT = ThreadLocal.withInitial(ArrayDeque::new);
    private static final ThreadLocal<Deque<CombatHitContext>> COMBAT_CONTEXT = ThreadLocal.withInitial(ArrayDeque::new);
    private static final ThreadLocal<Integer> NEXT_BURST_SHOT = ThreadLocal.withInitial(() -> 0);

    static final class ShotPlan {
        final RagdollBodyPart physicalPart;
        final BodyPartType damagePart;
        final String label;

        ShotPlan(RagdollBodyPart physicalPart, BodyPartType damagePart, String label) {
            this.physicalPart = physicalPart;
            this.damagePart = damagePart;
            this.label = label;
        }
    }

    private static final class HitContext {
        final IsoGameCharacter attacker;
        final HandWeapon weapon;
        final ShotPlan shotPlan;
        boolean damagePartPending;
        HitContext(IsoGameCharacter attacker, HandWeapon weapon, ShotPlan shotPlan) {
            this.attacker = attacker;
            this.weapon = weapon;
            this.shotPlan = shotPlan;
            this.damagePartPending = shotPlan != null && shotPlan.damagePart != null;
        }
    }

    private static final class CombatHitContext {
        final IsoGameCharacter attacker;
        final int targetId;
        final HandWeapon weapon;
        final ShotPlan shotPlan;

        CombatHitContext(IsoGameCharacter attacker, IsoGameCharacter target, HandWeapon weapon, ShotPlan shotPlan) {
            this.attacker = attacker;
            this.targetId = target == null ? -1 : target.getID();
            this.weapon = weapon;
            this.shotPlan = shotPlan;
        }
    }

    private SolHeadshot() {}

    @LuaMethod(name = "solHeadshotSet", global = true)
    public static void setEnabled(boolean value) { enabled = value; }

    @LuaMethod(name = "solHeadshotSetLethal", global = true)
    public static void setOneShotKills(boolean value) { oneShotKills = value; }

    @LuaMethod(name = "solHeadshotSetFireMode", global = true)
    public static void setFireMode(String value) {
        if ("single".equals(value) || "burst".equals(value)) {
            if (!value.equals(requestedFireMode)) NEXT_BURST_SHOT.set(0);
            requestedFireMode = value;
        }
    }

    static ShotPlan nextShotPlan() {
        if (!"burst".equals(requestedFireMode)) {
            return new ShotPlan(RagdollBodyPart.BODYPART_HEAD, BodyPartType.Head, "HEAD");
        }
        int shot = NEXT_BURST_SHOT.get();
        NEXT_BURST_SHOT.set((shot + 1) % 3);
        if (shot < 2) {
            return new ShotPlan(RagdollBodyPart.BODYPART_SPINE, BodyPartType.Torso_Upper, "CHEST");
        }
        return new ShotPlan(RagdollBodyPart.BODYPART_HEAD, BodyPartType.Head, "HEAD");
    }

    public static boolean begin(HandWeapon weapon, IsoGameCharacter attacker) {
        boolean firearm = false;
        if (weapon != null) {
            try { firearm = weapon.isRanged(); } catch (RuntimeException ignored) { }
        }
        boolean force = shouldActivate(enabled, attacker == null ? null : attacker.getClass().getName(), firearm);
        ShotPlan plan = force ? findCombatPlan(attacker, weapon) : null;
        if (force && plan == null) plan = nextShotPlan();
        CONTEXT.get().push(new HitContext(attacker, weapon, plan));
        return force;
    }

    static boolean shouldActivate(boolean on, String actorClass, boolean ranged) {
        return on && ranged && "survivorcompanion.bridge.SCNativeCompanion".equals(actorClass);
    }

    static boolean shouldOneShotKill(boolean on, String actorClass, boolean ranged,
                                     boolean zombieTarget, boolean alreadyDead) {
        return shouldActivate(on, actorClass, ranged) && zombieTarget && !alreadyDead;
    }

    static boolean shouldForceDamagePart(boolean active, boolean pending) {
        return active && pending;
    }

    static boolean shouldForceCombatPart(boolean active, int scopedTargetId, int callbackTargetId) {
        return active && scopedTargetId >= 0 && scopedTargetId == callbackTargetId;
    }

    /** Overrides only the initial body-part selection in the active Sol firearm hit. */
    public static BodyPartType forceDamagePart(BodyPartType original) {
        Deque<HitContext> stack = CONTEXT.get();
        HitContext current = stack.peek();
        if (current == null || !shouldForceDamagePart(current.shotPlan != null, current.damagePartPending)) return original;
        current.damagePartPending = false;
        logDamagePart(current, original);
        return current.shotPlan.damagePart;
    }

    public static void end(IsoGameCharacter attacker) {
        Deque<HitContext> stack = CONTEXT.get();
        HitContext current = stack.peek();
        if (current != null && current.attacker == attacker) stack.pop();
        if (stack.isEmpty()) CONTEXT.remove();
    }

    public static void beginCombatHit(HandWeapon weapon, IsoGameCharacter attacker, IsoGameCharacter target) {
        boolean firearm = false;
        if (weapon != null) {
            try { firearm = weapon.isRanged(); } catch (RuntimeException ignored) { }
        }
        boolean force = shouldActivate(enabled, attacker == null ? null : attacker.getClass().getName(), firearm)
                && target instanceof IsoZombie;
        ShotPlan plan = force ? findHitPlan(attacker, weapon) : null;
        if (force && plan == null) plan = nextShotPlan();
        COMBAT_CONTEXT.get().push(new CombatHitContext(attacker, target, weapon, plan));
    }

    public static void endCombatHit(IsoGameCharacter attacker, IsoGameCharacter target) {
        Deque<CombatHitContext> stack = COMBAT_CONTEXT.get();
        CombatHitContext current = stack.peek();
        int targetId = target == null ? -1 : target.getID();
        if (current != null && current.attacker == attacker && current.targetId == targetId) stack.pop();
        if (stack.isEmpty()) COMBAT_CONTEXT.remove();
    }

    /** Makes an engine-resolved Sol firearm hit lethal without changing player or weapon stats. */
    public static void finishCombatHit(IsoGameCharacter attacker, IsoGameCharacter target) {
        CombatHitContext current = currentCombatHit();
        int targetId = target == null ? -1 : target.getID();
        if (current == null || current.attacker != attacker || current.targetId != targetId
                || current.weapon == null || target == null) return;
        boolean ranged = false;
        try { ranged = current.weapon.isRanged(); } catch (RuntimeException ignored) { }
        if (!shouldOneShotKill(oneShotKills,
                attacker == null ? null : attacker.getClass().getName(), ranged,
                target instanceof IsoZombie, target.isDead())) return;
        float healthBefore = target.getHealth();
        target.Kill(current.weapon, attacker);
        System.out.println("[SolHeadshot] one-shot-kill target=" + targetId
                + " weapon=" + current.weapon.getFullType()
                + " plannedPart=" + (current.shotPlan == null ? "native" : current.shotPlan.label)
                + " healthBefore=" + healthBefore + " healthAfter=" + target.getHealth());
    }

    private static CombatHitContext currentCombatHit() {
        return COMBAT_CONTEXT.get().peek();
    }

    /** Reuses the same per-shot plan across IsoZombie.Hit and CombatManager.processHit. */
    static ShotPlan sharedPlan(Object expectedAttacker, Object expectedWeapon,
                               Object callbackAttacker, Object callbackWeapon,
                               ShotPlan plan) {
        return plan != null && expectedAttacker == callbackAttacker && expectedWeapon == callbackWeapon
                ? plan : null;
    }

    private static ShotPlan findCombatPlan(IsoGameCharacter attacker, HandWeapon weapon) {
        CombatHitContext combat = currentCombatHit();
        return combat == null ? null : sharedPlan(combat.attacker, combat.weapon, attacker, weapon, combat.shotPlan);
    }

    private static ShotPlan findHitPlan(IsoGameCharacter attacker, HandWeapon weapon) {
        HitContext hit = CONTEXT.get().peek();
        return hit == null ? null : sharedPlan(hit.attacker, hit.weapon, attacker, weapon, hit.shotPlan);
    }

    private static void logDamagePart(HitContext context, BodyPartType original) {
        String weapon = "?";
        if (context.weapon != null) {
            try { weapon = context.weapon.getFullType(); } catch (RuntimeException ignored) { }
        }
        System.out.println("[SolHeadshot] damagePart=" + context.shotPlan.damagePart
                + " selectedPart=" + context.shotPlan.label
                + " originalPart=" + original + " weapon=" + weapon);
    }

    private static String partName(int ordinal) {
        RagdollBodyPart[] parts = RagdollBodyPart.values();
        return ordinal >= 0 && ordinal < parts.length ? parts[ordinal].name() : "index_" + ordinal;
    }

    private static void logPhysicalPart(CombatHitContext context, String path, String original) {
        String weapon = "?";
        if (context.weapon != null) {
            try { weapon = context.weapon.getFullType(); } catch (RuntimeException ignored) { }
        }
        System.out.println("[SolHeadshot] selectedPart=" + context.shotPlan.label
                + " damagePart=" + context.shotPlan.damagePart
                + " originalPart=" + original + " path=" + path
                + " weapon=" + weapon + " target=" + context.targetId);
    }

    /** Replaces the physics-selected target part before CombatManager stores damage data. */
    public static int forceCachedTargetPart(int targetId, int original) {
        CombatHitContext current = currentCombatHit();
        if (current == null || current.shotPlan == null
                || !shouldForceCombatPart(true, current.targetId, targetId)) return original;
        logPhysicalPart(current, "ballistics-cache", partName(original));
        return current.shotPlan.physicalPart.ordinal();
    }

    /** Replaces the fallback body-part choice for non-camera-target firearm hits. */
    public static RagdollBodyPart forceFallbackTargetPart(RagdollBodyPart original) {
        CombatHitContext current = currentCombatHit();
        if (current == null || current.shotPlan == null) return original;
        logPhysicalPart(current, "reaction-fallback", original == null ? "null" : original.name());
        return current.shotPlan.physicalPart;
    }

    @Patch(className = "zombie.CombatManager", methodName = "processHit", strictMatch = true)
    public static final class CombatHitScope {
        @Patch.OnEnter
        public static void enter(@Patch.Argument(0) HandWeapon weapon,
                                 @Patch.Argument(1) IsoGameCharacter attacker,
                                 @Patch.Argument(2) IsoGameCharacter target) {
            SolHeadshot.beginCombatHit(weapon, attacker, target);
        }

        @Patch.OnExit
        public static void exit(@Patch.Argument(1) IsoGameCharacter attacker,
                                @Patch.Argument(2) IsoGameCharacter target) {
            SolHeadshot.finishCombatHit(attacker, target);
            SolHeadshot.endCombatHit(attacker, target);
        }
    }

    @Patch(className = "zombie.core.physics.BallisticsController", methodName = "getCachedTargetedBodyPart", strictMatch = true)
    public static final class CachedPhysicalPartSelection {
        @Patch.OnExit
        public static void exit(@Patch.Argument(0) int targetId,
                                @Patch.Return(readOnly = false) int part) {
            part = SolHeadshot.forceCachedTargetPart(targetId, part);
        }
    }

    @Patch(className = "zombie.CombatManager", methodName = "getBodyPart", strictMatch = true)
    public static final class FallbackPhysicalPartSelection {
        @Patch.OnExit
        public static void exit(@Patch.Argument(0) HitReaction reaction,
                                @Patch.Argument(1) ShotDirection direction,
                                @Patch.Return(readOnly = false) RagdollBodyPart part) {
            part = SolHeadshot.forceFallbackTargetPart(part);
        }
    }

    @Patch(className = "zombie.characters.IsoZombie", methodName = "Hit", strictMatch = true)
    public static final class ZombieHitScope {
        @Patch.OnEnter
        public static void enter(@Patch.Argument(0) HandWeapon weapon,
                                 @Patch.Argument(1) IsoGameCharacter attacker) {
            SolHeadshot.begin(weapon, attacker);
        }

        @Patch.OnExit
        public static void exit(@Patch.Argument(1) IsoGameCharacter attacker) {
            SolHeadshot.end(attacker);
        }
    }

    /** The first FromIndex in IsoZombie.Hit selects the body part; global random behavior stays untouched. */
    @Patch(className = "zombie.characters.BodyDamage.BodyPartType", methodName = "FromIndex", strictMatch = true)
    public static final class HeadPartSelection {
        @Patch.OnExit
        public static void exit(@Patch.Argument(0) int index,
                                @Patch.Return(readOnly = false) BodyPartType part) {
            part = SolHeadshot.forceDamagePart(part);
        }
    }
}
