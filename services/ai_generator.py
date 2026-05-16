import urllib.parse
import requests
import time
import logging

logger = logging.getLogger(__name__)

# Groq API Configuration
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

class AIGenerator:
    def __init__(self, groq_api_key):
        self.groq_api_key = groq_api_key

    def _call_groq(self, prompt, max_tokens=2000, temperature=0.85):
        """Call Groq API with retries on rate-limit (429)."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.groq_api_key}"
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are the world's #1 LinkedIn ghostwriter. Your posts go viral every week."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }

        for attempt in range(1, 5):
            try:
                resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=45)
                if resp.status_code == 429:
                    wait = 3 * attempt
                    logger.warning(f"[groq] 429 rate-limit, retrying in {wait}s (attempt {attempt}/4)")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                result = resp.json()
                return result["choices"][0]["message"]["content"].strip()
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt}/4, retrying...")
                time.sleep(3)
            except Exception as e:
                raise RuntimeError(f"Groq API error: {str(e)}")

        raise RuntimeError("Groq API failed after 4 attempts. Please check your API key and rate limits.")

    def _to_unicode_bold(self, text):
        """Converts standard ASCII text to Unicode Mathematical Bold characters.
        e.g. 'Hello World' -> '𝐇𝐞𝐥𝐥𝐨 𝐖𝐨𝐫𝐥𝐝'
        Safe to call on any string — non-alpha/digit chars pass through unchanged.
        """
        result = ""
        for char in text:
            cp = ord(char)
            if 65 <= cp <= 90:    # A-Z  → 𝐀-𝐙
                result += chr(cp + 119743)
            elif 97 <= cp <= 122: # a-z  → 𝐚-𝐳
                result += chr(cp + 119737)
            elif 48 <= cp <= 57:  # 0-9  → 𝟎-𝟗
                result += chr(cp + 120764)
            else:
                result += char
        return result

    def _apply_unicode_bold(self, text):
        """Finds every **...** span in text and replaces it with Unicode bold."""
        import re
        return re.sub(r'\*\*(.*?)\*\*', lambda m: self._to_unicode_bold(m.group(1)), text)

    def generate_text(self, topic, tone, length):
        if not self.groq_api_key:
            return "⚠️ Error: Groq API Key not configured. Please add GROQ_API_KEY to your .env file."

        length_map = {
            "Short":  "50-100 words. One punchy insight. Hook + 3 bullet points + CTA.",
            "Medium": "180-260 words. 3-5 key points with data. Hook + breakdown + CTA.",
            "Large":  "320-500 words. Deep thought-leadership piece. Full narrative arc + data + CTA.",
        }
        length_desc = length_map.get(length, length_map["Medium"])

        # The AI is told to use standard **bold** Markdown — something it does reliably.
        # The backend then converts those tags to Unicode bold, so the LinkedIn post
        # still looks premium without the AI struggling with complex Unicode codepoints.
        prompt = f"""You are a world-class LinkedIn ghostwriter. Write a viral LinkedIn post.

TOPIC: {topic}
TONE: {tone}
LENGTH: {length_desc}

RULES:
1. Use **bold** for ALL headings and key phrases (standard Markdown bold, nothing else).
2. Start with a punchy heading + 1 relevant emoji.
3. Use bullet points (• or -) for lists.
4. Include 2-3 specific, realistic data points or statistics.
5. Keep total emoji count in the post at 4 or fewer.
6. End with a "Your turn:" question to drive comments.
7. Finish with exactly 10 relevant hashtags on the last line.
8. CRITICAL: Write the COMPLETE post from first word to last hashtag. Never stop early.

OUTPUT ONLY THE POST TEXT. NO INTRO, NO EXPLANATION."""

        try:
            import re
            raw = self._call_groq(prompt, max_tokens=3500, temperature=0.8)

            # 1. Strip markdown-style headings (## Heading) but leave #hashtags untouched
            clean = re.sub(r'(?m)^#{1,6}\s+', '', raw)

            # 2. Convert **bold** → Unicode bold characters
            clean = self._apply_unicode_bold(clean)

            # 3. Remove any stray asterisks the model may have left
            clean = clean.replace('*', '')

            logger.info(f"Generated text ({len(clean)} chars)")
            return clean.strip()
        except Exception as e:
            logger.error(f"generate_text failed: {e}")
            return f"⚠️ Could not generate content. Please try again in a moment.\n\nDetails: {str(e)}"

    def _generate_smart_image_prompt(self, topic, style):
        """Use Groq to generate or refine a professional, knowledge-focused image prompt for Pollinations.AI."""
        
        # Determine if the topic is already a detailed prompt
        is_detailed = len(topic) > 80
        
        task_desc = "Refine and enhance this detailed image description" if is_detailed else "Create a highly professional LinkedIn banner image prompt for the topic"
        
        user_prompt = f"""{task_desc}: {topic}. 
Style: {style}. 

CRITICAL THEME: The image must convey "Information", "Knowledge", and "Authority". 
Visual Ideas: 
- Minimalist data visualizations or elegant infographics.
- Abstract concepts representing growth, intelligence, or connectivity.
- Modern, clean architectural spaces or high-end tech workspaces.
- Soft, professional color palettes (blues, teals, dark grays).
- NO generic or low-quality stock photos.

