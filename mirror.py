import time
import math
import transm_global_params
import threading
from utils import get_time_h_m_s
from utils import get_reflected_vector
from utils import rotate
from utils import normalize
from ray import Ray


class Mirror:
    def __init__(self, identifier, coord):
        self.id_ = identifier
        self.coord_ = coord
        self.normal_ = [0.0, 1.0]
        self.light_src_center_ = None

        self.receiver_light_src_ = None
        self.sender_focus_ = None
        self.receiver_focus_ = None
        self.senders_mirrors_ = {}
        self.receivers_mirrors_ = {}

        self.is_turn_to_adjust = False
        self.neighbor_ids_ = []
        self.prev_adjusted_id_ = -1

    def receive_light_src_coord(self):
        start_time = time.time()
        while time.time() - start_time < transm_global_params.MIRROR_TO_LIGHT_SRC_TIMEOUT:
            is_connected = self.receiver_light_src_.wait_for_connection()
            if is_connected:
                light_src_coord = self.receiver_light_src_.receive()
                if light_src_coord is not None:
                    # print("mirror #", self.id_, ":", "received light source coordinates", get_time_h_m_s())
                    return light_src_coord
        return None

    def receive_intensity(self):
        start_time = time.time()
        while time.time() - start_time < transm_global_params.MIRROR_TO_FOCUS_TIMEOUT:
            is_connected = self.receiver_focus_.wait_for_connection()
            if is_connected:
                intensity = self.receiver_focus_.receive()
                if intensity is not None:
                    # print("mirror #", self.id_, ":", "received current intensity:", intensity[0], get_time_h_m_s())
                    return intensity[0]
        return None

    def send_ray(self, ray):
        start_time = time.time()
        while time.time() - start_time < transm_global_params.MIRROR_TO_LIGHT_SRC_TIMEOUT:
            is_connected = self.sender_focus_.wait_for_connection()
            if is_connected:
                is_sent = self.sender_focus_.send([ray])
                if is_sent:
                    return True
        return False

    def adjust(self):
        print("mirror #", self.id_, ":", "start adjusting", get_time_h_m_s())
        light_src_coord = self.receive_light_src_coord()
        if light_src_coord is None:
            return
        intensity_before_adjusting = self.receive_intensity()
        if intensity_before_adjusting is None:
            return
        cur_intensity = intensity_before_adjusting

        dir_from_light = [
            self.coord_[0] - light_src_coord[0],
            self.coord_[1] - light_src_coord[1]
        ]

        rotation_angle = 0
        iter_count = 0
        dir_on_focus = []

        while intensity_before_adjusting == cur_intensity:

            if iter_count != 0:
                rotate(self.normal_, transm_global_params.ROTATION_DELTA_RAD)
                rotation_angle += transm_global_params.ROTATION_DELTA_RAD

            if dir_from_light[0] * self.normal_[0] + dir_from_light[1] * self.normal_[1] <= 0:
                dir_on_focus = get_reflected_vector(dir_from_light, self.normal_)
                normalize(dir_on_focus)

                ray = Ray(point=self.coord_, vector=dir_on_focus)
                is_sent = self.send_ray(ray)
                if not is_sent:
                    return

                time.sleep(0.5)

                cur_intensity = self.receive_intensity()
                if cur_intensity is None:
                    return

            iter_count += 1

        print("mirror #", self.id_, ":", "final angle:", rotation_angle, get_time_h_m_s())
        print("mirror #", self.id_, ":", "rotations count:", iter_count - 1, get_time_h_m_s())
        print("mirror #", self.id_, ":", "final normal:", self.normal_[0], self.normal_[1], get_time_h_m_s())
        print("mirror #", self.id_, ":", "final dir on focus:", dir_on_focus[0], dir_on_focus[1], get_time_h_m_s())
        print("mirror #", self.id_, ":", "end adjusting", get_time_h_m_s())

    def send_hello(self, stop_event, sender):
        while not stop_event.is_set():
            is_connected = sender.wait_for_connection()
            if is_connected:
                sender.send([transm_global_params.MSG_HELLO])

    def receive_hello(self, stop_event, lock, receiver, node, neighbor_id):
        while not stop_event.is_set():
            is_connected = receiver.wait_for_connection()
            if is_connected:
                hello = receiver.receive()
                if hello is not None and hello[0] == transm_global_params.MSG_HELLO:
                    lock.acquire()

                    if neighbor_id not in node.neighbor_ids_:
                        print("mirror #", node.id_, ":", "mirror #", neighbor_id,
                              "discovered, appending to neighbors",
                              get_time_h_m_s())
                        node.neighbor_ids_.append(neighbor_id)

                    lock.release()

    def receive_adj_ctrl(self, stop_event, receiver, mirror, id_sender):
        while not stop_event.is_set():
            is_connected = receiver.wait_for_connection()
            if is_connected:
                adj_ctrl = receiver.receive()
                if adj_ctrl is not None and adj_ctrl[0] == transm_global_params.MSG_TAKE_ADJUSTING_CONTROL:
                    print("mirror #", self.id_, ":", "adjusting control is received", get_time_h_m_s())
                    mirror.is_turn_to_adjust = True
                    mirror.prev_adjusted_id_ = id_sender

    def send_adj_ctrl(self):
        id_to_send_to = -1
        for i in self.neighbor_ids_:
            if i != self.prev_adjusted_id_ or len(self.neighbor_ids_) == 1:
                id_to_send_to = i
                continue
        start_time = time.time()
        while time.time() - start_time < transm_global_params.MIRROR_TO_MIRROR_TIMEOUT:
            is_connected = self.senders_mirrors_[id_to_send_to].wait_for_connection()
            if is_connected:
                is_sent = self.senders_mirrors_[id_to_send_to].send([transm_global_params.MSG_TAKE_ADJUSTING_CONTROL])
                if is_sent:
                    print("mirror #", self.id_, ":", "transfer control to mirror #", id_to_send_to, get_time_h_m_s())
                    return True
        return False

    def run(self, is_first_to_adjust=False):
        threads_send_hello = []
        threads_receive_hello = []
        stop_hello_event = threading.Event()

        for i in self.senders_mirrors_:
            threads_send_hello.append(
                threading.Thread(target=self.send_hello,
                                 args=(stop_hello_event, self.senders_mirrors_[i])))

        lock = threading.Lock()

        for i in self.receivers_mirrors_:
            threads_receive_hello.append(
                threading.Thread(target=self.receive_hello,
                                 args=(stop_hello_event, lock, self.receivers_mirrors_[i], self, i)))

        for thread in threads_send_hello:
            thread.start()
        for thread in threads_receive_hello:
            thread.start()

        time.sleep(transm_global_params.HELLO_TIMEOUT)
        stop_hello_event.set()

        for thread in threads_receive_hello:
            thread.join()
        for thread in threads_send_hello:
            thread.join()

        if is_first_to_adjust:
            self.is_turn_to_adjust = True

        threads_receive_adj_ctrl = []
        stop_mirror_proc_event = threading.Event()

        for i in self.neighbor_ids_:
            threads_receive_adj_ctrl.append(
                threading.Thread(target=self.receive_adj_ctrl,
                                 args=(stop_mirror_proc_event, self.receivers_mirrors_[i], self, i)
                                 )
            )
        for thread in threads_receive_adj_ctrl:
            thread.start()

        start_time = time.time()
        while time.time() - start_time < transm_global_params.MIRROR_TIMEOUT:
            if self.is_turn_to_adjust:
                self.adjust()
                self.is_turn_to_adjust = False
                self.send_adj_ctrl()
        stop_mirror_proc_event.set()
        for thread in threads_receive_adj_ctrl:
            thread.join()

        print("mirror #", self.id_, ":", "I'm out", get_time_h_m_s())
