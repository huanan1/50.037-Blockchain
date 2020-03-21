import requests
import random
import json
import time
import ecdsa
import binascii


list_of_ports = []
list_of_ips = []
list_of_wallets = []
list_of_public_keys = []
f = open("ports_miner.txt", "r")
for i in range(2):
    for line in f:
        single_line = line.strip().split("\t")
        list_of_ports.append(single_line[0])
        list_of_ips.append(
            "127.0.0.1:" + single_line[0])
        list_of_wallets.append(single_line[1])
        for i in list_of_wallets:
            list_of_public_keys.append(binascii.hexlify(ecdsa.SigningKey.from_string(
                binascii.unhexlify(bytes(i, 'utf-8'))).get_verifying_key().to_string()).decode())
    f.close()
    f = open("ports_spv.txt", "r")
f.close()

while True:
    try:
        amt_selfish = json.loads(requests.get(
        "http://{}/account_balance".format(list_of_ips[0])).text)["amount"]
    except:
        amt_selfish = 0
    try:
        amt_honest_1 = json.loads(requests.get(
        "http://{}/account_balance".format(list_of_ips[1])).text)["amount"]
    except:
        amt_honest_1 = 0
    print("Selfish miner: {} coins\tHonest miner: {} coins".format(amt_selfish, amt_honest_1))
    time.sleep(1)
