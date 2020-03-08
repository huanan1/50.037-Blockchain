import os
import copy

# define the name of the directory to be created

path = "generated_miners"
os.system('rm -rf ' + path)

try:
    os.mkdir(path)
except:
    pass

os.system('cp *.py *.txt ' + path)

file = open("miner_ports.txt", "r") 
list_of_miner_ports=[]
list_of_miner_ips=[]
for line in file: 
    list_of_miner_ports.append(line.strip())
    list_of_miner_ips.append("INV_COMMA_REPLACE127.0.0.1:" + line.strip() + "INV_COMMA_REPLACE")

for count, i in enumerate(list_of_miner_ports):
    list_of_partner_miners = copy.deepcopy(list_of_miner_ips)
    del list_of_partner_miners[count]
    os.system('cp miner.py {0}/miner_{1}.py'.format(path, i))
    os.system("sed -i 's/\"$MY_IP_HERE\"/\"127.0.0.1:{1}\"/' {0}/miner_{1}.py".format(path, i))
    os.system("sed -i 's/\"$LIST_OF_MINER_IP_HERE\"/{2}/' {0}/miner_{1}.py".format(path, i, list_of_partner_miners))
    os.system("sed -i 's/INV_COMMA_REPLACE/\"/g' {0}/miner_{1}.py".format(path, i))
    os.system("python3 {0}/miner_{1}.py &".format(path, i))