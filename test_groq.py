# test_groq.py
import os
import sys
from dotenv import load_dotenv
from services.ai_generator import AIGenerator

def test_groq_model() -> int:
    print("Loading environment variables...")
    load_dotenv()

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in environment variables.")
        print("Please add GROQ_API_KEY to your .env file.")
        return 1

    print(f"Found GROQ_API_KEY (starts with: {api_key[:8]}...)")
    generator = AIGenerator(api_key)

    topic  = "The benefits of using Groq for AI inference"
    tone   = "Professional"
    length = "Short"

    print(f"\nSending test prompt to llama-3.3-70b-versatile via Groq...")
    print(f"Topic={topic!r}  Tone={tone!r}  Length={length!r}\n")

    result = generator.generate_text(topic, tone, length)
    with open("test_output.txt", "w", encoding="utf-8") as f:
        f.write(result)
    print("====== GENERATED CONTENT SAVED TO test_output.txt ======\n")
    # print(result) # Commented out to avoid console encoding issues
    print("\n================================")

    if "⚠️" in result or "Error" in result:
        print("\n❌ Groq Model Test FAILED — see output above.")
        return 1

    print("\n✅ Groq Model Test PASSED!")
    return 0

if __name__ == "__main__":
    sys.exit(test_groq_model())
