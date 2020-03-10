import os
import copy
import time

# This file is only for local testing, if using multiple comps, don't use
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
    os.system("python3 miner.py -p {0} -i partner_miner_ip.txt -c {1} -m 2&".format(i, colors[count%len(colors)]))
    time.sleep(2)
    # Removes file for cleanup
    os.system('rm partner_miner_ip.txt')
