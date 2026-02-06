import time
import struct
import ipaddress
from CryptoMobile.conv import *
from message.code import ProcedureCode
from message.identity import FGGUTI
from utils.cryproutils import plmn_bcd_encode, plmn_bcd_decode, bcd, calculateRes, int_to_hex8, int_to_hex4
from pycrate_mobile.TS24501_IE import FGSIDTYPE_IMEISV
from pycrate_mobile.TS24501_FGSM import FGSMPDUSessionEstabRequest, FGSMPDUSessionEstabAccept
from pycrate_mobile.TS24501_FGMM import FGMMRegistrationRequest, FGMMSecurityModeComplete, \
    FGMMSecProtNASMessage, FGMMULNASTransport, FGMMRegistrationComplete, FGMMDLNASTransport, \
    FGMMRegistrationAccept, FGMMServiceRequest, FGMMControlPlaneServiceRequest, FGMMSecurityModeCommand



def NGAPSetupReqeust(plmn, gnb_name, gnb_id, gnb_id_len, tac, sst=0x1, sd=None):
    IEs = []
    IEs.append({'id': 27, 'criticality': 'reject', 'value': ('GlobalRANNodeID', ('globalGNB-ID', {'pLMNIdentity': plmn_bcd_encode(plmn), 'gNB-ID': ('gNB-ID', (gnb_id, gnb_id_len))}))})
    IEs.append({'id': 82, 'criticality': 'ignore', 'value': ('RANNodeName', gnb_name)})
    IEs.append({'id': 102, 'criticality': 'reject', 'value': ('SupportedTAList', [{'tAC': bytes.fromhex(tac), 'broadcastPLMNList': [{'pLMNIdentity': plmn_bcd_encode(plmn), 'tAISliceSupportList': [{'s-NSSAI': {'sST': bytes.fromhex(hex(sst)[2:].zfill(2)), **({'sD': bytes.fromhex(hex(sd)[2:].zfill(6))} if sd is not None else {})}}]}]}])})
    IEs.append({'id': 21, 'criticality': 'ignore', 'value': ('PagingDRX', 'v128')})
    val = ('initiatingMessage', {'procedureCode': 21, 'criticality': 'reject', 'value': ('NGSetupRequest', {'protocolIEs': IEs})})
    return val  

def NGAPSetupResponse(sctp_socket, PDU):
    buffer = sctp_socket.recv(4096)
    PDU.from_aper(buffer)
    (type, pdu_dict) = PDU()
    procedure, protocolIEs_list = pdu_dict['value'][0], pdu_dict['value'][1]['protocolIEs']
    return NGAPSetupResponseProcessing(protocolIEs_list, {})

def NGAPSetupResponseProcessing(IEs, dic):
    amf_name = ''
    servedPLMNs = b''
    servedGroupIDs = b''
    servedMMECs = b''
    RelativeMMECapacity = 0
    
    for i in IEs:
        if i['id'] == 1:
            amf_name = i['value'][1]
        elif i['id'] == 80:
            servedPLMNs = i['value'][1][0]['pLMNIdentity']
            sliceSupportList = i['value'][1][0]['sliceSupportList']
        elif i['id'] == 86:
            RelativeAMFCapacity = i['value'][1]
            
    dic['AMF-NAME'] = amf_name
    dic['AMF-PLMN'] = servedPLMNs
    dic['AMF-GROUP-ID'] = servedGroupIDs
    dic['AMF-CODE'] = servedMMECs
    dic['AMF-RELATIVE-CAPACITY'] = RelativeAMFCapacity
    
    dic['STATE'] = 1
    return dic

