# CoinJoinXT 

See https://gist.github.com/AdamISZ/a5b3fcdd8de4575dbb8e5fba8a9bd88c for the base idea.

In a nutshell: do cooperative contracts over multiple transactions, including CoinJoins but boosting deniability cf a single CoinJoin, with no extra
interactivity (time-wise) overhead. See BIP141 for the main point about the ability to sign in advance. More docs here later.

Note that this repo is marked "POC" because it is, in fact, just a proof of concept, there is no intent to create fully usable code at this point.
Using [joinmarket-clientserver](https://github.com/Joinmarket-Org/joinmarket-clientserver) as a backend for the bitcoin stuff,
but note the `for-occ-poc` branch is needed.
Install in development mode, then you can just switch to that branch.

(As you can see from the last sentence, this is just a bunch of monkey patching. I told you it was POC!).

Consequently, this is a **DO NOT USE** at least for now.

Try it on regtest if you like, of course.

(Warning mainly because no test suite yet, but there are other issues too).

The syntax is:

```
python occreceiver.py wallet-name server port
```

```
python occsender.py wallet-name server port
```

On regtest, it just funds with necessary utxos on regtest to make it work; remove/comment if you want to try it with wallets, then you need utxos in the specified ranges.
There is just one template found in the occbase.py file, retrieved as fixed, for now. You'd either edit it (see comments)
or make a new one. Alter the input amount ranges passed to the `get_utxos_from_wallet` function correspondingly.

(Here should go actual documentation).

The input utxos are p2sh-p2wpkh (funded from segwit Joinmarket wallets, compatible, see above), and
the 2 of 2 co-owned outputs are native p2wsh.

Publishes whole tx chain to `occresults.txt` so you can take a look.

Bitcoin tx fees: set statically at top of occbase.py for now. Obv needs to be dynamic.

Optionally broadcasts everything directly to chain without waiting if you set `broadcast_all = 1` in the config under `POLICY`.
Otherwise use what's in `occresults.txt` to broadcast them manually, in
sequence, using `sendrawtransaction`. Config and wallets are in `~/.CoinJoinXT/*`

