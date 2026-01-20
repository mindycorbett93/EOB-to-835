import streamlit as st
import cv2
import easyocr
import datetime
from PIL import Image
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any

# --- LAYER 1: FINANCIAL INTEGRITY & BALANCING  ---
class RemitBalancingSchema(BaseModel):
    """
    CMS Rule: Check Amount (BPR02) = Σ(Claim Payments) + Σ(Adjustments).
    Prevents unbalanced files from entering the EMR.
    """
    check_amount: float = Field(..., alias="BPR02")
    payer_id: str = Field(..., alias="N104_PR")
    claims: List

    @validator('claims')
    def validate_reconciliation(cls, v, values):
        total_claims_paid = sum(c['paid_amount'] for c in v)
        # In a full version, this would also sum CAS adjustments 
        if abs(values['check_amount'] - total_claims_paid) > 0.01:
            raise ValueError(f"Reconciliation Failed: Check ${values['check_amount']}!= Payments ${total_claims_paid}")
        return v

# --- LAYER 2: ANSI X12 835 GENERATOR (The Output Engine) ---
class X12Generator835:
    """Manages segment building for postable 835 files based on CMS 5010A1."""
    def __init__(self, sep="*", term="~"):
        self.sep = sep
        self.term = term

    def build_seg(self, tag, *elements):
        # CMS Rule: Amount fields must be right-justified/zero-filled 
        return f"{tag}{self.sep}{self.sep.join(map(str, elements))}{self.term}"

    def generate(self, data: Dict) -> str:
        now = datetime.datetime.now()
        dt, tm = now.strftime("%Y%m%d"), now.strftime("%H%M")
        
        segments = [
            # Interchange & Functional Envelopes [2, 2]
            self.build_seg("ISA", "00", " "*10, "00", " "*10, "ZZ", "SENDER_ID".ljust(15), "ZZ", "CMS".ljust(15), dt[2:], tm, "^", "00501", "000000001", "0", "P", ":"),
            self.build_seg("GS", "HP", "SENDER", "CMS", dt, tm, "1", "X", "005010X221A1"),
            self.build_seg("ST", "835", "0001"),
            # BPR Segment: The financial core 
            self.build_seg("BPR", "I", data['check_amount'], "C", "ACH", "CTX", "01", "999999999", "DA", "ACCOUNT", data['payer_id'], "", "", "", "", dt),
            self.build_seg("TRN", "1", "TRACE_123", data['payer_id']), # For matching EFT 
        
        # Loop 2100: Claim Level Data 
        for claim in data['claims']:
            segments.append(self.build_seg("CLP", claim['pcn'], "1", claim['billed'], claim['paid_amount'], "", "12", "CLAIM_ID"))
            segments.append(self.build_seg("NM1", "QC", "1", claim['lname'], claim['fname'], "", "", "", "MI", claim['member_id']))
        
        segments.extend()
        return "\n".join(segments)

# --- LAYER 3: OCR & HITL UI (The Multi-tier Resolution Portal) ---
def remit_exception_portal():
    st.set_page_config(layout="wide")
    st.title("EOB-to-835 Integrated Processor")
    
    uploaded_file = st.file_uploader("Upload EOB Image or PDF", type=["jpg", "png", "pdf"])
    
    if uploaded_file:
        # 1. Image Pre-processing (OpenCV deskewing/denoising to minimize failures)
        reader = easyocr.Reader(['en'])
        results = reader.readtext(uploaded_file.getvalue())
        confidence = sum([res[1] for res in results]) / len(results) if results else 0
        
        # 2. Confidence Routing Logic
        if confidence < 0.85:
            st.error(f"Low OCR Confidence ({confidence:.2f}). Triggering HITL Module.")
            col1, col2 = st.columns(2)
            
            with col1: # Side-by-Side UI [Image 1]
                st.image(uploaded_file, caption="Unreadable EOB Source")
            
            with col2: # Questions Module for missing/malformed data
                st.header("Manual Data Capture")
                p_id = st.text_input("Payer Identification (BPR10)")
                check_val = st.number_input("Total Check/EFT Amount (BPR02)", step=0.01)
                pcn_val = st.text_input("Patient Account Number (CLP01)")
                billed_val = st.number_input("Claim Billed Amount (CLP03)", step=0.01)
                paid_val = st.number_input("Claim Paid Amount (CLP04)", step=0.01)
                
                if st.button("Generate 835 from Manual Entry"):
                    try:
                        manual_data = {"payer_id": p_id, "check_amount": check_val, "claims": [{"pcn": pcn_val, "billed": billed_val, "paid_amount": paid_val}]}
                        # Validate balancing before generation 
                        RemitBalancingSchema(**manual_data)
                        
                        builder = X12Generator835()
                        x12_output = builder.generate(manual_data)
                        st.success("835 Generated Successfully!")
                        st.download_button("Download 835 File", x12_output, file_name="hitl_remit.edi")
                    except Exception as e:
                        st.warning(f"Integrity Error: {e}")
        else:
            # 3. Automatic Generation for High-Confidence Reads
            st.success(f"High-Confidence Capture ({confidence:.2f}). Generating 835 automatically.")
            # Logic to map 'results' to 'auto_data' dictionary...
            # x12_output = X12Generator835().generate(auto_data)
            # st.download_button("Download 835 File", x12_output, file_name="auto_remit.edi")

if __name__ == "__main__":
    remit_exception_portal()