def InitialUEMessage(plmn_bcd: bytes, tac: str, imsi_bcd: bytes, nr_cell_id=1, ran_ue_ngap_id=1):
    """
    gNB->AMF, Initial UE Message
    """
    # TODO: 
    IEs = []
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 38, 'criticality': 'reject', 'value': ('NAS-PDU', bytes.fromhex(f'7e004179000d01{plmn_bcd.hex()}00000000{imsi_bcd.hex()}2e04f0f0f0f0'))})
    IEs.append({'id': 121, 'criticality': 'reject', 'value': ('UserLocationInformation', ('userLocationInformationNR', {'tAI': {'pLMNIdentity': plmn_bcd, 'tAC': bytes.fromhex(tac)},'nR-CGI': {'pLMNIdentity': plmn_bcd, 'nRCellIdentity': (nr_cell_id, 36)}}))})
    IEs.append({'id': 90, 'criticality': 'ignore', 'value': ('RRCEstablishmentCause', 'mo-Signalling')})
    IEs.append({'id': 112, 'criticality': 'ignore', 'value': ('UEContextRequest', "requested")})
    val = ('initiatingMessage', {'procedureCode': 15, 'criticality': 'ignore', 'value': ('InitialUEMessage', {'protocolIEs': IEs})})
    return val

def ServiceRequestMessage(plmn_bcd: bytes, tac: str, ue_5g_guti: FGGUTI, k_nas_enc, k_nas_int, ciphAlgo, integAlgo, nr_cell_id=1, ran_ue_ngap_id=1):
    SevIE = {}
    SevIE['NAS_KSI'] = {'TSC': 0, 'Value': 1}
    SevIE['5GSID'] = {'ind': 0, 'Type': 4, 'AMFSetID': ue_5g_guti.amf_set_id.get_val(), 'AMFPtr': ue_5g_guti.amf_ptr.get_val(), '5GTMSI': ue_5g_guti.tmsi.get_val()}
    SevIE['ULDataStat'] = {'PSI_7': 0, 'PSI_6': 0, 'PSI_5': 0, 'PSI_4': 0, 'PSI_3': 0, 'PSI_2': 0, 'PSI_1': 1, 'PSI_15': 0, 'PSI_14': 0, 'PSI_13': 0, 'PSI_12': 0, 'PSI_11': 0, 'PSI_10': 0, 'PSI_9': 0, 'PSI_8': 0}
    SevIE['PDUSessStat'] = {'PSI_7': 0, 'PSI_6': 0, 'PSI_5': 0, 'PSI_4': 0, 'PSI_3': 0, 'PSI_2': 1, 'PSI_1': 1, 'PSI_15': 0, 'PSI_14': 0, 'PSI_13': 0, 'PSI_12': 0, 'PSI_11': 0, 'PSI_10': 0, 'PSI_9': 0, 'PSI_8': 0}
    SevReqMsg = FGMMServiceRequest(val=SevIE)
    SevReqMsg['ServiceType'].set_val({'V': 2})
    SevReqMsg = SevReqMsg.to_bytes()
    SevIE2 = {}
    SevIE2['NAS_KSI'] = {'TSC': 0, 'Value': 1}

    SevIE2['5GSID'] = {'ind': 0, 'Type': 4, 'AMFSetID': ue_5g_guti.amf_set_id.get_val(), 'AMFPtr': ue_5g_guti.amf_ptr.get_val(), '5GTMSI': ue_5g_guti.tmsi.get_val()}
    # SevIE['5GSID'] = {'ind': 0, 'Type': 4, 'AMFSetID': ue_5g_guti.amf_set_id, 'AMFPtr': ue_5g_guti.amf_ptr, '5GTMSI': ue_5g_guti.tmsi}
    SevReqMsg2 = FGMMServiceRequest(val=SevIE2)
    SevReqMsg2['ServiceType'].set_val({'V': 2})
    nas_container_id = 0x71
    nas_container_len = len(SevReqMsg)
    nas_container_content = SevReqMsg
    nas_pdu = SevReqMsg2.hex() + hex(nas_container_id)[2:] + f"{nas_container_len:0>4x}" + nas_container_content.hex()
    SecMsg = fgmm_security_protected_nas_message(ciphAlgo, integAlgo, k_nas_enc, k_nas_int, bytes.fromhex(nas_pdu), is_service_request=True)
    nas_encoded = SecMsg.hex()

    IEs = []
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 38, 'criticality': 'reject', 'value': ('NAS-PDU', bytes.fromhex(nas_encoded))})
    IEs.append({'id': 121, 'criticality': 'reject', 'value': ('UserLocationInformation', ('userLocationInformationNR', {'tAI': {'pLMNIdentity': plmn_bcd, 'tAC': bytes.fromhex(tac)},'nR-CGI': {'pLMNIdentity': plmn_bcd, 'nRCellIdentity': (nr_cell_id, 36)}}))})
    IEs.append({'id': 90, 'criticality': 'ignore', 'value': ('RRCEstablishmentCause', 'mt-Access')})
    IEs.append({'id': 26, 'criticality': 'reject', 'value': ('FiveG-S-TMSI', {'aMFSetID': (ue_5g_guti.amf_set_id.get_val(), 10), 'aMFPointer': (ue_5g_guti.amf_ptr.get_val(), 6), 'fiveG-TMSI': ue_5g_guti.tmsi.get_val().to_bytes(4, byteorder='big')})})
    IEs.append({'id': 112, 'criticality': 'ignore', 'value': ('UEContextRequest', "requested")})
    val = ('initiatingMessage', {'procedureCode': 15, 'criticality': 'ignore', 'value': ('InitialUEMessage', {'protocolIEs': IEs})})
    return val

