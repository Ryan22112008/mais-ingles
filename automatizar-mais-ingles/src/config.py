import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    username: str
    password: str
    base_url: str = "https://maisingles.seduc.mt.gov.br"
    headless: bool = True
    screenshot_dir: str = "artifacts/screenshots"
    llm_model: str = "gpt-4o-mini"
    provider: str = "openai"
    openai_api_key: str = ""
    debug: bool = False
    slow_mo_ms: int = 150
    page_timeout_ms: int = 60000
    human_delay_min: float = 2.5
    human_delay_max: float = 6.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            username=os.getenv("MAIS_INGLES_USERNAME", "").strip(),
            password=os.getenv("MAIS_INGLES_PASSWORD", "").strip(),
            base_url=os.getenv("MAIS_INGLES_BASE_URL", "https://maisingles.seduc.mt.gov.br").strip(),
            headless=os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() in {"1", "true", "yes", "on"},
            screenshot_dir=os.getenv("SCREENSHOT_DIR", "artifacts/screenshots"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip(),
            provider=os.getenv("LLM_PROVIDER", "openai").strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            debug=os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "on"},
            slow_mo_ms=int(os.getenv("PLAYWRIGHT_SLOW_MO_MS", "150") or 150),
            page_timeout_ms=int(os.getenv("PAGE_TIMEOUT_MS", "60000") or 60000),
            human_delay_min=float(os.getenv("HUMAN_DELAY_MIN", "2.5") or 2.5),
            human_delay_max=float(os.getenv("HUMAN_DELAY_MAX", "6.0") or 6.0),
        )
