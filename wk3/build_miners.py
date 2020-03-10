import os
import copy
import time

# define the name of the directory to be created
f = open("miner_ports.txt", "r")
list_of_miner_ports = []
list_of_miner_ips = []
for line in f:
    list_of_miner_ports.append(line.strip())
    list_of_miner_ips.append(
        "127.0.0.1:" + line)
f.close()

for count, i in enumerate(list_of_miner_ports):
    list_of_partner_miners = copy.deepcopy(list_of_miner_ips)
    del list_of_partner_miners[count]
    f = open("partner_miner_ip.txt", "w+")
    f.writelines(list_of_partner_miners)
    print(i, list_of_partner_miners)
    f.close()
    os.system("python3 miner.py -p {} -i partner_miner_ip.txt &".format(i))
    time.sleep(1.5)
    os.system('rm partner_miner_ip.txt')
