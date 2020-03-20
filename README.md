# 50.037-Blockchain

## SUTDCoin
## Setting up the environment
```
python3 -m venv venv
source venv/bin/activate
pip3 install wheel
pip3 install -r requirements.txt
```

## Usage
All demonstrations can either be done locally or across multiple computers. The instructions here are for running on a single machine.


| Command                                         | Demo                      |
| ----------------------------------------------- | ------------------------  |
| `python3 build_miners_local_automation.py`      | Multiple honest miners    |
| `python3 build_miners_local_automation.py -s 1` | One miner will be selfish |
| `python3 build_miners_local_automation.py -d 1` | Double-spending           |


## Documentation of displayed features
###	Simulate miners running Nakamoto consensus and making transactions
Features:
- new blocks arrive every few (2-5) seconds
- coinbase transaction of 100 SUTDcoins
- transactions occur
- validation checks (no double spending, validated sender, sender must have enough money)
- forks resolved

### Interaction of SPV clients with miners
Features:
- associated key pairs
- receive block headers
- receive transactions and verify them
- send transactions


### Double-spending attack
1. At a specified block in the code, the attacker will send a transaction.
2. Right after the transaction in 1. is sent, the attacker empties his account by creating a new address and transferring the money to the new account. Subsequent mining will also be carried out under the new address.
3. When at least one block has been mined since the transaction, the attacker will start to mine blocks, publishing them after three blocks has been mined. If the attack is not successful, the attacker continues mining blocks for his intended fork and publishes them again after 3 blocks. Since attacker has majority hashing power, attacker will eventually overwrite block with bad transaction in 1.

#### Example output
<img width="473" alt="double_spending" src="https://user-images.githubusercontent.com/28921108/77196109-b1d56f80-6b1d-11ea-9db2-3d2aad71288b.PNG">
- Block following `000005d864` was originally `000005b93b` but is `0000061ea` after attack

### Selish-mining

## Major differences between Bitcoin and SUTDcoin
- UTXO vs Addr:Balance
- Dynamic vs Static difficulty
- Name
- _add more and put in a table_
