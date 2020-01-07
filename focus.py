import time
import math
import transm_global_params
import threading
from utils import get_time_h_m_s
from utils import is_point_on_ray


class Focus:
    def __init__(self, coord):
        self.coord_ = coord
        self.senders_ = []
        self.receivers_ = []
        self.intensity_ = 0

    def send_intensity(self, stop_event, sender, focus):
        while not stop_event.is_set():
            is_connected = sender.wait_for_connection()
            if is_connected:
                is_sent = sender.send([focus.intensity_])

    def check_and_submit_intersection(self, ray):
        if is_point_on_ray(ray, self.coord_):
            print("focus :", "mirror successfully adjusted", get_time_h_m_s())
            self.intensity_ += 1

    def receive_ray(self, stop_event, receiver, focus):
        while not stop_event.is_set():
            is_connected = receiver.wait_for_connection()
            if is_connected:
                ray = receiver.receive()
                if ray is not None:
                    focus.check_and_submit_intersection(ray[0])

    def run(self):

        threads_send = []
        threads_receive = []

        stop_receivers_event = threading.Event()
        stop_senders_event = threading.Event()

        for i in range(len(self.senders_)):
            threads_send.append(
                threading.Thread(target=self.send_intensity,
                                 args=(
                                     stop_senders_event, self.senders_[i], self)
                                 )
            )

        for i in range(len(self.receivers_)):
            threads_send.append(
                threading.Thread(target=self.receive_ray,
                                 args=(
                                     stop_receivers_event, self.receivers_[i], self)
                                 )
            )

        for thread in threads_send:
            thread.start()
        for thread in threads_receive:
            thread.start()

        time.sleep(transm_global_params.FOCUS_TIMEOUT)

        stop_receivers_event.set()
        stop_senders_event.set()

        for thread in threads_send:
            thread.join()
        for thread in threads_receive:
            thread.join()

        print("focus :", "I'm out", get_time_h_m_s())