def ServiceAcceptMessage(pdu_dict):
    amf_ue_ngap_id = pdu_dict['value'][1]['protocolIEs'][0]['value'][1]
    return amf_ue_ngap_id


def AuthRequestMessage(pdu_dict, k, opc, mcc, mnc, amf=b"8000"):
    """
    AMF->gNB, Authentication Request.
    When processing the response, it will ignore extended protocol discriminator, 
    security header type, message type, padding octet, ngKSI and ABBA.


    returns:
        KSEAF, ngap_uplink_message.to_hex()+authentication_response_message.to_hex()
    """
    
    amf_ue_ngap_id = pdu_dict['value'][1]['protocolIEs'][0]['value'][1]
    ran_ue_ngap_id = pdu_dict['value'][1]['protocolIEs'][1]['value'][1]
    nas_pdu = pdu_dict['value'][1]['protocolIEs'][2]['value'][1]
    rand = nas_pdu[8:24]
    autn = nas_pdu[24:]
    autn_sqn_xor_ak = autn[2:8]
    amf = autn[8:10]
    mac = autn[10:18]
    KSEAF, res_star = calculateRes(opc, k, rand, autn_sqn_xor_ak, mnc, mcc, amf)
    # different UE with different amf_ue_ngap_id, ran_ue_ngap_id
    return KSEAF, res_star, amf_ue_ngap_id

def AuthenticationResponseMessage(res_star, amf_ue_ngap_id, plmn_bcd: bytes, tac="000001", gnb_nr_cell_id=1, ran_ue_ngap_id=1):
    """
    gNB->AMF, UplinkNASTransport, NAS-PDU message_type is 0x57.
    """
    IEs = []
    IEs.append({'id': 10, 'criticality': 'reject', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 38, 'criticality': 'reject', 'value': ('NAS-PDU', bytes.fromhex(f'7e00572d10{res_star}'))})
    IEs.append({'id': 121, 'criticality': 'ignore', 'value': ('UserLocationInformation', ('userLocationInformationNR', {'timeStamp': (int(time.time()) + 2208988800).to_bytes(4, byteorder='big'), 'tAI': {'pLMNIdentity': plmn_bcd, 'tAC': bytes.fromhex(tac)},'nR-CGI': {'pLMNIdentity': plmn_bcd, 'nRCellIdentity': (gnb_nr_cell_id, 36)}}))})
    val = ('initiatingMessage', {'procedureCode': 46, 'criticality': 'ignore', 'value': ('UplinkNASTransport', {'protocolIEs': IEs})})
    return val

def SecurityModeCommandMessage(pdu_dict):
    for IE in pdu_dict['value'][1]['protocolIEs']:
        if IE['value'][0] == 'NAS-PDU':
            nas_pdu = IE['value'][1]
    SecModeMsg = FGMMSecurityModeCommand()
    SecModeMsg.from_bytes(nas_pdu[7:])
    ciphAlgo = SecModeMsg['NASSecAlgo']['NASSecAlgo']['CiphAlgo']
    ntegAlgo = SecModeMsg['NASSecAlgo']['NASSecAlgo']['IntegAlgo']
    return ciphAlgo.get_val(), ntegAlgo.get_val()

