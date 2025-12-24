#!/usr/bin/env python3
"""
Quick test script for chat execution.

Usage:
    python test_chat.py <dataset_id> "Your question here"
"""

import sys
import requests
import json

BASE_URL = "http://localhost:8000"

def test_question(dataset_id: str, question: str):
    """Test a question on a dataset."""
    url = f"{BASE_URL}/api/chat/{dataset_id}/execute"
    
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.post(
            url,
            json={"question": question},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Success!")
            print(f"\nResult Type: {result.get('result', {}).get('type', 'unknown')}")
            print(f"Metadata: {json.dumps(result.get('metadata', {}), indent=2)}")
            
            # Format result based on type
            result_data = result.get('result', {})
            result_type = result_data.get('type')
            
            if result_type == "scalar":
                value = result_data.get('value')
                agg = result_data.get('aggregation', 'value')
                print(f"\nAnswer: {agg} = {value}")
                
            elif result_type == "ranking":
                data = result_data.get('data', [])
                print(f"\nTop {len(data)} results:")
                for item in data[:5]:
                    print(f"  {item.get('rank')}. {item.get('group')}: {item.get('value')}")
                    
            elif result_type == "time_series":
                data = result_data.get('data', [])
                print(f"\nTime series ({len(data)} points):")
                for item in data[:5]:
                    print(f"  {item.get('time')}: {item.get('value')}")
                    
            elif result_type == "breakdown":
                data = result_data.get('data', [])
                print(f"\nBreakdown ({len(data)} groups):")
                for item in data[:5]:
                    print(f"  {item.get('dimension')}: {item.get('value')}")
                    
            elif result_type == "clarification":
                print(f"\n⚠️  Clarification needed:")
                print(f"   {result_data.get('message', 'No message')}")
                
            elif result_type == "empty":
                print(f"\n📭 No results found")
                
            elif result_type == "table":
                data = result_data.get('data', [])
                print(f"\n📊 Table ({len(data)} rows)")
                if data:
                    print(f"   Columns: {', '.join(result_data.get('columns', []))}")
                    print(f"   First row: {data[0]}")
            else:
                print(f"\nRaw result: {json.dumps(result_data, indent=2)}")
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to backend")
        print("   Make sure backend is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_chat.py <dataset_id> \"Your question here\"")
        print("\nExample:")
        print('  python test_chat.py abc123 "How many records are in this dataset?"')
        sys.exit(1)
    
    dataset_id = sys.argv[1]
    question = " ".join(sys.argv[2:])
    
    test_question(dataset_id, question)

