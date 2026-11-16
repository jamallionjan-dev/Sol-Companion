package localplayerbody;

public final class SolHeadshotTest {
    private static int checks;
    private static void check(String name, boolean value) {
        checks++;
        if (!value) throw new AssertionError(name);
        System.out.println("PASS " + name);
    }
    public static void main(String[] args) {
        String sol = "survivorcompanion.bridge.SCNativeCompanion";
        check("enabled Sol firearm", SolHeadshot.shouldActivate(true, sol, true));
        check("disabled switch preserves vanilla", !SolHeadshot.shouldActivate(false, sol, true));
        check("other actors preserve vanilla", !SolHeadshot.shouldActivate(true, "zombie.characters.IsoPlayer", true));
        check("Sol melee preserves vanilla", !SolHeadshot.shouldActivate(true, sol, false));
        check("Sol firearm hit kills a living zombie only when lethal switch is on",
                SolHeadshot.shouldOneShotKill(true, sol, true, true, false));
        check("lethal switch off preserves engine damage",
                !SolHeadshot.shouldOneShotKill(false, sol, true, true, false));
        check("player firearm damage is unchanged",
                !SolHeadshot.shouldOneShotKill(true, "zombie.characters.IsoPlayer", true, true, false));
        check("Sol melee damage is unchanged",
                !SolHeadshot.shouldOneShotKill(true, sol, false, true, false));
        check("Sol shots do not instantly kill non-zombies",
                !SolHeadshot.shouldOneShotKill(true, sol, true, false, false));
        check("dead zombies are not processed again",
                !SolHeadshot.shouldOneShotKill(true, sol, true, true, true));
        check("active Sol hit selects scoped damage part", SolHeadshot.shouldForceDamagePart(true, true));
        check("body-part override is consumed once", !SolHeadshot.shouldForceDamagePart(true, false));
        check("non-Sol hits retain native body part", !SolHeadshot.shouldForceDamagePart(false, true));
        check("Sol physical hit forces only its scoped target", SolHeadshot.shouldForceCombatPart(true, 42, 42));
        check("other target keeps native physical part", !SolHeadshot.shouldForceCombatPart(true, 42, 43));
        check("inactive physical switch keeps native part", !SolHeadshot.shouldForceCombatPart(false, 42, 42));
        Object solActor = new Object();
        Object otherActor = new Object();
        Object weaponA = new Object();
        Object weaponB = new Object();
        SolHeadshot.ShotPlan shared = new SolHeadshot.ShotPlan(
                zombie.core.physics.RagdollBodyPart.BODYPART_HEAD,
                zombie.characters.BodyDamage.BodyPartType.Head, "HEAD");
        check("nested hit hooks share plan for same actor and weapon",
                SolHeadshot.sharedPlan(solActor, weaponA, solActor, weaponA, shared) == shared);
        check("nested hooks do not share plan across actors",
                SolHeadshot.sharedPlan(solActor, weaponA, otherActor, weaponA, shared) == null);
        check("nested hooks do not share plan across weapons",
                SolHeadshot.sharedPlan(solActor, weaponA, solActor, weaponB, shared) == null);
        check("missing parent plan is not shared",
                SolHeadshot.sharedPlan(solActor, weaponA, solActor, weaponA, null) == null);
        SolHeadshot.setFireMode("single");
        SolHeadshot.ShotPlan singleA = SolHeadshot.nextShotPlan();
        check("single-shot selects physical Head", singleA.physicalPart == zombie.core.physics.RagdollBodyPart.BODYPART_HEAD);
        check("single-shot damages Head", singleA.damagePart == zombie.characters.BodyDamage.BodyPartType.Head);
        check("single-shot continues selecting Head", SolHeadshot.nextShotPlan().damagePart == zombie.characters.BodyDamage.BodyPartType.Head);
        SolHeadshot.setFireMode("burst");
        SolHeadshot.ShotPlan burst1 = SolHeadshot.nextShotPlan();
        SolHeadshot.ShotPlan burst2 = SolHeadshot.nextShotPlan();
        SolHeadshot.ShotPlan burst3 = SolHeadshot.nextShotPlan();
        check("burst hit 1 selects physical Spine", burst1.physicalPart == zombie.core.physics.RagdollBodyPart.BODYPART_SPINE);
        check("burst hit 1 damages upper torso", burst1.damagePart == zombie.characters.BodyDamage.BodyPartType.Torso_Upper);
        check("burst hit 2 selects physical Spine", burst2.physicalPart == zombie.core.physics.RagdollBodyPart.BODYPART_SPINE);
        check("burst hit 2 damages upper torso", burst2.damagePart == zombie.characters.BodyDamage.BodyPartType.Torso_Upper);
        check("burst hit 3 selects physical Head", burst3.physicalPart == zombie.core.physics.RagdollBodyPart.BODYPART_HEAD);
        check("burst hit 3 damages Head", burst3.damagePart == zombie.characters.BodyDamage.BodyPartType.Head);
        check("burst pattern repeats chest chest head", SolHeadshot.nextShotPlan().damagePart == zombie.characters.BodyDamage.BodyPartType.Torso_Upper);
        SolHeadshot.setFireMode("single");
        SolHeadshot.setFireMode("burst");
        check("changing mode resets burst pattern", SolHeadshot.nextShotPlan().damagePart == zombie.characters.BodyDamage.BodyPartType.Torso_Upper);
        System.out.println(checks + " passed");
    }
}
