"""
Roteador local de intencoes do R.O.N.Y.

Mantem uma memoria curta para comandos incompletos, como "fecha" seguido de
"a camera", e evita que frases ambiguas virem acoes perigosas.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re
import time
import unicodedata


@dataclass(slots=True)
class Intent:
    action: str | None = None
    target: str | None = None
    confidence: float = 0.0
    needs_clarification: bool = False
    question: str | None = None
    source: str = "router"


@dataclass(slots=True)
class PendingIntent:
    action: str
    created_at: float


class IntentRouter:
    def __init__(self, pending_ttl: float = 12.0, context_ttl: float = 45.0) -> None:
        self.pending_ttl = pending_ttl
        self.context_ttl = context_ttl
        self._pending: PendingIntent | None = None
        self._context: deque[tuple[str, float]] = deque(maxlen=6)

    def route(self, text: str, now: float | None = None) -> Intent:
        now = now or time.time()
        normalized = normalize_text(text)
        tokens = set(normalized.split())

        self._expire(now)

        target = self._detect_target(normalized, tokens)
        action = self._detect_action(normalized, tokens)

        if target:
            self.remember_target(target, now)

        if self._pending:
            if target:
                action = self._pending.action
                self._pending = None
                return Intent(action=action, target=target, confidence=0.9, source="pending_context")
            if self._is_cancel(normalized, tokens):
                self._pending = None
                return Intent(action="cancelar", confidence=0.9, source="pending_context")

        if action in {"fechar", "desligar", "parar"}:
            if target:
                return Intent(action=action, target=target, confidence=0.95, source="direct")

            recent_target = self._last_target(now)
            if recent_target and recent_target != "rony":
                return Intent(action=action, target=recent_target, confidence=0.74, source="recent_context")

            self._pending = PendingIntent(action=action, created_at=now)
            return Intent(
                action=action,
                confidence=0.45,
                needs_clarification=True,
                question="O que você quer que eu feche?",
                source="missing_target",
            )

        if self._is_shutdown(normalized):
            return Intent(action="encerrar", target="rony", confidence=0.98, source="direct")

        return Intent(action=action, target=target, confidence=0.3 if action or target else 0.0, source="pass")

    def remember_target(self, target: str, now: float | None = None) -> None:
        now = now or time.time()
        self._context.append((target, now))

    def _expire(self, now: float) -> None:
        if self._pending and now - self._pending.created_at > self.pending_ttl:
            self._pending = None
        while self._context and now - self._context[0][1] > self.context_ttl:
            self._context.popleft()

    def _last_target(self, now: float) -> str | None:
        self._expire(now)
        for target, _ in reversed(self._context):
            if target:
                return target
        return None

    def _detect_action(self, normalized: str, tokens: set[str]) -> str | None:
        if tokens & {"fecha", "fechar", "feche", "close"}:
            return "fechar"
        if tokens & {"desliga", "desligar"} or "turn off" in normalized:
            return "desligar"
        if tokens & {"para", "parar", "pare", "stop"}:
            return "parar"
        if tokens & {"abre", "abrir", "abra", "open"}:
            return "abrir"
        return None

    def _detect_target(self, normalized: str, tokens: set[str]) -> str | None:
        if tokens & {"camera", "webcam", "cam"}:
            return "camera"
        if tokens & {"rony", "assistente"}:
            return "rony"
        if tokens & {"som", "audio", "volume"}:
            return "audio"
        if tokens & {"chrome"}:
            return "chrome"
        if tokens & {"edge"}:
            return "edge"
        if tokens & {"firefox"}:
            return "firefox"
        if tokens & {"spotify", "musica"}:
            return "spotify"
        if tokens & {"discord"}:
            return "discord"
        if tokens & {"vscode", "code"} or "visual studio code" in normalized:
            return "vscode"
        if tokens & {"teams"}:
            return "teams"
        if tokens & {"zoom"}:
            return "zoom"
        if tokens & {"slack"}:
            return "slack"
        return None

    def _is_cancel(self, normalized: str, tokens: set[str]) -> bool:
        return bool(tokens & {"cancela", "cancelar", "deixa", "esquece", "nao"}) or normalized in {
            "deixa pra la",
            "deixa para la",
        }

    def _is_shutdown(self, normalized: str) -> bool:
        despedidas_exatas = {
            "tchau", "ate logo", "ate mais", "au revoir", "goodbye", "bye rony",
            "adios", "ciao", "auf wiedersehen", "boa noite rony", "boa tarde rony",
        }
        comandos_com_alvo = {
            "encerrar rony", "encerra rony", "encerre rony", "pode encerrar rony",
            "fechar rony", "fecha rony", "feche rony", "pode fechar rony",
            "desligar rony", "desliga rony", "pode desligar rony",
            "sair rony", "rony pode sair", "pode sair rony",
            "stop rony", "close rony", "exit rony", "shut down rony",
            "para rony", "para o rony", "cierra rony", "sal rony",
        }
        return normalized in despedidas_exatas or any(cmd in normalized for cmd in comandos_com_alvo)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()
