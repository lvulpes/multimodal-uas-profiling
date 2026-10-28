//
// Socket bridge between a real loopback UDP socket and the simulated network.
// See UdpSocketBridge.ned and docs/decisions/0003-socket-bridge-network-coupling.md.
//

#include "UdpSocketBridge.h"

#include <arpa/inet.h>
#include <cerrno>
#include <cstring>
#include <sys/socket.h>
#include <unistd.h>

#include <omnetpp/platdep/timeutil.h>

#include "inet/common/TimeTag_m.h"
#include "inet/common/packet/Packet.h"
#include "inet/common/packet/chunk/BytesChunk.h"
#include "inet/networklayer/common/L3AddressResolver.h"

namespace linkloss {

Define_Module(UdpSocketBridge);

simsignal_t UdpSocketBridge::fromRealSignal = registerSignal("fromReal");
simsignal_t UdpSocketBridge::toRealSignal = registerSignal("toReal");
simsignal_t UdpSocketBridge::droppedSignal = registerSignal("dropped");
simsignal_t UdpSocketBridge::transitDelaySignal = registerSignal("transitDelay");
simsignal_t UdpSocketBridge::schedulerLagSignal = registerSignal("schedulerLag");

UdpSocketBridge::~UdpSocketBridge()
{
    cancelAndDelete(lagProbeTimer);
    closeRealSocket();
}

void UdpSocketBridge::initialize(int stage)
{
    ApplicationBase::initialize(stage);

    if (stage == INITSTAGE_LOCAL) {
        rtScheduler = dynamic_cast<RealTimeScheduler *>(getSimulation()->getScheduler());
        if (rtScheduler == nullptr)
            throw cRuntimeError("UdpSocketBridge requires scheduler-class = \"inet::RealTimeScheduler\"");
        lagProbeInterval = par("lagProbeInterval");
        lagProbeTimer = new cMessage("lagProbe");
        WATCH(numFromReal);
        WATCH(numToReal);
        WATCH(numDropped);
    }
}

void UdpSocketBridge::handleMessageWhenUp(cMessage *msg)
{
    if (msg == lagProbeTimer) {
        emitSchedulerLag();
        scheduleAfter(lagProbeInterval, lagProbeTimer);
    }
    else
        socket.processMessage(msg);
}

void UdpSocketBridge::handleStartOperation(LifecycleOperation *operation)
{
    socket.setOutputGate(gate("socketOut"));
    socket.bind(par("localPort"));
    socket.setCallback(this);
    destAddress = L3AddressResolver().resolve(par("destAddress"));
    destPort = par("destPort");
    openRealSocket();
    if (lagProbeInterval > 0)
        scheduleAfter(lagProbeInterval, lagProbeTimer);
}

void UdpSocketBridge::handleStopOperation(LifecycleOperation *operation)
{
    cancelEvent(lagProbeTimer);
    closeRealSocket();
    socket.close();
    delayActiveOperationFinish(par("stopOperationTimeout"));
}

void UdpSocketBridge::handleCrashOperation(LifecycleOperation *operation)
{
    cancelEvent(lagProbeTimer);
    closeRealSocket();
    if (operation->getRootModule() != getContainingNode(this))
        socket.destroy();
    socket.setCallback(nullptr);
}

void UdpSocketBridge::openRealSocket()
{
    fd = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0)
        throw cRuntimeError("Cannot create UDP socket: %s", strerror(errno));

