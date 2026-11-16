import com.sun.tools.attach.VirtualMachine;
/** Local same-user Attach API only; the Python caller verifies the dedicated QA process. */
public class AttachReadGate {
    public static void main(String[] args) throws Exception {
        if(args.length!=3 || !args[0].matches("[1-9][0-9]*"))throw new IllegalArgumentException("QA PID, agent and mode required");
        VirtualMachine target=VirtualMachine.attach(args[0]);
        try{
            String command=target.getSystemProperties().getProperty("sun.java.command","").replace('\\','/').toLowerCase(java.util.Locale.ROOT);
            if(!command.contains("/qa/runtime/java/purchase-") || !command.contains("--server.port=18023") || !command.contains("--spring.application.name=qa-purchase"))throw new IllegalArgumentException("Only the dedicated QA purchase JVM can be gated");
            target.loadAgent(args[1],args[2]);
        }finally{target.detach();}
    }
}
