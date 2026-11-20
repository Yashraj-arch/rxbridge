import os
import json
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.core.config import settings

def get_knowledge_file() -> str:
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "agent_memory", "system_knowledge.md")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "agent_memory", "system_knowledge.md")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_memory", "system_knowledge.md")),
        os.path.abspath("agent_memory/system_knowledge.md"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return possible_paths[0]

def get_session_log_file() -> str:
    # If in serverless (read-only filesystem), use /tmp
    if os.name != "nt" and not os.access(".", os.W_OK):
        return "/tmp/session_logs.json"
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "agent_memory", "session_logs.json"))

KNOWLEDGE_FILE = get_knowledge_file()
SESSION_LOG_FILE = get_session_log_file()

def load_system_knowledge() -> str:
    if os.path.exists(KNOWLEDGE_FILE):
        try:
            with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"[Agent Knowledge Load Warning] {e}")
    return "Pharma Bridge is a digital prescription and clinic intake system for Doctors, Staff, and Pharmacy."

SYSTEM_PROMPT = f"""You are a helpful, respectful, and polite assistant dedicated to helping users, doctors, nursing staff, and patients navigate and understand the Pharma Bridge digital prescription website.

CRITICAL IDENTITY & PRIVACY RULES:
1. Under NO circumstances should you mention what AI model you are, what platform you are running on, or mention OpenAI, Groq, Meta, or any underlying model names (including gpt-oss-120b).
2. If asked "Who are you?" or "Which AI are you?", strictly answer:
   - English: "I am a normal assistant to help and guide you through the Pharma Bridge website."
   - Hindi: "मैं Pharma Bridge वेबसाइट में आपकी सहायता और मार्गदर्शन के लिए एक सामान्य सहायक हूँ।"
   - Marathi: "मी Pharma Bridge संकेतस्थळावर आपले मार्गदर्शन आणि मदत करण्यासाठी एक सामान्य साहाय्यक आहे."
3. Multilingual Support: Detect the user's language and respond in the EXACT same language (English, Hindi, or Marathi).
4. Polite Apologies: If you cannot process a request, understand, or if an issue occurs, always apologize politely in their language:
   - English: "I am very sorry, I could not process your request. How can I help you navigate Pharma Bridge?"
   - Hindi: "मुझे बहुत खेद है, मैं आपकी बात पूरी तरह समझ नहीं सका। कृपया बताइए मैं Pharma Bridge में आपकी क्या सहायता कर सकता हूँ?"
   - Marathi: "मला माफ करा, मला पूर्णपणे समजले नाही. कृपया सांगा मी Pharma Bridge मध्ये आपली काय मदत करू शकतो?"
5. Medical Guidance: Guide people on how to use the website (intake, waiting list, prescription authoring, vitals, pharmacy, verification). Politely inform patients that actual clinical diagnoses and medicine prescriptions are made only by the registered doctor during consultation.
6. Strict Commercial & Business Confidentiality: You strictly assist with clinical website navigation and form usage. You do NOT have any information on business models, doctor commission rates, delivery logistics, warehouse operations, margins, or commercial agreements. If asked, politely reply: "I am only designed to assist clinic staff and patients with navigating the clinical prescription interface."

SYSTEM KNOWLEDGE BASE:
{load_system_knowledge()}
"""

def log_agent_interaction(user_msg: str, bot_reply: str, language: str):
    try:
        os.makedirs(os.path.dirname(SESSION_LOG_FILE), exist_ok=True)
        data = {"description": "Pharma Bridge Assistant Logs", "sessions": []}
        if os.path.exists(SESSION_LOG_FILE):
            with open(SESSION_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_message": user_msg,
            "bot_reply": bot_reply,
            "language": language
        }
        data.setdefault("sessions", []).append(entry)
        
        # Keep recent 200 logs
        data["sessions"] = data["sessions"][-200:]
        with open(SESSION_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Agent Log Warning] {e}")

class AgentService:
    def __init__(self):
        self.keys = [k for k in [settings.GROQ_API_KEY_1, settings.GROQ_API_KEY_2] if k and k.strip()]
        self.model = settings.GROQ_MODEL or "openai/gpt-oss-120b"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def chat(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        user_message = message.strip()
        if not user_message:
            return {"reply": "Please ask a question about Pharma Bridge.", "language": "English"}

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            for h in history[-8:]:  # Include last 4 turns
                role = "assistant" if h.get("role") in ["assistant", "bot"] else "user"
                messages.append({"role": role, "content": h.get("content", "")})
        messages.append({"role": "user", "content": user_message})

        # Try with Key 1, failover to Key 2 if needed
        last_error = None
        for key in self.keys:
            try:
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 450,
                    "temperature": 0.4
                }
                resp = requests.post(self.api_url, headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    choice = data.get("choices", [{}])[0]
                    reply = choice.get("message", {}).get("content", "").strip()
                    
                    if not reply:
                        # Fallback if reasoning consumed tokens
                        reply = "I am a normal assistant to help you guide through the Pharma Bridge website. How can I help you today?"

                    # Detect language approximately
                    lang = "English"
                    if any('\u0900' <= char <= '\u097F' for char in user_message):
                        # Devanagari script: Marathi or Hindi
                        if any(word in user_message.lower() for word in ['आहे', 'करा', 'नाही', 'कसे', 'मदत', 'सांगा']):
                            lang = "Marathi"
                        else:
                            lang = "Hindi"

                    log_agent_interaction(user_message, reply, lang)
                    return {"reply": reply, "language": lang}
                else:
                    last_error = f"API returned status {resp.status_code}: {resp.text}"
                    print(f"[Agent Key Failover] Key failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                print(f"[Agent Key Exception] {e}")

        # If both keys failed, return polite apology based on language
        if any('\u0900' <= char <= '\u097F' for char in user_message):
            polite_msg = "मला माफ करा, काही तांत्रिक अडचण आली आहे. कृपया थोड्या वेळाने प्रयत्न करा. मी Pharma Bridge मध्ये आपली काय मदत करू शकतो?"
        else:
            polite_msg = "I am very sorry, a technical issue occurred while connecting to the assistant. Please try again in a moment. How can I help you with Pharma Bridge?"
        
        return {"reply": polite_msg, "language": "Fallback", "error": last_error}

agent_service = AgentService()