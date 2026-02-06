from nr import GNB
from loguru import logger

"""

"""
log_level = 'INFO'
# # log_level = 'DEBUG'
# MCC = "505"
# MNC = "03"
# SLICES = {"SST": 1, "SD": 1}
# GNB_ADDRESS = "192.168.55.9"
# AMF_ADDRESS = "192.168.55.211"
# GNB_NR_CELL_ID = 11
# START_SUFFIX10 = "0000000001"
# NUMBER_OF_UES = 1
# DNN = "internet"
# log_level = 'INFO'
# # log_level = 'DEBUG'
# KI = "8baf473f2f8fd09487cccbd7097c6862"
# OPC = "e8ed289deba952e4283b54e88e618abc"


MCC = "460"
MNC = "99"
SLICES = {"SST": 1}
GNB_ADDRESS = "192.168.55.9"
AMF_ADDRESS = "192.168.55.53"
GNB_NR_CELL_ID = 1
START_SUFFIX10 = "0000000001"
NUMBER_OF_UES = 1
KI="12341234123412341234123412340000"
OPC="71a121bb69baf3c0cc53fb5038a0131f"
DNN = "internet"


# MCC = "466"
# MNC = "92"
# SLICES = {"SST": 1, "SD": 1}
# GNB_ADDRESS = "192.168.55.9"
# AMF_ADDRESS = "192.168.55.78"
# GNB_NR_CELL_ID = 3
# # START_SUFFIX10 = "0000000001"
# START_SUFFIX10 = "0123500000"
# NUMBER_OF_UES = 1
# KI="465B5CE8B199B49FAA5F0A2EE238A6BC"
# OPC="E8ED289DEBA952E4283B54E88E6183CA"

TAC = "000001"

# if a sctp pipe is broken, please change the GNB_ID

# MCC = "460"
# MNC = "02"
# SLICES = {"SST": 1, "SD": 1}
# GNB_ADDRESS = "192.168.55.9"
# AMF_ADDRESS = "192.168.20.121"
# GNB_NR_CELL_ID = 2
# START_SUFFIX10 = "0000000001"
# NUMBER_OF_UES = 1
# TAC = "000051"
# KI = "8baf473f2f8fd09487cccbd7097c6862"
# OPC = "e8ed289deba952e4283b54e88e618abc"

# mobilenet testing (46002)
# MCC = "460"
# MNC = "02"
# SLICES = {"SST": 1, "SD": 1}
# GNB_ADDRESS = "192.168.55.9"
# AMF_ADDRESS = "192.168.29.211"
# GNB_NR_CELL_ID = 2
# START_SUFFIX10 = "0000000001"
# NUMBER_OF_UES = 1
# TAC = "000001"
# KI = "8baf473f2f8fd09487cccbd7097c6862"
# OPC = "e8ed289deba952e4283b54e88e618abc"
# DNN = "cmnet"

OP = False

# IPLOOK CoreNet (46009)
# MCC = "460"
# MNC = "09"
# SLICES = {"SST": 1, "SD": 10101}
# GNB_ADDRESS = "192.168.55.9"
# AMF_ADDRESS = "172.30.55.51"
# GNB_NR_CELL_ID = 2
# START_SUFFIX10 = "0112345038"
# NUMBER_OF_UES = 1
# TAC = "000001"
# KI = "1234567890abcdef1111111111111111"
# OPC = "12345678901234561234567890123456"
# DNN = "net"
# OP = True




GNB_ID = 109
ACCEPTOR_THREAD_POOL_SIZE = 2000


gnb = GNB(
    mcc=MCC,
    mnc=MNC,
    tac=TAC,
    slices=SLICES,
    gnb_address=GNB_ADDRESS,
    amf_address=AMF_ADDRESS,
    gnb_id=GNB_ID,
    gnb_nr_cell_id=GNB_NR_CELL_ID,
    start_suffix10=START_SUFFIX10, 
    number_ofUEs=NUMBER_OF_UES,
    ki=KI,
    opc=OPC,
    op=OP,
    dnn=DNN,
    logging_level=log_level
)

gnb.run()