def SecurityModeCompleteMessage(amf_ue_ngap_id, kseaf, plmn_bcd: bytes, slices, imeisv, SUPI=b"460991234567893", tac="000001", ABBA=b"\x00\x00", ciphAlgo=0, ntegAlgo=2, ran_ue_ngap_id=1):
    k_amf = conv_501_A7(kseaf, SUPI, ABBA)
    k_nas_enc = conv_501_A8(k_amf, alg_type=1, alg_id=ciphAlgo)
    k_nas_enc = k_nas_enc[16:]
    k_nas_int = conv_501_A8(k_amf, alg_type=2, alg_id=ntegAlgo)
    k_nas_int = k_nas_int[16:]
    regReqMsg = fgmm_registration_request_message(plmn=plmn_bcd_decode(plmn_bcd), nssai=[slices])
    secModeMsg = fgmm_security_mode_command_message(regReqMsg, imeisv)
    secProtNasMsg = fgmm_security_protected_nas_message(ciphAlgo, ntegAlgo, k_nas_enc, k_nas_int, secModeMsg)
    nas_encoded = secProtNasMsg.hex()
    IEs = []
    IEs.append({'id': 10, 'criticality': 'reject', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 38, 'criticality': 'reject', 'value': ('NAS-PDU', bytes.fromhex(nas_encoded))})
    IEs.append({'id': 121, 'criticality': 'ignore', 'value': ('UserLocationInformation', ('userLocationInformationNR', {'timeStamp': (int(time.time()) + 2208988800).to_bytes(4, byteorder='big'), 'tAI': {'pLMNIdentity': plmn_bcd, 'tAC': bytes.fromhex(tac)},'nR-CGI': {'pLMNIdentity': plmn_bcd, 'nRCellIdentity': (1, 36)}}))})
    val = ('initiatingMessage', {'procedureCode': 46, 'criticality': 'ignore', 'value': ('UplinkNASTransport', {'protocolIEs': IEs})})
    return val, k_nas_int, k_nas_enc

def InitialContextSetupRequestMessage(pdu_dict):
    for IE in pdu_dict['value'][1]['protocolIEs']:
        if IE['value'][0] == 'NAS-PDU':
            nas_pdu = IE['value'][1]
    RegAcceptMsg = FGMMRegistrationAccept()
    RegAcceptMsg.from_bytes(nas_pdu[7:])
    GUTI = RegAcceptMsg['GUTI']['5GSID']
    ue_5g_guti =  FGGUTI(GUTI['PLMN'], GUTI['AMFRegionID'], GUTI['AMFSetID'],GUTI['AMFPtr'], GUTI['5GTMSI'])
    # print(RegAcceptMsg)
    return ue_5g_guti

