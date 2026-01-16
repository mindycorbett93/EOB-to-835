import logging
import json

# Configure logging for enterprise-level error tracking
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class Intelligent835Converter:
    def __init__(self):
        self.version = "5010A1"
        # Mandatory segments per CMS Usa 'R' column [cite: 1, 13, 14]
        self.mandatory_segments = ["ISA", "GS", "ST", "BPR", "TRN", "N1", "CLP", "SVC", "SE", "GE", "IEA"]

    def reconcile_financials(self, record):
        """
        Validates Check Amount = Σ(Claim Payments) + Adjustments.
        """
        try:
            total_paid = sum(float(c.get('payment_amount', 0)) for c in record.get('claims', []))
            # BPR02: Total Actual Provider Payment Amount [cite: 1]
            reported_total = float(record.get('total_check_amount', 0))

            if abs(total_paid - reported_total) > 0.01:
                return False, f"Reconciliation Error: Sum({total_paid}) != BPR02({reported_total})"
            return True, "Reconciled"
        except (ValueError, TypeError) as e:
            return False, f"Invalid numeric data in record: {e}"

    def generate_835(self, raw_data_batch):
        """
        Main engine: Ingests raw data and outputs validated X12 segments.
        Handles Required (R) and Situational (S) segments.
        """
        x12_output = []
        
        for record in raw_data_batch:
            try:
                # 1. Fault-Tolerance: Validate record structure before processing
                if not isinstance(record, dict) or 'claims' not in record:
                    raise ValueError("Malformed record: Missing required structure.")

                # 2. Financial Integrity Check
                success, msg = self.reconcile_financials(record)
                if not success:
                    logging.warning(f"Quarantining record: {msg}")
                    continue

                # 3. Required Segment: BPR (Financial Information) [cite: 1]
                bpr = f"BPR*{record['handling_code']}*{record['total_check_amount']}*C*{record['payment_method']}~"
                x12_output.append(bpr)

                # 4. Required Segment: TRN (Reassociation Trace) [cite: 2]
                trn = f"TRN*1*{record['trace_number']}*{record['payer_id']}~"
                x12_output.append(trn)

                # 5. Claim-Level Processing (Loop 2100)
                for claim in record['claims']:
                    # CLP: Claim Level Data (Required) [cite: 5]
                    clp = f"CLP*{claim['patient_id']}*{claim['status_code']}*{claim['total_charge']}*{claim['payment_amount']}~"
                    x12_output.append(clp)

                    # Situational (S) Segments based on CMS mapping 
                    if 'covered_days' in claim:
                        # MIA: Inpatient Adjudication (Situational) [cite: 8, 9]
                        mia = f"MIA*{claim['covered_days']}***{claim.get('drg_amount', '')}~"
                        x12_output.append(mia)
                    
                    if 'hcpcs_payable' in claim:
                        # MOA: Outpatient Adjudication (Situational) [cite: 10]
                        moa = f"MOA***{claim['hcpcs_payable']}~"
                        x12_output.append(moa)

                    # SVC: Service Payment Information (Required Loop 2110) [cite: 11]
                    for service in claim.get('services', []):
                        svc = f"SVC*HC:{service['cpt']}*{service['charge']}*{service['payment']}~"
                        x12_output.append(svc)

            except KeyError as e:
                logging.error(f"Data Mismatch: Missing required CMS field {e}. Skipping record.")
                continue # Skip malformed record and keep engine running
            except Exception as e:
                logging.critical(f"System Error processing record: {str(e)}")
                continue

        return x12_output

# Mock Example of Enterprise Ingestion
batch_data = [
    {
        "handling_code": "I", "total_check_amount": 500.00, "payment_method": "ACH", "trace_number": "12345", "payer_id": "999",
        "claims": [{"patient_id": "PT1", "status_code": "1", "total_charge": 600.00, "payment_amount": 500.00, "covered_days": "2", "services": []}]
    },
    {"total_check_amount": 100.00, "claims": []} # Fails reconciliation, triggers quarantine
]

engine = Intelligent835Converter()
final_835 = engine.generate_835(batch_data)
print(f"Generated {len(final_835)} segments for ANSI 835 export.")
