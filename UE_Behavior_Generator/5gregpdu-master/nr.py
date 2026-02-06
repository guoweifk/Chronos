import sys
import time 
import queue
import threading
import socket
from tqdm import tqdm
from pycrate_asn1dir.NGAP import NGAP_PDU_Descriptions
from message.message import NGAPSetupReqeust
from message.code import ProcedureCode, RAN_UE_NGAP_LEN_LABLES
from utils.cryproutils import plmn_bcd_decode, plmn_bcd_encode
from multiprocessing import Array, Process, Manager
from multiprocessing.managers import BaseManager
from concurrent.futures import ThreadPoolExecutor
from ue import UE
from loguru import logger

class GNB:
    def __init__(self, mcc, mnc, slices,
                 gnb_address, amf_address, amf_port=38412, 
                 sst="01", tac="000001", gnb_id=513, 
                 gnb_id_len=32, gnb_nr_cell_id=1, gnb_name="gnb1",
                 start_suffix10="0000000001", number_ofUEs=1,
                 ki="12341234123412341234123412340000", 
                 opc="71a121bb69baf3c0cc53fb5038a0131f", 
                 dnn="internet",
                 imeisv="4370816125816151",
                 op=False,
                 ABBA=b"\x00\x00", ciphAlgo=0, ntegAlgo=2,
                 inactive_time_delay=10, release_time_delay=2,
                 logging_level='INFO'):
        self.mnc = mnc
        self.mcc = mcc
        self.slices = slices
        self.gnb_address = gnb_address
        self.gnb_id = gnb_id
        self.gnb_id_len = gnb_id_len
        self.gnb_nr_cell_id = gnb_nr_cell_id
        self.gnb_name = gnb_name
        self.gnb_tac = tac
        self.amf_address = amf_address
        self.amf_port = amf_port
        self.gnb_amf = None
        self.start_suffix10 = start_suffix10
        self.number_ofUEs = number_ofUEs
        self.sst = sst
        # UE parameters
        self.ki = ki
        self.opc = opc
        self.op = op
        self.dnn = dnn
        self.tac = tac
        self.ABBA = ABBA
        self.ciphAlgo = ciphAlgo
        self.ntegAlgo = ntegAlgo
        

        # Shared UE array for multiprocessing access
        self.manager = Manager()
        # self.message_queue = self.manager.Queue()
        # self.ues = self.manager.list()
        self.message_queue = queue.Queue()
        self.ues = []
        self.ue_lock = self.manager.Lock()  # Lock for synchronizing UE access
        self.socket_lock = threading.Lock()

        self.sctp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_SCTP)
        self.PDU = NGAP_PDU_Descriptions.NGAP_PDU
        
        # self._setup_gnb()
        # Message processing thread
        self._setup_gnb()
        self.message_thread = threading.Thread(target=self.acceptor)
        self.message_thread.start()
        self.sender = threading.Thread(target=self.sender)
        self.sender.start()
        self.running = True
        self.ran_ue_ngap_idx = 1

        self.executor = ThreadPoolExecutor(max_workers=2000)

        # timer
        self.inactive_time_delay = inactive_time_delay
        self.release_time_delay = release_time_delay

        # self.pdu_checker = threading.Thread(target=self.pdu_checker)
        # self.pdu_checker.start()
        self.inactive_timer = None

        # logger 
        self.logging_level = logging_level
        logger.remove()
        logger.add(
            sink=sys.stdout, 
            level=logging_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )


    def run(self):
        self._initializes_ues()

    def _initializes_ues(self):
        start_suffix10 = int(self.start_suffix10)
        for idx, ueid in tqdm(enumerate(range(start_suffix10, start_suffix10 + self.number_ofUEs)), desc="Initializing UEs"):
            ue = UE(mcc=self.mcc, mnc=self.mnc, imsi_suffix10='{:010d}'.format(ueid), ran_ue_ngap_id=idx + 1, imeisv='{:016d}'.format(ueid),
                    gnb_nr_cell_id=self.gnb_nr_cell_id, gnb_address=self.gnb_address, slices=self.slices, 
                    ki=self.ki, opc=self.opc, tac=self.tac, dnn=self.dnn, op=self.op, logging_level=self.logging_level)
            self.ran_ue_ngap_idx += 1
            with self.ue_lock:
                self.ues.append(ue)
            # time.sleep(1.0/100)
        logger.info(f"{len(self.ues)} ues are ready!")
        for ue in self.ues:
            initial_message = ue.send_initial_ue_message()
            self.message_queue.put(initial_message)
            time.sleep(1.0/500)

    def _setup_gnb(self):
        self._set_stream(0)
        self.sctp_socket.bind((self.gnb_address, 0))
        self.sctp_socket.connect((self.amf_address, self.amf_port))
        self.PDU.set_val(NGAPSetupReqeust(self.mcc + self.mnc, self.gnb_name, self.gnb_id, self.gnb_id_len, tac=self.gnb_tac, sst=self.slices["SST"], sd=self.slices.get("SD", None)))
        self.sctp_socket.send(self.PDU.to_aper())
        _, pdu_dict = self.receive_message()
        self.process_ngap_setup_response(pdu_dict)
        logger.info(f"GNB connected to AMF, {self.gnb_amf}")

    def _set_stream(self, stream):    
        sctp_default_send_param = bytearray(self.sctp_socket.getsockopt(132,10,32))
        sctp_default_send_param[0]= stream
        self.sctp_socket.setsockopt(132, 10, sctp_default_send_param)    

    def _get_ue_by_id(self, ue_id):
        if ue_id < len(self.ues):
            return self.ues[ue_id]
        else:
            return None

    def process_ngap_setup_response(self, pdu_dict):
        procedure, protocolIEs_list = pdu_dict['value'][0], pdu_dict['value'][1]['protocolIEs']
        self.gnb_amf = GNBAMF(protocolIEs_list)

    def send_message(self, message):
        # logger.debug(f"Sending message: {message}")
        self.PDU.set_val(message)
        self.sctp_socket.send(self.PDU.to_aper())

    def initializer(self, ue):
        # ue = UE(mcc=self.mcc, mnc=self.mnc, imsi_suffix10='{:010d}'.format(ueid), ran_ue_ngap_id=idx + 1, gnb_nr_cell_id=self.gnb_nr_cell_id, gnb_address=self.gnb_address, ki=self.ki, opc=self.opc, tac=self.tac)
        with self.ue_lock:
            initial_message = ue.send_initial_ue_message()
            self.message_queue.put(initial_message)
            self.ues.append(ue)
    
    def acceptor(self):
        while True:
            data = self.sctp_socket.recv(4096)
            if data:
                data_hex = data.hex()
                ran_ue_ngap_id = self._extract_ran_ue_ngap_id(data_hex)
                logger.debug(f"Received message from UE with RAN UE NGAP ID: {ran_ue_ngap_id}, procedure code: {int(data_hex[2:4], 16)}, data: {data_hex}")
                if ran_ue_ngap_id == None:
                    continue
                # self.executor.submit(self.ngap_message_handler, data, ran_ue_ngap_id - 1, self.PDU)
                process = threading.Thread(target=self.ngap_message_handler, args=(data, ran_ue_ngap_id - 1, self.PDU))
                process.start()
            pass
    def sender(self):
        while True:
            message = self.message_queue.get()
            # time.sleep(0.05)
            self.send_message(message)
            pass

    def ngap_message_handler(self, data, idx, PDU=None):
        if PDU is None:
            PDU = NGAP_PDU_Descriptions.NGAP_PDU
        PDU.from_aper(data)
        type_t, pdu_dict = PDU()
        # print(pdu_dict)
        logger.debug(f"UE ID: {idx}")
        with self.socket_lock:
            ue, messages = self.ues[idx].handle_message(type_t, pdu_dict)
            for message in messages:
                self.message_queue.put(message)
                self.ues[idx] = ue
        pass

    def _extract_ran_ue_ngap_id(self, data_hex):
        procedurecode = ProcedureCode(int(data_hex[2:4], 16))
        if procedurecode == ProcedureCode.ID_ERROR_INDICATION:
            return None
        elif procedurecode == ProcedureCode.ID_INITIAL_CONTEXT_SETUP:
            extra_length = (int(data_hex[22:24], 16) - 2) * 2
            length = int(data_hex[34 + extra_length:36 + extra_length], 16)
            return int(data_hex[38 + extra_length:38 + extra_length + (length - 1) * 2], 16)
        elif procedurecode == ProcedureCode.ID_PDU_SESSION_RESOURCE_SETUP:
            
            start_ind = data_hex.find("005500") + 6
            # start_ind = 10 + 6 + 4
            # # throw the AMF_UE_NGAP_ID
            # extra_length = int(data_hex[start_ind:start_ind + 2], 16) * 2 + 2 + 6
            # start_ind += extra_length
            length = int(data_hex[start_ind:start_ind + 2], 16)
            # logger.debug(f"PDU Session Resource Setup Request: {int(data_hex[start_ind + 4:start_ind + 4 + (length - 1) * 2], 16)}")
            return int(data_hex[start_ind + 4:start_ind + 4 + (length - 1) * 2], 16)
        elif procedurecode == ProcedureCode.ID_UE_CONTEXT_RELEASE:
            
            logger.debug(f"RELASE HEX: {data_hex}")
            start_ind = 20
            amf_ran_len = int(data_hex[start_ind:start_ind + 2], 16)
            start_ind += 2
            amf_id_len = int(data_hex[start_ind:start_ind + 2], 16)
            start_ind += 2 + (amf_id_len - 1) * 2 if amf_id_len != 6 else 8 + 2
            ran_id_len = RAN_UE_NGAP_LEN_LABLES[data_hex[start_ind:start_ind + 2]]
            return int(data_hex[start_ind + 2:start_ind + 2 + ran_id_len*2], 16)
        elif procedurecode == ProcedureCode.ID_PAGING:
            # TODO: Paging
            return None
        else:
            extra_length = (int(data_hex[20:22], 16) - 2) * 2
            length = int(data_hex[32 + extra_length:34 + extra_length], 16)
            return int(data_hex[36 + extra_length:36 + extra_length + (length - 1) * 2], 16)

    def _extract_amf_ue_ngap_id(self, data_hex):
        pass

    def receive_message(self):
        data = self.sctp_socket.recv(4096)
        if not data:
            return None
        self.PDU.from_aper(data)
        type_t, pdu_dict = self.PDU()
        return type_t, pdu_dict
    
    def close(self):
        self.sctp_socket.shutdown(0)
        self.sctp_socket.close()

    def pdu_checker(self):
        while True:
            count = sum(1 for ue in self.ues if ue.dnn_internet_connected)
            if count >= 0.8 * self.number_ofUEs:
                for ue in self.ues:
                    if ue.dnn_internet_connected:
                        self.send_ues_service_request(ue)
                        time.sleep(1)

    def pdu_checker2(self):
        # while True:
        #     for ue in self.ues:
        #         if ue.dnn_internet_connected:
        #             threading.Timer(self.inactive_time_delay, self.send_ues_service_request, args=(ue,)).start()
        pass

    def send_ues_service_request(self, ue):
        message = ue.send_service_request()
        self.message_queue.put(message)
        self.release_timer = threading.Timer(self.release_time_delay + 2, self.send_ue_context_release_command, args=(ue,))
        self.release_timer.start()
        # self.inactive_timer = threading.Timer(self.inactive_time_delay, self.send_ues_service_request)
        # self.inactive_timer.start()

    def send_ue_context_release_command(self, ue):
        if ue.ue_release_enabled:
            message = ue.release_ue_context()
            self.message_queue.put(message)
        pass


