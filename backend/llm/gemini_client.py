import os
import json
from google import genai
from google.genai import types

def ask_gemini(system_prompt: str, user_prompt: str, context_data: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key in [None, "", "your_gemini_api_key_here", "dummy_key", "YOUR_API_KEY"]:
        return _fallback_response(missing_key=True)

    try:
        client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1alpha"}
        )
        model_name = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        
        full_prompt = f"""
DATA CONTEXT:
{json.dumps(context_data, indent=2)}

USER QUESTION:
{user_prompt}
"""
        
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json"
            )
        )
        text = response.text
        
        # Clean markdown formatting if present just in case
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        text = text.strip()
        
        try:
            parsed_json = json.loads(text)
            return parsed_json
        except json.JSONDecodeError:
            print("Failed to parse Gemini output:", text)
            return _fallback_response()
            
    except Exception as e:
        import traceback
        print("=== Gemini API Error ===")
        print(f"Model: {os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')}")
        print(f"API Key set: {bool(api_key)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        traceback.print_exc()
        print("=======================")
        return _fallback_response()

def _fallback_response(missing_key=False):
    msg = "Gemini API key is not configured. Showing deterministic retail insights instead." if missing_key else "AI service is currently unavailable or returned malformed data. Here are the deterministic insights from your retail data."
    limitations = "API key missing" if missing_key else "AI response formatting failed or API error"
    return {
      "answer": msg,
      "evidence": [],
      "recommendations": [],
      "confidence": "low",
      "data_limitations": [limitations]
    }
