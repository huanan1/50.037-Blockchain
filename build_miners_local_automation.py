import os
import copy
import time
import sys
import getopt

# This file is only for local testing, if using multiple comps, don't use

# Parsing arguments when entered via CLI
def parse_arguments(argv):
    selfish = False
    mode = 1
    try:
        opts, args = getopt.getopt(
            argv, "hs:", ["selfish="])
    # Only port and input is mandatory
    except getopt.GetoptError:
        print('build_miners_local_automation.py -s <1 if one selfish miner>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('build_miners_local_automation.py -s <1 if one selfish miner>')
            sys.exit()
        elif opt in ("-s", "--selfish"):
            if arg=="1":
                selfish = True
    return selfish
# deploys single selfish miner if true
SELFISH = parse_arguments(sys.argv[1:])

# Reads LOCAL ports to use via miner_ports.txt
f = open("miner_ports.txt", "r")
list_of_miner_ports = []
list_of_miner_ips = []
for line in f:
    list_of_miner_ports.append(line.strip())
    list_of_miner_ips.append(
        "127.0.0.1:" + line)
f.close()

# Color args
colors = ['w','r','g','y','b','m','c']
for count, i in enumerate(list_of_miner_ports):
    list_of_partner_miners = copy.deepcopy(list_of_miner_ips)
    del list_of_partner_miners[count]
    # Creates a file called partner_miner_ip.txt
    f = open("partner_miner_ip.txt", "w+")
    f.writelines(list_of_partner_miners)
    f.close()
    # Reads file
    if not SELFISH:
        os.system("python3 miner.py -p {0} -m partner_miner_ip.txt -c {1} -d 2&".format(i, colors[count%len(colors)]))
    else:
        if count == 0:
            os.system("python3 miner.py -p {0} -m partner_miner_ip.txt -c {1} -d 2 -s 1&".format(i, colors[count%len(colors)]))
        else:
            os.system("python3 miner.py -p {0} -m partner_miner_ip.txt -c {1} -d 2&".format(i, colors[count%len(colors)]))
    time.sleep(2)
    # Removes file for cleanup
    os.system('rm partner_miner_ip.txt')
