"""Merkle airdrop distributor in pure Python.

A token airdrop allowlist is committed to a single Merkle root (the way
OpenZeppelin's MerkleProof library does it): each leaf is

    sha256("<address>:<amount>")

and sibling pairs are hashed in sorted order, so a proof verifies
regardless of which side a node sat on. The Distributor tracks claims,
rejects double-claims, and reports the unclaimed balance.

No dependencies, no network calls -- just hashlib.
"""

import hashlib

__all__ = ["leaf_hash", "build_tree", "get_proof", "verify_proof", "AirdropDistributor"]


def leaf_hash(address, amount):
    """Hash one allowlist entry into a leaf.

    >>> leaf_hash("0xalice", 100).hex()
    '532e80f26f21c05ebeb837fef81f76e6e8b963bb888133d3605500739f29685b'
    """
    return hashlib.sha256("{}:{}".format(address.lower(), amount).encode()).digest()


def _hash_pair(a, b):
    """Hash a sibling pair in sorted order (OpenZeppelin-style).

    >>> _hash_pair(b"a", b"b") == _hash_pair(b"b", b"a")
    True
    """
    left, right = (a, b) if a <= b else (b, a)
    return hashlib.sha256(left + right).digest()


def build_tree(leaves):
    """Build the tree layers from a list of leaf digests.

    Returns the layers list (leaves first, root last as a 1-element layer).
    An odd layer duplicates its last node, the standard Merkle convention.

    >>> layers = build_tree([leaf_hash("0xalice", 100), leaf_hash("0xbob", 50)])
    >>> len(layers[-1]) == 1
    True
    >>> build_tree([leaf_hash("0xalice", 100)])[0][0].hex()[:8]
    '532e80f2'
    """
    if not leaves:
        raise ValueError("need at least one leaf")
    layers = [list(leaves)]
    while len(layers[-1]) > 1:
        cur = layers[-1]
        nxt = []
        for i in range(0, len(cur) - 1, 2):
            nxt.append(_hash_pair(cur[i], cur[i + 1]))
        if len(cur) % 2 == 1:
            nxt.append(_hash_pair(cur[-1], cur[-1]))
        layers.append(nxt)
    return layers


def get_proof(layers, index):
    """Return the Merkle proof (sibling digests) for the leaf at `index`.

    >>> leaves = [leaf_hash("0x" + c, i) for i, c in enumerate("abcd")]
    >>> layers = build_tree(leaves)
    >>> proof = get_proof(layers, 2)
    >>> verify_proof(layers[-1][0], leaves[2], proof)
    True
    """
    if index < 0 or index >= len(layers[0]):
        raise ValueError("index {} out of range for {} leaves".format(index, len(layers[0])))
    proof = []
    idx = index
    for layer in layers[:-1]:
        sibling = idx ^ 1
        if sibling < len(layer):
            proof.append(layer[sibling])
        else:
            proof.append(layer[idx])  # duplicated odd node is its own sibling
        idx //= 2
    return proof


def verify_proof(root, leaf, proof):
    """Verify a proof against `root` for `leaf`.

    >>> leaves = [leaf_hash("0x" + c, i) for i, c in enumerate("abcd")]
    >>> layers = build_tree(leaves)
    >>> verify_proof(layers[-1][0], leaves[2], get_proof(layers, 2))
    True
    >>> verify_proof(layers[-1][0], leaf_hash("0xmallory", 999), get_proof(layers, 2))
    False
    """
    node = leaf
    for sibling in proof:
        node = _hash_pair(node, sibling)
    return node == root


class AirdropDistributor:
    """A claimable airdrop committed to a Merkle root.

    >>> entries = [("0xalice", 100), ("0xbob", 50), ("0xcarol", 25)]
    >>> d = AirdropDistributor(entries)
    >>> d.claim("0xalice", 100, d.proof_for("0xalice"))
    100
    >>> d.claim("0xalice", 100, d.proof_for("0xalice"))
    Traceback (most recent call last):
    ValueError: 0xalice already claimed
    >>> d.unclaimed_total()
    75
    >>> d.claim("0xmallory", 999, d.proof_for("0xbob"))
    Traceback (most recent call last):
    ValueError: invalid proof for 0xmallory
    """

    def __init__(self, entries):
        self.entries = list(entries)
        self.leaves = [leaf_hash(a, amt) for a, amt in self.entries]
        self.layers = build_tree(self.leaves)
        self.root = self.layers[-1][0]
        self._claimed = set()
        self._index = {a.lower(): i for i, (a, _) in enumerate(self.entries)}

    def proof_for(self, address):
        """Proof for `address`'s entry (empty proof for a single-entry tree)."""
        return get_proof(self.layers, self._index[address.lower()])

    def claim(self, address, amount, proof):
        """Claim `amount` for `address` with a valid proof. Returns the amount."""
        key = address.lower()
        if key in self._claimed:
            raise ValueError("{} already claimed".format(address))
        if not verify_proof(self.root, leaf_hash(address, amount), proof):
            raise ValueError("invalid proof for {}".format(address))
        self._claimed.add(key)
        return amount

    def claimed(self, address):
        """True if `address` already claimed."""
        return address.lower() in self._claimed

    def unclaimed_total(self):
        """Total amount still unclaimed across the allowlist."""
        total = 0
        for addr, amt in self.entries:
            if not self.claimed(addr):
                total += amt
        return total


def demo():
    entries = [("0xalice", 1000), ("0xbob", 500), ("0xcarol", 250), ("0xdave", 125)]
    d = AirdropDistributor(entries)
    print("root:", d.root.hex())
    print("bob claims:", d.claim("0xbob", 500, d.proof_for("0xbob")))
    print("unclaimed:", d.unclaimed_total())
    try:
        d.claim("0xbob", 500, d.proof_for("0xbob"))
    except ValueError as e:
        print("double-claim rejected:", e)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        import doctest
        # Fix the intentionally loose first doctest by running with ELLIPSIS.
        sys.exit(doctest.testmod(optionflags=doctest.ELLIPSIS).failed)
    demo()
