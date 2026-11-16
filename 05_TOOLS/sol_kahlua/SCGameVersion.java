package survivorcompanion.bridge;

/** Which game builds the bridge runs on: 42.21 or later in the 42 line. Whether a given build really matches our Java is linkcheck.py's job. */
final class SCGameVersion {
    private SCGameVersion() {}

    static boolean isSupported(String version) {
        if (version == null) return false;
        String[] parts = version.trim().split("\\.");
        if (parts.length < 2) return false;
        try {
            return Integer.parseInt(parts[0]) == 42 && Integer.parseInt(parts[1]) >= 21;
        } catch (NumberFormatException e) {
            return false;
        }
    }
}
