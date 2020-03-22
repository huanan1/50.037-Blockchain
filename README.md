# Group: GOLD EXPERIENCE
## SUTDcoin
## Setting up the environment
```
python3 -m venv venv
source venv/bin/activate
pip3 install wheel
pip3 install -r requirements.txt
```

## Usage
All demonstrations can either be done locally or across multiple computers.

### Automated local deployment
`build_miners_local_automation.py` allows for quick local deployment and demonstration of the SUTDCoin network. It will run as many instances as there are in `ports_miner.txt` for miners and `ports_spv.txt` for SPV Clients. The formatting of both files will be touched on later.

It runs both `miner_manage.py` and `spv_client.py` with preset arguments, some of which are taken from the `ports_*.txt` files.

| Command                                         | Demo                   |
| ----------------------------------------------- | ---------------------- |
| `python3 build_miners_local_automation.py`      | Multiple honest miners |
| `python3 build_miners_local_automation.py -s 1` | Selfish mining demo    |
| `python3 build_miners_local_automation.py -d 1` | Double-spending demo   |

#### ports_*.txt format
Both `ports_miner.txt` and `ports_spv.txt` have identical formats.

The format in the current repo is as follows:
`<port_number>\t<private_key>\t<public_key>\n`

**Note:** Ensure 'tab character' is in between each field, as some IDEs might do 4 spaces

- `<port_number>` field is mandatory, and the code will run as many instances as there are ports in the file
- `<private_key>` field is not mandatory, as the `miner_manage.py` and `spv_client.py` files will generate their own private keys when no input is detected
- `<public_key>` field is not used by any of the codes, and is more of a reference for the user for testing

### Network deployment
There are two kinds of clients to be deployed, miners and SPV clients, using `miner_manage.py` and `spv_client.py` respectively.

#### Miner
`miner_manage.py`
| Argument          | Description                                                | Example      | Additional Notes                                                                         |
| ----------------- | ---------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------- |
| -p, --port        | Port number of miner to run on                             | 25100        | **(Mandatory)**                                                                          |
| -m, --iminerfile  | Directory of list of other miner IPs (10.0.2.5:2134)       | miner_ip.txt | **(Optional)**                                                                           |
| -s, --ispvfile    | Directory of list of other miner IPs (10.0.2.6:213)        | spv_ip.txt   | **(Optional)**                                                                           |
| -c, --color       | Color of text                                              | r            | **(Optional)** Available colors: Red, White(Default), Green, Yellow, Blue, Magenta, Cyan |
| -d, --description | Configures how much information to print to console        | 2            | **(Optional)** 1(default): More information; 2: Less information                         |
| -f, --selfish     | Configures the miner to become a selfish miner             | 1            | **(Optional)** 0(Default): Honest miner; 1: Selfish miner                                |
| -w, --wallet      | Sets the wallet's private key, if empty, generates new key | b0cfe80...   | **(Optional)**                                                                           |

Sample startup:
- `miner_manage.py -p 2200`
- `miner_manage.py -p 1500 -m miner_ip.txt -c g -s spv_ip.txt -d 2 -w b0cfe80dbda0d882b6d517321b3eb3343c48864ad097c5df`
- `miner_manage.py -p 1200 -m miner_ip.txt -c r -f 1`

#### SPV
`spv_client.py`
| Argument          | Description                                                | Example      | Additional Notes                                                                         |
| ----------------- | ---------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------- |
| -p, --port        | Port number of SPV to run on                             | 25200        | **(Mandatory)**                                                                          |
| -m, --iminerfile  | Directory of list of other miner IPs (10.0.2.5:2134)       | miner_ip.txt | **(Mandatory)**                                                                           |
| -w, --wallet      | Sets the wallet's private key, if empty, generates new key | b0cfe80...   | **(Optional)**                                                                           |

Sample startup:
- `spv_client.py -p 2300 -m miner_ip.txt`
- `spv_client.py -p 1500 -m miner_ip.txt -w c218953cd1e1ebff4cead74f25420dcffd6239ed1f48796f`


## Documentation of displayed features
###	Simulate miners running Nakamoto consensus and making transactions
Implemented features:
- new blocks arrive every few (2-5) seconds
  - static difficulty of `00000f`
- coinbase transaction of 100 SUTDcoins
  - under `create_merkle` method in `miner.py`
- transactions occur randomly
  - see `random_transactions.py`
- validation checks (no double spending, validated sender, sender must have enough money)
  - see `network_block` method in `blockchain.py`
- forks resolved
  - Example:
  - ![fork](https://user-images.githubusercontent.com/28921108/77232316-36d28e80-6bdb-11ea-83a9-4d76e346a78e.png)
  red miner originally had the block `0000ae565b` after `000044cc2f` while white miner had the block `00006e7b8c`. The fork is only resolved when one chain becomes longer. The miner(s) with the shorter chain will stop mining on that chain and work on the longer one instead.
  - ![fork_resolved](https://user-images.githubusercontent.com/28921108/77232319-3934e880-6bdb-11ea-83b1-35d231c8def1.png)
  in this case, the red miner stopped working on a chain with his original block (`0000ae56fb`) and adopts the longer chain which builts on white's mined block (`00006e7b8c`)

### Interaction of SPV clients with miners
Implemented features:
- associated key pairs
- receive block headers
- receive transactions and verify them
- send transactions


### Double-spending attack
1. At a specified block in the code, the attacker will send a transaction.
2. Right after the transaction in 1. is sent, the attacker empties his account by creating a new address and transferring the money to the new account. Subsequent mining will also be carried out under the new address.
3. When at least one block has been mined since the transansaction in 1, the attacker will start to mine blocks with the prev header hash being the block before the one with the transaction we would like to void. The attacker publishes the blocks after three blocks has been mined. If the attack is not successful, the attacker continues mining blocks for his intended fork and publishes them again after 3 blocks. Since attacker has majority hashing power, attacker will eventually overwrite block with bad transaction in 1.

#### Example output
<img width="473" alt="double_spending" src="https://user-images.githubusercontent.com/28921108/77196109-b1d56f80-6b1d-11ea-9db2-3d2aad71288b.PNG">

- Block following `000005d864` was originally `000005b93b` but is `0000061ea` after attack

### Selish-mining
| Selfish miner | Honest miner |
| ------------- | ------------ |
| 0 coins       | 0 coins      |
| 400 coins     | 200 coins    |
| 500 coins     | 300 coins    |
| 800 coins     | 100 coins    |
| 1200 coins    | 200 coins    |
| 1300 coins    | 300 coins    |
| 1700 coins    | 500 coins    |
| 2000 coins    | 700 coins    |
| 2400 coins    | 1200 coins   |
| 2700 coins    | 100 coins    |
| 3300 coins    | 400 coins    |
| 3400 coins    | 700 coins    |
| 3700 coins    | 1200 coins   |
| 3400 coins    | 900 coins    |
| 4000 coins    | 1200 coins   |
| 4500 coins    | 1200 coins   |
| 4700 coins    | 1700 coins   |
| 5200 coins    | 2000 coins   |
| 5500 coins    | 2000 coins   |
- __DESCRIPTION of what a selfish miner does, how it manages to win despite not necesarily having majority hashing power__


## Major differences between Bitcoin and SUTDcoin
| Property          | Bitcoin                        | SUTDcoin        |
| ----------------- | ------------------------------ | --------------- |
| Name              | Bitcoin                        | SUTDcoin        |
| Difficulty        | Dynamic, adjusts every 2 weeks | Static          |
| Transaction model | UTXO                           | Address:Balance |
