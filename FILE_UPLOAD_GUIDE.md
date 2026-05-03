# File Upload & Pricing Analysis Guide

## Overview
The HydroQuote AI system now supports uploading project reports to receive instant pricing estimates for hydro turbine installations.

## Supported File Formats
- **TXT** - Plain text files
- **PDF** - Adobe PDF documents
- **DOCX** - Microsoft Word documents
- **DOC** - Legacy Word documents

## File Requirements
- Maximum file size: **10MB**
- Minimum text content: **50 characters**
- File must contain project-related information

## How to Use

### Via Web Interface
1. Open http://localhost:3000 in your browser
2. Navigate to the "Project Report Analysis & Pricing" section
3. Click "Choose File" and select your project report
4. Click "Analyze & Get Pricing"
5. View the detailed pricing breakdown and project analysis

### Via API
```bash
curl -X POST "http://localhost:8000/api/analyze-project" \
  -F "file=@your_project_report.pdf"
```

### Via Python
```python
import requests

with open('project_report.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/analyze-project', files=files)
    data = response.json()
    print(data['analysis']['pricing_breakdown'])
```

## API Response Format
```json
{
  "success": true,
  "filename": "project_report.pdf",
  "file_size_bytes": 12345,
  "text_length": 1500,
  "analysis": {
    "project_type": "Micro Hydro System",
    "estimated_capacity_kw": 150,
    "pricing_breakdown": {
      "equipment_cost": "$300,000.00",
      "installation_cost": "$90,000.00",
      "engineering_cost": "$45,000.00",
      "total_estimated_cost": "$435,000.00"
    },
    "timeline_estimate": "12-18 months",
    "confidence_level": "Medium",
    "notes": [...]
  },
  "timestamp": "2026-05-02T03:45:00Z"
}
```

## Pricing Calculation

### Base Rates (per kW)
- **Micro Hydro Systems**: $2,000/kW
- **Standard Systems**: $1,500/kW
- **Industrial Systems**: $1,200/kW

### Cost Components
- **Equipment Cost**: Base rate × Capacity
- **Installation Cost**: 30% of equipment cost
- **Engineering Cost**: 15% of equipment cost

### Example
For a 150kW Micro Hydro System:
- Equipment: 150kW × $2,000 = $300,000
- Installation: $300,000 × 0.30 = $90,000
- Engineering: $300,000 × 0.15 = $45,000
- **Total**: $435,000 (±5% variation)

## Important Notes

⚠️ **This is a Demo Version**
- Pricing is based on simplified keyword analysis
- Production version would use Watson NLU and Watsonx.ai
- Final pricing requires detailed site assessment
- Prices vary by location and specific requirements

## Testing

A sample project report is included: `sample_project_report.txt`

Run the test script:
```bash
python test_upload.py
```

## Troubleshooting

### "Unsupported file type"
- Ensure file has .txt, .pdf, .docx, or .doc extension
- Check file is not corrupted

### "File size exceeds 10MB limit"
- Compress or reduce file size
- Extract relevant sections only

### "File appears to be empty"
- Ensure file contains readable text
- PDF/DOCX files must have extractable text (not scanned images)

### "Cannot connect to API"
- Verify backend is running: `python start_backend.py`
- Check API is accessible at http://localhost:8000
- Verify CORS settings allow frontend access

## Future Enhancements
- Integration with Watson NLU for entity extraction
- Watsonx.ai LLM for intelligent analysis
- Historical pricing database
- Location-based pricing adjustments
- Multi-language support
- Batch file processing