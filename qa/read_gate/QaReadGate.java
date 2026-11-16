import java.lang.instrument.*;
import java.nio.file.*;
import java.security.ProtectionDomain;
import jdk.internal.org.objectweb.asm.*;

/** Temporary local QA scheduling gate. It never replaces queries or business values. */
public class QaReadGate {
    private static final String TARGET="com/zeroone/star/purchase/service/PurchaseOrderListView";
    private static volatile Path folder;
    private static ClassFileTransformer transformer;
    public static void agentmain(String args, Instrumentation instrumentation) throws Exception {
        if(transformer!=null){instrumentation.removeTransformer(transformer);transformer=null;retransform(instrumentation);}
        if("off".equals(args)){folder=null;return;}
        if(!args.startsWith("on:"))throw new IllegalArgumentException("QA gate mode required");
        folder=Paths.get(args.substring(3));
        transformer=new ClassFileTransformer(){
            public byte[] transform(ClassLoader loader,String name,Class<?> type,ProtectionDomain domain,byte[] original){
                if(!TARGET.equals(name))return null;
                ClassReader reader=new ClassReader(original);ClassWriter writer=new ClassWriter(0);
                reader.accept(new ClassVisitor(Opcodes.ASM5,writer){
                    public MethodVisitor visitMethod(int access,String name,String descriptor,String signature,String[] exceptions){
                        MethodVisitor method=super.visitMethod(access,name,descriptor,signature,exceptions);
                        if(!"enrich".equals(name))return method;
                        return new MethodVisitor(Opcodes.ASM5,method){
                            public void visitCode(){super.visitCode();visitMethodInsn(Opcodes.INVOKESTATIC,"QaReadGate","pause","()V",false);}
                        };
                    }
                },0);
                return writer.toByteArray();
            }
        };
        instrumentation.addTransformer(transformer,true);retransform(instrumentation);
    }
    private static void retransform(Instrumentation instrumentation) throws Exception {
        for(Class<?> type:instrumentation.getAllLoadedClasses())if(TARGET.replace('/','.').equals(type.getName()))instrumentation.retransformClasses(type);
    }
    public static void pause(){
        Path current=folder;if(current==null)return;
        try{
            if(!Files.deleteIfExists(current.resolve("armed")))return;
            Files.write(current.resolve("entered"),new byte[]{1});long deadline=System.nanoTime()+15000000000L;
            while(!Files.exists(current.resolve("resume")) && System.nanoTime()<deadline)Thread.sleep(25);
            if(!Files.exists(current.resolve("resume")))Files.write(current.resolve("timed-out"),new byte[]{1});
        }catch(Exception error){throw new IllegalStateException("Temporary QA read gate failed",error);}
    }
}