def InitialContextSetupResponseMessage(amf_ue_ngap_id, ran_ue_ngap_id=1):
    IEs = []
    IEs.append({'id': 10, 'criticality': 'reject', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    val = ('successfulOutcome', {'procedureCode': 14, 'criticality': 'ignore', 'value': ('InitialContextSetupResponse', {'protocolIEs': IEs})})
    return val

def InitialContextSetupResponseMessage2(amf_ue_ngap_id, ran_ue_ngap_id, gnb_ipaddress, qos, pdu_session_id, gtp_teid):

    IEs = []
    IEs.append({'id': 10, 'criticality': 'reject', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 72, 'criticality': 'ignore', 'value': ('PDUSessionResourceSetupListCxtRes', [{'pDUSessionID': pdu_session_id, 'pDUSessionResourceSetupResponseTransfer': ('PDUSessionResourceSetupResponseTransfer', {'dLQosFlowPerTNLInformation': {'uPTransportLayerInformation': ('gTPTunnel', {'transportLayerAddress': (int.from_bytes(ipaddress.ip_address(gnb_ipaddress).packed, 'big'), 32), 'gTP-TEID': bytes.fromhex(gtp_teid)}), 'associatedQosFlowList': [{'qosFlowIdentifier': qos}]}})}])})    
    val = ('successfulOutcome', {'procedureCode': 14, 'criticality': 'ignore', 'value': ('InitialContextSetupResponse', {'protocolIEs': IEs})})
    return val


def RegistrationCompleteMessage(amf_ue_ngap_id, k_nas_int, k_nas_enc, plmn_bcd, ran_ue_ngap_id=1, tac="000001", ciphAlgo=0, ntegAlgo=2):
    
    regCompleteMsg = fgmm_registration_complete_message()
    secProtNasMsg = fgmm_security_protected_nas_message(ciphAlgo, ntegAlgo, k_nas_enc, k_nas_int, regCompleteMsg)
    nas_encoded = secProtNasMsg.hex()
    
    IEs = []
    IEs.append({'id': 10, 'criticality': 'reject', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 38, 'criticality': 'reject', 'value': ('NAS-PDU', bytes.fromhex(nas_encoded))})
    IEs.append({'id': 121, 'criticality': 'reject', 'value': ('UserLocationInformation', ('userLocationInformationNR', {'tAI': {'pLMNIdentity': plmn_bcd, 'tAC': bytes.fromhex(tac)},'nR-CGI': {'pLMNIdentity': plmn_bcd, 'nRCellIdentity': (1, 36)}}))})

    val = ('initiatingMessage', {'procedureCode': 46, 'criticality': 'ignore', 'value': ('UplinkNASTransport', {'protocolIEs': IEs})})
    return val

def PDUSessionEstablishmentRequestMessage(amf_ue_ngap_id, k_nas_int, k_nas_enc, plmn_bcd, slices, dnn, ran_ue_ngap_id=1, tac="000001", ciphAlgo=0, ntegAlgo=2, gnb_id=1):
    pduSessEstablishmentReq = fgsm_pdu_session_establishment_request_message()
    ulNasTransportMsg = fgmm_ul_nas_transport_message(pduSessEstablishmentReq, dnn=dnn, snssai=slices)
    secProtNasMsg = fgmm_security_protected_nas_message(ciphAlgo, ntegAlgo, k_nas_enc, k_nas_int, ulNasTransportMsg, is_pdu=True)
    
    nas_encoded = secProtNasMsg.hex()
    IEs = []
    IEs.append({'id': 10, 'criticality': 'reject', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 38, 'criticality': 'reject', 'value': ('NAS-PDU', bytes.fromhex(nas_encoded))})
    IEs.append({'id': 121, 'criticality': 'reject', 'value': ('UserLocationInformation', ('userLocationInformationNR', {'tAI': {'pLMNIdentity': plmn_bcd, 'tAC': bytes.fromhex(tac)},'nR-CGI': {'pLMNIdentity': plmn_bcd, 'nRCellIdentity': (gnb_id, 36)}}))})

    val = ('initiatingMessage', {'procedureCode': 46, 'criticality': 'ignore', 'value': ('UplinkNASTransport', {'protocolIEs': IEs})})
    return val

def ConfigurationUpdateMessage(pdu_dict):
    pass

def LocationReportingControlMessage(pdu_dict):
    pass    

def PDUSessionResourceSetupRequestMessage(pdu_dict):
    PDUSessionResourceSetupListSUReq = None
    # print(pdu_dict['value'][1]['protocolIEs'])
    for IE in pdu_dict['value'][1]['protocolIEs']:
        if IE['value'][0] == 'PDUSessionResourceSetupListSUReq':
            PDUSessionResourceSetupListSUReq = IE['value'][1]
            break
    PDUSessID = PDUSessionResourceSetupListSUReq[0]['pDUSessionID']
    pDUSessionNAS_PDU = PDUSessionResourceSetupListSUReq[0]['pDUSessionNAS-PDU'][7:]
    DLNasTransport = FGMMDLNASTransport()
    DLNasTransport.from_bytes(pDUSessionNAS_PDU)
    PDUSessEstabAccept = FGSMPDUSessionEstabAccept()
    PDUSessEstabAccept.from_bytes(DLNasTransport['PayloadContainer']['V'].get_val())
    PDUAddress = PDUSessEstabAccept['PDUAddress']['PDUAddress']['Addr'].get_val()
    SNSSAI = PDUSessEstabAccept['SNSSAI']['SNSSAI']
    SNSSAI = {'SST': SNSSAI['SST'].get_val(), 'SD': SNSSAI['SD'].get_val()}
    DNN = PDUSessEstabAccept['DNN']['DNN'].get_val()[0][1]
    
    oct1, oct2, oct3, oct4 = struct.unpack('!BBBB', PDUAddress)
    ipv4_str = f'{oct1}.{oct2}.{oct3}.{oct4}'
    # print(pdu_dict['value'])
    PDUSessionResourceSetupRequestTransfer = PDUSessionResourceSetupListSUReq[0]['pDUSessionResourceSetupRequestTransfer'][1]['protocolIEs']
    ie_139 = next(ie for ie in PDUSessionResourceSetupRequestTransfer if ie['id'] == 139)
    gTP_TEID = ie_139['value'][1][1]['gTP-TEID']
    ie_136 = next(ie for ie in PDUSessionResourceSetupRequestTransfer if ie['id'] == 136)
    qosFlowIdentifier = ie_136['value'][1][0]['qosFlowIdentifier']
    return ipv4_str, gTP_TEID, qosFlowIdentifier, SNSSAI, DNN, PDUSessID


def PDUSessResourceSetupResponseMessage(amf_ue_ngap_id, qosFlowIdentifier, plmn_bcd, gnb_ip="192.168.55.9", gnb_teid=2, ran_ue_ngap_id=1, tac="000001"):
    ip_obj = ipaddress.ip_address(gnb_ip)
    IEs = []
    IEs.append({'id': 10, 'criticality': 'ignore', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'ignore', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 75, 'criticality': 'ignore', 'value':   ('PDUSessionResourceSetupListSURes', [{'pDUSessionID': 1, 'pDUSessionResourceSetupResponseTransfer': bytes.fromhex(f'0003e0{ip_obj.packed.hex()}{int_to_hex8(2)}{int_to_hex4(qosFlowIdentifier)}')}])})
    # IEs.append({'id': 121, 'criticality': 'ignore', 'value': ('UserLocationInformation', ('userLocationInformationNR', {'tAI': {'pLMNIdentity': plmn_bcd, 'tAC': bytes.fromhex(tac)},'nR-CGI': {'pLMNIdentity': plmn_bcd, 'nRCellIdentity': (1, 36)}}))})

    val = ('successfulOutcome', {'procedureCode': 29, 'criticality': 'reject', 'value': ('PDUSessionResourceSetupResponse', {'protocolIEs': IEs})})
    
    
    return val 


def fgmm_registration_request_message(msin="0112345038", plmn="46099", nssai=[{'SST': 1}]):
    RegIEs = {}
    RegIEs['5GMMHeader'] = {'EPD': 126, 'spare': 0, 'SecHdr': 0, 'Type': 65}
    RegIEs['NAS_KSI'] = {'TSC': 0, 'Value': 7}
    RegIEs['5GSRegType'] = {'FOR': 1, 'Value': 1}
    RegIEs['5GSID'] = {'spare': 0, 'Fmt': 0, 'spare': 0, 'Type': 1, 'Value': {'PLMN': plmn, 'RoutingInd': b'\x00\x00', 'spare': 0, 'ProtSchemeID': 0, 'HNPKID': 0, 'Output': bcd(msin)}}
    RegIEs['UESecCap'] = {'5G-EA0': 1, '5G-EA1_128': 1, '5G-EA2_128': 1, '5G-EA3_128': 1, '5G-EA4': 0, '5G-EA5': 0, '5G-EA6': 0, '5G-EA7': 0, '5G-IA0': 1, '5G-IA1_128': 1, '5G-IA2_128': 1, '5G-IA3_128': 1, '5G-IA4': 0, '5G-IA5': 0, '5G-IA6': 0, '5G-IA7': 0, 'EEA0': 1, 'EEA1_128': 1, 'EEA2_128': 1, 'EEA3_128': 1, 'EEA4': 0, 'EEA5': 0, 'EEA6': 0, 'EEA7': 0, 'EIA0': 1, 'EIA1_128': 1, 'EIA2_128': 1, 'EIA3_128': 1, 'EIA4': 0, 'EIA5': 0, 'EIA6': 0, 'EIA7': 0}
    RegIEs['5GSUpdateType'] = {'EPS-PNB-CIoT': 0, '5GS-PNB-CIoT': 0, 'NG-RAN-RCU': 0, 'SMSRequested': 0}
    RegIEs['5GMMCap'] = {'SGC': 0, '5G-HC-CP-CIoT': 0, 'N3Data': 0, '5G-CP-CIoT': 0, 'RestrictEC': 0, 'LPP': 0, 'HOAttach': 0, 'S1Mode': 0}
    RegIEs['NSSAI'] = [{'SNSSAI': s} for s in nssai]
    RegMsg = FGMMRegistrationRequest(val=RegIEs)
    RegMsg['5GMMCap']['5GMMCap'].disable_from(8)
    return RegMsg.to_bytes()

def fgmm_security_mode_command_message(regReqMsg, imeisv):
    IEs = {}
    IEs['5GMMHeader'] = {'EPD': 126, 'spare': 0, 'SecHdr': 0}
    IEs['IMEISV'] = {'Type': FGSIDTYPE_IMEISV, 'Digit1': int(imeisv[0]), 'Digits': imeisv[1:]}
    IEs['NASContainer'] = {}
    SMC_Msg = FGMMSecurityModeComplete(val=IEs)
    SMC_Msg['NASContainer']['V'].set_val(regReqMsg)
    return SMC_Msg.to_bytes()

def fgmm_security_protected_nas_message(CiphAlgo, IntegAlgo, k_nas_enc, k_nas_int, secModeMsg, is_pdu=False, is_service_request=False):
    IEs = {}
    if is_service_request:
        IEs['5GMMHeaderSec'] = {'EPD': 126, 'spare': 0, 'SecHdr': 1}
    elif CiphAlgo != 0 or is_pdu:
        IEs['5GMMHeaderSec'] = {'EPD': 126, 'spare': 0, 'SecHdr': 2}
    else:
        IEs['5GMMHeaderSec'] = {'EPD': 126, 'spare': 0, 'SecHdr': 4}
    SecMsg = FGMMSecProtNASMessage(val=IEs)
    SecMsg['NASMessage'].set_val(secModeMsg)
    # if CiphAlgo=0, it is not encrypted, so no need to encrypt
    if CiphAlgo != 0:
        SecMsg.encrypt(key=k_nas_enc, dir=0, fgea=CiphAlgo, seqnoff=0, bearer=1)
    SecMsg.mac_compute(key=k_nas_int, dir=0, fgia=IntegAlgo, seqnoff=0, bearer=1)
    return SecMsg.to_bytes()

def fgmm_registration_complete_message():
    RegCompleteMsg = FGMMRegistrationComplete()
    return RegCompleteMsg.to_bytes()

def fgsm_pdu_session_establishment_request_message():
    
    smIEs = {}
    # TODO: PTI 是用户事务的唯一标识，不同用户需要不同的 PTI，以确保事务的唯一性和关联性。
    smIEs['5GSMHeader'] = {'Type': 193, 'PTI': 1}
    smIEs['PDUSessType'] = {'Value': 1}  # PDU Session Type: IPv4
    smIEs['SSCMode'] = {'Value': 1}
    smIEs['5GSMCap'] = {'TPMIC': 0, 'ATSSS-ST': 0, 'EPT-S1': 0, 'MH6-PDU': 0, 'RQoS': 0}
    smIEs['ExtProtConfig'] = {'Ext': 1, 'spare': 0, 'Prot': 0} 
    # smIEs['IntegrityProtMaxDataRate'] = {}  # Request accepted

    PduSessEstabReq = FGSMPDUSessionEstabRequest(val=smIEs)
    return PduSessEstabReq.to_bytes()

def fgmm_ul_nas_transport_message(pduSessEstablishmentReq, dnn=b'internet', snssai={'SST': 1}): 
    ulIEs = {}
    ulIEs['5GMMHeader'] = {'EPD': 126, 'spare': 0, 'SecHdr': 0, 'Type': 103}
    ulIEs['PDUSessID'] = 1
    ulIEs['RequestType'] = 1
    ulIEs['SNSSAI'] = {'SST': snssai["SST"]}  # Service Data
    if snssai.get("SD"):
        ulIEs['SNSSAI']['SD'] = snssai["SD"]        
 
    ULNasTransportMsg = FGMMULNASTransport(val=ulIEs)
    ULNasTransportMsg['PayloadContainer']['V'].set_val(pduSessEstablishmentReq)
    # ULNasTransportMsg['DNN'].set_val({'T': 0x25, 'V': dnn})

    # mamually set DNN, because of the bug in to_bytes method makes dnn information lost
    # fomat is 25[length of the DNN + length of the Length field)][length of the DNN][DNN]
    # for example, if DNN is "internet", the length of the DNN is 8, the length of the Length field is 1, 
    # the hex of DNN is 696e7465726e6574, so the DNN message is 250908696e7465726e6574
    dnn_str_len = len(dnn)
    dnn_msg = f"25{hex(dnn_str_len + 1)[2:].zfill(2)}{hex(dnn_str_len)[2:].zfill(2)}" + dnn.hex()
    dnn_msg = bytes.fromhex(dnn_msg)

    return ULNasTransportMsg.to_bytes() + dnn_msg



def UEContextReleaseRequestMessage(amf_ue_ngap_id, ran_ue_ngap_id, pdu_session_id=None):
    IEs = []
    IEs.append({'id': 10, 'criticality': 'reject', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'reject', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 133, 'criticality': 'reject', 'value': ('PDUSessionResourceListCxtRelReq', [{'pDUSessionID': 1}, {'pDUSessionID': 2}])})
    IEs.append({'id': 15, 'criticality': 'ignore', 'value': ('Cause', ('radioNetwork', 'user-inactivity'))})
    val = ('initiatingMessage', {'procedureCode': 42, 'criticality': 'ignore', 'value': ('UEContextReleaseRequest', {'protocolIEs': IEs})})

    return val

def UEContextReleaseCommandMessage(pdu_dict):
    protocolIEs = pdu_dict['value'][1]['protocolIEs']
    
    for ie in protocolIEs:
        if ie['id'] == 114 and ie['value'][0] == 'UE-NGAP-IDs':
            # 检查是否是uE-NGAP-ID-pair类型
            if ie['value'][1][0] == 'uE-NGAP-ID-pair':
                ue_ngap_id_pair = ie['value'][1][1]
                amf_ue_ngap_id = ue_ngap_id_pair['aMF-UE-NGAP-ID']
                ran_ue_ngap_id = ue_ngap_id_pair['rAN-UE-NGAP-ID'] 
    return amf_ue_ngap_id, ran_ue_ngap_id

def UEContextReleaseCompleteMessage(amf_ue_ngap_id, ran_ue_ngap_id, plmn_bcd, tac, gnb_id):
    IEs = []
    IEs.append({'id': 10, 'criticality': 'ignore', 'value': ('AMF-UE-NGAP-ID', amf_ue_ngap_id)})
    IEs.append({'id': 85, 'criticality': 'ignore', 'value': ('RAN-UE-NGAP-ID', ran_ue_ngap_id)})
    IEs.append({'id': 121, 'criticality': 'ignore', 'value': ('UserLocationInformation', ('userLocationInformationNR', {'tAI': {'pLMNIdentity': plmn_bcd, 'tAC': bytes.fromhex(tac)},'nR-CGI': {'pLMNIdentity': plmn_bcd, 'nRCellIdentity': (gnb_id, 36)}}))})
    IEs.append({'id': 60, 'criticality': 'reject', 'value': ('PDUSessionResourceListCxtRelCpl', [{'pDUSessionID': 1}, {'pDUSessionID': 2}])})
    val = ('successfulOutcome', {'procedureCode': 41, 'criticality': 'reject', 'value': ('UEContextReleaseComplete', {'protocolIEs': IEs})})
    return val
