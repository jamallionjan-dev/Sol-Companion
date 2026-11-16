package localplayerbody;
public class SolStationsTowns { static int fails; static void ck(String n, boolean c, String d) { System.out.println((c ? "PASS " : "FAIL ") + n + (c ? "" : " : " + d)); if (!c) fails++; }
 public static void main(String[] a) {
  // towns across the map, none near where it was first tried
  SolStations.remember(10660, 10010, 500, "gas2go"); SolStations.remember(10663, 10010, 480, "");           // Muldraugh: two pumps, one named
  SolStations.remember(11920, 6900, 300, "fossoil");                                                         // West Point
  SolStations.remember(8100, 11640, 200, "");                                                                // Rosewood, a brand the game does not name
  SolStations.remember(6500, 5300, 0, "gas2go");                                                             // Riverside: pumped dry
  SolStations.remember(12640, 1800, 900, "fossoil");                                                         // Louisville
  String s;
  s = SolStations.nearest(10700, 10100); ck("from Muldraugh: Muldraugh", s.startsWith("1066") && s.endsWith(",gas2go"), s);
  s = SolStations.nearest(11900, 7000); ck("from West Point: West Point", s.startsWith("11920,6900,") && s.endsWith(",fossoil"), s);
  s = SolStations.nearest(8000, 11500); ck("from Rosewood: Rosewood, with no name", s.equals("8100,11640,200,"), s);
  s = SolStations.nearest(12500, 1700); ck("from Louisville: Louisville", s.startsWith("12640,1800,"), s);
  s = SolStations.nearest(6500, 5300); ck("the dry station at Riverside is skipped", !s.startsWith("6500,"), s);
  s = SolStations.nearest(10664, 10011); ck("the unnamed pump takes its station's name", s.startsWith("10663,10010,") && s.endsWith(",gas2go"), s);
  SolStations.remember(10670, 10015, 300, "gas2go");                                                          // a third pump at Muldraugh
  s = SolStations.top(10700, 10100, 3); String[] e = s.split(";");
  ck("three towns, not three pumps", e.length == 3 && e[0].startsWith("106") && !e[1].startsWith("106") && !e[2].startsWith("106"), s);
  ck("one entry per station however many pumps", s.split("1066").length == 2 || !s.contains(";10663") && !s.contains(";10670"), s);
  ck("its nearest working pump stands for the station", e[0].startsWith("10670,10015,"), s);
  s = SolStations.top(6500, 5300, 9); ck("dry stations are not offered", !s.contains("6500,5300"), s);
  ck("asking for more than exist is fine", s.split(";").length == 4, s);
  System.exit(fails == 0 ? 0 : 1); } }
