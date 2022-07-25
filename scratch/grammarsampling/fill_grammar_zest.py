import numpy as np
from scipy.stats import geom


def numToBytes(bytes_a) -> bytes:
    bytes_a = (np.array(bytes_a) % 256).tolist()
    final_bytes = [f'\\x{y:02x}' for y in bytes_a]
    return R"".join(final_bytes)


def generate_indiv(count, mean, itr_str=" byte"):
    weight = geom(1 / mean).pmf(count)
    my_str = "_" + str(count) + "_from" + str(mean) + "Geo"
    res_str = my_str

    for i in range(count):
        res_str += itr_str

    return "'" + res_str + "' : " + str(weight)


def generate_bytes_from_mean():
    d = {}  # e.g. key = _1_from10Geo, value = [0,0,0,0,0,0,1]
    with open("goal_from_mean_geo.txt") as f:
        for line in f:
            (key, val) = line.split("split")
            temp_val = val.replace("\n", "").replace("byteArrayOf", "").replace("(", "").strip(')').split(', ')
            temp_val = [int(x) for x in temp_val]
            d[key.strip()] = temp_val

    result = {}
    for k in d.keys():
        result[k] = numToBytes(d[k])
        print(k + ":\n " + "  - \'\"" + result[k] + "\"\'")


def generate_weights():
    itr_str = " byte"
    mean_list = [10]
    for x in mean_list:
        print("mean: {}".format(x))
        for i in range(1, 2 * x + 1):
            new_str = generate_indiv(i, x, itr_str)
            print(new_str)


if __name__ == "__main__":
    # generate_bytes_from_mean()
    generate_weights()
