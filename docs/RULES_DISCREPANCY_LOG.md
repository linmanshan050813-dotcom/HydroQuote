# Rules Discrepancy Log

Source of truth for engineering pricing: `Planning Docs/报价规则.docx` (and README restatements).  
**Do not silently change source documents.** Unresolved items force `review_required`.

| ID | Topic | Conflict / gap | Implementation decision |
|----|-------|----------------|-------------------------|
| D1 | Personnel cost @ 1500 kW | Table lists USD **3,000**; formula `USD 20,000 × TotalCapacity_kW / 1000` yields **30,000** for 1500 kW | Use **formula**; flag table as erroneous in audit; do not use 3,000 |
| D2 | RiskReserveRate | Formula requires rate; no single approved default in source | If not provided/approved → `review_required` (no fabricated firm quote). MVP allows explicit approved rate in request/config for tests only when `risk_reserve_rate_approved=true` |
| D3 | Governor / Valve / Automation bands | Ranges like USD 15,000–22,000 without fixed mid-point for >1500 kW | Outside exact interpolation bands (1000–1500) → `review_required` unless approved fixed coefficient provided |
| D4 | Generator high-voltage factor | Range 1.08–1.15 | Default 1.00 for standard; unknown high-voltage → review unless factor supplied |
| D5 | Inlet valve pressure factor | Range 1.10–1.30 | Default 1.00 low pressure; otherwise require approved factor |
| D6 | Automation Standard PLC | Range USD 8,000–15,000 | Default Standard base **USD 10,000** (doc “标准水电站控制系统”); Advanced SCADA only as optional upgrade line, not a 6th main item |
| D7 | >5000 kW per unit | Explicit manual review | Always `review_required` |
| D8 | Gross head vs net head | Net head required | Gross-only → missing field / confirmation; do not invent net head |

Approved for automated Fast Quote without human price gate (when inputs complete):

- Turbine / Generator / Governor / Valve interpolation **1000–1500 kW** exact formulas from doc
- Turbine type factors table (Francis 1.00 … Cross-flow 0.85)
- Frequency 50Hz factor 1.00; 60Hz 1.05
- Automation Standard default 10,000 × units (or Basic 1,900 when explicitly Basic)
- Personnel formula; after-sales **0.08**; commercial **× 2.40**
- Risk reserve only when explicitly approved numeric rate is present
