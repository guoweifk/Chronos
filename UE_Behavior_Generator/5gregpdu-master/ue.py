import sys
import time
import threading
from utils.cryproutils import plmn_bcd_decode
from Crypto.Cipher import AES
from pycrate_asn1dir.NGAP import NGAP_PDU_Descriptions
# from nr import GNB
from message.code import ProcedureCode, MessageType 
from utils.cryproutils import plmn_bcd_encode, bcd
from message.message import InitialUEMessage, AuthRequestMessage, AuthenticationResponseMessage, \
    SecurityModeCommandMessage, SecurityModeCompleteMessage, InitialContextSetupRequestMessage, \
    InitialContextSetupResponseMessage, RegistrationCompleteMessage, PDUSessionEstablishmentRequestMessage, \
    ConfigurationUpdateMessage, PDUSessionResourceSetupRequestMessage, PDUSessResourceSetupResponseMessage, \
    LocationReportingControlMessage, ServiceRequestMessage, ServiceAcceptMessage, InitialContextSetupResponseMessage2, \
    UEContextReleaseCommandMessage, UEContextReleaseCompleteMessage, UEContextReleaseRequestMessage
from loguru import logger


class UE:
    def __init__(self, mcc, mnc, imsi_suffix10, ran_ue_ngap_id, gnb_nr_cell_id, gnb_address,
                 slices={"SST": 1},
                 ki="12341234123412341234123412340000", 
                 opc="71a121bb69baf3c0cc53fb5038a0131f", 
                 dnn="internet", tac="000001", 
                 imeisv="4370816125816151",
                 op=False,
                 ABBA=b"\x00\x00", ciphAlgo=0, ntegAlgo=2,
                 logging_level='INFO'):
        
        # ue information
        self.mcc = mcc
        self.mnc = mnc
        self.tac = tac
        self.slices = slices
        self.ki = bytes.fromhex(ki)
        self.opc = bytes.fromhex(opc)
        if op:
            self._calc_opc_from_k_op()
        self.imsi_suffix10 = imsi_suffix10
        self.supi = f"{mcc}{mnc}{imsi_suffix10.zfill(10)}"
        self.imeisv = imeisv
        self.plmn_bcd = plmn_bcd_encode(self.mcc + self.mnc)
        self.dnn = dnn.encode()
        self.dnn2 = "ims".encode()
        self.ran_ue_ngap_id = ran_ue_ngap_id
        # gnb information
        self.gnb_nr_cell_id = gnb_nr_cell_id
        self.gnb_address = gnb_address
        self.ABBA = ABBA
        self.paging = False

        
        # Integer value used to record the current state of the User Equipment (UE)
        # This variable tracks the different states of the UE such as IDLE, CONNECTED, REGISTERED, etc.
        # 0x1 represents the Authentication Request Message has been received from 5GC
        # 0x2 represents the Security Mode Command Message has been received from 5GC
        # 0x4 represents the Registration Accept Message has been received from 5GC
        # 0x8 represents the PDU Session Establishment Request Message has been received from 5GC
        self.ue_state = 0x0

        # automatically set ciphAlgo, ntegAlgo
        self.ciphAlgo = None
        self.ntegAlgo = None
        
        # variables to be set during registration
        self.kseaf = None
        self.res = None
        self.amf_ue_ngap_id = None
        
        self.k_nas_int = None
        self.k_nas_enc = None
        self.gtp_teid = None
        self.dnn_ipv4 = None
        self.dnn_ipv6 = None
        self.dnn_internet_qos = None
        self.dnn2_internet_pdu_sess_id = None
        self.dnn2_ipv4 = None
        self.dnn2_ipv6 = None
        self.dnn2_ims_qos = None
        self.dnn2_ims_pdu_sess_id = None
        self.ue_5g_guti = None

        # label of procedures
        self.registered = False
        self.dnn_internet_connected = False
        self.dnn_ims_connected = False
        self.ue_release_enabled = True
        
        self.PDU = NGAP_PDU_Descriptions.NGAP_PDU
        # self.register()
        # self.pdu_session_establish(dnn=self.dnn)
        # self.pdu_session_establish(dnn=self.dnn2)
        
        logger.remove()
        logger.add(
            sink=sys.stdout, 
            level=logging_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        pass
    
    def handle_message(self, type_t, pdu_dict):
        procedureCode = ProcedureCode(pdu_dict['procedureCode'])
        message_type = None
        if procedureCode != ProcedureCode.ID_LOCATION_REPORTING_CONTROL and procedureCode != ProcedureCode.ID_UE_CONTEXT_RELEASE:
            message_type = self._extract_message_type(pdu_dict)
            if message_type is None:
                return self, []
        # print(f"{procedureCode} {message_type}")
        messages = []
        if type_t == 'initiatingMessage':
            if procedureCode == ProcedureCode.ID_DOWNLINK_NAS_TRANSPORT:
                if message_type == MessageType.AUTHENTICATION_REQUEST:
                    self.kseaf, self.res, self.amf_ue_ngap_id = AuthRequestMessage(pdu_dict, self.ki, self.opc, self.mcc, self.mnc)
                    message = AuthenticationResponseMessage(self.res, self.amf_ue_ngap_id, plmn_bcd=self.plmn_bcd, tac=self.tac, gnb_nr_cell_id=self.gnb_nr_cell_id, ran_ue_ngap_id=self.ran_ue_ngap_id)
                    messages.append(message)
                    self.ue_state = self.ue_state | 0x1
                elif message_type == MessageType.SECURITY_MODE_COMMAND:
                    # if self.ue_state & 0x1 == 1 and self.ue_state & 0x4 == 0:
                    self.ciphAlgo, self.ntegAlgo = SecurityModeCommandMessage(pdu_dict)
                    self.ue_state = self.ue_state | 0x2
                    message, self.k_nas_int, self.k_nas_enc = SecurityModeCompleteMessage(self.amf_ue_ngap_id, self.kseaf, self.plmn_bcd, self.slices, self.imeisv, self.supi.encode(), self.tac, self.ABBA, self.ciphAlgo, self.ntegAlgo, ran_ue_ngap_id=self.ran_ue_ngap_id)
                    messages.append(message)
                    
                elif message_type == MessageType.CONFIGURATION_UPDATE_COMMNAD:
                    ConfigurationUpdateMessage(pdu_dict)
                    time.sleep(0.05)
                    # message = self.send_pdusession_establishment_request(self.dnn)
                    # messages.append(message)
                    # IMS APN PDU Session Establishment Request
                    # message = self.send_pdusession_establishment_request(self.dnn2)
                    # messages.append(message)
                    pass
            elif procedureCode == ProcedureCode.ID_INITIAL_CONTEXT_SETUP:
                if message_type == MessageType.REGISTRATION_ACCEPT:
                    # if self.ue_state & 0x2 == 1 and self.ue_state & 0x8 == 0:
                    self.ue_5g_guti = InitialContextSetupRequestMessage(pdu_dict)
                    self.ue_state = self.ue_state | 0x4
                    message = InitialContextSetupResponseMessage(self.amf_ue_ngap_id, ran_ue_ngap_id=self.ran_ue_ngap_id)
                    messages.append(message)
                    message = RegistrationCompleteMessage(self.amf_ue_ngap_id, self.k_nas_int, self.k_nas_enc, self.plmn_bcd, tac=self.tac, ciphAlgo=self.ciphAlgo, ntegAlgo=self.ntegAlgo, ran_ue_ngap_id=self.ran_ue_ngap_id)
                    messages.append(message)
                    message = self.send_pdusession_establishment_request(self.dnn)
                    messages.append(message)
                else:
                    logger.warn("Unknown or Unsupported message type: ", message_type)
            elif procedureCode == ProcedureCode.ID_PDU_SESSION_RESOURCE_SETUP:
                if message_type == MessageType.DL_NAS_TRANSPORT:
                    # if self.ue_state & 0x4 == 1 and self.ue_state & 0x8 == 0:
                    ipv4_str, gTP_TEID, qosFlowIdentifier, SNSSAI, DNN, PDUSessID = PDUSessionResourceSetupRequestMessage(pdu_dict)
                    self.ue_state = self.ue_state | 0x8
                    logger.info(f"UE {self.supi} registered with AMF UE NGAP ID: {self.amf_ue_ngap_id}, IPv4: {ipv4_str}, TEID: {gTP_TEID.hex()}, QoS Flow ID: {qosFlowIdentifier}, SNSSAI: {SNSSAI}, DNN: {DNN}")
                    self._configure_dnn_session(ipv4_str, gTP_TEID, qosFlowIdentifier, SNSSAI, DNN, PDUSessID)
                    message = PDUSessResourceSetupResponseMessage(self.amf_ue_ngap_id, qosFlowIdentifier, self.plmn_bcd, gnb_ip=self.gnb_address, gnb_teid=2, ran_ue_ngap_id=self.ran_ue_ngap_id, tac=self.tac)
                    messages.append(message)
                    
                elif message_type == MessageType.SERVICE_ACCEPT:
                    self.amf_ue_ngap_id = ServiceAcceptMessage(pdu_dict)
                    message = InitialContextSetupResponseMessage2(self.amf_ue_ngap_id, self.ran_ue_ngap_id, self.gnb_address, self.dnn_internet_qos, self.dnn_internet_pdu_sess_id, self.dnn_gtp_teid)
                    messages.append(message)
                    self.ue_release_enabled = True
                else:
                    logger.warn("Unknown or Unsupported message type: ", message_type)
            elif procedureCode == ProcedureCode.ID_LOCATION_REPORTING_CONTROL:
                LocationReportingControlMessage(pdu_dict)
            elif procedureCode == ProcedureCode.ID_UE_CONTEXT_RELEASE:
                self.amf_ue_ngap_id, self.ran_ue_ngap_id = UEContextReleaseCommandMessage(pdu_dict)
                message = UEContextReleaseCompleteMessage(self.amf_ue_ngap_id, self.ran_ue_ngap_id, self.plmn_bcd, self.tac, self.gnb_nr_cell_id)
                messages.append(message)
                self.ue_release_enabled = False
        # time.sleep(0.01)
        return self, messages

    def _extract_message_type(self, pdu_dict):
        nas_pdu = ""
        protocolIEs = pdu_dict['value'][1]['protocolIEs']
        for ie in protocolIEs:
            if ie['value'][0] == 'NAS-PDU':
                nas_pdu = ie['value'][1]
                break
            if ie['value'][0] == 'PDUSessionResourceSetupListSUReq':
                nas_pdu = ie["value"][1][0]['pDUSessionNAS-PDU']
        nas_pdu_hex = nas_pdu.hex()

        if nas_pdu_hex[3] != "0":
            nas_pdu_hex = nas_pdu_hex[14:]
        message_type_str = nas_pdu_hex[4:6]
        if message_type_str == "":
            return None
        message_type = MessageType(int(message_type_str, 16))
        return message_type

    def _configure_dnn_session(self, ipv4_str, gTP_TEID, qosFlowIdentifier, SNSSAI, DNN, PDUSessID):
        """
        Private method to configure DNN session based on the returned DNN value
        """
        if DNN == self.dnn:  # "internet"
            self.dnn_ipv4 = ipv4_str
            self.dnn_gtp_teid = gTP_TEID.hex()
            self.dnn_internet_connected = True
            self.dnn_internet_qos = qosFlowIdentifier
            self.dnn_internet_pdu_sess_id = PDUSessID
            logger.debug(f"Configured internet DNN session with IPv4: {ipv4_str}")
        elif DNN == self.dnn2:  # "ims"
            self.dnn2_ipv4 = ipv4_str
            self.dnn2_gtp_teid = gTP_TEID.hex()
            self.dnn2_ims_connected = True
            self.dnn2_ims_qos = qosFlowIdentifier
            self.dnn2_ims_pdu_sess_id = PDUSessID
            logger.debug(f"Configured IMS DNN session with IPv4: {ipv4_str}")
        else:
            logger.warn(f"Unknown DNN received: {DNN}")

    def _calc_opc_from_k_op(self):
        cipher = AES.new(self.ki, AES.MODE_ECB)
        self.opc = bytes(a ^b for a, b in zip(cipher.encrypt(self.opc), self.opc))

    def send_initial_ue_message(self):
        imsi_bcd = bcd(self.imsi_suffix10)
        message = InitialUEMessage(self.plmn_bcd, self.tac, imsi_bcd, ran_ue_ngap_id=self.ran_ue_ngap_id)

        return message
    
    def send_service_request(self):
        # TODO: Below code for debugging
        message = ServiceRequestMessage(self.plmn_bcd, self.tac, self.ue_5g_guti, self.k_nas_enc, self.k_nas_int, self.ciphAlgo, self.ntegAlgo, self.gnb_nr_cell_id, self.ran_ue_ngap_id)
        return message

    def release_ue_context(self):
        message = UEContextReleaseRequestMessage(self.amf_ue_ngap_id, self.ran_ue_ngap_id)
        return message

    def send_pdusession_establishment_request(self, dnn):
        message = PDUSessionEstablishmentRequestMessage(self.amf_ue_ngap_id,self.k_nas_int, self.k_nas_enc, self.plmn_bcd, slices=self.slices, dnn=dnn, ran_ue_ngap_id=self.ran_ue_ngap_id, tac=self.tac, ciphAlgo=self.ciphAlgo, ntegAlgo=self.ntegAlgo, gnb_id=self.gnb_nr_cell_id)
        return message
    
    def __repr__(self):
        return f"UE(imsi={self.imsi_suffix10}, ran_ue_ngap_id={self.ran_ue_ngap_id}, amf_ue_ngap_id={self.amf_ue_ngap_id})"
    