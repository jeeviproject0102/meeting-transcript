import asyncio
import spacy
import os
import tempfile
from collections import Counter
import re

# Load NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

# Lazy Whisper model
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
        except ImportError:
            pass
        # Upgrade to 'base' for better quality
        _whisper_model = whisper.load_model("base", device="cpu")
    return _whisper_model

def clean_transcript(text: str) -> str:
    # 1. Remove obvious repetitions like "you you you" or "the the"
    # This regex looks for 3 or more repeated words
    text = re.sub(r'\b(\w+)( \1){2,}\b', r'\1', text, flags=re.IGNORECASE)
    # 2. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def process_meeting_file(content: bytes, filename: str, extension: str):
    
    # =========================
    # 1. TRANSCRIPTION
    # =========================
    
    transcript = ""

    if extension == "txt":
        try:
            transcript = content.decode("utf-8")
        except:
            transcript = content.decode("latin-1", errors="ignore")

    elif extension in ["mp3", "mp4"]:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            loop = asyncio.get_event_loop()
            
            def transcribe_file():
                model = get_whisper_model()
                # Use fp16=False to ensure CPU compatibility and better stability
                return model.transcribe(temp_path, fp16=False)

            result = await loop.run_in_executor(None, transcribe_file)
            raw_transcript = result.get("text", "").strip()
            transcript = clean_transcript(raw_transcript)

            if os.path.exists(temp_path):
                os.unlink(temp_path)

        except Exception as e:
            transcript = f"Transcription unavailable for {filename}. (Error: {str(e)})"

    # Fallback if empty
    if not transcript or len(transcript.strip()) < 10:
        transcript = f"The content of {filename} was too short or could not be processed into text."

    # =========================
    # 2. NLP PROCESSING
    # =========================

    summary = ""
    key_points = []
    action_items = []

    if nlp and len(transcript) > 20:
        doc = nlp(transcript)
        # Filter sentences to ensure they are meaningful (longer than 10 chars and not just noise)
        sentences = [
            sent.text.strip() 
            for sent in doc.sents 
            if len(sent.text.strip()) > 15 and not re.match(r'^[\W\d]+$', sent.text.strip())
        ]

        if len(sentences) >= 1:
            # 🔹 SUMMARY: Use high-ranking sentences based on length and structure
            # Instead of just the first 3, we take the first 3 meaningful ones
            summary = " ".join(sentences[:3])
            if len(sentences) > 3:
                summary += "..."
        else:
            summary = transcript[:200]
            if len(transcript) > 200:
                summary += "..."

        # 🔹 KEY POINTS: Extract sentences containing important nouns, filtering out noise
        nouns = [
            token.text.lower()
            for token in doc
            if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop and len(token.text) > 2
        ]
        common_nouns = [word for word, _ in Counter(nouns).most_common(8)]

        seen = set()
        for sent in sentences:
            # Filter out sentences that look like transcription errors or are too short
            if len(sent) < 30 or any(noise in sent.lower() for noise in ["thank you", "you know", "i mean"]):
                continue
                
            if any(noun in sent.lower() for noun in common_nouns):
                if sent not in seen and len(key_points) < 5:
                    key_points.append(sent)
                    seen.add(sent)

            # 🔹 ACTION ITEMS
            action_keywords = [
                "implement", "create", "build", "setup",
                "update", "send", "fix", "research",
                "develop", "prepare", "organize",
                "start", "finish", "need to", "must", "should"
            ]

            for sent in sentences:
                lower = sent.lower()
                if (
                    any(k in lower for k in action_keywords)
                    or re.search(r"\b(we|i|you|they) (should|must|need to|will)\b", lower)
                    or re.search(r"\b(let's|lets)\b", lower)
                ):
                    if len(action_items) < 5:
                        action_items.append(sent)
        else:
            summary = transcript[:200]
            key_points = ["Detailed points not detected."]
            action_items = ["No clear actions found."]
    else:
        summary = transcript[:200]
        key_points = ["Manual review recommended."]
        action_items = ["Manual review recommended."]

    # =========================
    # 3. CLEAN OUTPUT
    # = : 3. CLEAN OUTPUT
    # =========================

    if not key_points:
        key_points = ["No key points detected"]

    if not action_items:
        action_items = ["No action items detected"]

    return {
        "filename": filename,
        "transcript": transcript,
        "summary": summary,
        "key_points": key_points,
        "action_items": action_items
    }