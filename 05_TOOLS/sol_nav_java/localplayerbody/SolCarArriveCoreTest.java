package localplayerbody;

import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/** far_arrival, the database half, against copies of a real vehicles.db (each case on a fresh copy). Usage: SolCarArriveCoreTest <vehicles.db copy> */
public final class SolCarArriveCoreTest {
    private static int failed, passed;
    private static void ck(String name, boolean ok, Object detail) {
        System.out.println((ok ? "PASS " : "FAIL ") + name + (ok ? "" : " : " + detail));
        if (ok) passed++; else failed++;
    }
    private static Path fresh(Path src, String tag) throws Exception {
        Path p = Files.createTempFile("sol_arrive_" + tag + "_", ".db");
        Files.copy(src, p, StandardCopyOption.REPLACE_EXISTING);
        return p;
    }
    private static Connection open(Path p) throws Exception { return DriverManager.getConnection("jdbc:sqlite:" + p.toAbsolutePath()); }
    private static long count(Connection c) throws Exception { try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT COUNT(*), COUNT(DISTINCT id) FROM vehicles")) { r.next(); return r.getLong(1) * 1000 + r.getLong(2); } }
    private static Object[] row(Connection c, int id) throws Exception {
        try (Statement s = c.createStatement(); ResultSet r = s.executeQuery("SELECT wx, wy, x, y, data, worldversion, inMeta FROM vehicles WHERE id = " + id)) {
            if (!r.next()) return null;
            return new Object[] { r.getInt(1), r.getInt(2), r.getFloat(3), r.getFloat(4), r.getBytes(5), r.getInt(6), r.getBoolean(7) };
        }
    }
    private static String script(byte[] d) {
        String s = new String(d, 0, Math.min(d.length, 400), java.nio.charset.StandardCharsets.ISO_8859_1);
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("Base\\.[A-Za-z0-9_]{3,40}").matcher(s);
        return m.find() ? m.group() : "?";
    }

    // far_meta: rows kept "in meta" (his Bradley, row 6; a SmallCar, row 9), staged only when the main thread saw their VirtualVehicle
    private static boolean onlyPosChanged(byte[] d0, byte[] d1, float x, float y) {
        if (d0.length != d1.length) return false;
        for (int i = 0; i < d0.length; i++) if ((i < SolCarMoveCore.BLOB_X || i >= SolCarMoveCore.BLOB_Y + 4) && d0[i] != d1[i]) return false;
        ByteBuffer b = ByteBuffer.wrap(d1);
        return b.getFloat(SolCarMoveCore.BLOB_X) == x && b.getFloat(SolCarMoveCore.BLOB_Y) == y;
    }
    static void meta(Path src) throws Exception {
        for (int id : new int[] { 6, 9 }) {
            Path p = fresh(src, "meta" + id);
            try (Connection c = open(p)) {
                long before = count(c);
                Object[] was = row(c, id);
                String name = "kept in meta " + id + " (" + script((byte[]) was[4]) + ")";
                ck(name + ": the copy has it in meta", (boolean) was[6], was[6]);
                SolCarArriveCore.Staged no = SolCarArriveCore.stage(c, id, 7225.5f, 8190.5f, false);
                ck(name + ": without its VirtualVehicle seen: in_meta, untouched", "in_meta".equals(no.state) && Arrays.equals((byte[]) row(c, id)[4], (byte[]) was[4]) && no.data == null, no.state);
                SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, id, 7225.5f, 8190.5f, true);
                Object[] now = row(c, id);
                ck(name + ": with it: staged, and the stage says it was kept", "ok".equals(s.state) && s.inMeta, s.state);
                ck(name + ": one row, same count", count(c) == before && now != null, count(c));
                ck(name + ": x, y, wx, wy at the spot", (float) now[2] == 7225.5f && (float) now[3] == 8190.5f && (int) now[0] == 903 && (int) now[1] == 1023, Arrays.toString(Arrays.copyOf(now, 4)));
                ck(name + ": its inMeta flag is left as the game wrote it", (boolean) now[6], now[6]);
                ck(name + ": the blob changed only in its x/y floats; the bytes handed over are the table's", onlyPosChanged((byte[]) was[4], (byte[]) now[4], 7225.5f, 8190.5f) && Arrays.equals(s.data, (byte[]) now[4]) && s.worldVersion == (int) now[5], s.worldVersion);
            }
        }
        // a crash inside the transaction (Bradley): nothing written
        Path p = fresh(src, "metacrash");
        Object[] b6;
        try (Connection c = open(p)) {
            b6 = row(c, 6);
            c.setAutoCommit(false);
            SolCarArriveCore.Staged s = new SolCarArriveCore.Staged();
            ck("Bradley crash: the update ran inside the transaction", "ok".equals(SolCarArriveCore.stageInTransaction(c, 6, 7225.5f, 8190.5f, s, true)), null);
        }
        try (Connection c = open(p)) {
            Object[] after = row(c, 6);
            ck("Bradley crash before commit: where it was, bytes, flag and all", (float) after[2] == (float) b6[2] && (float) after[3] == (float) b6[3] && Arrays.equals((byte[]) after[4], (byte[]) b6[4]) && (boolean) after[6], Arrays.toString(Arrays.copyOf(after, 4)));
        }
        // a crash after the commit: at the spot, still kept in meta; the next start loads it in meta there (VehiclesDB2 loadVehiclesInMeta
        // reads WHERE inMeta=TRUE) and his chunk's own load brings it in (the chunk SELECT has no inMeta filter); one row either way
        p = fresh(src, "metaafter");
        try (Connection c = open(p)) { SolCarArriveCore.stage(c, 6, 7225.5f, 8190.5f, true); }
        try (Connection c = open(p)) {
            Object[] after = row(c, 6);
            int inChunk = 0, inMetaQ = 0;
            try (Statement st = c.createStatement(); ResultSet r = st.executeQuery("SELECT id FROM vehicles WHERE wx=903 AND wy=1023")) { while (r.next()) if (r.getInt(1) == 6) inChunk++; }
            try (Statement st = c.createStatement(); ResultSet r = st.executeQuery("SELECT id FROM vehicles WHERE inMeta=TRUE")) { while (r.next()) if (r.getInt(1) == 6) inMetaQ++; }
            ck("Bradley crash after commit: one row at the spot, found by the game's chunk query and by its in-meta query", (float) after[2] == 7225.5f && inChunk == 1 && inMetaQ == 1 && count(c) / 1000 == count(c) % 1000, inChunk + "," + inMetaQ);
        }
        // the kept copy's own save racing ours: its queued UPDATE (the game's SQL) runs after our commit -> one row, where the game put it
        p = fresh(src, "metarace");
        try (Connection c = open(p)) {
            Object[] w = row(c, 6);
            SolCarArriveCore.stage(c, 6, 7225.5f, 8190.5f, true);
            try (java.sql.PreparedStatement u = c.prepareStatement("UPDATE vehicles SET wx = ?, wy = ?, x = ?, y = ?, worldversion = ?, inMeta = ?, data = ? WHERE id=?")) {
                u.setInt(1, (int) w[0]); u.setInt(2, (int) w[1]); u.setFloat(3, (float) w[2]); u.setFloat(4, (float) w[3]); u.setInt(5, (int) w[5]); u.setBoolean(6, false); u.setBytes(7, (byte[]) w[4]); u.setInt(8, 6);
                u.executeUpdate();
            }
            Object[] after = row(c, 6);
            ck("race: the kept copy's save after ours: one row, back where the game says (we created nothing: meta_changed)", (float) after[2] == (float) w[2] && count(c) / 1000 == count(c) % 1000 && "meta_changed".equals(SolCarArriveCore.mainChoice(false, true, false, true)), Arrays.toString(Arrays.copyOf(after, 4)));
            // and if the kept copy's save ran BEFORE our stage: the row is no longer kept, so it is staged as a plain row and spawned
            SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, 6, 7225.5f, 8190.5f, true);
            ck("race the other way: its save first, then ours: a plain row (not kept), spawned from the table's bytes", "ok".equals(s.state) && !s.inMeta && "spawn".equals(SolCarArriveCore.mainChoice(false, s.inMeta, false, true)), s.state + "," + s.inMeta);
        }
        // every row of the save with its VirtualVehicle seen: all staged, one row each
        p = fresh(src, "metaall");
        try (Connection c = open(p)) {
            long before = count(c);
            int ok = 0, n = 0, kept = 0;
            java.util.List<Integer> ids = new java.util.ArrayList<>();
            try (Statement st = c.createStatement(); ResultSet r = st.executeQuery("SELECT id FROM vehicles ORDER BY id")) { while (r.next()) ids.add(r.getInt(1)); }
            for (int id : ids) {
                n++;
                SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, id, 100000f + id * 40, 100000f, true);
                if ("ok".equals(s.state)) ok++;
                if (s.inMeta) kept++;
            }
            ck("every row, VirtualVehicles seen: " + ok + " of " + n + " staged (" + kept + " kept in meta among them), one row each", ok == n && kept == 2 && count(c) == before, count(c));
        }
        // the main thread's choice
        ck("main: loaded by the game first -> loaded", "loaded".equals(SolCarArriveCore.mainChoice(true, true, true, true)) && "loaded".equals(SolCarArriveCore.mainChoice(true, false, false, true)), null);
        ck("main: kept, VirtualVehicle still there, square loaded -> spawn", "spawn".equals(SolCarArriveCore.mainChoice(false, true, true, true)), null);
        ck("main: kept, VirtualVehicle gone -> meta_changed (nothing created)", "meta_changed".equals(SolCarArriveCore.mainChoice(false, true, false, true)) && "meta_changed".equals(SolCarArriveCore.mainChoice(false, true, false, false)), null);
        ck("main: kept, he moved -> meta_deferred (she walks); a plain row -> deferred as before", "meta_deferred".equals(SolCarArriveCore.mainChoice(false, true, true, false)) && "deferred".equals(SolCarArriveCore.mainChoice(false, false, false, false)), null);
        ck("main: a plain row, loaded square -> spawn as before", "spawn".equals(SolCarArriveCore.mainChoice(false, false, false, true)), null);
    }

    // 20:44:59 live run: BaseVehicle.load was handed the blob from byte 0 ("newLimit > capacity: (19781 > 6264)", row 11). The game's own
    // read (VehiclesDB2$SQLStore.loadChunk) takes the serialise flag and the class id first, so load starts at byte 2. Replayed here on
    // every row: the buffer the game builds, its two header bytes, then IsoMovingObject.load's first reads (two floats, x, y, z, the
    // direction, the table flag), which must land on the row's own x and y; and the far_car parser on the same bytes.
    static void gameRead(Path src) throws Exception {
        Path p = fresh(src, "read");
        try (Connection c = open(p)) {
            int n = 0, good = 0, shiftedWrong = 0, parsed = 0;
            StringBuilder bad = new StringBuilder();
            boolean saw6 = false, saw9 = false, saw11 = false;
            try (Statement st = c.createStatement(); ResultSet r = st.executeQuery("SELECT id, x, y, data, worldversion, inMeta FROM vehicles ORDER BY id")) {
                while (r.next()) {
                    n++;
                    int id = r.getInt(1); float x = r.getFloat(2), y = r.getFloat(3); byte[] d = r.getBytes(4);
                    ByteBuffer bb = SolCarArriveCore.gameReadBuffer(d, SolCarArriveCore.VEHICLE_CLASS_ID);
                    boolean ok = bb != null && bb.position() == SolCarArriveCore.HEADER_BYTES && bb.limit() == d.length && bb.capacity() >= d.length;
                    if (ok) {
                        bb.getFloat(); bb.getFloat();
                        float lx = bb.getFloat(), ly = bb.getFloat(), lz = bb.getFloat();
                        int dir = bb.getInt();
                        int table = bb.get();
                        ok = lx == x && ly == y && Float.isFinite(lz) && dir >= 0 && dir < 9 && (table == 0 || table == 1)
                            && bb.position() == SolCarArriveCore.HEADER_BYTES + 25 && 10 == SolCarMoveCore.BLOB_X && 14 == SolCarMoveCore.BLOB_Y;
                    }
                    ByteBuffer wrong = ByteBuffer.wrap(d);                       // the 20:44 read: from byte 0
                    wrong.getFloat(); wrong.getFloat();
                    if (wrong.getFloat() != x || wrong.getFloat() != y) shiftedWrong++;
                    SolCarsNearCore.Car car = new SolCarsNearCore.Car();
                    SolCarsNearCore.decode(d, car);
                    if (car.script != null && car.quality >= 0) parsed++;
                    if (ok) good++; else bad.append(id).append(' ');
                    if (id == 6) saw6 = ok && r.getBoolean(6);
                    if (id == 9) saw9 = ok && r.getBoolean(6);
                    if (id == 11) {
                        saw11 = ok;
                        System.out.println("row 11 now: x,y " + x + "," + y + " length " + d.length + " worldversion " + r.getInt(5) + " inMeta " + r.getBoolean(6) + " header " + d[0] + "," + d[1]);
                    }
                }
            }
            ck("game's read on every row: header (1, 33), load from byte 2, x/y read where the row says, " + good + " of " + n + (bad.length() > 0 ? " bad: " + bad : ""), good == n && n > 0, bad);
            ck("in-meta rows 6 and 9 read the same way", saw6 && saw9, saw6 + "," + saw9);
            ck("row 11 (the 20:44 failure) reads cleanly from byte 2", saw11, null);
            ck("the 20:44 read from byte 0 misses x/y on every row (" + shiftedWrong + " of " + n + ")", shiftedWrong == n, shiftedWrong);
            ck("far_car's parser reads every row (" + parsed + " of " + n + ")", parsed == n, parsed);
            ck("a row the game would skip (serialise 0, or another class id) is not read", SolCarArriveCore.gameReadBuffer(new byte[] { 0, 33, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }, 33) == null
                && SolCarArriveCore.gameReadBuffer(new byte[] { 1, 32, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }, 33) == null, null);
        }
    }

    // the live load failed after the stage: the row goes back, in one transaction, exactly; a crash anywhere leaves one row
    static void rollback(Path src) throws Exception {
        int id = 11;
        Path p = fresh(src, "rb");
        try (Connection c = open(p)) {
            long before = count(c);
            Object[] was = row(c, id);
            SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, id, 7225.5f, 8190.5f);
            ck("rollback: row 11 staged", "ok".equals(s.state) && (float) row(c, id)[2] == 7225.5f, s.state);
            ck("rollback: the stage remembers the row as it was", s.fromWx == (int) was[0] && s.fromWy == (int) was[1] && Arrays.equals(s.fromData, (byte[]) was[4]), null);
            String rb = SolCarArriveCore.rollback(c, id, s);
            Object[] now = row(c, id);
            ck("rollback: rolled_back, wx/wy/x/y and every byte as before, one row", "rolled_back".equals(rb) && (int) now[0] == (int) was[0] && (int) now[1] == (int) was[1]
                && (float) now[2] == (float) was[2] && (float) now[3] == (float) was[3] && Arrays.equals((byte[]) now[4], (byte[]) was[4]) && count(c) == before, rb);
            ck("rollback: a second rollback finds nothing to undo (skipped, row unchanged)", "rollback_skipped".equals(SolCarArriveCore.rollback(c, id, s)) && Arrays.equals((byte[]) row(c, id)[4], (byte[]) was[4]), null);
            ck("rollback: autocommit restored", c.getAutoCommit(), null);
        }
        // the game rewrote the row after the stage (a save of its own): ours does not overwrite it
        p = fresh(src, "rbgame");
        try (Connection c = open(p)) {
            long before = count(c);
            SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, id, 7225.5f, 8190.5f);
            byte[] game = s.data.clone(); game[game.length - 1] ^= 1;
            try (java.sql.PreparedStatement u = c.prepareStatement("UPDATE vehicles SET data = ? WHERE id = ?")) { u.setBytes(1, game); u.setInt(2, id); u.executeUpdate(); }
            String rb = SolCarArriveCore.rollback(c, id, s);
            ck("rollback after the game's own save: skipped, the game's row stands, one row", "rollback_skipped".equals(rb) && Arrays.equals((byte[]) row(c, id)[4], game) && count(c) == before, rb);
        }
        // a crash between the stage and the rollback: one row, at the spot (the chunk's own load brings it there)
        p = fresh(src, "rbcrash1");
        try (Connection c = open(p)) { SolCarArriveCore.stage(c, id, 7225.5f, 8190.5f); }
        try (Connection c = open(p)) {
            Object[] after = row(c, id);
            int rows;
            try (Statement st = c.createStatement(); ResultSet r = st.executeQuery("SELECT COUNT(*) FROM vehicles WHERE id = " + id)) { r.next(); rows = r.getInt(1); }
            ck("crash between stage and rollback: exactly one row for 11, at the spot, one row per id", rows == 1 && (float) after[2] == 7225.5f && count(c) / 1000 == count(c) % 1000, rows);
        }
        // a crash inside the rollback's transaction: nothing of it written, still one row at the spot
        p = fresh(src, "rbcrash2");
        try (Connection c = open(p)) {
            SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, id, 7225.5f, 8190.5f);
            c.setAutoCommit(false);
            ck("crash in rollback: the update ran inside the transaction", SolCarArriveCore.rollbackInTransaction(c, id, s) == 1, null);
        }
        try (Connection c = open(p)) {
            Object[] after = row(c, id);
            ck("crash in rollback before commit: one row, still at the spot", (float) after[2] == 7225.5f && count(c) / 1000 == count(c) % 1000, Arrays.toString(Arrays.copyOf(after, 4)));
        }
        // a row kept in meta (the Bradley) rolls back the same way, its inMeta flag untouched
        p = fresh(src, "rbmeta");
        try (Connection c = open(p)) {
            Object[] was = row(c, 6);
            SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, 6, 7225.5f, 8190.5f, true);
            String rb = SolCarArriveCore.rollback(c, 6, s);
            Object[] now = row(c, 6);
            ck("rollback, kept in meta (6): back exactly, still kept", "rolled_back".equals(rb) && (float) now[2] == (float) was[2] && Arrays.equals((byte[]) now[4], (byte[]) was[4]) && (boolean) now[6], rb);
        }
    }
    public static void main(String[] a) throws Exception {
        Class.forName("org.sqlite.JDBC");
        Path src = Path.of(a[0]);
        // 1 his car: 5 (Base.SmallCar) into the loaded area at a spot 60 tiles from where the live run put it
        Path p = fresh(src, "his");
        try (Connection c = open(p)) {
            long before = count(c);
            Object[] was = row(c, 5);
            SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, 5, 7225.5f, 8190.5f);
            Object[] now = row(c, 5);
            ck("his car 5: staged", "ok".equals(s.state), s.state);
            ck("his car 5: one row, same count, no duplicate id", count(c) == before && now != null, count(c) + " vs " + before);
            ck("his car 5: x, y, wx, wy at the spot", (float) now[2] == 7225.5f && (float) now[3] == 8190.5f && (int) now[0] == 903 && (int) now[1] == 1023, Arrays.toString(Arrays.copyOf(now, 4)));
            byte[] d0 = (byte[]) was[4], d1 = (byte[]) now[4];
            ByteBuffer b = ByteBuffer.wrap(d1);
            boolean onlyPos = d0.length == d1.length;
            for (int i = 0; i < d0.length && onlyPos; i++) if ((i < SolCarMoveCore.BLOB_X || i >= SolCarMoveCore.BLOB_Y + 4) && d0[i] != d1[i]) onlyPos = false;
            ck("his car 5: the blob changed only in its x/y floats", onlyPos && b.getFloat(SolCarMoveCore.BLOB_X) == 7225.5f && b.getFloat(SolCarMoveCore.BLOB_Y) == 8190.5f, onlyPos);
            ck("his car 5: the bytes handed to the main thread are the table's own, with its worldversion", Arrays.equals(s.data, d1) && s.worldVersion == (int) now[5], s.worldVersion);
            ck("his car 5: the old place is remembered (" + s.fromX + "," + s.fromY + ")", Math.abs(s.fromX - (float) was[2]) < 0.01 && Math.abs(s.fromY - (float) was[3]) < 0.01, null);
            SolCarArriveCore.Staged again = SolCarArriveCore.stage(c, 5, 7225.5f, 8190.5f);
            ck("his car 5: staged again from where it now is: still one row", "ok".equals(again.state) && count(c) == before, again.state);
        }
        // 2 a crash in the middle of the transaction: nothing written
        p = fresh(src, "crash");
        Object[] before5;
        try (Connection c = open(p)) {
            before5 = row(c, 5);
            c.setAutoCommit(false);
            SolCarArriveCore.Staged s = new SolCarArriveCore.Staged();
            String st = SolCarArriveCore.stageInTransaction(c, 5, 7225.5f, 8190.5f, s);
            ck("crash: the update ran inside the transaction", "ok".equals(st), st);
        }                                                                         // closed without commit: the process died here
        try (Connection c = open(p)) {
            Object[] after = row(c, 5);
            ck("crash before commit: the row is where it was, bytes and all", (float) after[2] == (float) before5[2] && Arrays.equals((byte[]) after[4], (byte[]) before5[4]), Arrays.toString(Arrays.copyOf(after, 4)));
        }
        // 3 a crash after the commit, before the main thread: the row is at the spot (the chunk's own load brings it), one row
        p = fresh(src, "after");
        try (Connection c = open(p)) { SolCarArriveCore.stage(c, 5, 7225.5f, 8190.5f); }
        try (Connection c = open(p)) {
            Object[] after = row(c, 5);
            ck("crash after commit: the row is at the spot, one copy", (float) after[2] == 7225.5f && count(c) / 1000 == count(c) % 1000, count(c));
        }
        // 4 refusals: next to another car, a vehicle kept in meta (here the Bradley, row 6), an unknown id; each leaves the table as it was
        p = fresh(src, "refuse");
        try (Connection c = open(p)) {
            Object[] four = row(c, 4);
            long before = count(c);
            SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, 5, (float) four[2] + 2, (float) four[3]);
            ck("next to another car: spot_taken, nothing written", "spot_taken".equals(s.state) && (float) row(c, 5)[2] != (float) four[2] + 2 && s.data == null, s.state);
            Object[] six = row(c, 6);
            SolCarArriveCore.Staged m = SolCarArriveCore.stage(c, 6, 7225.5f, 8190.5f);
            ck("the Bradley (" + script((byte[]) six[4]) + ") is kept in meta: in_meta, untouched", "in_meta".equals(m.state) && Arrays.equals((byte[]) row(c, 6)[4], (byte[]) six[4]), m.state);
            ck("an id not in the table: not_in_db", "not_in_db".equals(SolCarArriveCore.stage(c, 99999, 1, 1).state), null);
            ck("refusals: the table is as it was", count(c) == before, count(c));
        }
        // 5 every row of the save, each kind of vehicle in it: staged to a free spot on a fresh copy, one row each time
        Set<String> kinds = new HashSet<>();
        int ok = 0, inMeta = 0, n = 0;
        p = fresh(src, "all");
        try (Connection c = open(p)) {
            long before = count(c);
            try (Statement st = c.createStatement(); ResultSet r = st.executeQuery("SELECT id, data, inMeta FROM vehicles ORDER BY id")) {
                java.util.List<Object[]> rows = new java.util.ArrayList<>();
                while (r.next()) rows.add(new Object[] { r.getInt(1), r.getBytes(2), r.getBoolean(3) });
                for (Object[] row : rows) {
                    n++;
                    int id = (int) row[0];
                    SolCarArriveCore.Staged s = SolCarArriveCore.stage(c, id, 100000f + id * 40, 100000f);
                    if ("ok".equals(s.state)) { ok++; kinds.add(script((byte[]) row[1])); }
                    else if ("in_meta".equals(s.state)) inMeta++;
                }
            }
            ck("every row: " + ok + " staged, " + inMeta + " kept in meta refused, of " + n + "; one row each, " + (count(c) / 1000) + " rows", ok + inMeta == n && count(c) == before, count(c));
        }
        System.out.println("kinds staged: " + kinds);
        meta(src);
        gameRead(src);
        rollback(src);
        System.out.println("SUMMARY pass=" + passed + " fail=" + failed);
        System.exit(failed == 0 ? 0 : 1);
    }
}
