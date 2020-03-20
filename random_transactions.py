import requests
import random
import json
import time

f = open("miner_ports.txt", "r")
list_of_miner_ports = []
list_of_miner_ips = []
list_of_miner_wallets = []
list_of_miner_public_key = []
for line in f:
    single_line = line.strip().split("\t")
    list_of_miner_ports.append(single_line[0])
    list_of_miner_ips.append(
        "127.0.0.1:" + single_line[0])
    list_of_miner_public_key.append(single_line[2])
    if len(single_line) > 1:
        list_of_miner_wallets.append(single_line[1])
    else:
        list_of_miner_wallets.append("NO_WALLET")
f.close()

while True:
    miner_ip = random.choice(list_of_miner_ips)
    public_key = random.choice(list_of_miner_public_key)
    amount = random.randint(1,100)
    # print(requests.get("http://{}/send_transaction?receiver={}&amount={}".format(miner_ip, public_key, amount)).text)
    response = json.loads(requests.get("http://{}/send_transaction?receiver={}&amount={}".format(miner_ip, public_key, amount)).text)
    print(response)
    time.sleep(1.5)
