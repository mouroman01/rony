import html
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Optional

import requests
from dotenv import load_dotenv


load_dotenv()


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)


class _DuckResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_link = False
        self._in_snippet = False
        self._current_href = ""
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attrs_d = dict(attrs)
        klass = attrs_d.get("class", "") or ""
        if tag == "a" and "result__a" in klass:
            self._in_link = True
            self._current_href = attrs_d.get("href", "") or ""
            self._title_parts = []
        if tag in {"a", "div"} and ("result__snippet" in klass or "result__body" in klass):
            self._in_snippet = True
            self._snippet_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._title_parts.append(data)
        if self._in_snippet:
            self._snippet_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_link:
            title = _limpar_texto(" ".join(self._title_parts))
            url = _limpar_duck_url(self._current_href)
            if title and url:
                self.results.append({"title": title, "url": url, "snippet": "", "provider": "DuckDuckGo"})
            self._in_link = False
        if tag in {"a", "div"} and self._in_snippet:
            snippet = _limpar_texto(" ".join(self._snippet_parts))
            if snippet and self.results and not self.results[-1].get("snippet"):
                self.results[-1]["snippet"] = snippet
            self._in_snippet = False


class _BingResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._result_depth = 0
        self._in_title = False
        self._in_snippet = False
        self._href = ""
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attrs_d = dict(attrs)
        klass = attrs_d.get("class", "") or ""
        if tag == "li" and "b_algo" in klass:
            self._in_result = True
            self._result_depth = 1
            self._href = ""
            self._title_parts = []
            self._snippet_parts = []
            return
        if self._in_result:
            self._result_depth += 1
            if tag == "a" and not self._href:
                self._href = attrs_d.get("href", "") or ""
                self._in_title = True
            if tag == "p":
                self._in_snippet = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._in_snippet:
            self._snippet_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._in_title and tag == "a":
            self._in_title = False
        if self._in_snippet and tag == "p":
            self._in_snippet = False
        if self._in_result:
            self._result_depth -= 1
            if tag == "li" or self._result_depth <= 0:
                title = _limpar_texto(" ".join(self._title_parts))
                snippet = _limpar_texto(" ".join(self._snippet_parts))
                if title and self._href:
                    self.results.append({"title": title, "url": self._href, "snippet": snippet, "provider": "Bing"})
                self._in_result = False
                self._result_depth = 0


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "nav", "footer", "header"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = _limpar_texto(data)
            if len(text) > 40:
                self.parts.append(text)


def _limpar_texto(texto: str) -> str:
    texto = html.unescape(texto or "")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _limpar_duck_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    parsed = urllib.parse.urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = urllib.parse.parse_qs(parsed.query)
        uddg = qs.get("uddg", [""])[0]
        return urllib.parse.unquote(uddg)
    return url


def buscar_web(consulta: str, limite: int = 5) -> list[dict[str, str]]:
    consulta = consulta.strip()
    if not consulta:
        return []
    resultados = _buscar_google_serpapi(consulta, limite=limite)
    if resultados:
        return resultados
    resultados = _buscar_bing_rss(consulta, limite=limite)
    if resultados:
        return resultados
    resultados = _buscar_bing(consulta, limite=limite)
    if resultados:
        return resultados
    return _buscar_duckduckgo(consulta, limite=limite)


def _buscar_google_serpapi(consulta: str, limite: int = 5) -> list[dict[str, str]]:
    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key or "VOTRE_CLE" in api_key:
        return []
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": consulta,
        "api_key": api_key,
        "hl": "pt",
        "gl": "br",
        "num": limite,
    }
    resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    resultados = []
    for item in data.get("organic_results", []):
        title = _limpar_texto(item.get("title", ""))
        link = _limpar_texto(item.get("link", ""))
        snippet = _limpar_texto(item.get("snippet", ""))
        if title and link:
            resultados.append({"title": title, "url": link, "snippet": snippet, "provider": "Google"})
        if len(resultados) >= limite:
            break
    return resultados


def _buscar_bing_rss(consulta: str, limite: int = 5) -> list[dict[str, str]]:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": consulta, "format": "rss"})
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    resultados = []
    for item in root.findall("./channel/item"):
        title = _limpar_texto(item.findtext("title", ""))
        link = _limpar_texto(item.findtext("link", ""))
        snippet = _limpar_texto(item.findtext("description", ""))
        if title and link:
            resultados.append({"title": title, "url": link, "snippet": snippet, "provider": "Bing"})
        if len(resultados) >= limite:
            break
    return resultados


