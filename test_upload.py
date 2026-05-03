"""
Simple test script to verify file upload functionality
"""
import sys
import io
import requests

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "http://localhost:8000/api/analyze-project"
TEST_FILE = "sample_project_report.txt"

def test_file_upload():
    print("Testing file upload endpoint...")
    print(f"API URL: {API_URL}")
    print(f"Test file: {TEST_FILE}")
    print("-" * 50)
    
    try:
        # Open and upload the file
        with open(TEST_FILE, 'rb') as f:
            files = {'file': (TEST_FILE, f, 'text/plain')}
            response = requests.post(API_URL, files=files)
        
        print(f"Status Code: {response.status_code}")
        print("-" * 50)
        
        if response.status_code == 200:
            data = response.json()
            print("✓ SUCCESS! File uploaded and analyzed.")
            print(f"\nFilename: {data['filename']}")
            print(f"File size: {data['file_size_bytes']} bytes")
            print(f"Text length: {data['text_length']} characters")
            print(f"\nProject Type: {data['analysis']['project_type']}")
            print(f"Estimated Capacity: {data['analysis']['estimated_capacity_kw']} kW")
            print(f"\nPricing Breakdown:")
            for key, value in data['analysis']['pricing_breakdown'].items():
                print(f"  {key}: {value}")
            print(f"\nTimeline: {data['analysis']['timeline_estimate']}")
            print(f"Confidence: {data['analysis']['confidence_level']}")
            print("\n✓ Test PASSED!")
            return True
        else:
            print(f"✗ FAILED! Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    test_file_upload()

# Made with Bob
