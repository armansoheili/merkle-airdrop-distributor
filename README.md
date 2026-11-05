# merkle-airdrop-distributor

Merkle-tree airdrop distributor in pure Python (zero dependencies).

An allowlist of `(address, amount)` entries is committed to a single Merkle
root. Each leaf is `sha256("<address>:<amount>")` and sibling pairs are
hashed in sorted order, following the OpenZeppelin `MerkleProof` convention,
so a proof verifies regardless of which side a node sat on.

## Features

- `leaf_hash` / `build_tree` / `get_proof` / `verify_proof` — the tree itself
- `AirdropDistributor` — claims with double-claim rejection, proof
  verification, and an unclaimed-balance total
- Odd layers duplicate their last node (the standard Merkle convention)

## Usage

```python
from airdrop import AirdropDistributor

d = AirdropDistributor([("0xalice", 1000), ("0xbob", 500)])
d.claim("0xbob", 500, d.proof_for("0xbob"))  # -> 500
d.unclaimed_total()                          # -> 1000
```

## Run

```sh
python3 airdrop.py            # demo
python3 airdrop.py --test     # doctests
```
