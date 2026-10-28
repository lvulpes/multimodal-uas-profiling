//
// Socket bridge between a real loopback UDP socket and the simulated network
// (docs/decisions/0003-socket-bridge-network-coupling.md).
//

package linkloss.bridge;

import inet.applications.contract.IApp;

//
// Owns one real UDP socket (registered with inet::RealTimeScheduler) and one simulated UDP socket.
// Datagrams read from the real socket are sent as opaque bytes to destAddress:destPort in the
// simulated network; datagrams arriving on localPort are written to the real peer.
//
// The real peer is either fixed (realPeerPort >= 0) or learned from the source of the most recent
// datagram read from the real socket (realPeerPort = -1, for a stack that sends to a known port).
//
// Records the real-time scheduler lag (wall clock minus simulation time) at every bridge event and
// every lagProbeInterval, and the one-way transit time through the simulated network.
//
simple UdpSocketBridge like IApp
{
    parameters:
        int localPort;                              // simulated UDP port
        string destAddress;                         // simulated peer (module path or address)
        int destPort;                               // simulated peer port
        string realBindAddress = default("127.0.0.1");
        int realBindPort;                           // 0 = ephemeral
        string realPeerAddress = default("127.0.0.1");
        int realPeerPort = default(-1);             // -1 = learn from received datagrams
        double lagProbeInterval @unit(s) = default(100ms);  // 0 = only measure at bridge events
        double stopOperationExtraTime @unit(s) = default(-1s);
        double stopOperationTimeout @unit(s) = default(2s);
        @display("i=block/bridge");
        @lifecycleSupport;
        @signal[fromReal](type=inet::Packet);
        @signal[toReal](type=inet::Packet);
        @signal[dropped](type=inet::Packet);
        @signal[transitDelay](type=simtime_t);
        @signal[schedulerLag](type=double);
        @statistic[fromReal](title="datagrams from real socket"; record=count,"sum(packetBytes)"; interpolationmode=none);
        @statistic[toReal](title="datagrams to real socket"; record=count,"sum(packetBytes)"; interpolationmode=none);
        @statistic[dropped](title="datagrams dropped"; record=count; interpolationmode=none);
        @statistic[transitDelay](title="one-way transit time in simulation"; unit=s; record=vector,mean,max; interpolationmode=none);
        @statistic[schedulerLag](title="real-time scheduler lag"; unit=s; record=vector,mean,max; interpolationmode=none);
    gates:
        input socketIn @labels(UdpControlInfo/up);
        output socketOut @labels(UdpControlInfo/down);
}
