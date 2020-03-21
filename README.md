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
All demonstrations can either be done locally or across multiple computers. The instructions here are for running on a single machine.


| Command                                         | Demo                      |
| ----------------------------------------------- | ------------------------  |
| `python3 build_miners_local_automation.py`      | Multiple honest miners    |
| `python3 build_miners_local_automation.py -s 1` | One miner will be selfish |
| `python3 build_miners_local_automation.py -d 1` | Double-spending           |


## Documentation of displayed features
###	Simulate miners running Nakamoto consensus and making transactions
Implemented features:
- new blocks arrive every few (2-5) seconds
  - static difficulty of `00000f`
- coinbase transaction of 100 SUTDcoins
  - under `create_merkle` method in `miner.py`
- transactions occur randomly
- validation checks (no double spending, validated sender, sender must have enough money)
  - see `network_block` method in `blockchain.py`
- forks resolved
  - Example:
  - ![fork](https://user-images.githubusercontent.com/28921108/77232316-36d28e80-6bdb-11ea-83a9-4d76e346a78e.png)
  red miner originally had the block `0000ae565b` after `000044cc2f` while white miner had the block `00006e7b8c`. The fork is only resolved when one chain becomes longer so the miner who mined a block on the short chain will drop it and work on the longer chain instead
  - ![fork_resolved](https://user-images.githubusercontent.com/28921108/77232319-3934e880-6bdb-11ea-83b1-35d231c8def1.png)
  in this case, the red miner dropped his original block (`0000ae56fb` and adopts the longer chain which builts on white's mined block)

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

## Major differences between Bitcoin and SUTDcoin
| Property           | Bitcoin                               | SUTDcoin                 |
| -----------------  | ------------------------------------- | ------------------------ |
| Name               | Bitcoin                               | SUTDcoin                 |
| Difficulty         | Dynamic, adjusts every 2 weeks        | Static                   |
| Transaction model  | UTXO                                  | Address:Balance          |

