package localplayerbody;

/** What counts as a garden, and what she keeps of it. Runs against the game's jar, without a world. */
public final class SolGardensTest {
    static int fails;
    static void check(String name, boolean ok, Object detail) {
        System.out.println((ok ? "PASS " : "FAIL ") + name + (ok ? "" : " : " + detail));
        if (!ok) fails++;
    }
    public static void main(String[] a) {
        for (String s : new String[] { "vegetation_farming_01_3", "vegetation_farming_dead_02_1", "vegetation_gardening_01_7", "vegetation_farm_01_12" }) check("crops: " + s, SolStations.isGardenSprite(s), s);
        for (String s : new String[] { "vegetation_foliage_01_1", "location_farm_accesories_01_3", "walls_exterior_house_01_4", "", null }) check("not crops: " + s, !SolStations.isGardenSprite(s), s);
        SolStations.noteGarden(1003, 2005); SolStations.noteGarden(1004, 2006);
        String one = SolStations.gardens(1000, 2000, 5);
        check("one garden, one place", one.split(";").length == 1 && one.startsWith("1003,2005"), one);
        SolStations.noteGarden(1500, 2000);
        String two = SolStations.gardens(1490, 2000, 5);
        check("the nearest comes first", two.startsWith("1500,2000") && two.split(";").length == 2, two);
        check("as many as asked", SolStations.gardens(1490, 2000, 1).split(";").length == 1, "");
        SolStations.forget();
        check("forgotten with her", SolStations.gardens(1000, 2000, 5).isEmpty(), "");
        System.out.println("SUMMARY " + (fails == 0 ? "ALL PASS" : "FAILED " + fails));
        System.exit(fails == 0 ? 0 : 1);
    }
}
