"""
Test script to verify missing criteria detection
"""
import sys
import io
import requests

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "http://localhost:8000/api/analyze-project"

def test_file(filename, description):
    """Test a single file and display results"""
    print(f"\n{'='*70}")
    print(f"Testing: {description}")
    print(f"File: {filename}")
    print('='*70)
    
    try:
        with open(filename, 'rb') as f:
            files = {'file': (filename, f, 'text/plain')}
            response = requests.post(API_URL, files=files)
        
        if response.status_code == 200:
            data = response.json()
            analysis = data['analysis']
            
            print(f"\n✓ Analysis Complete")
            print(f"\nProject Type: {analysis['project_type']}")
            print(f"Capacity: {analysis['estimated_capacity_kw']} kW")
            print(f"Confidence Level: {analysis['confidence_level']}")
            print(f"Data Completeness: {analysis.get('data_completeness', '100%')}")
            
            # Display missing criteria
            if 'missing_criteria' in analysis:
                print(f"\n⚠️  MISSING CRITERIA ({len(analysis['missing_criteria'])} items):")
                for item in analysis['missing_criteria']:
                    print(f"   • {item}")
            else:
                print(f"\n✓ All critical criteria found!")
            
            # Display pricing
            print(f"\nPRICING ESTIMATE:")
            for key, value in analysis['pricing_breakdown'].items():
                print(f"   {key.replace('_', ' ').title()}: {value}")
            
            # Display warnings
            warnings = [note for note in analysis['notes'] if '⚠️' in note]
            if warnings:
                print(f"\nWARNINGS:")
                for warning in warnings:
                    print(f"   {warning}")
            
            return True
        else:
            print(f"✗ FAILED! Status: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return False

def main():
    print("\n" + "="*70)
    print("MISSING CRITERIA DETECTION TEST SUITE")
    print("="*70)
    
    results = []
    
    # Test 1: Complete report
    results.append(test_file(
        'sample_project_report.txt',
        'Complete Project Report (should have minimal missing criteria)'
    ))
    
    # Test 2: Incomplete report
    results.append(test_file(
        'incomplete_project_report.txt',
        'Incomplete Project Report (should detect missing criteria)'
    ))
    
    # Test 3: Minimal report
    results.append(test_file(
        'minimal_project_report.txt',
        'Minimal Project Report (should detect many missing criteria)'
    ))
    
    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print('='*70)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n✓ All tests PASSED!")
    else:
        print("\n✗ Some tests FAILED!")
    
    print('='*70 + "\n")

if __name__ == "__main__":
    main()

# Made with Bob
