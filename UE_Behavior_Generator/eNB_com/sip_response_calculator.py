# main.py
from CryptoMobile.Milenage import Milenage
from binascii import unhexlify, hexlify
import base64
import hashlib

def calculate_response(imsi, nonce_b64):
    # ================== 配置参数 ==================
    # 所有用户的K、OPC等参数写死
    K_hex = "8BAF473F2F8FD09487CCCBD7097C6862"
    OPc_hex = "E8ED289DEBA952E4283B54E88E618ABC"
    username = f"{imsi}@ims.mnc092.mcc466.3gppnetwork.org"
    realm = "ims.mnc092.mcc466.3gppnetwork.org"
    method = "REGISTER"
    uri = "sip:ims.mnc092.mcc466.3gppnetwork.org"
    nc = "00000001"
    cnonce = "4149304045"
    qop = "auth"

    #  数据预处理
    K = unhexlify(K_hex)
    OPc = unhexlify(OPc_hex)
    nonce_bytes = base64.b64decode(nonce_b64)
    RAND = nonce_bytes[:16]

    # Milenage 计算RES
    milenage = Milenage(OPc)
    milenage.set_opc(OPc)
    RES, CK, IK, AK = milenage.f2345(K, RAND)
    RES_hex = hexlify(RES).decode()

    # Digest 计算部分
    xres_bytes = RES
    ha1_input = f"{username}:{realm}:".encode() + xres_bytes
    ha1 = hashlib.md5(ha1_input).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    response_input = f"{ha1}:{nonce_b64}:{nc}:{cnonce}:{qop}:{ha2}"
    response = hashlib.md5(response_input.encode()).hexdigest()

    return response

if __name__ == "__main__":
    # 示例
    imsi = "466920123456795"  # 传入的IMSI
    nonce_b64 = "AIT+zJvkDKZFLVPdJf3udtpYprxCAIAAHZmy2LyhaZQ="
    print(calculate_response(imsi, nonce_b64))
