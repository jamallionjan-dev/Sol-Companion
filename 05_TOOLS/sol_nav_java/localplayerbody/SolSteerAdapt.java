package localplayerbody;

import java.util.HashMap;
import java.util.Map;

import me.zed_0xff.zombie_buddy.Exposer;
import se.krka.kahlua.integration.annotations.LuaMethod;
import zombie.characters.IsoGameCharacter;
import zombie.characters.IsoPlayer;
import zombie.core.physics.CarController;
import zombie.vehicles.BaseVehicle;

/** Switch vehicle_steer_adapt. Every steering writer of Sol's (the follower, the route driver) assumes an ordinary car:
 *  positive steering turns the nose to the positive-angle side when driving forward. Some vehicles answer the other way,
 *  such as tracked vehicles that a mod turns from the steering value (Trucksmith on the Bradley). Here, for any vehicle
 *  Sol drives, the real turn is compared with the steering the game applied. When it keeps answering the wrong way,
 *  her steering is mirrored for that vehicle. No vehicle names: only what the vehicle does. */
@Exposer.LuaClass
public final class SolSteerAdapt {
    private static volatile boolean enabled = true;
    static final int DECIDE = 6, CAP = 10;
    static final long SAMPLE_MS = 100;
    static final double MIN_KMH = 3, MIN_STEER = 0.15, MIN_RATE = 0.05;

    static final class State { long t; double th; int evidence; boolean flip, hasOut; float out; }
    private static final Map<Short, State> STATES = new HashMap<>();

    private SolSteerAdapt() {}

    @LuaMethod(name = "solSteerAdaptSet", global = true)
    public static void setEnabled(boolean on) { enabled = on; if (!on) STATES.clear(); }

    @LuaMethod(name = "solSteerAdaptInfo", global = true)
    public static String info() {
        StringBuilder b = new StringBuilder();
        for (Map.Entry<Short, State> e : STATES.entrySet()) b.append(e.getKey()).append(e.getValue().flip ? ":mirrored " : ":normal ").append(e.getValue().evidence).append(' ');
        return b.toString().trim();
    }

    /** Public: called from the CarController.update patch, after the other writers. */
    public static void apply(CarController cc) {
        if (!enabled || cc == null) return;
        BaseVehicle car = cc.vehicleObject;
        if (car == null) return;
        IsoGameCharacter d = car.getDriver();
        if (d == null || (d instanceof IsoPlayer && ((IsoPlayer) d).isLocalPlayer())) return;
        State s = STATES.computeIfAbsent(car.getId(), k -> new State());
        boolean wheeled = steersByWheels(car);
        long now = System.currentTimeMillis();
        org.joml.Vector3f f = car.getForwardVector(new org.joml.Vector3f());
        double th = Math.atan2(f.z, f.x);
        if (s.t != 0 && now - s.t >= SAMPLE_MS) {
            double dt = (now - s.t) / 1000.0;
            if (dt < 0.5) s.evidence = learn(s.evidence, wrap(th - s.th) / dt, car.getCurrentSteering(), car.getCurrentSpeedKmHour());
            boolean was = s.flip;
            if (wheeled) {                                                // her steering is made for these: they set what "like a car" means
                if (Math.abs(s.evidence) >= DECIDE) reference = s.evidence > 0 ? 1 : -1;
            } else {
                s.flip = decide(s.flip, s.evidence, reference);
            }
            if (was != s.flip) System.out.println("[SolSteerAdapt] vehicle " + car.getId() + " " + car.getScriptName() + (s.flip ? " turns the other way: mirroring her steering" : " turns like a car again"));
            s.t = now; s.th = th;
        } else if (s.t == 0) { s.t = now; s.th = th; }
        CarController.ClientControls c = cc.clientControls;
        float raw = c.steering;
        if (s.hasOut && Math.abs(raw - s.out) < 1e-6f) return;           // already this frame's answer: never mirror twice
        float out = s.flip ? -raw : raw;
        c.steering = out; s.out = out; s.hasOut = true;
    }

    /** Which way an ordinary car answers, measured on cars that steer by their wheels. Until one is measured, the tracker's own convention. */
    private static volatile int reference = 1;

    /** A vehicle with a steered wheel turns natively, the way her steering assumes. Only vehicles without one are ever mirrored. */
    static boolean steersByWheels(BaseVehicle car) {
        zombie.scripting.objects.VehicleScript sc = car.getScript();
        if (sc == null) return true;
        for (int i = 0; i < sc.getWheelCount(); i++) { zombie.scripting.objects.VehicleScript.Wheel w = sc.getWheel(i); if (w != null && w.front) return true; }
        return sc.getWheelCount() == 0;
    }

    /** Mirror once the evidence clearly says this vehicle answers against the reference; go back once it clearly agrees. */
    static boolean decide(boolean flip, int evidence, int reference) {
        int agree = evidence * reference;
        if (agree <= -DECIDE) return true;
        if (agree >= DECIDE) return false;
        return flip;
    }

    /** One sample: +1 when the turn follows the applied steering like a car, -1 when it goes the other way, 0 when it says nothing. */
    static int learn(int evidence, double yawRate, double appliedSteering, double kmh) {
        if (Math.abs(kmh) < MIN_KMH || Math.abs(appliedSteering) < MIN_STEER || Math.abs(yawRate) < MIN_RATE) return evidence;
        double like = Math.signum(yawRate) * Math.signum(appliedSteering) * Math.signum(kmh);
        return (int) Math.max(-CAP, Math.min(CAP, evidence + (like > 0 ? 1 : -1)));
    }

    static double wrap(double a) { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; }
}
