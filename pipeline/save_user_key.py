import argparse
import os
import json
import tempfile
from huggingface_hub import HfApi, hf_hub_download
from pipeline.crypto import encrypt_data

def save_user_key(user_id: str, provider_id: str, raw_key: str):
    token = os.getenv("HF_TOKEN")
    repo_id = os.getenv("HF_KEYS_DATASET_REPO_ID") or "traderade/auto-clipper-keys"
    
    if not token:
        print("[Error] HF_TOKEN is not set.")
        return

    clean_user = user_id.strip()
    clean_provider = provider_id.strip().lower()
    
    api = HfApi()
    
    # Try to download existing keys file
    user_data = {}
    try:
        local_path = hf_hub_download(
            repo_id=repo_id,
            repo_type="dataset",
            filename=f"keys/{clean_user}.json",
            token=token
        )
        with open(local_path, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    except Exception as e:
        print(f"[Info] Dataset for {clean_user} not found or error ({e}). Creating new.")
        user_data = {"providers": []}

    # If it's the old format for groq
    if clean_provider == "groq" and "groq_key_encrypted" in user_data:
        user_data["groq_key_encrypted"] = encrypt_data(raw_key)
    
    if "providers" not in user_data:
        user_data["providers"] = []
        
    # Update or add provider
    found = False
    for p in user_data["providers"]:
        if p.get("provider_id", "").lower() == clean_provider:
            p["key_encrypted"] = encrypt_data(raw_key)
            found = True
            break
            
    if not found:
        user_data["providers"].append({
            "provider_id": clean_provider,
            "key_encrypted": encrypt_data(raw_key)
        })

    # Save to temp file and upload
    temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8")
    json.dump(user_data, temp_file, indent=2)
    temp_file.close()
    
    try:
        api.upload_file(
            path_or_fileobj=temp_file.name,
            path_in_repo=f"keys/{clean_user}.json",
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            commit_message=f"Update key for {clean_user} ({clean_provider})"
        )
        print(f"[Success] Successfully saved {clean_provider} key for {clean_user} to Hugging Face dataset.")
    except Exception as e:
        print(f"[Error] Failed to upload to Hugging Face: {e}")
    finally:
        os.remove(temp_file.name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user_id", required=True)
    parser.add_argument("--provider_id", required=True)
    parser.add_argument("--raw_key", required=True)
    args = parser.parse_args()
    
    save_user_key(args.user_id, args.provider_id, args.raw_key)
