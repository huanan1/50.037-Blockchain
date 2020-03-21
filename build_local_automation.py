import os
import copy
import time
import sys
import getopt

# This file is only for local testing, if using multiple comps, don't use

# Parsing arguments when entered via CLI


def parse_arguments(argv):
    selfish = False
    double_spending = False
    mode = 1
    try:
        opts, args = getopt.getopt(
            argv, "hf:d:", ["selfish=", "double_spending="])
    # Only port and input is mandatory
    except getopt.GetoptError:
        print('build_miners_local_automation.py -f <1 if one selfish miner> -d <1 for double spending demo>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(
                'build_miners_local_automation.py -f <1 if one selfish miner> -d <1 for double spending demo>')
            sys.exit()
        elif opt in ("-f", "--selfish"):
            if arg == "1":
                selfish = True
        elif opt in ("-d", "--double_spending"):
            if arg == "1":
                double_spending = True
    return selfish, double_spending


# deploys single selfish miner if true
SELFISH, DOUBLE_SPENDING = parse_arguments(sys.argv[1:])

# Reads LOCAL ports to use via miner_ports.txt
f = open("ports_miner.txt", "r")
list_of_miner_ports = []
list_of_miner_ips = []
list_of_miner_wallets = []
for line in f:
    single_line = line.strip().split("\t")
    list_of_miner_ports.append(single_line[0])
    list_of_miner_ips.append(
        "127.0.0.1:" + single_line[0])
    if len(single_line) > 1:
        list_of_miner_wallets.append(single_line[1])
    else:
        list_of_miner_wallets.append("NO_WALLET")
f.close()

# Reads LOCAL ports to use via miner_ports.txt
f = open("ports_spv.txt", "r")
list_of_spv_ports = []
list_of_spv_ips = []
list_of_spv_wallets = []
for line in f:
    single_line = line.strip().split("\t")
    list_of_spv_ports.append(single_line[0])
    list_of_spv_ips.append(
        "127.0.0.1:" + single_line[0])
    if len(single_line) > 1:
        list_of_spv_wallets.append(single_line[1])
    else:
        list_of_spv_wallets.append("NO_WALLET")
f.close()

f = open("spv_ip.txt", "w+")
for i in list_of_spv_ips:
    f.write(i+"\n")
f.close()

if not SELFISH:
    f = open("miner_ip.txt", "w+")
    for i in list_of_miner_ips:
        f.write(i+"\n")
    f.close()
elif SELFISH:
    f = open("miner_ip.txt", "w+")
    count = 0
    for i in list_of_miner_ips:
        count+=1
        f.write(i+"\n")
        if count >=2:
            break
    f.close()
# Color args
colors = ['w', 'r', 'g', 'y', 'b', 'm', 'c']

if DOUBLE_SPENDING or SELFISH:
    print("Restricting to only 2 miners for demostration.")

for count, i in enumerate(list_of_miner_ports):
    # Reads file
    if not (DOUBLE_SPENDING or SELFISH):
        os.system("python3 miner_manage.py -p {0} -m miner_ip.txt -s spv_ip.txt -c {1} -w {2} -d 2&".format(
            i, colors[count % len(colors)], list_of_miner_wallets[count]))
    elif DOUBLE_SPENDING:
        if count == 0:
            os.system("python3 double_spend.py --port {0} --ip_other {1} --attacker --color r&".format(
                i, "127.0.0.1:"+list_of_miner_ports[1]
            ))
        elif count == 1:
            os.system("python3 double_spend.py --port {0} --ip_other {1} --color g&".format(
                i, "127.0.0.1:"+list_of_miner_ports[0]
            ))
        else:
            break
    elif SELFISH:
        if count == 0:
            os.system("python3 miner_manage.py -p {0} -m miner_ip.txt -s spv_ip.txt -c r -w {1} -d 2 -f 1&".format(
                i, list_of_miner_wallets[count]))
        elif count == 1:
            os.system("python3 miner_manage.py -p {0} -m miner_ip.txt -s spv_ip.txt -c g -w {1} -d 2&".format(
                i, list_of_miner_wallets[count]))
        else:
            break
    else:
        print("Wait, how did you reach here?")
    # Removes file for cleanup


for count, i in enumerate(list_of_spv_ports):
    os.system("python3 spv_client.py -p {0} -m miner_ip.txt -w {1}&".format(
        i, list_of_spv_wallets[count]))

time.sleep(1*(len(list_of_miner_ports) + len(list_of_spv_ports)))

os.system('rm miner_ip.txt spv_ip.txt')
