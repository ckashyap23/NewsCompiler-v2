# News Compiler

Research topics and email summaries to recipients. Uses OpenAI for research and Gmail for delivery.

## Setup

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

Create a `.env` file with:

```
OPENAI_API_KEY=your-openai-key
GMAIL_EMAIL=your@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
```

## Usage

**Streamlit app:**
```bash
streamlit run app.py
```

**CLI:**
```bash
python orchestrator.py "tech trends in India" recipient@example.com
python topic_research.py "topic"
python send_email.py "message" recipient@example.com
```