Instructions: 
- Focus on high-end corporate aesthetics, sharp focus, and cinematic professional lighting. 
- The image should feel like a premium editorial illustration or a high-quality tech header.
- If the user provided specific text in quotes, ENSURE the prompt includes that text as a central element.
- If no text was provided, include a very subtle, clean text overlay saying '{topic[:20]}' if it fits the design.

OUTPUT ONLY THE PROMPT. NO INTRODUCTIONS."""

        try:
            prompt = self._call_groq(user_prompt, max_tokens=100, temperature=0.7)
            # Add quality boosters and negative constraints directly into the prompt string
            boosted_prompt = f"{prompt.strip()}, high-resolution, 8k, professional LinkedIn banner style, masterpiece, sharp details, cinematic lighting, ultra-detailed, --no low quality, blurry, distorted, messy, lowres"
            return boosted_prompt
        except Exception as e:
            logger.error(f"Smart image prompt failed: {e}")
            return f"Professional high-end information and knowledge visual about {topic}, clean minimalist design, 8k, masterpiece"

    def generate_image_url(self, topic, style):
        """Generate a high-quality LinkedIn banner image via Pollinations.AI, download it, and return local URL."""
        import urllib.parse
        import random
        import os
        import uuid
        import requests
        
        smart_prompt = self._generate_smart_image_prompt(topic, style)
        # Clean the prompt but allow more characters that might be useful for boosters
        clean_prompt = "".join(c for c in smart_prompt if c.isalnum() or c in " ,.-_")
        encoded = urllib.parse.quote(clean_prompt)
        seed = random.randint(1, 1000000)
        
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1350&nologo=true&seed={seed}"
        
        try:
            # Download the image to the backend as a backup/log
            response = requests.get(pollinations_url, timeout=30)
            if response.ok:
                filename = f"{uuid.uuid4().hex}.jpg"
                save_dir = os.path.join("static", "generated")
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)
            
            # ALWAYS return the public URL for LinkedIn to fetch
            return pollinations_url
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            return pollinations_url

    def parse_nlp(self, text):
        """Parse natural language like 'post about AI on Friday at 9am' into JSON."""
        if not self.groq_api_key:
            return None

        import time
        prompt = f"""You are a smart calendar assistant. Parse the following request and output ONLY a JSON object.
Request: "{text}"

JSON Structure:
{{
  "topic": "Cleaned up topic of the post",
  "scheduled_time": "ISO 8601 datetime string"
}}

Rules:
1. Current time is: {time.strftime('%Y-%m-%d %H:%M:%S')}
2. If day of week is mentioned (e.g. 'Friday'), use the next upcoming day of that name.
3. If no time is mentioned, default to 09:00:00.
4. Topic should be concise and professional.
5. OUTPUT ONLY THE JSON. NO OTHER TEXT."""

        try:
            result = self._call_groq(prompt, max_tokens=200, temperature=0.1)
            import json
            import re
            # Extract JSON from potential wrapper
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(result)
        except Exception as e:
            logger.error(f"parse_nlp failed: {e}")
            return None

    def generate_trends(self):
        """Generate 4 daily AI/ML/Tech trend headlines via Groq. Called once per day."""
        from datetime import date
        today = date.today().strftime("%B %d, %Y")

        prompt = f"""Today is {today}. You are a tech news curator. Generate exactly 4 current, specific AI/ML/Tech trend news items.

Each item must be:
- Specific to a real-sounding company, model, or research
- Based on plausible 2025-2026 AI market trends  
- Fresh and relevant to {today}

Return ONLY a valid JSON array with exactly 4 objects, no extra text:
[
  {{"emoji": "🤖", "title": "Short Title max 38 chars", "description": "Brief insight max 55 chars", "tag": "Category"}},
  {{"emoji": "⚡", "title": "Another Title", "description": "Another insight", "tag": "Category"}},
  {{"emoji": "🧠", "title": "Third Title", "description": "Third insight", "tag": "Category"}},
  {{"emoji": "📊", "title": "Fourth Title", "description": "Fourth insight", "tag": "Category"}}
]

Categories: LLM, Google, OpenAI, Meta, Market, Research, Hardware, Open Source, Startup, Enterprise
OUTPUT ONLY THE JSON ARRAY."""

        try:
            result = self._call_groq(prompt, max_tokens=400, temperature=0.75)
            import json, re
            match = re.search(r'\[.*?\]', result, re.DOTALL)
            if match:
                trends = json.loads(match.group())
                if isinstance(trends, list) and len(trends) > 0:
                    return trends[:4]
        except Exception as e:
            logger.error(f"generate_trends failed: {e}")
        return self._default_trends()

    def _default_trends(self):
        """Fallback trends shown when Groq is unavailable."""
        return [
            {"emoji": "🤖", "title": "Agentic AI Revolution", "description": "80% of execs: critical by 2027", "tag": "Market"},
            {"emoji": "⚡", "title": "Google Gemma 4 for Mobile", "description": "Open-source, runs fully on-device", "tag": "Google"},
            {"emoji": "🧠", "title": "GPT-5 \"Orion\" Released", "description": "10x cheaper inference, smarter reasoning", "tag": "OpenAI"},
            {"emoji": "🔬", "title": "Quantum ML Breakthrough", "description": "100x training speed gains reported", "tag": "Research"},
        ]

