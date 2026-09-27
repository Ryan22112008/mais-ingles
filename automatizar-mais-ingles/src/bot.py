import random
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from playwright.sync_api import Page, sync_playwright

try:
    from playwright_stealth import Stealth
except ImportError:
    Stealth = None

try:
    if Stealth is not None:
        pass
    else:
        from playwright_stealth import stealth_sync  # type: ignore
except ImportError:
    stealth_sync = None

from .config import Settings
from .llm import LLMClient
from .utils import configure_logger, ensure_dir, human_delay, normalize_text


class MaisInglesBot:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = configure_logger("mais_ingles_bot")
        self.llm = LLMClient(settings.openai_api_key, settings.llm_model) if settings.openai_api_key else None
        self.browser = None
        self.page: Optional[Page] = None

    def save_screenshot(self, name: str) -> None:
        if not self.page:
            return
        directory = ensure_dir(self.settings.screenshot_dir)
        screenshot_path = directory / f"{name}_{random.randint(1000, 9999)}.png"
        self.page.screenshot(path=str(screenshot_path), full_page=True)
        self.logger.info("Screenshot salvo em %s", screenshot_path)

    def _find_first_visible(self, selectors: Iterable[str]):
        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if locator.count() > 0:
                    return locator
            except Exception:
                continue
        return None

    def _build_absolute_url(self, url: str) -> str:
        if not url:
            return ""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return url if url.startswith("/") else f"{self.settings.base_url.rstrip('/')}/{url.lstrip('/')}"

    def _extract_question_text(self) -> str:
        if not self.page:
            return ""

        candidate_selectors = [
            "h1, h2, h3, p, .question, .enunciado, .statement, .exercise, .content, .prompt, .task",
            "div[class*=question], div[id*=question], div[class*=exercise], div[class*=statement]",
            "label, .text",
        ]

        texts: List[str] = []
        for selector in candidate_selectors:
            for element in self.page.locator(selector).all():
                text = normalize_text(element.inner_text())
                if text and len(text) > 20 and len(text) < 1000:
                    texts.append(text)

        if not texts:
            return normalize_text(self.page.locator("body").inner_text())

        texts.sort(key=len, reverse=True)
        return texts[0]

    def _extract_option_candidates(self) -> List[Tuple[str, str]]:
        if not self.page:
            return []

        option_selectors = [
            "label",
            "button",
            "[role='radio']",
            "[role='option']",
            ".option",
            ".choice",
            ".alternative",
            "li",
        ]

        result: List[Tuple[str, str]] = []
        seen = set()
        for selector in option_selectors:
            for element in self.page.locator(selector).all():
                text = normalize_text(element.inner_text())
                if not text or len(text) > 200:
                    continue
                lower = text.lower()
                if any(token in lower for token in ["próximo", "avançar", "continuar", "voltar", "enviar", "salvar", "confirmar"]):
                    continue
                if text in seen:
                    continue
                seen.add(text)
                result.append((element.get_attribute("data-testid") or selector, text))

        return result

    def _collect_links(self) -> List[str]:
        if not self.page:
            return []

        hrefs = set()
        for element in self.page.locator("a[href]").all():
            href = element.get_attribute("href")
            if not href:
                continue
            absolute = self._build_absolute_url(href)
            lowered = absolute.lower()
            if any(keyword in lowered for keyword in ["curso", "modulo", "módulo", "aula", "lesson", "unidade", "classe", "atividade", "exercise", "learning", "course", "class", "unit"]):
                hrefs.add(absolute)

        text_map = self.page.locator("a[href]")
        for idx in range(text_map.count()):
            element = text_map.nth(idx)
            href = element.get_attribute("href")
            if not href:
                continue
            text = normalize_text(element.inner_text())
            lowered_text = text.lower()
            if any(keyword in lowered_text for keyword in ["curso", "módulo", "aula", "unidade", "lesson", "atividade", "module", "class", "course"]):
                hrefs.add(self._build_absolute_url(href))

        return sorted(hrefs)

    def _fill_form_field(self, selector_candidates: Iterable[str], value: str) -> bool:
        locator = self._find_first_visible(selector_candidates)
        if locator is None:
            return False
        try:
            locator.scroll_into_view_if_needed()
            locator.click()
            locator.fill("")
            self.page.keyboard.type(value, delay=random.uniform(30, 90))
            return True
        except Exception:
            try:
                locator.fill(value)
                return True
            except Exception:
                return False

    def _click_best_match(self, selectors: Iterable[str], text_candidates: Iterable[str] = ()) -> bool:
        candidates = list(selectors)
        for text in text_candidates:
            candidates.append(f"button:has-text('{text}')")
            candidates.append(f"a:has-text('{text}')")
            candidates.append(f"input[value*='{text}']")

        for selector in candidates:
            try:
                locator = self.page.locator(selector).first
                if locator.count() > 0:
                    locator.scroll_into_view_if_needed()
                    locator.click(force=True)
                    return True
            except Exception:
                continue
        return False

    def _is_restricted_access_page(self) -> bool:
        if not self.page:
            return False
        page_text = normalize_text(self.page.locator("body").inner_text())
        lower = page_text.lower()
        indicators = [
            "página restrita",
            "acesso ao domínio",
            "políticas de segurança da seplag",
            "restrito de acordo com",
            "não há autorização",
            "acesso negado",
        ]
        return any(indicator in lower for indicator in indicators)

    def _open_platform_entry(self) -> bool:
         if self._is_restricted_access_page():
            self.logger.error("Página de acesso restrito detectada. Verifique rede/VPN, domínio autorizado e credenciais do ambiente.")
            return False

            page_text = normalize_text(self.page.locator("body").inner_text())
            if "mais ingl" in page_text.lower():
                click_candidates = [
                "a:has-text('Mais Inglês')",
                "button:has-text('Mais Inglês')",
                "div:has-text('Mais Inglês')",
                "span:has-text('Mais Inglês')",
                "text=Mais Inglês",
                "a:has-text('mais ingles')",
                "button:has-text('mais ingles')",
                "[title*='Mais Inglês' i]",
                "[aria-label*='Mais Inglês' i]",
            ]
            for selector in click_candidates:
                try:
                    locator = self.page.locator(selector).first
                    if locator.count() > 0:
                        locator.scroll_into_view_if_needed()
                        locator.click(force=True)
                        self.logger.info("Clicou na entrada da plataforma Mais Inglês.")
                        human_delay(self.settings.human_delay_min, self.settings.human_delay_max)
                        return True
                except Exception:
                    continue
            return False

    def _login_google_sso(self) -> bool:
        self.logger.info("Detectado login via Google SSO; tratando fluxo de duas etapas.")

        email_selectors = ["input[type='email']", "#identifierId"]
        if not self._fill_form_field(email_selectors, self.settings.username):
            self.logger.warning("Não encontrou o campo de e-mail do Google.")
            return False

        if not self._click_best_match(["#identifierNext button", "#identifierNext"], ["Próxima", "Next", "Avançar"]):
            self.logger.warning("Não encontrou o botão 'Próxima' do e-mail.")
            return False

        human_delay(self.settings.human_delay_min, self.settings.human_delay_max)

        try:
            self.page.wait_for_selector("input[type='password']", timeout=self.settings.page_timeout_ms)
        except Exception:
            self.logger.warning("Campo de senha do Google não apareceu a tempo.")
            return False

        password_selectors = ["input[type='password']", "input[name='Passwd']"]
        if not self._fill_form_field(password_selectors, self.settings.password):
            self.logger.warning("Não encontrou o campo de senha do Google.")
            return False

        return self._click_best_match(["#passwordNext button", "#passwordNext"], ["Próxima", "Next", "Avançar"])

    def login(self) -> None:
        self.logger.info("Abrindo a página de login")

        if not self.settings.username or not self.settings.password:
            raise ValueError("Credenciais ausentes. Configure MAIS_INGLES_USERNAME e MAIS_INGLES_PASSWORD no .env.")

        self.page.goto(self.settings.base_url, wait_until="domcontentloaded")
        try:
            self.page.wait_for_load_state("networkidle", timeout=self.settings.page_timeout_ms)
        except Exception:
            pass
        human_delay(self.settings.human_delay_min, self.settings.human_delay_max)

        current_url = self.page.url.lower()
        if "accounts.google.com" not in current_url:
            try:
                self.page.wait_for_url("**accounts.google.com**", timeout=8000)
                current_url = self.page.url.lower()
            except Exception:
                pass

        if "accounts.google.com" in current_url:
            if not self._login_google_sso():
                self.save_screenshot("google_login_failed")
                raise PermissionError("Não foi possível concluir o login do Google. Confira usuário/senha no .env.")
        else:
            self.logger.info("Login não parece ser Google SSO; tentando fluxo genérico de formulário único.")

        human_delay(self.settings.human_delay_min, self.settings.human_delay_max)
        try:
            self.page.wait_for_load_state("networkidle", timeout=self.settings.page_timeout_ms)
        except Exception:
            self.logger.warning("Timeout de rede ao tentar logar; segue com o fluxo atual.")

        if self._is_restricted_access_page():
            self.logger.error("Acesso bloqueado pela política de segurança do domínio.")
            self.save_screenshot("restricted_access")
            raise PermissionError("Acesso restrito: domínio bloqueado pela política de segurança.")

        self._open_platform_entry()
        self.logger.info("Página após login: %s", self.page.url)

    def _solve_multiple_choice(self) -> bool:
        question = self._extract_question_text()
        options = self._extract_option_candidates()
        if not options:
            return False

        option_texts = [value for _, value in options]
        if self.llm and self.llm.available():
            selected = self.llm.resolve_multiple_choice(question, option_texts)
        else:
            selected = option_texts[0]

        for locator, text in options:
            if text.lower() == selected.lower() or selected.lower() in text.lower() or text.lower() in selected.lower():
                self.logger.info("Respondendo questão de múltipla escolha: %s", text)
                try:
                    element = self.page.locator(f"label:has-text('{text}')")
                    if element.count() > 0:
                        element.first.click(force=True)
                    else:
                        self.page.locator("button", has_text=text).first.click(force=True)
                    return True
                except Exception:
                    self.logger.exception("Erro ao responder múltipla escolha.")
                    self.save_screenshot("multiple_choice_error")
                    return False
        return False

    def _solve_fill_blank(self) -> bool:
        question = self._extract_question_text()
        if not question:
            return False

        input_selectors = [
            "input:not([type='hidden']):not([type='checkbox']):not([type='radio'])",
            "textarea",
            "[contenteditable='true']",
        ]
        locator = self._find_first_visible(input_selectors)
        if locator is None:
            return False

        if self.llm and self.llm.available():
            guess = self.llm.resolve_fill_blank(question)
        else:
            guess = "example"

        if not guess:
            guess = "example"

        try:
            locator.click()
            self.page.keyboard.type(guess, delay=random.uniform(35, 95))
            self.logger.info("Preenchendo lacuna com: %s", guess)
            return True
        except Exception:
            self.logger.exception("Erro ao preencher lacuna")
            self.save_screenshot("fill_blank_error")
            return False

    def _extract_audio_url(self) -> str:
        for selector in ["audio source", "audio[src]", "source[src]", "video source", "video[src]"]:
            for element in self.page.locator(selector).all():
                url = element.get_attribute("src")
                if url:
                    return self._build_absolute_url(url)
        return ""

    def _solve_listening_activity(self) -> bool:
        audio_url = self._extract_audio_url()
        if not audio_url:
            return False

        self.logger.info("Áudio detectado: %s", audio_url)
        if self.llm and self.llm.available():
            transcript = self.llm.transcribe_audio_url(audio_url)
        else:
            transcript = "Áudio identificado, mas sem transcrição disponível."

        question = self._extract_question_text()
        if not question and not transcript:
            return False

        self.logger.info("Transcrição do áudio: %s", transcript[:500])
        if not self.llm or not self.llm.available():
            return False

        result = self.llm.ask(
            "Você está resolvendo uma atividade de listening. "
            "Usando a pergunta e a transcrição do áudio, responda APENAS com a alternativa correta ou frase mais adequada.\n\n"
            f"Pergunta:\n{question}\n\nTranscrição:\n{transcript}"
        )

        if not result:
            return False

        for option in self._extract_option_candidates():
            text = option[1]
            if result.lower() in text.lower() or text.lower() in result.lower():
                self.page.locator("button", has_text=text).first.click(force=True)
                return True

        return False

    def _handle_current_activity(self) -> bool:
        body_text = normalize_text(self.page.locator("body").inner_text())
        lower = body_text.lower()

        if any(token in lower for token in ["lacuna", "complete", "fill", "blank", "preencha", "complete the sentence"]):
            return self._solve_fill_blank()

        if self.page.locator("input[type='radio'], [role='radio'], label, button").count() > 0:
            return self._solve_multiple_choice()

        if any(token in lower for token in ["listening", "audio", "listen", "ouça", "escute"]) or self.page.locator("audio, source, video").count() > 0:
            return self._solve_listening_activity()

        if self.page.locator("input:not([type='hidden']), textarea").count() > 0:
            return self._solve_fill_blank()

        return False

    def process_lessons(self) -> None:
        self.logger.info("Coletando links de aulas e módulos disponíveis.")
        candidates = self._collect_links()
        if not candidates:
            self.logger.warning("Nenhum módulo ou lição encontrado na página inicial. Verifique se a URL do ambiente está correta.")
            self.save_screenshot("no_lessons_detected")
            return

        for url in candidates[:25]:
            self.logger.info("Acessando lição ou módulo: %s", url)
            try:
                self.page.goto(url, wait_until="domcontentloaded")
                human_delay(self.settings.human_delay_min, self.settings.human_delay_max)

                for _ in range(20):
                    if self._handle_current_activity():
                        human_delay(self.settings.human_delay_min, self.settings.human_delay_max)
                        continue

                    next_selectors = [
                        "button:has-text('Próximo')",
                        "button:has-text('Avançar')",
                        "button:has-text('Continuar')",
                        "button:has-text('Enviar')",
                        "button:has-text('Concluir')",
                        "button:has-text('Next')",
                        "button:has-text('Continue')",
                        "a:has-text('Próximo')",
                        "a:has-text('Avançar')",
                        "a:has-text('Continuar')",
                    ]
                    clicked = self._click_best_match(next_selectors, ["Próximo", "Avançar", "Continuar", "Next", "Continue", "Enviar", "Concluir"])
                    if not clicked:
                        self.logger.info("Nenhum botão de avanço identificado; encerrando looping da lição atual.")
                        break
                    human_delay(self.settings.human_delay_min, self.settings.human_delay_max)

                self.logger.info("Lição finalizada com sucesso: %s", url)
            except Exception:
                self.logger.exception("Erro ao processar a lição: %s", url)
                self.save_screenshot(f"lesson_error_{abs(hash(url))}")

    def run(self) -> None:
        ensure_dir(self.settings.screenshot_dir)
        with sync_playwright() as playwright:
            self.browser = playwright.chromium.launch(
                headless=self.settings.headless,
                slow_mo=self.settings.slow_mo_ms,
                args=["--disable-blink-features=AutomationControlled"],
            )
            self.page = self.browser.new_page(viewport={"width": 1440, "height": 1200}, locale="pt-BR")
            if Stealth is not None:
                Stealth().apply_stealth_sync(self.page)
            elif stealth_sync is not None:
                stealth_sync(self.page)
            self.page.set_default_timeout(self.settings.page_timeout_ms)

            try:
                self.login()
                self._open_platform_entry()
                self.process_lessons()
            except Exception:
                self.logger.exception("Erro fatal na execução do bot.")
                self.save_screenshot("fatal_error")
                raise
            finally:
                self.browser.close()
