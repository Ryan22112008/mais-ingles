import re
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from openai import OpenAI


class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key.strip()
        self.model = model or "gpt-4o-mini"
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def available(self) -> bool:
        return self.client is not None

    def _safe_response(self, response) -> str:
        if not response or not getattr(response, "choices", None):
            return ""
        message = response.choices[0].message
        content = getattr(message, "content", "")
        return str(content).strip()

    def ask(self, prompt: str) -> str:
        if not self.available():
            raise RuntimeError("OpenAI API key não configurada.")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Você é um tutor especialista em inglês e educação. Responda de forma objetiva e sempre em português, salvo quando a tarefa exigir a resposta em inglês."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return self._safe_response(response)

    def resolve_multiple_choice(self, question: str, options: List[str]) -> str:
        if not options:
            return ""
        if not self.available():
            return options[0]

        option_text = "\n".join(f"{index + 1}. {option}" for index, option in enumerate(options))
        prompt = (
            "Analise a pergunta e as alternativas abaixo. "
            "Retorne apenas o texto exato da alternativa correta, sem explicação.\n\n"
            f"Pergunta:\n{question}\n\nAlternativas:\n{option_text}"
        )

        answer = self.ask(prompt)
        cleaned = re.sub(r"^\d+[\).\-\s]*", "", answer).strip()
        for option in options:
            if option.lower() == cleaned.lower():
                return option
            if cleaned.lower() in option.lower() or option.lower() in cleaned.lower():
                return option
        return options[0]

    def resolve_fill_blank(self, sentence: str) -> str:
        if not self.available():
            return ""

        prompt = (
            "Dada a frase abaixo, responda apenas com a palavra ou trecho que melhor completa o espaço em branco. "
            "Não inclua explicações.\n\nFrase:\n"
            f"{sentence}"
        )
        answer = self.ask(prompt)
        return re.sub(r"\s+", " ", answer).strip()

    def transcribe_audio_url(self, audio_url: str) -> str:
        if not self.available():
            return ""

        response = requests.get(audio_url, timeout=30)
        response.raise_for_status()

        file_name = "temp_audio.wav"
        temp_path = Path(file_name)
        temp_path.write_bytes(response.content)

        try:
            with temp_path.open("rb") as audio_file:
                result = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                )
            return str(getattr(result, "text", "")).strip()
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
