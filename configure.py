from __future__ import print_function

import io
import logging
import os
import binascii
import sys

from ConfigParser import SafeConfigParser, NoOptionError

import jmbitcoin as btc

from jmclient import (get_p2pk_vbyte, get_p2sh_vbyte, JsonRpc, set_config,
                      get_network, BitcoinCoreInterface,
                      RegtestBitcoinCoreInterface)

logFormatter = logging.Formatter(
    "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
log = logging.getLogger('CoinJoinXT')
log.setLevel(logging.DEBUG)

debug_silence = [False]
import jmbase.support
jmbase.support.debug_silence = [True]
#consoleHandler = logging.StreamHandler(stream=sys.stdout)
class CJXTStreamHandler(logging.StreamHandler):

    def __init__(self, stream):
        super(CJXTStreamHandler, self).__init__(stream)

    def emit(self, record):
        if not debug_silence[0]:
            super(CJXTStreamHandler, self).emit(record)


consoleHandler = CJXTStreamHandler(stream=sys.stdout)
consoleHandler.setFormatter(logFormatter)

log.debug('CoinJoinXT logging started.')

class AttributeDict(object):
    """
    A class to convert a nested Dictionary into an object with key-values
    accessibly using attribute notation (AttributeDict.attribute) instead of
    key notation (Dict["key"]). This class recursively sets Dicts to objects,
    allowing you to recurse down nested dicts (like: AttributeDict.attr.attr)
    """

    def __init__(self, **entries):
        self.currentlogpath = None
        self.add_entries(**entries)

    def add_entries(self, **entries):
        for key, value in entries.items():
            if type(value) is dict:
                self.__dict__[key] = AttributeDict(**value)
            else:
                self.__dict__[key] = value

    def __setattr__(self, name, value):
        if name == 'logs_path' and value != self.currentlogpath:
            self.currentlogpath = value
            logFormatter = logging.Formatter(
                ('%(asctime)s [%(threadName)-12.12s] '
                 '[%(levelname)-5.5s]  %(message)s'))
            fileHandler = logging.FileHandler(value + ".log")
            fileHandler.setFormatter(logFormatter)
            log.addHandler(fileHandler)

        super(AttributeDict, self).__setattr__(name, value)

    def __getitem__(self, key):
        """
        Provides dict-style access to attributes
        """
        return getattr(self, key)


global_singleton = AttributeDict()
global_singleton.CJXT_VERSION = 0.1
global_singleton.APPNAME = "CoinJoinXT"
global_singleton.homedir = None
global_singleton.BITCOIN_DUST_THRESHOLD = 2730
global_singleton.DUST_THRESHOLD = 10 * global_singleton.BITCOIN_DUST_THRESHOLD
global_singleton.bc_interface = None
global_singleton.logs_path = None
global_singleton.config = SafeConfigParser()
#This is reset to a full path after load_cjxt_config call
global_singleton.config_location = 'coinjoinxt.cfg'
#Not currently exposed in config file but could be; it is not expected that
#confirmation for one block could conceivably take this long
global_singleton.one_confirm_timeout = 7200

def cjxt_single():
    return global_singleton

def get_log():
    return log

defaultconfig = \
    """
[BLOCKCHAIN]
#options: bitcoin-rpc, regtest, (no non-Bitcoin Core currently supported)
blockchain_source = bitcoin-rpc
network = mainnet
rpc_host = localhost
rpc_port = 8332
rpc_user = bitcoin
rpc_password = password

[SESSIONS]
#Location of directory where sessions are stored for recovery, it is located under
#the main CoinJoinXT data directory (APPDATA/.CoinJoinXT/). Currently unused,
#may be used later.
sessions_dir = sessions

[POLICY]
#don't edit this; not supporting non-segwit here
segwit = true
broadcast_all = 0
# the fee estimate is based on a projection of how many satoshis
# per kB are needed to get in one of the next N blocks, N set here
# as the value of 'tx_fees'. Any value > 144 is interpreted as the
# number of satoshis per *kilobyte* (e.g. 3000 means 3 sat/byte).
tx_fees = 1
#A value, in satoshis/kB, above which the fee is not allowed to be.
#keep this fairly high, as exceeding it causes the program to 'panic'
#and shut down.
absurd_fee_per_kb = 250000
# for dust sweeping, try merge_algorithm = gradual
# for more rapid dust sweeping, try merge_algorithm = greedy
# for most rapid dust sweeping, try merge_algorithm = greediest
merge_algorithm = default
# the range of confirmations passed to the `listunspent` bitcoind RPC call
# 1st value is the inclusive minimum, defaults to one confirmation
# 2nd value is the exclusive maximum, defaults to most-positive-bignum (Google Me!)
# leaving it unset or empty defers to bitcoind's default values, ie [1, 9999999]
#listunspent_args = []
# that's what you should do, unless you have a specific reason, eg:
#  spend from unconfirmed transactions:  listunspent_args = [0]
# display only unconfirmed transactions: listunspent_args = [0, 1]
# defend against small reorganizations:  listunspent_args = [3]
#   who is at risk of reorganization?:   listunspent_args = [0, 2]

[LOGGING]
# Set the log level for the output to the terminal/console
# Possible choices: DEBUG / INFO / WARNING / ERROR
# Log level for the files in the logs-folder will always be DEBUG
console_log_level = INFO

[SERVER]
#These settings not currently in use, may be added later.
#Hidden service is the preferred way of serving; if use_onion is set to anything
#except 'false', clearnet modes will be ignored.
#(Tor will be started within the application)
use_onion = true
onion_port = 1234
#Location of hostname and private key for hidden service - Note:
#if not set, default is APPDIR/hiddenservice (~/.CoinJoinXT/hiddenservice)
#hs_dir = /chosen/directory
#port on which to serve clearnet
port = 7080
#whether to use SSL; non-SSL is *strongly* disrecommended, mainly because
#you lose confidentiality, it also allows MITM which is not a loss of funds risk,
#but again a loss of confidentiality risk. Note that client-side verification
#of cert is required to actually prevent MITM.
use_ssl = true
#directory containing private key and cert *.pem files; 0 means default location,
#which is homedir/ssl/ ; replace with fully qualified paths if needed.
ssl_private_key_location = 0
ssl_certificate_location = 0
"""

def lookup_appdata_folder():
    from os import path, environ
    if sys.platform == 'darwin':
        if "HOME" in environ:
            data_folder = path.join(os.environ["HOME"],
                                   "Library/Application support/",
                                   global_singleton.APPNAME) + '/'
        else:
            print("Could not find home folder")
            os.exit()

    elif 'win32' in sys.platform or 'win64' in sys.platform:
        data_folder = path.join(environ['APPDATA'], global_singleton.APPNAME) + '\\'
    else:
        data_folder = path.expanduser(path.join("~",
                                    "." + global_singleton.APPNAME + "/"))
    return data_folder

def load_coinjoinxt_config(config_path=None, bs=None):
    global_singleton.config.readfp(io.BytesIO(defaultconfig))
    if not config_path:
        global_singleton.homedir = lookup_appdata_folder()
    else:
        global_singleton.homedir = config_path
    if not os.path.exists(global_singleton.homedir):
        os.makedirs(global_singleton.homedir)
    #prepare folders for wallets and logs
    if not os.path.exists(os.path.join(global_singleton.homedir, "wallets")):
        os.makedirs(os.path.join(global_singleton.homedir, "wallets"))
    if not os.path.exists(os.path.join(global_singleton.homedir, "logs")):
        os.makedirs(os.path.join(global_singleton.homedir, "logs"))
    global_singleton.config_location = os.path.join(
        global_singleton.homedir, global_singleton.config_location)
    loadedFiles = global_singleton.config.read([global_singleton.config_location
                                               ])
    if len(loadedFiles) != 1:
        with open(global_singleton.config_location, "w") as configfile:
            configfile.write(defaultconfig)
    # configure the interface to the blockchain on startup
    global_singleton.bc_interface = get_blockchain_interface_instance(
        global_singleton.config)
    # set the console log level and initialize console logger
    try:
        global_singleton.console_log_level = global_singleton.config.get(
            "LOGGING", "console_log_level")
    except (NoSectionError, NoOptionError):
        print("No log level set, using default level INFO ")
    print("Setting console level to: ", global_singleton.console_log_level)
    consoleHandler.setLevel(global_singleton.console_log_level)
    log.addHandler(consoleHandler)
    #inject the configuration to the underlying jmclient code.
    set_config(global_singleton.config, bcint=global_singleton.bc_interface)
    

def get_blockchain_interface_instance(_config):
    source = _config.get("BLOCKCHAIN", "blockchain_source")
    network = _config.get("BLOCKCHAIN", "network")
    testnet = network == 'testnet'
    rpc_host = _config.get("BLOCKCHAIN", "rpc_host")
    rpc_port = _config.get("BLOCKCHAIN", "rpc_port")
    rpc_user = _config.get("BLOCKCHAIN", "rpc_user")
    rpc_password = _config.get("BLOCKCHAIN", "rpc_password")
    rpc = JsonRpc(rpc_host, rpc_port, rpc_user, rpc_password)
    if source == 'bitcoin-rpc': #pragma: no cover
        #This cannot be tested without mainnet or testnet blockchain (not regtest)
        bc_interface = BitcoinCoreInterface(rpc, network)
    elif source == 'regtest':
        bc_interface = RegtestBitcoinCoreInterface(rpc)
    return bc_interface
