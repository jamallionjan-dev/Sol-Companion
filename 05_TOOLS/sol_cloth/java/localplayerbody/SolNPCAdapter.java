package localplayerbody;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

/**
 * Sol: which NPC gets Sol's body (s161 body_scope, 2026-11-17).
 *
 * SolNPCAdapter$E (an exit advice on PlayerChoice.isEnabled and AppearanceProfiles.renderable) turns the answer to
 * "yes" when ok(character) says so. The shipped ok() said yes for EVERY living female NPC, so female NPCs of other mods
 * took Sol's body and her under-cloth chest. Jamal 2026-11-17: the chest fix must be Sol's only.
 * SCActor.lua marks Sol (and only her) with modData SolAppearanceVSGirlBody = true; with the switch on, ok() also
 * requires that mark. Switch: body_scope=on in SolFixes_LAB.txt, else SolFixes_MAIN.txt, read once per session;
 * anything else keeps the old answer (any living female NPC).
 */
public final class SolNPCAdapter {
    private static Boolean scoped;

    public SolNPCAdapter() {}

    public static boolean ok(zombie.characters.IsoGameCharacter c) {
        if (!(c instanceof zombie.characters.IsoPlayer)) return false;
        zombie.characters.IsoPlayer p = (zombie.characters.IsoPlayer) c;
        if (!p.isNpc() || !p.isFemale() || c.isDead()) return false;
        if (!scoped()) return true;
        try {
            Object mark = c.getModData().rawget("SolAppearanceVSGirlBody");
            return Boolean.TRUE.equals(mark);
        } catch (Throwable t) {
            return false;
        }
    }

    static synchronized boolean scoped() {
        if (scoped != null) return scoped;
        boolean on = false;
        try {
            String dir = zombie.ZomboidFileSystem.instance.getCacheDir();
            Path lab = Path.of(dir, "Lua", "SolFixes_LAB.txt"), main = Path.of(dir, "Lua", "SolFixes_MAIN.txt");
            String v = Files.isRegularFile(lab) ? value(lab) : null;
            if (v == null && Files.isRegularFile(main)) v = value(main);
            on = "on".equals(v);
        } catch (Throwable t) {
            on = false;
        }
        scoped = on;
        System.out.println("[SolNPCAdapter] switch body_scope " + (on ? "ON: Sol's body only for Sol" : "OFF"));
        return on;
    }

    private static String value(Path file) throws Exception {
        List<String> lines = Files.readAllLines(file);
        String found = null;
        for (String line : lines) {
            String s = line.trim();
            if (s.startsWith("body_scope=")) found = s.substring("body_scope=".length()).trim().toLowerCase(Locale.ROOT);
        }
        return found;
    }
}
