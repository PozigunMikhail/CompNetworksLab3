import time
import random
import math
import transm_global_params


def get_delta_ms(start, finish):
    diff = finish - start
    millis = diff.days * 24 * 60 * 60 * 1000
    millis += diff.seconds * 1000
    millis += diff.microseconds / 1000
    return millis


def get_time_h_m_s():
    strings = time.strftime("%Y,%m,%d,%H,%M,%S")
    t = strings.split(',')
    return "time: " + t[3] + ":" + t[4] + ":" + t[5]


def split_string(str, substr_count):
    substr_len = len(str) // substr_count
    for i in range(0, len(str), substr_len):
        yield str[i: i + substr_len]


def flip_biased_coin(p):
    return True if random.random() < p else False


def rotate(vector, angle):
    cos = math.cos(angle)
    sin = math.sin(angle)
    rotated_vector = [
        vector[0] * cos - vector[1] * sin,
        vector[0] * sin + vector[1] * cos
    ]
    vector[0] = rotated_vector[0]
    vector[1] = rotated_vector[1]


def normalize(vector):
    len = math.sqrt(vector[0] ** 2 + vector[1] ** 2)
    vector[0] /= len
    vector[1] /= len


def get_distance(ray, point):
    p1 = ray.point_
    p2 = [p1[0] + 1000 * ray.vector_[0],
          p1[1] + 1000 * ray.vector_[1]]
    return math.fabs((p2[1] - p1[1]) * point[0] - (p2[0] - p1[0]) * point[1] + p2[0] * p1[1] - p2[1] * p1[0]) / \
           math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def get_reflected_vector(dir_from_light, normal):
    proj_dir_to_normal = dir_from_light[0] * normal[0] + dir_from_light[1] * normal[1]
    return [
        dir_from_light[0] - 2 * proj_dir_to_normal * normal[0],
        dir_from_light[1] - 2 * proj_dir_to_normal * normal[1]
    ]


def is_point_on_ray(ray, point):

    p1 = ray.point_
    p2 = [p1[0] + ray.vector_[0],
          p1[1] + ray.vector_[1]]
    is_on_line = False
    p1p2 = [p2[0] - p1[0], p2[1] - p1[1]]
    p1c = [point[0] - p1[0], point[1] - p1[1]]
    # if math.fabs(p1p2[0] * p1c[1] - p1p2[1] * p1c[0]) < transm_global_params.FOCUS_HITTING_PRECISION:
    #     is_on_line = True
    distance = get_distance(ray, point)
    # print("focus :", "distance:", get_distance(ray, point), get_time_h_m_s())
    if distance < transm_global_params.FOCUS_HITTING_PRECISION:
        is_on_line = True
    if is_on_line:
        dot_product = p1p2[0] * p1c[0] + p1p2[1] * p1c[1]
        if math.fabs(dot_product) < transm_global_params.FOCUS_HITTING_PRECISION or dot_product > 0:
            # print("focus :", "final distance:", get_distance(ray, point), get_time_h_m_s())
            # print("focus :", "final dot:", dot_product, get_time_h_m_s())
            # print("focus :", "final cross:", p1p2[0] * p1c[1] - p1p2[1] * p1c[0], get_time_h_m_s())
            return True
    return False
