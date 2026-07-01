import os
import httpx
from backend.app.core.config import settings

def get_google_access_token() -> str:
    """ Obtain Google access token for Vertex AI using google-auth library """
    try:
        import google.auth
        import google.auth.transport.requests
        
        credentials, project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        if credentials.token:
            return credentials.token
        raise Exception("Access token not found in credentials")
    except Exception as e:
        print(f"[LLM Client] google-auth error: {str(e)}. Trying CLI fallback...")
        
    # CLI fallback if google-auth fails or isn't authenticated yet
    try:
        import subprocess
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True
        )
        token = result.stdout.strip()
        if token:
            return token
    except Exception as cli_err:
        print(f"[LLM Client] gcloud CLI fallback failed: {str(cli_err)}")
        
    raise Exception("Could not authenticate with Google Cloud. Please run 'gcloud auth application-default login'.")

def call_gemini(model: str, prompt: str) -> str:
    """
    Calls Gemini API (either Developer API key or Vertex AI project).
    model: e.g. "gemini-2.5-pro" or "gemini-2.5-flash"
    """
    # 1. Developer API Key
    if settings.GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                response_json = resp.json()
                return response_json["candidates"][0]["content"]["parts"][0]["text"]
            else:
                raise Exception(f"Gemini API key returned status {resp.status_code}: {resp.text}")
                
    # 2. Vertex AI API
    elif settings.VERTEX_PROJECT:
        token = get_google_access_token()
        location = settings.VERTEX_LOCATION
        project = settings.VERTEX_PROJECT
        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                response_json = resp.json()
                return response_json["candidates"][0]["content"]["parts"][0]["text"]
            else:
                raise Exception(f"Vertex AI API returned status {resp.status_code}: {resp.text}")
                
    else:
        raise Exception("Neither GEMINI_API_KEY nor VERTEX_PROJECT is configured.")
