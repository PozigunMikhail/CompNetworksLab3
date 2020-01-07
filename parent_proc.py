import time
from multiprocessing import Process

from ipc_manager_pipes import IPCManagerPipes
from mirror import Mirror
from focus import Focus
from light_source import LightSource
from sender import Sender
from receiver import Receiver
from utils import get_time_h_m_s
import transm_global_params


def get_topology(points_number):
    edges = []

    for i in range(0, points_number - 1):
        edges.append((i, i + 1))

    return edges


def run_light_src(coord, transmission_protocol, senders):
    light_src = LightSource(coord)

    for sender in senders:
        light_src.senders_.append(Sender(sender, transmission_protocol, verbose=False))

    light_src.run()


def run_focus(coord, transmission_protocol, senders, receivers):
    focus = Focus(coord)

    for sender in senders:
        focus.senders_.append(Sender(sender, transmission_protocol, verbose=False))
    for receiver in receivers:
        focus.receivers_.append(Receiver(receiver, transmission_protocol, verbose=False))

    focus.run()


def run_mirror(
        coord,
        transmission_protocol,
        identifier,
        sender_ipc_focus,
        receiver_ipc_focus,
        receiver_ipc_light,
        senders_ipc_mirrors,
        receivers_ipc_mirrors):
    mirror = Mirror(identifier=identifier, coord=coord)

    mirror.sender_focus_ = Sender(sender_ipc_focus, transmission_protocol, verbose=False)
    mirror.receiver_focus_ = Receiver(receiver_ipc_focus, transmission_protocol, verbose=False)

    mirror.receiver_light_src_ = Receiver(receiver_ipc_light, transmission_protocol, verbose=False)

    for i, ipc in senders_ipc_mirrors.items():
        mirror.senders_mirrors_[i] = Sender(ipc, transmission_protocol, verbose=False)
    for i, ipc in receivers_ipc_mirrors.items():
        mirror.receivers_mirrors_[i] = Receiver(ipc, transmission_protocol, verbose=False)

    if identifier == 0:
        mirror.run(is_first_to_adjust=True)
    else:
        mirror.run()


if __name__ == '__main__':
    focus_coord = transm_global_params.FOCUS_COORDINATE
    light_src_coord = transm_global_params.LIGHT_SOURCE_COORDINATE

    nodes_number = len(transm_global_params.MIRRORS_COORDINATES)
    mirrors_coordinates = transm_global_params.MIRRORS_COORDINATES

    edges = get_topology(nodes_number)

    print(mirrors_coordinates)

    transmission_protocol = transm_global_params.TransmissionProtocol.ALGORITHM_TYPE_SR

    senders_ipc_managers_m2m = []
    receivers_ipc_managers_m2m = []
    senders_ipc_managers_m2f = []
    receivers_ipc_managers_m2f = []
    senders_ipc_managers_f2m = []
    receivers_ipc_managers_f2m = []
    senders_ipc_managers_m2l = []
    receivers_ipc_managers_m2l = []
    senders_ipc_managers_l2m = []
    receivers_ipc_managers_l2m = []

    for i in range(nodes_number):
        senders_ipc_managers_m2m.append({})
        receivers_ipc_managers_m2m.append({})

        senders_ipc_managers_m2f.append(None)
        receivers_ipc_managers_m2f.append(None)
        senders_ipc_managers_f2m.append(None)
        receivers_ipc_managers_f2m.append(None)

        senders_ipc_managers_m2l.append(None)
        receivers_ipc_managers_m2l.append(None)
        senders_ipc_managers_l2m.append(None)
        receivers_ipc_managers_l2m.append(None)

    for edge in edges:
        i = edge[0]
        j = edge[1]

        ipc_manager1 = IPCManagerPipes()
        ipc_manager2 = IPCManagerPipes()

        senders_ipc_managers_m2m[i][j] = ipc_manager1
        receivers_ipc_managers_m2m[i][j] = ipc_manager2

        senders_ipc_managers_m2m[j][i] = ipc_manager2
        receivers_ipc_managers_m2m[j][i] = ipc_manager1

    for i in range(nodes_number):
        ipc_manager1 = IPCManagerPipes()
        ipc_manager2 = IPCManagerPipes()

        senders_ipc_managers_m2f[i] = ipc_manager1
        receivers_ipc_managers_m2f[i] = ipc_manager2

        senders_ipc_managers_f2m[i] = ipc_manager2
        receivers_ipc_managers_f2m[i] = ipc_manager1

        ipc_manager3 = IPCManagerPipes()
        ipc_manager4 = IPCManagerPipes()

        senders_ipc_managers_m2l[i] = ipc_manager3
        receivers_ipc_managers_m2l[i] = ipc_manager4

        senders_ipc_managers_l2m[i] = ipc_manager4
        receivers_ipc_managers_l2m[i] = ipc_manager3

    processes = [
        Process(
            target=run_focus,
            args=(
                focus_coord,
                transmission_protocol,
                senders_ipc_managers_f2m,
                receivers_ipc_managers_f2m
            )
        ),
        Process(
            target=run_light_src,
            args=(
                light_src_coord,
                transmission_protocol,
                senders_ipc_managers_l2m
            )
        )
    ]

    for i in range(nodes_number):
        processes.append(Process(target=run_mirror, args=(
            mirrors_coordinates[i],
            transmission_protocol,
            i,
            senders_ipc_managers_m2f[i],
            receivers_ipc_managers_m2f[i],
            receivers_ipc_managers_m2l[i],
            senders_ipc_managers_m2m[i],
            receivers_ipc_managers_m2m[i]
        )))

    print("Network launch", get_time_h_m_s())

    for i in range(len(processes)):
        processes[i].start()

    time.sleep(transm_global_params.NETWORK_TIMEOUT)

    print("Network timeout, exiting", get_time_h_m_s())

    for p in processes:
        p.join()
