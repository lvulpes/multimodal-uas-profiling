//
// Socket bridge between a real loopback UDP socket and the simulated network.
// See UdpSocketBridge.ned and docs/decisions/0003-socket-bridge-network-coupling.md.
//

#ifndef __LINKLOSS_UDPSOCKETBRIDGE_H
#define __LINKLOSS_UDPSOCKETBRIDGE_H

#include <netinet/in.h>

#include "inet/applications/base/ApplicationBase.h"
#include "inet/common/scheduler/RealTimeScheduler.h"
#include "inet/transportlayer/contract/udp/UdpSocket.h"

namespace linkloss {

using namespace omnetpp;
using namespace inet;

/**
 * Forwards datagrams between one real UDP socket and the simulated network. See NED for more info.
 */
class UdpSocketBridge : public ApplicationBase, public UdpSocket::ICallback, public RealTimeScheduler::ICallback
{
  protected:
    // simulated side
    UdpSocket socket;
    L3Address destAddress;
    int destPort = -1;

    // real side
    RealTimeScheduler *rtScheduler = nullptr;
    int fd = -1;
    sockaddr_in realPeer = {};
    bool realPeerKnown = false;
    bool learnRealPeer = false;

    simtime_t lagProbeInterval;
    cMessage *lagProbeTimer = nullptr;

    // statistics
    long numFromReal = 0;
    long numToReal = 0;
    long numDropped = 0;

    static simsignal_t fromRealSignal;
    static simsignal_t toRealSignal;
    static simsignal_t droppedSignal;
    static simsignal_t transitDelaySignal;
    static simsignal_t schedulerLagSignal;

  protected:
    virtual int numInitStages() const override { return NUM_INIT_STAGES; }
    virtual void initialize(int stage) override;
    virtual void handleMessageWhenUp(cMessage *msg) override;
    virtual void finish() override;

    virtual void handleStartOperation(LifecycleOperation *operation) override;
    virtual void handleStopOperation(LifecycleOperation *operation) override;
    virtual void handleCrashOperation(LifecycleOperation *operation) override;

    // UdpSocket::ICallback: simulated network -> real socket
    virtual void socketDataArrived(UdpSocket *socket, Packet *packet) override;
    virtual void socketErrorArrived(UdpSocket *socket, Indication *indication) override;
    virtual void socketClosed(UdpSocket *socket) override;

    // RealTimeScheduler::ICallback: real socket -> simulated network
    virtual bool notify(int fd) override;

    virtual void openRealSocket();
    virtual void closeRealSocket();
    virtual void emitSchedulerLag();

  public:
    virtual ~UdpSocketBridge();
};

} // namespace linkloss

#endif
