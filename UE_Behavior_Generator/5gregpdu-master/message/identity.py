
class FGGUTI:
    def __init__(self, plmn, amf_region_id, amf_set_id, amf_ptr, tmsi):
        """
        Initialize a 5G GUTI object
        
        Args:
            plmn (int): Public Land Mobile Network identifier (MCC/MNC)
            amf_region_id (int): AMF Region ID (8 bits)
            amf_set_id (int): AMF Set ID (10 bits)
            amf_ptr (int): AMF Pointer (6 bits)
            tmsi (int): 5G Temporary Mobile Subscriber Identity (32 bits)
        """
        self.plmn = plmn
        self.amf_region_id = amf_region_id
        self.amf_set_id = amf_set_id
        self.amf_ptr = amf_ptr
        self.tmsi = tmsi
    
    def __str__(self):
        """
        String representation of the GUTI
        
        Returns:
            str: String representation
        """
        guti_dict = {
            "5G-GUTI": {
                "PLMN": self.plmn,
                "AMFRegionID": self.amf_region_id,
                "AMFSetID": self.amf_set_id,
                "AMFPtr": self.amf_ptr,
                "5GTMSI": hex(self.tmsi)
            }
        }
        return str(guti_dict)

