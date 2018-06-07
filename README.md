# CoinJoinXT 
In a nutshell: do cooperative contracts over multiple transactions, including CoinJoins but boosting deniability cf a single CoinJoin, with no extra
interactivity (time-wise) overhead. See BIP141 for the main point about the ability to sign in advance. More docs here later.

Note that this repo is marked "POC" because it is, in fact, just a proof of concept, there is no intent to create fully usable code at this point.
Using [joinmarket-clientserver](https://github.com/Joinmarket-Org/joinmarket-clientserver) as a backend for the bitcoin stuff,
but note the `for-occ-poc` branch is needed.
Install in development mode, then you can just switch to that branch.

(As you can see from the last sentence, this is just a bunch of monkey patching. I told you it was POC!).

The syntax is:

```
python occreceiver.py wallet-name server port
```

```
python occsender.py wallet-name server port
```

Just funds with necessary utxos on regtest to make it work; don't try it on anything else yet.
The input utxos are p2sh-p2wpkh (funded from segwit Joinmarket wallets, compatible, see above), and
the 2 of 2 co-owned outputs are native p2wsh.

Publishes whole tx chain to `occresults.txt` so you can take a look.
Optionally broadcasts everything directly to chain without waiting if you set `broadcast_all = 1` in the config under `POLICY`.
Otherwise use what's in `occresults.txt` to broadcast them manually, in
sequence, using `sendrawtransaction`. Config and wallets are in `~/.CoinJoinXT/*`

