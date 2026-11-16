package zombie.characters;
import zombie.iso.IsoCell;
public class IsoPlayer extends IsoGameCharacter {
    public IsoPlayer(IsoCell cell, SurvivorDesc descriptor, int x, int y, int z, boolean remote) {}
    public static IsoPlayer getInstance() { return null; }
    public static void setInstance(IsoPlayer player) {}
    public boolean isLocalPlayer() { return true; }
    public void updateLOS() {}
    public void update() {}
    public boolean isPlayerMoving() { return false; }
    public void setMoving(boolean moving) {}
    public void pathToLocationF(float x, float y, float z) {}
    public void pathToLocation(int x, int y, int z) {}
    public void pathToCharacter(IsoGameCharacter target) {}
    public zombie.core.skinnedmodel.advancedanimation.IAnimationVariableSlot setVariable(String name, boolean value) { return null; }
}
