import os
import time
import pandas
import numpy

MBIT_TO_KBIT = 1024
TIME_INTERVAL = 5


def load_trace(trace_file_path, scale=40):
    # Time interval为带宽的时间粒度，scale为带宽乘的倍数
    #scale=1
    trace_list = []
    data = pandas.read_csv(trace_file_path)
    col = data['DL_bitrate']
    trace_array = numpy.array(col)
    for throughput in trace_array:
        if float(throughput) > 0.2:
            trace_list.append(float(throughput) * scale)
    print(numpy.array(trace_list) / MBIT_TO_KBIT)
    return trace_list


def change_throughput(throughput):
    # 输入的throughput 是Mbit的形式
    throughput /= MBIT_TO_KBIT
    print(throughput)
    os.system('sudo tc class change dev enp129s0f0 parent 1:0 classid 1:1 htb rate {}Mbit'.format(int(throughput)))
    return


# def change_throughput(throughput):
# 输入的throughput 是Mbit的形式，要换算成 Kbit
# throughput_in_kbit = throughput #/ MBIT_TO_KBIT
# print('bitrate:{}'.format(throughput_in_kbit))
# res=os.system('sudo tc qdisc change dev enp129s0f0 parent 1:3 handle 30: tbf rate {}kbit buffer {} limit {}'
#           .format(throughput_in_kbit, throughput_in_kbit, throughput_in_kbit))
# return


def set_fcc_trace(client_num):
    for trace_no in [14]:  # [6, 12, 13]:  #, 14, 15, 16, 17, 18, 19, 20]:  # range(1, 20+1):
        trace_list = load_trace('TraceFile/handledFCCS{}.log'.format(trace_no), scale=client_num)
        for thr in trace_list:
            time.sleep(5)
            change_throughput(thr)


def set_4g_trace(client_num):
    # trace_dict = {'train': [12, 16], 'static': [2, 4, 5, 13, 14], 'pedestrian': [15, 16]}
    trace_dict = {'pedestrian': [10]}  # [2, 4, 5, 13]}  # 'test': 14
    for place, trace_idx_list in trace_dict.items():
        trace_path = 'Dataset/{}'.format(place)
        for idx in trace_idx_list:
            trace_list = load_trace('{}/LTE_{}.csv'.format(trace_path, idx), scale=client_num)
            print("The trace_list is {}.".format(trace_list))
            for thr in trace_list:
                time.sleep(5)
                change_throughput(thr)


def set_fix_trace(single_bw, client_num):
    while True:
        time.sleep(60)
        change_throughput(single_bw * client_num)


if __name__ == "__main__":

    # ------------------------------------------QSEC 实验--------------------------------------------
    # os.system("sudo tc qdisc del dev enp129s0f0 root")
    # os.system("sudo tc qdisc add dev enp129s0f0 root handle 1: prio")
    # os.system("sudo tc qdisc add dev enp129s0f0 parent 1:3 handle 30: tbf rate 61440kbit buffer 61440 limit 61440")
    # os.system("sudo tc qdisc add dev enp129s0f0 parent 30:1 handle 31: netem delay 30ms 3ms")
    # os.system(
    #     "sudo tc filter add dev enp129s0f0 protocol ip parent 1:0 prio 3 u32 match ip dst 10.103.11.72 flowid 1:3")

    # set_4g_trace(client_num=40)
    # # set_fcc_trace(client_num=40)
    # -----------------------------------------------------------------------------------------------
    # ---------------------------------------Steward 实验--------------------------------------------
    os.system("sudo tc qdisc del dev enp129s0f0 root")
    # os.system("sudo tc qdisc add dev enp129s0f0 root handle 1: prio")
    os.system("sudo tc qdisc add dev enp129s0f0 root handle 1: htb default 1")
    os.system("sudo tc class add dev enp129s0f0 parent 1:0 classid 1:1 htb rate 20Mbit")
    os.system(
        "sudo tc filter add dev enp129s0f0 parent 1:0 protocol ip prio 100 u32 match ip dst 10.103.11.72 flowid 1:1")
    # os.system(
    #    "sudo tc filter add dev enp129s0f0 parent 1:0 protocol ip prio 100 u32 match ip dst 219.223.189.206 flowid 1:1")

    while True:
        set_4g_trace(client_num=30)
        # set_fcc_trace(client_num=60)
        # set_fix_trace(4, 60)
    # ---------------------------------------Steward 实验--------------------------------------------
    # os.system("sudo tc qdisc del dev enp129s0f0 root")
    # os.system("sudo tc qdisc add dev enp129s0f0 root handle 1: prio")
    # os.system("sudo tc qdisc add dev enp129s0f0 parent 1:3 handle 30: tbf rate 61440kbit buffer 61440 limit 61440")
    # os.system("sudo tc qdisc add dev enp129s0f0 parent 30:1 handle 31: netem delay 30ms 3ms")
    # os.system(
    #     "sudo tc filter add dev enp129s0f0 protocol ip parent 1:0 prio 3 u32 match ip dst 10.103.11.72 flowid 1:3")
    # os.system(
    #     "sudo tc filter add dev enp129s0f0 protocol ip parent 1:0 prio 3 u32 match ip dst 10.103.11.73 flowid 1:3")

    # while True:
    # set_4g_trace(client_num=30)
    # set_fcc_trace(client_num=60)
    # set_fix_trace(4, 60)
    # ----------------------------------------------------------------------------------------------

    # ------------------------------------------临时测试用--------------------------------------------
    # os.system("sudo tc qdisc del dev enp129s0f0 root")
    # os.system("sudo tc qdisc add dev enp129s0f0 root handle 1: prio")
    # os.system("sudo tc qdisc add dev enp129s0f0 parent 1:3 handle 30: tbf rate 10240kbit buffer 10240 limit 10240")
    # os.system("sudo tc qdisc add dev enp129s0f0 parent 30:1 handle 31: netem delay 30ms 3ms")
    # os.system(
    #     "sudo tc filter add dev enp129s0f0 protocol ip parent 1:0 prio 3 u32 match ip dst 219.223.189.207 flowid 1:3")
    # os.system(
    #     "sudo tc filter add dev enp129s0f0 protocol ip parent 1:0 prio 3 u32 match ip dst 219.223.189.206 flowid 1:3")
    # -----------------------------------------------------------------------------------------------

    # -----------------------------------------分类测试用---------------------------------------------
    # os.system("sudo tc qdisc del dev enp129s0f0 root")
    # os.system("sudo tc qdisc add dev enp129s0f0 root handle 1: htb default 1")
    # os.system("sudo tc class add dev enp129s0f0 parent 1:0 classid 1:1 htb rate 20Mbit")
    # os.system(
    #    "sudo tc filter add dev enp129s0f0 parent 1:0 protocol ip prio 100 u32 match ip dst 219.223.189.207 flowid 1:1")
    # os.system("sudo tc class add dev enp129s0f0 parent 1:0 classid 1:2 htb rate 50Mbit")
    # os.system(
    #    "sudo tc filter add dev enp129s0f0 parent 1:0 protocol ip prio 100 u32 match ip dst 219.223.189.206 flowid 1:2")
    # -----------------------------------------------------------------------------------------------