def _buscar_bing(consulta: str, limite: int = 5) -> list[dict[str, str]]:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": consulta, "setlang": "pt-BR"})
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
    resp.raise_for_status()
    resultados = _parse_bing_regex(resp.text)
    if resultados:
        return _deduplicar(resultados, limite)
    parser = _BingResultParser()
    parser.feed(resp.text)
    return _deduplicar(parser.results, limite)


def _parse_bing_regex(html_text: str) -> list[dict[str, str]]:
    resultados: list[dict[str, str]] = []
    blocos = re.split(r'<li\s+class="b_algo"[^>]*>', html_text)
    for bloco in blocos[1:]:
        bloco = bloco.split('<li class="b_algo"', 1)[0]
        link = re.search(r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', bloco, re.I | re.S)
        if not link:
            link = re.search(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', bloco, re.I | re.S)
        if not link:
            continue
        url = html.unescape(link.group(1))
        title = _limpar_tags(link.group(2))
        snippet_m = re.search(r"<p[^>]*>(.*?)</p>", bloco, re.I | re.S)
        snippet = _limpar_tags(snippet_m.group(1)) if snippet_m else ""
        if title and url.startswith("http"):
            resultados.append({"title": title, "url": url, "snippet": snippet, "provider": "Bing"})
    return resultados


def _limpar_tags(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto)
    return _limpar_texto(texto)


def _buscar_duckduckgo(consulta: str, limite: int = 5) -> list[dict[str, str]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": consulta})
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
    resp.raise_for_status()
    parser = _DuckResultParser()
    parser.feed(resp.text)
    return _deduplicar(parser.results, limite)


def _deduplicar(items: list[dict[str, str]], limite: int) -> list[dict[str, str]]:
    vistos = set()
    resultados = []
    for item in items:
        if item["url"] in vistos:
            continue
        vistos.add(item["url"])
        resultados.append(item)
        if len(resultados) >= limite:
            break
    return resultados


def ler_pagina(url: str, max_chars: int = 2500) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "")
    if "text/html" not in ctype and "application/xhtml" not in ctype:
        return ""
    parser = _TextExtractor()
    parser.feed(resp.text[:500_000])
    texto = " ".join(parser.parts)
    texto = _limpar_texto(texto)
    return texto[:max_chars]


def _frases_relevantes(texto: str, termos: set[str], limite: int = 3) -> list[str]:
    frases = re.split(r"(?<=[.!?])\s+", texto)
    pontuadas: list[tuple[int, str]] = []
    for frase in frases:
        f = _limpar_texto(frase)
        if len(f) < 60 or len(f) > 260:
            continue
        score = sum(1 for termo in termos if termo and termo in f.lower())
        if score:
            pontuadas.append((score, f))
    pontuadas.sort(key=lambda item: item[0], reverse=True)
    return [f for _, f in pontuadas[:limite]]


def pesquisar_e_resumir(consulta: str, limite: int = 5, ler_sites: int = 3) -> str:
    resultados = buscar_web(consulta, limite=limite)
    if not resultados:
        return f"Nao encontrei resultados para {consulta}."
    provedor = resultados[0].get("provider", "web")

    termos = {t.lower() for t in re.findall(r"[a-zA-Z0-9À-ÿ]{4,}", consulta)}
    trechos: list[str] = []
    fontes: list[str] = []

    for item in resultados:
        if item.get("snippet"):
            trechos.append(f"{item['title']}: {item['snippet']}")

    for item in resultados[:ler_sites]:
        fontes.append(f"{item['title']} - {item['url']}")
        texto = ""
        try:
            texto = ler_pagina(item["url"])
        except Exception:
            texto = ""
        partes = _frases_relevantes(texto or item.get("snippet", ""), termos, limite=2)
        if partes:
            trechos.extend(partes)

    if not trechos:
        trechos = [r.get("snippet") or r["title"] for r in resultados[:3]]

    resumo = " ".join(trechos[:5])
    resumo = resumo[:900].rstrip()
    fontes_txt = "; ".join(fontes[:3])
    return f"Busca via {provedor}. Encontrei isto sobre {consulta}: {resumo}. Fontes: {fontes_txt}."