    // Allows restarting right after a killed run on the same port.
    int enable = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(enable)) < 0)
        throw cRuntimeError("Cannot set SO_REUSEADDR: %s", strerror(errno));

    sockaddr_in local = {};
    local.sin_family = AF_INET;
    local.sin_port = htons(par("realBindPort").intValue());
    if (inet_pton(AF_INET, par("realBindAddress").stringValue(), &local.sin_addr) != 1)
        throw cRuntimeError("Invalid realBindAddress '%s'", par("realBindAddress").stringValue());
    if (bind(fd, reinterpret_cast<sockaddr *>(&local), sizeof(local)) < 0)
        throw cRuntimeError("Cannot bind %s:%d: %s", par("realBindAddress").stringValue(),
                (int)par("realBindPort"), strerror(errno));

    int peerPort = par("realPeerPort");
    learnRealPeer = peerPort < 0;
    if (!learnRealPeer) {
        realPeer.sin_family = AF_INET;
        realPeer.sin_port = htons(peerPort);
        if (inet_pton(AF_INET, par("realPeerAddress").stringValue(), &realPeer.sin_addr) != 1)
            throw cRuntimeError("Invalid realPeerAddress '%s'", par("realPeerAddress").stringValue());
        realPeerKnown = true;
    }
    rtScheduler->addCallback(fd, this);
    EV_INFO << "Real socket bound to " << par("realBindAddress").stringValue() << ":" << (int)par("realBindPort")
            << (learnRealPeer ? ", peer learned from first datagram" : "") << endl;
}

void UdpSocketBridge::closeRealSocket()
{
    if (fd < 0)
        return;
    if (rtScheduler != nullptr)
        rtScheduler->removeCallback(fd, this);
    ::close(fd);
    fd = -1;
}

bool UdpSocketBridge::notify(int fd)
{
    Enter_Method("notify");
    if (fd != this->fd)
        return false;
    uint8_t buffer[1 << 16];
    sockaddr_in from = {};
    socklen_t fromLen = sizeof(from);
    ssize_t n = ::recvfrom(fd, buffer, sizeof(buffer), MSG_DONTWAIT, reinterpret_cast<sockaddr *>(&from), &fromLen);
    if (n < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK)
            return false;
        throw cRuntimeError("recvfrom failed: %s", strerror(errno));
    }
    emitSchedulerLag();
    if (learnRealPeer) {
        realPeer = from;
        realPeerKnown = true;
    }
    auto data = makeShared<BytesChunk>(buffer, n);
    data->addTag<CreationTimeTag>()->setCreationTime(simTime());
    auto packet = new Packet("c2", data);
    numFromReal++;
    emit(fromRealSignal, packet);
    socket.sendTo(packet, destAddress, destPort);
    return true;
}

void UdpSocketBridge::socketDataArrived(UdpSocket *socket, Packet *packet)
{
    emitSchedulerLag();
    for (auto& region : packet->peekData()->getAllTags<CreationTimeTag>())
        emit(transitDelaySignal, simTime() - region.getTag()->getCreationTime());
    if (fd < 0 || !realPeerKnown) {
        EV_WARN << "No real peer yet, dropping " << packet->getName() << endl;
        numDropped++;
        emit(droppedSignal, packet);
        delete packet;
        return;
    }
    const auto& bytes = packet->peekDataAsBytes()->getBytes();
    ssize_t n = ::sendto(fd, bytes.data(), bytes.size(), 0, reinterpret_cast<sockaddr *>(&realPeer), sizeof(realPeer));
    if (n < 0) {
        // The real peer may not be listening yet (ECONNREFUSED on loopback); not fatal.
        EV_WARN << "sendto failed: " << strerror(errno) << endl;
        numDropped++;
        emit(droppedSignal, packet);
    }
    else {
        numToReal++;
        emit(toRealSignal, packet);
    }
    delete packet;
}

void UdpSocketBridge::socketErrorArrived(UdpSocket *socket, Indication *indication)
{
    EV_WARN << "Ignoring UDP error report " << indication->getName() << endl;
    delete indication;
}

void UdpSocketBridge::socketClosed(UdpSocket *socket)
{
    if (operationalState == State::STOPPING_OPERATION)
        startActiveOperationExtraTimeOrFinish(par("stopOperationExtraTime"));
}

void UdpSocketBridge::emitSchedulerLag()
{
    // How far simulation time trails the wall clock (s). Positive = the scheduler is behind.
    int64_t wallNs = opp_get_monotonic_clock_nsecs() - rtScheduler->baseTime;
    emit(schedulerLagSignal, wallNs * 1e-9 - simTime().dbl());
}

void UdpSocketBridge::finish()
{
    ApplicationBase::finish();
    recordScalar("numFromReal", numFromReal);
    recordScalar("numToReal", numToReal);
    recordScalar("numDropped", numDropped);
}

} // namespace linkloss
