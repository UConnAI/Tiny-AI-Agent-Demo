import os
from pathlib import Path

import requests
from dotenv import load_dotenv
# For PDF generating
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


APP_DIR = Path(__file__).resolve().parent
SKILL_PATH = APP_DIR / "skills" / "pdf-generator" / "SKILL.md"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"


def load_skill():
    """
    Return the description for each skill, which remove metadata in --- here ---
    """
    text = SKILL_PATH.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text.strip()


def ask_ai(api_key, model, messages):
    """
    This is the original calling function
    """
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def get_code(text):
    text = text.replace("‑", "-")

    if "```python" in text:
        return text.split("```python", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return text.strip()


def run_code(code, filename):
    output_path = APP_DIR / filename
    # Limit what it can excute
    safe_builtins = {
        "str": str,
        "int": int,
        "float": float,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "min": min,
        "max": max,
        "sum": sum,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "zip": zip,
    }
    # what can be used
    scope = {
        "__builtins__": safe_builtins,
        "output_path": output_path,
        "Path": Path,
        "colors": colors,
        "letter": letter,
        "inch": inch,
        "SimpleDocTemplate": SimpleDocTemplate,
        "Paragraph": Paragraph,
        "Spacer": Spacer,
        "Table": Table,
        "TableStyle": TableStyle,
        "getSampleStyleSheet": getSampleStyleSheet,
    }
    exec(code, scope, {})
    return output_path


def main():
    load_dotenv(APP_DIR / ".env")
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("API_KEY")
    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    if not api_key:
        print("Missing OPENROUTER_API_KEY in mini-pdf-agent/.env")
        return

    messages = [{"role": "system", "content": load_skill()}]

    print("Mini PDF Agent")
    print("The model writes Python code for a PDF and this app executes it.")
    print("Press enter on the filename to use output.pdf.")
    print("Use /exit to quit.\n")

    while True:
        user_input = input("Instruction: ").strip()
        if not user_input:
            continue
        if user_input == "/exit":
            break

        filename = input("PDF file [output.pdf]: ").strip() or "output.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        # The topic of the PDF
        messages.append({"role": "user", "content": user_input})
        try:
            reply = ask_ai(api_key, model, messages)
            code = get_code(reply)
            saved = run_code(code, filename)
        # for debug
        except requests.RequestException as exc:
            messages.pop()
            print(f"Request failed: {exc}\n")
            continue
        except Exception as exc:
            messages.pop()
            print(f"Code execution failed: {exc}\n")
            print(get_code(reply))
            continue

        print(f"Saved PDF: {saved}")
        print("\nGenerated code:\n")
        # what it excute
        print(code)
        print()
        # include privious messages as memory
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
