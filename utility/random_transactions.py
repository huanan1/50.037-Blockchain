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
f = open("../ports_miner.txt", "r")
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
    f = open("../ports_spv.txt", "r")
f.close()

while True:
    sender, public_key = None, None
    while sender == public_key:
        miner_ip = random.choice(list_of_ips)
        sender = list_of_public_keys[list_of_ips.index(miner_ip)]
        public_key = random.choice(list_of_public_keys)
    amount = random.randint(1, 100)
    response = json.loads(requests.post(
        "http://{}/send_transaction?receiver={}&amount={}".format(miner_ip, public_key, amount)).text)
    print("Sending {} SUTDCoins from {} to {}, message from server:\n{}\n".format(amount, sender[:10], public_key[:10], response))
    time.sleep(float(random.randint(1, 100)/100))
