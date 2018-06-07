from __future__ import absolute_import, print_function
"""A simplified version of the wallet-tool script
   from Joinmarket, usable with CoinJoinXT (the wallets
   are cross-compatible between these applications).
"""
import datetime
import getpass
import json
import os
import sys
from optparse import OptionParser

from jmclient import (wallet_tool_main)
from configure import cjxt_single, load_coinjoinxt_config

if __name__ == "__main__":
    load_coinjoinxt_config()
    wallet_dir = os.path.join(cjxt_single().homedir, 'wallets')
    if not os.path.exists(wallet_dir):
        os.makedirs(wallet_dir)
    print(wallet_tool_main(wallet_dir))