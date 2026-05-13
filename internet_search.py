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


def _serpapi_key() -> str:
    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key or "VOTRE_CLE" in api_key:
        return ""
    return api_key


def _buscar_google_serpapi(consulta: str, limite: int = 5) -> list[dict[str, str]]:
    api_key = _serpapi_key()
    if not api_key:
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


def buscar_lojas_serpapi(consulta: str, limite: int = 6) -> list[dict[str, str]]:
    api_key = _serpapi_key()
    if not api_key:
        return []
    params = {
        "engine": "google_shopping",
        "q": consulta,
        "api_key": api_key,
        "hl": "pt",
        "gl": "br",
        "num": limite,
    }
    resp = requests.get("https://serpapi.com/search.json", params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    resultados = []
    for item in data.get("shopping_results", []):
        title = _limpar_texto(item.get("title", ""))
        price = _limpar_texto(item.get("price", ""))
        source = _limpar_texto(item.get("source", ""))
        link = _limpar_texto(item.get("link") or item.get("product_link") or "")
        rating = item.get("rating")
        reviews = item.get("reviews")
        snippet_parts = [p for p in [price, source, f"nota {rating}" if rating else "", f"{reviews} avaliacoes" if reviews else ""] if p]
        if title:
            resultados.append({
                "title": title,
                "url": link,
                "snippet": " | ".join(snippet_parts),
                "provider": "Google Shopping",
                "price": price,
                "source": source,
            })
        if len(resultados) >= limite:
            break
    return resultados


def buscar_lugares_serpapi(consulta: str, localidade: str = "", limite: int = 6) -> list[dict[str, str]]:
    api_key = _serpapi_key()
    if not api_key:
        return []
    q = f"{consulta} {localidade}".strip()
    params = {
        "engine": "google_maps",
        "q": q,
        "api_key": api_key,
        "hl": "pt",
        "gl": "br",
        "type": "search",
    }
    resp = requests.get("https://serpapi.com/search.json", params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    resultados = []
    for item in data.get("local_results", []):
        title = _limpar_texto(item.get("title", ""))
        address = _limpar_texto(item.get("address", ""))
        phone = _limpar_texto(item.get("phone", ""))
        rating = item.get("rating")
        reviews = item.get("reviews")
        website = _limpar_texto(item.get("website", ""))
        gps = item.get("gps_coordinates") or {}
        maps_url = ""
        if gps.get("latitude") and gps.get("longitude"):
            maps_url = f"https://www.google.com/maps/search/?api=1&query={gps['latitude']},{gps['longitude']}"
        snippet_parts = [p for p in [address, phone, f"nota {rating}" if rating else "", f"{reviews} avaliacoes" if reviews else ""] if p]
        if title:
            resultados.append({
                "title": title,
                "url": website or maps_url,
                "snippet": " | ".join(snippet_parts),
                "provider": "Google Maps",
                "address": address,
                "phone": phone,
                "rating": rating,
                "reviews": reviews,
            })
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


def _extrair_precos(resultados: list[dict[str, str]]) -> list[str]:
    precos = []
    for item in resultados:
        preco = item.get("price") or ""
        if preco:
            precos.append(preco)
    return precos


def _formatar_itens(titulo: str, resultados: list[dict[str, str]], limite: int = 4) -> str:
    if not resultados:
        return f"{titulo}: nao encontrei dados suficientes."
    partes = []
    for item in resultados[:limite]:
        trecho = item["title"]
        if item.get("snippet"):
            trecho += f" ({item['snippet']})"
        partes.append(trecho)
    return f"{titulo}: " + "; ".join(partes) + "."


def pesquisar_viabilidade(consulta: str, localidade: str = "", limite: int = 6) -> str:
    consulta = consulta.strip()
    if not consulta:
        return "O que voce quer que eu avalie?"

    consulta_l = consulta.lower()
    quer_lojas = any(p in consulta_l for p in (
        "comprar", "loja", "lojas", "preco", "preço", "produto", "barato",
        "mais barato", "oferta", "mercado", "shopping", "onde encontro",
    ))
    quer_local = any(p in consulta_l for p in (
        "perto", "perto de", "local", "localidade", "endereco", "endereço",
        "bairro", "cidade", "maps", "rota", "distancia", "distância",
        "restaurante", "hotel", "clinica", "clínica", "mercado", "assistencia",
    ))
    quer_viabilidade = any(p in consulta_l for p in (
        "viabilidade", "vale a pena", "compensa", "melhor opção", "melhor opcao",
        "analisa", "analise", "avaliar", "avalia", "comparar", "compare",
        "custo beneficio", "custo benefício",
    ))

    web = buscar_web(consulta, limite=limite)
    lojas = buscar_lojas_serpapi(consulta, limite=limite) if quer_lojas or quer_viabilidade else []
    lugares = buscar_lugares_serpapi(consulta, localidade=localidade, limite=limite) if quer_local or localidade else []

    if not web and not lojas and not lugares:
        return f"Nao encontrei dados suficientes para avaliar {consulta}."

    provedor = "Google/SerpAPI" if _serpapi_key() else (web[0].get("provider", "web") if web else "web")
    blocos = [f"Pesquisa de viabilidade via {provedor} para: {consulta}."]
    blocos.append(_formatar_itens("Resumo web", web, limite=3))
    if lojas:
        blocos.append(_formatar_itens("Lojas e precos", lojas, limite=4))
        precos = _extrair_precos(lojas)
        if precos:
            blocos.append(f"Faixa de precos encontrada: {', '.join(precos[:4])}.")
    if lugares:
        blocos.append(_formatar_itens("Opcoes locais", lugares, limite=4))

    sinais_positivos = []
    sinais_alerta = []
    texto_base = " ".join([i.get("title", "") + " " + i.get("snippet", "") for i in web + lojas + lugares]).lower()
    if any(p in texto_base for p in ("avalia", "nota", "reviews", "reclame aqui", "garantia")):
        sinais_positivos.append("ha sinais de reputacao/avaliacoes para comparar")
    if any(p in texto_base for p in ("indisponivel", "fora de estoque", "esgotado", "reclama", "problema")):
        sinais_alerta.append("apareceram possiveis alertas de disponibilidade ou reputacao")
    if lojas:
        sinais_positivos.append("ha opcoes de compra encontradas")
    if lugares:
        sinais_positivos.append("ha opcoes locais encontradas")

    conclusao = "Conclusao: "
    if lojas or lugares or len(web) >= 3:
        conclusao += "parece viavel continuar, mas eu recomendo comparar preco final, reputacao, prazo e garantia antes de decidir."
    else:
        conclusao += "a viabilidade ainda esta incerta; encontrei poucos dados e vale ampliar a busca."
    if sinais_positivos:
        conclusao += " Pontos a favor: " + "; ".join(sinais_positivos[:3]) + "."
    if sinais_alerta:
        conclusao += " Atenção: " + "; ".join(sinais_alerta[:2]) + "."
    blocos.append(conclusao)

    fontes = []
    for item in (web + lojas + lugares):
        if item.get("url"):
            fontes.append(f"{item['title']} - {item['url']}")
    if fontes:
        blocos.append("Fontes: " + "; ".join(fontes[:5]) + ".")

    resposta = " ".join(blocos)
    return resposta[:1800]
