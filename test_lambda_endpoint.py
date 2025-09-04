#!/usr/bin/env python3
"""
Test script for the deployed Lambda function endpoint.
This script tests the actual deployed API endpoint.
"""

import json
import base64
import sys
import os
import mimetypes
import requests


def test_lambda_endpoint(endpoint_url: str, file_path: str):
    """
    Test the deployed Lambda function endpoint.

    Args:
        endpoint_url (str): The Lambda function URL
        file_path (str): Path to the file to test
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    # Read and encode file
    with open(file_path, "rb") as f:
        file_data = f.read()
        data = base64.b64encode(file_data).decode("utf-8")

    # Prepare request payload
    media_type, _ = mimetypes.guess_type(file_path)
    payload = {"data": data, "media_type": media_type}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {os.getenv('API_KEY')}"}

    try:
        print("🚀 Sending request to Lambda endpoint...")
        import time

        start_time = time.time()

        response = requests.post(
            endpoint_url, json=payload, headers=headers, timeout=120
        )

        elapsed_time = time.time() - start_time
        print(f"📊 Response Status: {response.status_code}")
        print(f"⏱️  Response Time: {elapsed_time:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            print("✅ Success! Response:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("❌ Error response:")
            print(response.text)

    except requests.exceptions.Timeout:
        print(
            "❌ Request timed out. The Lambda function may be taking too long to process the file."
        )
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        print(f"Raw response: {response.text}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    file_path = sys.argv[1]
    test_lambda_endpoint(
        "https://aaw3hzxo522jzmiidkmvpoulmm0gtdeo.lambda-url.ap-northeast-1.on.aws/",
        file_path,
    )
