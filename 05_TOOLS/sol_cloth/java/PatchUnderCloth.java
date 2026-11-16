import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.jar.JarOutputStream;

import net.bytebuddy.jar.asm.ClassReader;
import net.bytebuddy.jar.asm.ClassVisitor;
import net.bytebuddy.jar.asm.ClassWriter;
import net.bytebuddy.jar.asm.MethodVisitor;
import net.bytebuddy.jar.asm.Opcodes;

/**
 * s159: narrow, reproducible patch of SolCombined.jar for SolUnderCloth (see that class).
 *   localplayerbody/BraGeometry.<init>([[D[ILjava/lang/String;)V   before every RETURN:
 *       SolUnderCloth.refit(canonical, elements, size, this.fitted, this.bare, "undercloth-1")
 *   localplayerbody/Physics.bra(Clothing)Z, PreviewSupport.bra(Item)Z, PreviewSupport.bra(ItemVisual)Z   before every IRETURN:
 *       result = SolUnderCloth.holds(result, argument)
 * and adds SolUnderCloth.class plus the shape files. Everything else is copied byte for byte.
 * usage: java -cp <ZombieBuddy.jar>;. PatchUnderCloth input.jar output.jar SolUnderCloth.class undercloth-L.bin [...]
 * (ZombieBuddy.jar carries the shaded ASM, as for ScopeVSGirlBodyToSol.)
 * Refuses to write unless each of the four methods was patched exactly once and the input is not patched already.
 */
public final class PatchUnderCloth {
    private static final String OWNER = "localplayerbody/SolUnderCloth";
    private static final String VERSION = "undercloth-1";

    public static void main(String[] args) throws Exception {
        if (args.length < 4) throw new IllegalArgumentException("usage: input.jar output.jar SolUnderCloth.class shape.bin...");
        Path input = Path.of(args[0]).toAbsolutePath(), output = Path.of(args[1]).toAbsolutePath();
        if (input.equals(output) || !Files.isRegularFile(input)) throw new IllegalArgumentException("input/output paths are invalid");
        int[] count = new int[4];
        Files.createDirectories(output.getParent());
        try (JarFile jar = new JarFile(input.toFile()); JarOutputStream out = new JarOutputStream(Files.newOutputStream(output))) {
            if (jar.getEntry(OWNER + ".class") != null) throw new IllegalStateException("already patched: " + input);
            var entries = jar.entries();
            while (entries.hasMoreElements()) {
                JarEntry e = entries.nextElement();
                byte[] bytes;
                try (InputStream in = jar.getInputStream(e)) { bytes = in.readAllBytes(); }
                String name = e.getName();
                if (name.equals("localplayerbody/BraGeometry.class")) bytes = patch(bytes, 0, count);
                else if (name.equals("localplayerbody/Physics.class")) bytes = patch(bytes, 1, count);
                else if (name.equals("localplayerbody/PreviewSupport.class")) bytes = patch(bytes, 2, count);
                JarEntry ne = new JarEntry(name);
                ne.setTime(e.getTime());
                out.putNextEntry(ne); out.write(bytes); out.closeEntry();
            }
            for (int i = 2; i < args.length; i++) {
                Path f = Path.of(args[i]);
                JarEntry ne = new JarEntry("localplayerbody/" + f.getFileName());
                out.putNextEntry(ne); out.write(Files.readAllBytes(f)); out.closeEntry();
            }
        }
        if (count[0] != 1 || count[1] != 1 || count[2] != 1 || count[3] != 1) {
            Files.deleteIfExists(output);
            throw new IllegalStateException("expected each method once, patched: init=" + count[0] + " Physics.bra=" + count[1]
                + " PreviewSupport.bra(Item)=" + count[2] + " PreviewSupport.bra(ItemVisual)=" + count[3]);
        }
        System.out.println("patched BraGeometry.<init>, Physics.bra, PreviewSupport.bra x2 -> " + output);
    }

    private static byte[] patch(byte[] bytes, int which, int[] count) {
        ClassReader reader = new ClassReader(bytes);
        ClassWriter writer = new ClassWriter(reader, ClassWriter.COMPUTE_MAXS);
        reader.accept(new ClassVisitor(Opcodes.ASM9, writer) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String desc, String sig, String[] ex) {
                MethodVisitor mv = super.visitMethod(access, name, desc, sig, ex);
                if (which == 0 && name.equals("<init>") && desc.equals("([[D[ILjava/lang/String;)V")) {
                    count[0]++;
                    return new MethodVisitor(Opcodes.ASM9, mv) {
                        @Override
                        public void visitInsn(int op) {
                            if (op == Opcodes.RETURN) {
                                super.visitVarInsn(Opcodes.ALOAD, 1);
                                super.visitVarInsn(Opcodes.ALOAD, 2);
                                super.visitVarInsn(Opcodes.ALOAD, 3);
                                super.visitVarInsn(Opcodes.ALOAD, 0);
                                super.visitFieldInsn(Opcodes.GETFIELD, "localplayerbody/BraGeometry", "fitted", "[[D");
                                super.visitVarInsn(Opcodes.ALOAD, 0);
                                super.visitFieldInsn(Opcodes.GETFIELD, "localplayerbody/BraGeometry", "bare", "[[D");
                                super.visitLdcInsn(VERSION);
                                super.visitMethodInsn(Opcodes.INVOKESTATIC, OWNER, "refit", "([[D[ILjava/lang/String;[[D[[DLjava/lang/String;)V", false);
                            }
                            super.visitInsn(op);
                        }
                    };
                }
                int slot = -1;
                if (which == 1 && name.equals("bra") && desc.equals("(Lzombie/inventory/types/Clothing;)Z")) slot = 1;
                if (which == 2 && name.equals("bra") && desc.equals("(Lzombie/scripting/objects/Item;)Z")) slot = 2;
                if (which == 2 && name.equals("bra") && desc.equals("(Lzombie/core/skinnedmodel/visual/ItemVisual;)Z")) slot = 3;
                if (slot < 0) return mv;
                if ((access & Opcodes.ACC_STATIC) == 0) throw new IllegalStateException(name + desc + " is not static");
                count[slot]++;
                return new MethodVisitor(Opcodes.ASM9, mv) {
                    @Override
                    public void visitInsn(int op) {
                        if (op == Opcodes.IRETURN) {
                            super.visitVarInsn(Opcodes.ALOAD, 0);
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, OWNER, "holds", "(ZLjava/lang/Object;)Z", false);
                        }
                        super.visitInsn(op);
                    }
                };
            }
        }, 0);
        return writer.toByteArray();
    }
}
