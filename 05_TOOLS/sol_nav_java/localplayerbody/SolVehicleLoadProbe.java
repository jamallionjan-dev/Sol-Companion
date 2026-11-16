package localplayerbody;

import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Offline proof for far_car state 3 (s92): the exact bytes SolCarArrive hands to the game, through the game's own classes, with no world.
 *   For every row of a COPY of a save's vehicles.db (opened read only):
 *     A  SolCarArriveCore.stage on a second scratch copy (the same transaction the streamer runs), so the bytes are the patched ones;
 *     B  SolCarArriveCore.gameReadBuffer(data, 33): the two header bytes the game's SQLStore.loadChunk reads before vehicleLoaded;
 *     C  new BaseVehicle(cell) with the cell the game would pass (null here: no IsoWorld; recorded as such);
 *     D  BaseVehicle.load(bb, worldVersion) from byte 2 (the 20:44:59 live failure was load from byte 0);
 *     E  the position the loaded object reports equals the staged spot, and the bytes read equal the blob's length (nothing left over / no overrun).
 *   Steps that need the running world (setSquare on a live chunk square, addToWorld, createPhysics, PathfindNative.addVehicle,
 *   VirtualVehicleManager.removeFromMeta) are NOT run here; the report says so per row.
 * Optional bootstrap: with -Dsol.scripts=1 it tries to load the game's vehicle scripts first (ZomboidFileSystem + ScriptManager) so that
 * load() resolves the vehicle script as in the game; how far that bootstrap got is printed.
 * usage: SolVehicleLoadProbe <copy of vehicles.db> <scratch dir>   (refuses a path inside a profile's Saves folder)
 */
public final class SolVehicleLoadProbe {
    private SolVehicleLoadProbe() {}

    static String firstFrames(Throwable t, int n) {
        StringBuilder b = new StringBuilder(String.valueOf(t));
        StackTraceElement[] st = t.getStackTrace();
        for (int i = 0; i < Math.min(n, st.length); i++) b.append(" | ").append(st[i]);
        Throwable c = t.getCause();
        if (c != null && c != t) b.append(" || cause ").append(c);
        return b.toString();
    }

    /** the game resolves the script after load (addToWorld / scriptReloaded): here only whether ScriptManager knows the name */
    static String scriptKnown(String name) {
        try { return zombie.scripting.ScriptManager.instance.getVehicle(name) != null ? " (script known)" : " (script NOT known)"; }
        catch (Throwable t) { return " (script lookup " + t + ")"; }
    }

    static String bootstrap() {
        StringBuilder out = new StringBuilder();
        for (String n : new String[] { "zombie.core.random.RandStandard", "zombie.core.random.RandLua" }) {     // Rand.Next needs its randomizer (ServerOptions.<init>)
            try { Object i = Class.forName(n).getField("INSTANCE").get(null); i.getClass().getMethod("init").invoke(i); out.append(n.substring(n.lastIndexOf('.') + 1)).append(".init=ok; "); }
            catch (Throwable t) { out.append(n).append(" ").append(t).append("; "); }
        }
        try {
            Class<?> zfs = Class.forName("zombie.ZomboidFileSystem");
            Object inst = zfs.getField("instance").get(null);
            out.append("ZomboidFileSystem.instance=").append(inst != null);
            try { zfs.getMethod("init").invoke(inst); out.append(" init=ok"); }
            catch (Throwable t) { out.append(" init=").append(firstFrames(t instanceof java.lang.reflect.InvocationTargetException ? t.getCause() : t, 4)); }
        } catch (Throwable t) { out.append("ZomboidFileSystem: ").append(firstFrames(t, 3)); }
        try { zombie.Lua.LuaManager.init(); out.append("; LuaManager.init=ok"); }                 // SandboxOptions.<clinit> runs the game's sandbox Lua
        catch (Throwable t) { out.append("; LuaManager.init=").append(firstFrames(t, 3)); }
        if (!"1".equals(System.getProperty("sol.scripts"))) return out.toString();
        try { zombie.core.Translator.loadFiles(); out.append("; Translator.loadFiles=ok"); }       // item display names (InventoryItem.getActualWeightUnmodded)
        catch (Throwable t) { out.append("; Translator.loadFiles=").append(firstFrames(t, 3)); }
        try { if (zombie.SoundManager.instance == null) zombie.SoundManager.instance = new zombie.DummySoundManager(); out.append("; sound=dummy"); }   // an animal in a trailer has an emitter
        catch (Throwable t) { out.append("; sound=").append(firstFrames(t, 3)); }
        try { zombie.core.physics.Bullet.init(); out.append("; Bullet.init=ok"); }                  // VehicleScript.Loaded defines each script in Bullet
        catch (Throwable t) { out.append("; Bullet.init=").append(firstFrames(t, 3)); }
        String mods = System.getProperty("sol.mods");                                           // the save's vehicle mods, from the scratch home's mods folder
        if (mods != null && !mods.isEmpty()) {
            try { zombie.ZomboidFileSystem.instance.loadMods(new java.util.ArrayList<>(java.util.Arrays.asList(mods.split(";")))); out.append("; loadMods=ok ").append(mods); }
            catch (Throwable t) { out.append("; loadMods=").append(firstFrames(t, 4)); }
        }
        try {
            Class<?> sm = Class.forName("zombie.scripting.ScriptManager");
            Object inst = sm.getField("instance").get(null);
            try { sm.getMethod("Load").invoke(inst); out.append("; ScriptManager.Load=ok"); }
            catch (Throwable t) { out.append("; ScriptManager.Load=").append(firstFrames(t instanceof java.lang.reflect.InvocationTargetException ? t.getCause() : t, 4)); }
            try {
                Object list = sm.getMethod("getAllVehicleScripts").invoke(inst);
                out.append("; vehicle scripts=").append(list instanceof java.util.Collection ? ((java.util.Collection<?>) list).size() : -1);
            } catch (Throwable t) { out.append("; getAllVehicleScripts=").append(firstFrames(t, 2)); }
        } catch (Throwable t) { out.append("; ScriptManager: ").append(firstFrames(t, 3)); }
        // the save's item / entity ids: a COPY of its WorldDictionary.bin under the scratch cache dir, as Saves/Sandbox/<sol.world>
        String world = System.getProperty("sol.world");
        if (world != null) {
            try {
                zombie.core.Core.gameSaveWorld = world;
                zombie.core.Core.getInstance().setGameMode("Sandbox");
                out.append("; save dir=").append(zombie.ZomboidFileSystem.instance.getCurrentSaveDir());
                zombie.world.WorldDictionary.init();
                out.append("; WorldDictionary.init=ok");
            } catch (Throwable t) { out.append("; WorldDictionary.init=").append(firstFrames(t, 5)); }
        }
        return out.toString();
    }

    public static void main(String[] a) throws Exception {
        if (a.length < 2) { System.out.println("usage: SolVehicleLoadProbe <copy of vehicles.db> <scratch dir>"); System.exit(2); }
        Path src = Paths.get(a[0]).toAbsolutePath(), dir = Paths.get(a[1]).toAbsolutePath();
        if (src.toString().replace('\\', '/').toLowerCase().contains("/zomboid/saves/")) { System.out.println("REFUSED: give a COPY, not the save's own file"); System.exit(2); }
        Files.createDirectories(dir);
        Path stageCopy = dir.resolve("probe_stage.db");
        Files.copy(src, stageCopy, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        Class.forName("org.sqlite.JDBC");
        System.out.println("BOOTSTRAP " + bootstrap());                                // run with the game folder as the working directory (read only)

        int vehicleClassId;
        try { vehicleClassId = zombie.iso.IsoObject.getFactoryVehicle().getClassID(); System.out.println("IsoObject.getFactoryVehicle().getClassID()=" + vehicleClassId); }
        catch (Throwable t) { vehicleClassId = SolCarArriveCore.VEHICLE_CLASS_ID; System.out.println("factory id not readable offline (" + firstFrames(t, 2) + "), using " + vehicleClassId); }

        Map<String, Integer> tally = new LinkedHashMap<>();
        List<String> lines = new ArrayList<>();
        int rows = 0;
        try (Connection ro = DriverManager.getConnection("jdbc:sqlite:file:" + src.toString().replace('\\', '/') + "?mode=ro");
             Connection rw = DriverManager.getConnection("jdbc:sqlite:" + stageCopy)) {
            List<Object[]> all = new ArrayList<>();
            try (PreparedStatement q = ro.prepareStatement("SELECT id, x, y, inMeta, worldversion, data FROM vehicles ORDER BY id"); ResultSet r = q.executeQuery()) {
                while (r.next()) all.add(new Object[] { r.getInt(1), r.getFloat(2), r.getFloat(3), r.getBoolean(4), r.getInt(5), r.getBytes(6) });
            }
            for (Object[] row : all) {
                rows++;
                int id = (Integer) row[0]; float x = (Float) row[1], y = (Float) row[2]; boolean meta = (Boolean) row[3]; int wv = (Integer) row[4]; byte[] data = (byte[]) row[5];
                String verdict;
                StringBuilder why = new StringBuilder();
                // A: the stage, 1.5 tiles east of where it is (a spot no other row holds unless one is parked there)
                float toX = x + 1.5f, toY = y;
                SolCarArriveCore.Staged s = SolCarArriveCore.stage(rw, id, toX, toY, true);
                byte[] bytes = "ok".equals(s.state) ? s.data : data;
                why.append("stage=").append(s.state);
                // B
                ByteBuffer bb = SolCarArriveCore.gameReadBuffer(bytes, vehicleClassId);
                if (bb == null) {
                    verdict = "skipped_by_game";                                   // serialise=0 or not the vehicle class: SQLStore.loadChunk skips it, so does stage
                    why.append(" header=").append(bytes == null ? "null" : (bytes.length > 1 ? (bytes[0] + "," + bytes[1]) : "short")).append(" len=").append(bytes == null ? 0 : bytes.length);
                } else {
                    zombie.vehicles.BaseVehicle v = null;
                    try {
                        v = new zombie.vehicles.BaseVehicle(null);                 // C
                        why.append(" new=ok");
                    } catch (Throwable t) { why.append(" new=").append(firstFrames(t, 5)); }
                    if (v == null) verdict = "construct_failed";
                    else {
                        try {
                            v.load(bb, wv);                                          // D: from byte 2, exactly as SolCarArrive.main
                            int left = bb.limit() - bb.position();
                            float lx = v.getX(), ly = v.getY();
                            boolean at = Math.abs(lx - ("ok".equals(s.state) ? toX : x)) < 0.01f && Math.abs(ly - ("ok".equals(s.state) ? toY : y)) < 0.01f;
                            why.append(" load=ok read=").append(bb.position()).append("/").append(bb.limit()).append(" left=").append(left)
                               .append(" script=").append(v.getScriptName()).append(scriptKnown(v.getScriptName())).append(" pos=").append(lx).append(",").append(ly).append(at ? " (at spot)" : " (NOT at spot)");
                            verdict = left == 0 && at ? "load_ok" : (at ? "load_ok_bytes_left" : "load_ok_wrong_pos");
                        } catch (Throwable t) {
                            verdict = "load_threw";
                            why.append(" load=").append(firstFrames(t, 6)).append(" at=").append(bb.position());
                        }
                    }
                }
                if (bb != null && "1".equals(System.getProperty("sol.control", "1"))) {        // control: the 20:44:59 mistake, load from byte 0
                    try {
                        ByteBuffer b0 = ByteBuffer.allocate(Math.max(32768, bytes.length)); b0.put(bytes); b0.flip();
                        new zombie.vehicles.BaseVehicle(null).load(b0, wv);
                        why.append(" control(byte0)=loaded?!");
                        tally.merge("control_byte0_loaded", 1, Integer::sum);
                    } catch (Throwable t) { why.append(" control(byte0)=threw ").append(String.valueOf(t).replace('\n', ' ')); tally.merge("control_byte0_threw", 1, Integer::sum); }
                }
                if (meta) why.append(" inMeta=1");
                tally.merge(verdict, 1, Integer::sum);
                lines.add(id + " " + verdict + " len=" + (data == null ? 0 : data.length) + " " + why);
            }
        }
        for (String l : lines) System.out.println(l);
        System.out.println("PROBE rows=" + rows + " " + tally + " (source opened read only; stage ran on " + stageCopy + ")");
        System.out.println("NOT RUN OFFLINE: setSquare/setCurrent on a live chunk square, chunk.vehicles.add, addToWorld (setVehicleLoaded, createPhysics,"
            + " PathfindNative.addVehicle), VirtualVehicleManager.removeFromMeta, updateVehicle. These need the running world.");
    }
}
