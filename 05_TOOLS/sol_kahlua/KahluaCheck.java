// Runs Lua through the game's own Kahlua (classes from projectzomboid.jar, read only).
//   probe <file.lua>            run a script in a plain Kahlua environment, print() goes to stdout
//   scan <out.tsv> <dir>...     compile every .lua under the dirs with the game's compiler and list what the bytecode uses
import java.io.*; import java.nio.charset.StandardCharsets; import java.nio.file.*; import java.util.*;
import se.krka.kahlua.vm.*; import se.krka.kahlua.j2se.J2SEPlatform; import se.krka.kahlua.luaj.compiler.LuaCompiler;
import org.luaj.kahluafork.compiler.LexState;
public class KahluaCheck {
  static final int MOVE=0,LOADK=1,GETGLOBAL=5,GETTABLE=6,SETGLOBAL=7,SETTABLE=9,SELF=11,CALL=28,TAILCALL=29,VARARG=37;
  static int op(int i){return i&63;} static int A(int i){return (i>>>6)&255;} static int C(int i){return (i>>>14)&511;} static int B(int i){return (i>>>23)&511;} static int Bx(int i){return i>>>14;}
  static Object rk(Prototype p,int x){return x>=256?p.constants[x-256]:null;}
  static PrintWriter out; static String cur;
  static void emit(String kind,int line,String a){ out.println(kind+"\t"+cur+"\t"+line+"\t"+a); }
  static String calleeOf(Prototype p,int pc,int reg){
    for(int k=pc-1;k>=0;k--){ int i=p.code[k]; int o=op(i);
      if(A(i)==reg && o==GETGLOBAL) return String.valueOf(p.constants[Bx(i)]);
      if(A(i)==reg && o==GETTABLE){ Object key=rk(p,C(i)); String owner=null;
        for(int m=k-1;m>=0;m--){int j=p.code[m]; if(A(j)==B(i)&&op(j)==GETGLOBAL){owner=String.valueOf(p.constants[Bx(j)]);break;} if(A(j)==B(i))break;}
        return (owner==null?"?":owner)+"."+key; }
      if(A(i)==reg && o==SELF) return ":"+rk(p,C(i));
      if(A(i)==reg && (o==MOVE||o==CALL)) return null;
    } return null; }
  static void walk(Prototype p){
    for(int pc=0;pc<p.code.length;pc++){ int i=p.code[pc]; int o=op(i); int line=p.lines!=null&&pc<p.lines.length?p.lines[pc]:0;
      if(o==GETGLOBAL){ String g=String.valueOf(p.constants[Bx(i)]); emit("G",line,g);
        int n=pc+1; if(n<p.code.length&&op(p.code[n])==GETTABLE&&B(p.code[n])==A(i)){Object key=rk(p,C(p.code[n])); if(key instanceof String) emit("F",line,g+"."+key);} }
      else if(o==SETGLOBAL) emit("S",line,String.valueOf(p.constants[Bx(i)]));
      else if(o==SELF){ Object key=rk(p,C(i)); if(key instanceof String) emit("M",line,(String)key); }
      else if(o==SETTABLE){ Object key=rk(p,B(i)); if(key instanceof String) emit("K",line,(String)key); }
      else if(o==16) emit("MOD",line,"B="+(rk(p,B(i))!=null?rk(p,B(i)):"r"+B(i))+" C="+(rk(p,C(i))!=null?rk(p,C(i)):"r"+C(i)));
      else if(o==VARARG&&B(i)==0&&pc+1<p.code.length&&op(p.code[pc+1])==34) emit("VT",line,"{...}");
      else if(o==20) emit("LEN",line,"");
      else if(o==CALL||o==TAILCALL){ if(B(i)==0){ String c=calleeOf(p,pc,A(i)); if(c!=null&&pc>0){int pv=p.code[pc-1]; int po=op(pv); String inner=po==CALL?(calleeOf(p,pc-1,A(pv))):po==VARARG?"...":"?"; emit("X",line,c+"\t"+inner);} } }
    }
    if(p.prototypes!=null) for(Prototype c:p.prototypes) walk(c);
  }
  static String read(Path f) throws IOException { return new String(Files.readAllBytes(f),StandardCharsets.UTF_8); }
  public static void main(String[] a) throws Exception {
    if(a[0].equals("probe")){
      J2SEPlatform pl=new J2SEPlatform(); KahluaTable env=pl.newEnvironment(); KahluaThread t=new KahluaThread(System.out,pl,env); t.debugOwnerThread=Thread.currentThread();
      String src=read(Paths.get(a[1])); if(src.startsWith("\uFEFF")) src=src.substring(1);
      LuaClosure f=LuaCompiler.loadstring(src,"probe",env); Object[] r=t.pcall(f);
      if(r.length>0&&Boolean.FALSE.equals(r[0])){System.out.println("PROBE_FAILED "+Arrays.toString(r));} System.out.flush(); return; }
    if(a[0].equals("api")){ // api <exposed.txt> <out.tsv>: every public method and static field of the classes the game exposes to Lua
      PrintWriter w=new PrintWriter(new OutputStreamWriter(new FileOutputStream(a[2]),StandardCharsets.UTF_8)); ClassLoader cl=KahluaCheck.class.getClassLoader();
      for(String n:Files.readAllLines(Paths.get(a[1]))){ n=n.trim(); if(n.isEmpty()) continue; try{ Class<?> c=Class.forName(n,false,cl); String sn=c.getSimpleName();
          for(var m:c.getMethods()){ w.println("M	"+sn+"	"+m.getName()+"	"+(java.lang.reflect.Modifier.isStatic(m.getModifiers())?"s":"i")); }
          for(var f:c.getFields()){ if(java.lang.reflect.Modifier.isStatic(f.getModifiers())) w.println("F	"+sn+"	"+f.getName()+"	s"); }
          for(Object e:(c.isEnum()?new Object[0]:new Object[0])){}
          for(var dc:c.getDeclaredFields()){ if(dc.isEnumConstant()) w.println("F	"+sn+"	"+dc.getName()+"	s"); }
        }catch(Throwable e){ w.println("X	"+n+"	"+e); } }
      Class<?> g=Class.forName("zombie.Lua.LuaManager$GlobalObject",false,cl); Class<? extends java.lang.annotation.Annotation> an=(Class)Class.forName("se.krka.kahlua.integration.annotations.LuaMethod",false,cl); var nm=an.getMethod("name");
      for(var m:g.getDeclaredMethods()){ var x=m.getAnnotation(an); if(x!=null) w.println("G	-	"+nm.invoke(x)+"	s"); }
      w.close(); System.out.println("api done"); return; }
    out=new PrintWriter(new OutputStreamWriter(new FileOutputStream(a[1]),StandardCharsets.UTF_8));
    int files=0,bad=0;
    for(int d=2;d<a.length;d++){ final List<Path> ls=new ArrayList<>(); try(var s=Files.walk(Paths.get(a[d]))){s.filter(x->x.toString().endsWith(".lua")).forEach(ls::add);}
      Collections.sort(ls);
      for(Path f:ls){ files++; cur=(d==2?"":"V:")+Paths.get(a[d]).relativize(f).toString().replace('\\','/'); String src=read(f); if(src.startsWith("\uFEFF")) src=src.substring(1);
        try{ Prototype p=LexState.compile(0,new StringReader(src),"x",f.getFileName().toString()); walk(p);}
        catch(Throwable e){ bad++; out.println("E\t"+cur+"\t0\t"+e.getMessage()); System.out.println("COMPILE ERROR "+cur+": "+e.getMessage()); } } }
    out.close(); System.out.println("files="+files+" compile_errors="+bad);
  }
}
