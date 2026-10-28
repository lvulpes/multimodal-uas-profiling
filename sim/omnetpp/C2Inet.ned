//
// Stage 2 (docs/poc-plan.md): plain INET between the GCS and the vehicle. Each host runs a
// UdpSocketBridge that connects it to the real GCS / flight software over loopback UDP.
//

package linkloss.omnetpp;

import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.node.inet.Router;
import inet.node.inet.StandardHost;
import ned.DatarateChannel;

network C2Inet
{
    parameters:
        double linkDelay @unit(s);
        double linkDatarate @unit(bps);
    submodules:
        configurator: Ipv4NetworkConfigurator;
        gcs: StandardHost;
        router: Router;
        uav: StandardHost;
    connections:
        gcs.ethg++ <--> DatarateChannel { delay = parent.linkDelay; datarate = parent.linkDatarate; } <--> router.ethg++;
        router.ethg++ <--> DatarateChannel { delay = parent.linkDelay; datarate = parent.linkDatarate; } <--> uav.ethg++;
}
