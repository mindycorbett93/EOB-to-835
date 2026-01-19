import streamlit as st
import cv2
import easyocr

class IntegratedRemitSuite:
    def __init__(self):
        self.reader = easyocr.Reader(['en'])

    def process_image(self, image_path):
        """Pre-processing and OCR logic (S_R46, S_R156)."""
        img = cv2.imread(image_path)
        # OpenCV denoising/deskewing to reduce HITL triggers
        results = self.reader.readtext(img)
        confidence = sum([res[1] for res in results]) / len(results)
        
        if confidence < 0.85:
            return self.launch_questions_module(image_path)
        return self.generate_835_flat_file(results)

    def launch_questions_module(self, image_path):
        """HITL Side-by-Side UI for rejected/malformed images (Image 1, S_R28)."""
        st.title("EOB Exception Resolution")
        col1, col2 = st.columns(2)
        with col1: st.image(image_path, caption="Rejected Image Source")
        with col2:
            st.warning("Automation Failed. Answer the following to complete 835:")
            payer_id = st.text_input("What is the Payer ID?")
            check_total = st.number_input("What is the Total Check/EFT Amount (BPR02)?")
            pcn = st.text_input("Enter Patient Account Number (CLP01)")
            
            if st.button("Generate 835 File"):
                # Pass manual data to generator
                return self.generate_835_flat_file({"payer": payer_id, "total": check_total, "pcn": pcn})

    def generate_835_flat_file(self, data):
        """Constructs the raw ANSI X12 835 segments (S_R24, S_R44)."""
        builder =
        builder.append(f"ST*835*0001~")
        builder.append(f"BPR*I*{data['total']}*C*ACH*CTX*01*999999999*DA*ACC*123~")
        builder.append(f"CLP*{data['pcn']}*1*150.00*125.00**12*CLAIM123~")
        builder.append(f"SE*4*0001~")
        return "\n".join(builder)
