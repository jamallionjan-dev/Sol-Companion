import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import net.bytebuddy.jar.asm.*;
import net.bytebuddy.jar.asm.commons.*;

/** Game 42.22 removed zombie.util.list.PZArrayList. Rewrites only the calls that named it, for classes with no matching source.
 *  usage: JarRetarget4222 in.jar out.jar  (classes in the jar that do not name the removed class are copied byte for byte) */
public class JarRetarget4222 {
    static final String OLD = "zombie/util/list/PZArrayList", LIST = "java/util/List";
    static final Set<String> LIST_METHODS = Set.of("get(I)Ljava/lang/Object;", "size()I");
    static final String BRIDGE = "survivorcompanion/bridge/SCBridge.class", HELPER = "survivorcompanion/bridge/SCGameVersion.class";
    static int calls, hits, gates;

    static byte[] retarget(byte[] in, String entry) {
        ClassReader r = new ClassReader(in);
        ClassWriter w = new ClassWriter(0);
        ClassVisitor remap = new ClassRemapper(w, new SimpleRemapper(OLD, LIST));
        r.accept(new ClassVisitor(Opcodes.ASM9, remap) {
            @Override public MethodVisitor visitMethod(int a, String n, String d, String s, String[] e) {
                if (entry.equals(BRIDGE) && n.equals("isSupportedGameVersion") && d.equals("(Ljava/lang/String;)Z")) {
                    MethodVisitor m = super.visitMethod(a, n, d, s, e);
                    m.visitCode();
                    m.visitVarInsn(Opcodes.ALOAD, 0);
                    m.visitMethodInsn(Opcodes.INVOKESTATIC, "survivorcompanion/bridge/SCGameVersion", "isSupported", d, false);
                    m.visitInsn(Opcodes.IRETURN);
                    m.visitMaxs(1, 1);
                    m.visitEnd();
                    gates++;
                    return null;
                }
                return new MethodVisitor(Opcodes.ASM9, super.visitMethod(a, n, d, s, e)) {
                    @Override public void visitMethodInsn(int op, String owner, String name, String desc, boolean itf) {
                        if (owner.equals(OLD)) {
                            if (op != Opcodes.INVOKEVIRTUAL || !LIST_METHODS.contains(name + desc))
                                throw new IllegalStateException(entry + ": unhandled " + name + desc);
                            calls++;
                            super.visitMethodInsn(Opcodes.INVOKEINTERFACE, LIST, name, desc, true);
                            return;
                        }
                        if (name.equals("getHitInfoList") && desc.equals("()L" + OLD + ";")) {
                            hits++;
                            super.visitMethodInsn(op, owner, name, "()Ljava/util/ArrayList;", itf);
                            return;
                        }
                        if (desc.contains(OLD) && !name.equals("getObjects"))
                            throw new IllegalStateException(entry + ": unhandled game call " + owner + "." + name + desc);
                        super.visitMethodInsn(op, owner, name, desc, itf);
                    }
                };
            }
        }, 0);
        return w.toByteArray();
    }

    public static void main(String[] a) throws Exception {
        byte[] needle = OLD.getBytes("UTF-8");
        int changed = 0;
        try (ZipFile in = new ZipFile(a[0]); ZipOutputStream out = new ZipOutputStream(new BufferedOutputStream(Files.newOutputStream(Path.of(a[1]))))) {
            for (Enumeration<? extends ZipEntry> en = in.entries(); en.hasMoreElements();) {
                ZipEntry e = en.nextElement();
                byte[] b;
                try (InputStream is = in.getInputStream(e)) { b = is.readAllBytes(); }
                if (e.getName().equals(HELPER)) continue;
                if (e.getName().endsWith(".class") && (indexOf(b, needle) >= 0 || e.getName().equals(BRIDGE))) {
                    b = retarget(b, e.getName());
                    changed++;
                    System.out.println("retargeted " + e.getName());
                }
                ZipEntry o = new ZipEntry(e.getName());
                o.setTime(e.getTime());
                out.putNextEntry(o);
                out.write(b);
                out.closeEntry();
            }
            if (a.length > 2) {
                out.putNextEntry(new ZipEntry(HELPER));
                out.write(Files.readAllBytes(Path.of(a[2])));
                out.closeEntry();
            }
        }
        System.out.println("classes " + changed + ", list calls " + calls + ", hit-list calls " + hits + ", version gates " + gates);
    }

    static int indexOf(byte[] h, byte[] n) {
        outer:
        for (int i = 0; i <= h.length - n.length; i++) {
            for (int j = 0; j < n.length; j++) if (h[i + j] != n[j]) continue outer;
            return i;
        }
        return -1;
    }
}
