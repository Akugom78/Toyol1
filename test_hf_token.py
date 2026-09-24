# test_hf_token.py
import sys
import os

# Fix path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import streamlit as st

print("=" * 60)
print("HF TOKEN DIAGNOSTIC TEST")
print("=" * 60)

# Test 1: Check if secrets.toml exists
print("\n[TEST 1] Checking if .streamlit/secrets.toml exists...")
secrets_path = os.path.join(current_dir, ".streamlit", "secrets.toml")
if os.path.exists(secrets_path):
    print(f"✅ Found: {secrets_path}")
else:
    print(f"❌ NOT FOUND: {secrets_path}")
    print("   Please create the .streamlit folder and secrets.toml file")
    sys.exit(1)

# Test 2: Read the token from secrets
print("\n[TEST 2] Reading HUGGINGFACE_TOKEN from secrets.toml...")
try:
    hf_token = st.secrets.get("HUGGINGFACE_TOKEN")
    if hf_token:
        print(f"✅ Token found!")
        print(f"   Token starts with: {hf_token[:10]}...")
        print(f"   Token length: {len(hf_token)} characters")
        
        # Check format
        if hf_token.startswith("hf_"):
            print("✅ Token format looks correct (starts with 'hf_')")
        else:
            print("⚠️  Warning: Token doesn't start with 'hf_' - might be incorrect")
    else:
        print("❌ HUGGINGFACE_TOKEN not found in secrets.toml")
        print("   Please add: HUGGINGFACE_TOKEN = \"hf_your_token_here\"")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error reading secrets: {e}")
    sys.exit(1)

# Test 3: Set environment variable and test
print("\n[TEST 3] Setting HF_TOKEN environment variable...")
os.environ["HF_TOKEN"] = hf_token
print(f"✅ Environment variable set")

# Test 4: Try to use the token with huggingface_hub
print("\n[TEST 4] Testing token with Hugging Face Hub API...")
try:
    from huggingface_hub import HfApi
    api = HfApi()
    
    # Try to get user info (this will fail if token is invalid)
    user_info = api.whoami(token=hf_token)
    print(f"✅ Token is VALID!")
    print(f"   Logged in as: {user_info.get('name', 'Unknown')}")
    print(f"   Email: {user_info.get('email', 'Unknown')}")
    
except Exception as e:
    print(f"❌ Token validation failed: {e}")
    print("   Your token might be invalid or expired")
    print("   Please generate a new token at: https://huggingface.co/settings/tokens")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nYour HF token is working correctly.")
print("You can now run: streamlit run app.py")