class GNBAMF:
    def __init__(self, protocolIEs_list):
        self.amf_name = None
        self.guami = None
        self.amf_region_id = None
        self.amf_region_id_len = None
        self.amf_set_id = None
        self.amf_set_id_len = None
        self.amf_pointer = None
        self.amf_pointer_len = None
        self.relative_amf_capacity = None
        self._parse_protocolIEs(protocolIEs_list)

    def _parse_protocolIEs(self, protocolIEs_list):
        for ie in protocolIEs_list:
            if ie['value'][0] == 'AMFName':
                self.amf_name = ie['value'][1]
            elif ie['value'][0] == 'ServedGUAMIList':
                guami = ie['value'][1][0]['gUAMI']
                self.guami = plmn_bcd_decode(guami['pLMNIdentity'])
                self.amf_region_id = guami['aMFRegionID'][0]
                self.amf_region_id_len = guami['aMFRegionID'][0]
                self.amf_set_id = guami['aMFSetID'][0]
                self.amf_set_id_len = guami['aMFSetID'][1]
                self.amf_pointer = guami['aMFPointer'][0]
                self.amf_pointer_len = guami['aMFPointer'][1]
            elif ie['value'][0] == 'RelativeAMFCapacity':
                self.relative_amf_capacity = ie['value'][1]

    def __str__(self):
        return f"AMF Name: {self.amf_name}, GUAMI: {self.guami}, AMF Region ID: {self.amf_region_id}, " \
               f"AMF Set ID: {self.amf_set_id}, AMF Pointer: {self.amf_pointer}, Relative Capacity: {self.relative_amf_capacity}"


