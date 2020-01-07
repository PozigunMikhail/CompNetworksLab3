import time
import transm_global_params
import threading
from utils import get_time_h_m_s


class LightSource:
    def __init__(self, coord):
        self.coord_ = coord
        self.delta_x_ = 1
        self.senders_ = []

    def send_coord(self, stop_event, sender, coord):
        while not stop_event.is_set():
            is_connected = sender.wait_for_connection()
            if is_connected:
                is_sent = sender.send(coord)

    def move_light_src(self):
        self.coord_[0] += self.delta_x_

    def run(self):
        threads_send = []
        stop_coord_send_event = threading.Event()

        for i in range(len(self.senders_)):
            threads_send.append(
                threading.Thread(target=self.send_coord,
                                 args=(stop_coord_send_event, self.senders_[i], self.coord_)
                                 )
            )

        for thread in threads_send:
            thread.start()

        start_time = time.time()
        start_standing = time.time()
        while time.time() - start_time < transm_global_params.LIGHT_SRC_TIMEOUT:
            if time.time() - start_standing > transm_global_params.LIGHT_SRC_MOVING_TIME_INTERVAL:
                print("light source :", "moving", get_time_h_m_s())
                self.move_light_src()
                start_standing = time.time()

        stop_coord_send_event.set()

        for thread in threads_send:
            thread.join()

        print("light source :", "I'm out", get_time_h_m_s())
