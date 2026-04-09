#!/usr/bin/env python3
"""
TDS — Kreativ Education: Recriação dos 7 Cursos com Qualidade
Lê cartilhas markdown, extrai imagens dos DOCX, gera áudio TTS,
e cria cursos completos no Frappe LMS via REST API.
"""

import json
import os
import re
import sys
import time
import asyncio
import hashlib
import zipfile
import requests
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────
FRAPPE_URL = "https://lms.ipexdesenvolvimento.cloud"
API_KEY = "056681de29fce7a"
API_SECRET = "7c78dcba6e3c5d1"
AUTH = f"token {API_KEY}:{API_SECRET}"
HEADERS = {
    "Authorization": AUTH,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

CARTILHAS_DIR = "/tmp/cartilhas_text"
DOCX_DIR = "/cartilhasedocs/extracted/Cartilhas/Cartilhas"

# Slugs dos cursos antigos a deletar
OLD_COURSE_SLUGS = [
    "agricultura-sustent-vel-sistemas-agroflorestais",
    "audiovisual-e-produ-o-de-conte-do-digital",
    "finan-as-e-empreendedorismo",
    "educa-o-financeira-para-a-melhor-idade",
    "associativismo-e-cooperativismo-3",
    "ia-no-meu-bolso-intelig-ncia-artificial-para-o-dia-a-dia",
    "sim-servi-o-de-inspe-o-municipal-para-pequenos-produtores",
]

# Tutores
TUTORES = {
    "valentine": "valentine@ipexdesenvolvimento.cloud",
    "pedroh": "pedroh@ipexdesenvolvimento.cloud",
    "gabriela": "gabriela@ipexdesenvolvimento.cloud",
    "sofia": "sofia@ipexdesenvolvimento.cloud",
    "rafael": "rafael@ipexdesenvolvimento.cloud",
    "sahaa": "sahaa@ipexdesenvolvimento.cloud",
}

TTS_VOICES = {
    "feminina": "pt-BR-FranciscaNeural",
    "masculino": "pt-BR-AntonioNeural",
}

# ─── HELPERS ──────────────────────────────────────────────────────

def api_get(endpoint, params=None):
    url = f"{FRAPPE_URL}/api/resource/{endpoint}"
    r = requests.get(url, headers=HEADERS, params=params or {})
    r.raise_for_status()
    return r.json()

def api_post(endpoint, data):
    url = f"{FRAPPE_URL}/api/resource/{endpoint}"
    r = requests.post(url, headers=HEADERS, json=data)
    if r.status_code >= 400:
        print(f"  ERROR POST {endpoint}: {r.status_code} {r.text[:300]}")
    r.raise_for_status()
    return r.json()

def api_delete(endpoint, name):
    url = f"{FRAPPE_URL}/api/resource/{endpoint}/{name}"
    r = requests.delete(url, headers=HEADERS)
    if r.status_code in (404,):
        print(f"    (not found) {name}")
        return None
    if r.status_code in (417, 409, 403):
        print(f"    (cannot delete {r.status_code}) {name}")
        return None
    if r.status_code >= 400:
        print(f"    (delete error {r.status_code}) {name}: {r.text[:200]}")
        return None
    return r.json() if r.text else None

def upload_file(filepath, doctype=None, docname=None, fieldname=None):
    """Upload file to Frappe and return the file URL."""
    url = f"{FRAPPE_URL}/api/method/upload_file"
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f)}
        data = {"is_private": "0"}
        if doctype:
            data["doctype"] = doctype
        if docname:
            data["docname"] = docname
        if fieldname:
            data["fieldname"] = fieldname
        r = requests.post(url, headers={"Authorization": AUTH}, files=files, data=data)
        r.raise_for_status()
        return r.json()["message"]["file_url"]

def read_cartilha(filename):
    """Read cartilha markdown file and return lines."""
    path = os.path.join(CARTILHAS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()

def extract_section(lines, start_line, end_line):
    """Extract text from line range (1-indexed, inclusive)."""
    section = lines[start_line - 1 : end_line]
    return "".join(section).strip()

def extract_between_markers(lines, start_marker, end_marker=None):
    """Extract text between two markers (line content contains marker)."""
    collecting = False
    result = []
    for line in lines:
        if start_marker in line:
            collecting = True
            result.append(line)
            continue
        if end_marker and end_marker in line and collecting:
            break
        if collecting:
            result.append(line)
    return "".join(result).strip()

def clean_body(text):
    """Clean up text for lesson body."""
    # Remove image reference placeholders
    text = re.sub(r'Imagem gerada por.*?Gemini\.?\s*', '', text)
    text = re.sub(r'Sugestão de local para buscar imagens:.*?\n', '', text)
    text = re.sub(r'https://br\.freepik\.com/?\s*', '', text)
    # Ensure proper paragraph spacing
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ─── EXTRACT IMAGES FROM DOCX ────────────────────────────────────

def extract_docx_images(docx_path, output_dir):
    """Extract images from a DOCX file. Returns list of image paths."""
    images = []
    if not os.path.exists(docx_path):
        print(f"  DOCX not found: {docx_path}")
        return images

    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(docx_path, 'r') as z:
        for name in z.namelist():
            if name.startswith("word/media/") and any(
                name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
            ):
                img_data = z.read(name)
                img_name = os.path.basename(name)
                out_path = os.path.join(output_dir, img_name)
                with open(out_path, 'wb') as f:
                    f.write(img_data)
                images.append(out_path)

    print(f"  Extracted {len(images)} images from {os.path.basename(docx_path)}")
    return sorted(images)


# ─── TTS AUDIO GENERATION ────────────────────────────────────────

async def generate_tts(text, voice, output_path):
    """Generate TTS audio for text using edge-tts."""
    import edge_tts
    # Strip markdown formatting for TTS
    clean = re.sub(r'[#*_\[\]()!]', '', text)
    clean = re.sub(r'\n{2,}', '. ', clean)
    clean = re.sub(r'\n', ' ', clean)
    # Limit to ~3000 chars for reasonable audio length
    if len(clean) > 3000:
        clean = clean[:3000] + "..."

    communicate = edge_tts.Communicate(clean, voice)
    await communicate.save(output_path)
    return output_path

def generate_lesson_audio(lesson_body, voice, output_path):
    """Sync wrapper for TTS generation."""
    try:
        asyncio.run(generate_tts(lesson_body, voice, output_path))
        return True
    except Exception as e:
        print(f"  TTS error: {e}")
        return False


# ─── COURSE DEFINITIONS ──────────────────────────────────────────

def build_courses():
    """Build all 7 course definitions with content from cartilhas."""

    # ── 1. AGRICULTURA SUSTENTÁVEL ──
    agri_lines = read_cartilha("agricultura-sustentavel.md")

    agricultura = {
        "title": "Agricultura Sustentável: Sistemas Agroflorestais",
        "short_introduction": "Aprenda a produzir em equilíbrio com a natureza através dos Sistemas Agroflorestais (SAFs), transformando sua propriedade em um lugar de abundância e vida.",
        "description": "<p>Esta cartilha foi desenvolvida para produtores rurais do Tocantins que desejam aprender sobre Sistemas Agroflorestais (SAFs) — uma forma de plantar que imita a floresta, misturando árvores, frutas e culturas anuais. Você vai aprender a planejar, implantar e manejar sua agrofloresta, garantindo comida na mesa e renda durante o ano inteiro.</p>",
        "instructor": TUTORES["valentine"],
        "tts_voice": TTS_VOICES["feminina"],
        "cartilha": "agricultura-sustentavel.md",
        "docx": os.path.join(DOCX_DIR, "AGRICULTURA SUSTENTÁVEL (Valentine)/Cartilha - Agricultura Sustentável.docx"),
        "chapters": [
            {
                "title": "Fundamentos da Agricultura Sustentável",
                "description": "Entenda o que são os SAFs, como funcionam e por que são importantes para o produtor rural do Tocantins.",
                "lessons": [
                    {
                        "title": "Introdução: A Nossa Terra é a Nossa Vida",
                        "body": extract_section(agri_lines, 23, 42),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "O que são os Sistemas Agroflorestais (SAFs)",
                        "body": extract_section(agri_lines, 44, 66),
                    },
                    {
                        "title": "Tempo na Agrofloresta e Benefícios do SAF",
                        "body": extract_section(agri_lines, 67, 91),
                    },
                ],
            },
            {
                "title": "Planejamento e Diagnóstico Rural",
                "description": "Ferramentas de diagnóstico participativo para conhecer sua propriedade e planejar o futuro.",
                "lessons": [
                    {
                        "title": "Conhecendo o Sítio: Mapa e Diagnóstico",
                        "body": extract_section(agri_lines, 93, 138),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "A Ferramenta FOFA e o Mapa do Futuro",
                        "body": extract_section(agri_lines, 139, 158),
                    },
                ],
            },
            {
                "title": "Implantação da Agrofloresta",
                "description": "Passo a passo para desenhar, preparar o solo e plantar sua agrofloresta.",
                "lessons": [
                    {
                        "title": "Planejando a Fartura: O Desenho da Agrofloresta",
                        "body": extract_section(agri_lines, 160, 198),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Preparando o Chão: Plantio e Técnicas Especiais",
                        "body": extract_section(agri_lines, 199, 237),
                    },
                ],
            },
            {
                "title": "Manejo e Viabilidade Econômica",
                "description": "Como cuidar da agrofloresta e garantir retorno financeiro com os produtos do Cerrado.",
                "lessons": [
                    {
                        "title": "As Podas: O Penteado da Floresta",
                        "body": extract_section(agri_lines, 240, 261),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Produtos do Cerrado e Retorno Financeiro",
                        "body": extract_section(agri_lines, 262, len(agri_lines)),
                    },
                ],
            },
        ],
    }

    # ── 2. AUDIOVISUAL (line-based extraction) ──
    aud_lines = read_cartilha("audiovisual.md")

    audiovisual = {
        "title": "Audiovisual e Produção de Conteúdo Digital",
        "short_introduction": "Aprenda a planejar, gravar e editar vídeos usando seu celular para divulgar produtos e contar histórias da sua comunidade.",
        "description": "<p>Esta cartilha ensina os fundamentos da produção audiovisual de forma acessível. Desde a ideia até a publicação, você vai aprender a criar vídeos de qualidade usando equipamentos simples como o celular, para promover seus produtos e fortalecer a comunicação na sua comunidade.</p>",
        "instructor": TUTORES["pedroh"],
        "tts_voice": TTS_VOICES["masculino"],
        "cartilha": "audiovisual.md",
        "docx": os.path.join(DOCX_DIR, "Audiovisual (Pedro H.)/Audiovisual.docx"),
        "chapters": [
            {
                "title": "Fundamentos do Audiovisual",
                "description": "O que é audiovisual, sua história e a linguagem visual básica.",
                "lessons": [
                    {
                        "title": "O que é Audiovisual?",
                        "body": extract_section(aud_lines, 48, 55),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "História do Audiovisual",
                        "body": extract_section(aud_lines, 56, 61),
                    },
                    {
                        "title": "Linguagem Audiovisual e Tipos de Produção",
                        "body": extract_section(aud_lines, 62, 87),
                    },
                ],
            },
            {
                "title": "Pré-produção",
                "description": "Planejamento: da ideia ao roteiro, storyboard e equipamentos.",
                "lessons": [
                    {
                        "title": "Ideia e Roteiro",
                        "body": extract_section(aud_lines, 88, 112),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Storyboard e Planejamento",
                        "body": extract_section(aud_lines, 113, 128),
                    },
                    {
                        "title": "Equipamentos Básicos e Tipos de Câmera",
                        "body": extract_section(aud_lines, 129, 145),
                    },
                ],
            },
            {
                "title": "Gravação",
                "description": "Técnicas de enquadramento, iluminação, áudio e filmagem.",
                "lessons": [
                    {
                        "title": "Enquadramento e Ângulos de Câmera",
                        "body": extract_section(aud_lines, 146, 174),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Iluminação e Captação de Áudio",
                        "body": extract_section(aud_lines, 175, 190),
                    },
                    {
                        "title": "Direção, Filmagem e Continuidade",
                        "body": extract_section(aud_lines, 191, 224),
                    },
                ],
            },
            {
                "title": "Pós-produção e Publicação",
                "description": "Edição, exportação, publicação em redes sociais e marketing de vídeo.",
                "lessons": [
                    {
                        "title": "Edição de Vídeo: Corte, Trilha e Cor",
                        "body": extract_section(aud_lines, 225, 262),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Exportação, Publicação e Marketing",
                        "body": extract_section(aud_lines, 263, 296),
                    },
                    {
                        "title": "Direitos Autorais e Dicas para Iniciantes",
                        "body": extract_section(aud_lines, 297, 353),
                    },
                ],
            },
        ],
    }

    # ── 3. FINANÇAS E EMPREENDEDORISMO ──
    fin_lines = read_cartilha("financas-empreendedorismo.md")

    financas = {
        "title": "Finanças e Empreendedorismo",
        "short_introduction": "Educação financeira para a vida e o trabalho: do planejamento pessoal à gestão do seu negócio.",
        "description": "<p>Aprenda a organizar suas finanças pessoais, controlar gastos, usar crédito com responsabilidade e precificar seus produtos. Uma cartilha prática pensada para quem quer ter mais segurança financeira e fortalecer seu pequeno negócio.</p>",
        "instructor": TUTORES["gabriela"],
        "tts_voice": TTS_VOICES["feminina"],
        "cartilha": "financas-empreendedorismo.md",
        "docx": os.path.join(DOCX_DIR, "Finanças (Gabriela)/Gabriela - Finanças 1.docx"),
        "chapters": [
            {
                "title": "Conceitos Básicos de Educação Financeira",
                "description": "Entenda o que é educação financeira, receitas, despesas e o papel do dinheiro na sua vida.",
                "lessons": [
                    {
                        "title": "Introdução: Para Onde Vai o Seu Dinheiro?",
                        "body": extract_section(fin_lines, 18, 44),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Conceitos Básicos: Receitas e Despesas",
                        "body": extract_section(fin_lines, 45, 87),
                    },
                    {
                        "title": "O Dinheiro e as Trocas",
                        "body": extract_section(fin_lines, 59, 87),
                    },
                ],
            },
            {
                "title": "Crédito, Dívidas e Poupança",
                "description": "Como usar crédito com responsabilidade, evitar dívidas e começar a poupar.",
                "lessons": [
                    {
                        "title": "Crédito: Aliado ou Vilão?",
                        "body": extract_section(fin_lines, 88, 130),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Evitando Dívidas e Começando a Poupar",
                        "body": extract_section(fin_lines, 131, 172),
                    },
                ],
            },
            {
                "title": "Orçamento e Planejamento Financeiro",
                "description": "Monte seu orçamento pessoal, controle gastos e defina metas financeiras.",
                "lessons": [
                    {
                        "title": "Orçamento Familiar: Como Montar o Seu",
                        "body": extract_section(fin_lines, 173, 238),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Planejamento Financeiro na Prática",
                        "body": extract_section(fin_lines, 239, 348),
                    },
                ],
            },
            {
                "title": "Finanças do Negócio",
                "description": "Precificação, markup, ponto de equilíbrio e gestão financeira do seu empreendimento.",
                "lessons": [
                    {
                        "title": "Controle Financeiro em Pequenos Negócios",
                        "body": extract_section(fin_lines, 349, 384),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Precificação e Ponto de Equilíbrio",
                        "body": extract_section(fin_lines, 385, 443),
                    },
                ],
            },
        ],
    }

    # ── 4. EDUCAÇÃO FINANCEIRA MELHOR IDADE ──
    fi3_lines = read_cartilha("financas-terceira-idade.md")

    financas_idade = {
        "title": "Educação Financeira para a Melhor Idade",
        "short_introduction": "Guia prático para cuidar do seu dinheiro na terceira idade com segurança e autonomia.",
        "description": "<p>Cartilha especialmente pensada para pessoas da terceira idade, com orientações simples sobre organização financeira, proteção contra golpes, uso do crédito e planejamento para viver com mais tranquilidade.</p>",
        "instructor": TUTORES["gabriela"],
        "tts_voice": TTS_VOICES["feminina"],
        "cartilha": "financas-terceira-idade.md",
        "docx": os.path.join(DOCX_DIR, "Finanças (Gabriela)/Gabriela - Finanças 2 - Terceira idade.docx"),
        "chapters": [
            {
                "title": "Sua Aposentadoria e Seus Direitos",
                "description": "Tipos de benefício, BPC/LOAS e direitos da pessoa idosa.",
                "lessons": [
                    {
                        "title": "Introdução: Educação Financeira na Terceira Idade",
                        "body": extract_section(fi3_lines, 22, 52),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Fundamentos: Receitas, Despesas e Equilíbrio",
                        "body": extract_section(fi3_lines, 69, 99),
                    },
                    {
                        "title": "Orçamento Familiar e Aposentadoria",
                        "body": extract_section(fi3_lines, 100, 167),
                    },
                ],
            },
            {
                "title": "Proteção Financeira",
                "description": "Golpes e fraudes, crédito consignado e segurança digital para a terceira idade.",
                "lessons": [
                    {
                        "title": "Cuidado com Golpes e Fraudes",
                        "body": extract_section(fi3_lines, 168, 172),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Proteção Financeira e Crédito Seguro",
                        "body": extract_section(fi3_lines, 170, 191),
                    },
                ],
            },
            {
                "title": "Planejamento para a Terceira Idade",
                "description": "Orçamento, saúde, qualidade de vida e direitos da pessoa idosa.",
                "lessons": [
                    {
                        "title": "Planejamento Financeiro para a Melhor Idade",
                        "body": extract_section(fi3_lines, 173, 198),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Direitos da Pessoa Idosa e Considerações Finais",
                        "body": extract_section(fi3_lines, 192, len(fi3_lines)),
                    },
                ],
            },
        ],
    }

    # ── 5. ASSOCIATIVISMO E COOPERATIVISMO ──
    assoc_lines = read_cartilha("associativismo-cooperativismo.md")

    associativismo = {
        "title": "Associativismo e Cooperativismo",
        "short_introduction": "Aprenda a se organizar em associações e cooperativas para fortalecer sua comunidade e aumentar sua renda.",
        "description": "<p>Esta cartilha explica como o Associativismo e o Cooperativismo podem transformar sua realidade. Você vai entender as diferenças entre associação e cooperativa, os 7 princípios do cooperativismo e como criar sua própria organização coletiva no Tocantins.</p>",
        "instructor": TUTORES["sofia"],
        "tts_voice": TTS_VOICES["feminina"],
        "cartilha": "associativismo-cooperativismo.md",
        "docx": os.path.join(DOCX_DIR, "Associativismo e Cooperativismo (Sofia)/ TDS-CARTILHA ASSOCIATIVISMO E COOPERATIVISMO_.docx"),
        "chapters": [
            {
                "title": "Fundamentos: Associativismo e Cooperativismo",
                "description": "O que são associações e cooperativas, suas diferenças e por que a união faz a diferença.",
                "lessons": [
                    {
                        "title": "Introdução: A União que Transforma",
                        "body": extract_section(assoc_lines, 8, 37),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Associativismo e Cooperativismo: Conceitos e Diferenças",
                        "body": extract_section(assoc_lines, 38, 53),
                    },
                    {
                        "title": "O Cooperativismo no Tocantins: História e Desafios",
                        "body": extract_section(assoc_lines, 54, 61),
                    },
                ],
            },
            {
                "title": "Como se Organizar",
                "description": "Passo a passo para criar uma associação, estatuto e decisões coletivas.",
                "lessons": [
                    {
                        "title": "Criando uma Associação: Passo a Passo",
                        "body": extract_section(assoc_lines, 61, 80),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Direitos e Deveres dos Membros",
                        "body": extract_section(assoc_lines, 63, 80) if len(assoc_lines) > 80 else extract_section(assoc_lines, 63, len(assoc_lines)),
                    },
                ],
            },
            {
                "title": "Cooperativismo na Prática",
                "description": "Os 7 princípios do cooperativismo, benefícios e exemplos no Tocantins.",
                "lessons": [
                    {
                        "title": "Os 7 Princípios do Cooperativismo",
                        "body": extract_section(assoc_lines, 42, 53),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Benefícios e Exemplos Práticos no Tocantins",
                        "body": extract_section(assoc_lines, 54, len(assoc_lines)),
                    },
                ],
            },
        ],
    }

    # ── 6. IA NO MEU BOLSO (line-based extraction) ──
    ia_lines = read_cartilha("ia-no-bolso.md")

    ia = {
        "title": "IA no meu Bolso: Inteligência Artificial para o Dia a Dia",
        "short_introduction": "Aprenda a usar ferramentas gratuitas de Inteligência Artificial no celular para melhorar seu negócio e sua vida.",
        "description": "<p>Descubra como a Inteligência Artificial já está presente no seu dia a dia e aprenda a usar ferramentas gratuitas como ChatGPT e Google Gemini para criar textos, imagens, atender clientes e impulsionar seu negócio no Tocantins.</p>",
        "instructor": TUTORES["rafael"],
        "tts_voice": TTS_VOICES["masculino"],
        "cartilha": "ia-no-bolso.md",
        "docx": os.path.join(DOCX_DIR, "IA - RAFAEL /Cartilha_IA_TDS_com_imagens.docx"),
        "chapters": [
            {
                "title": "O que é Inteligência Artificial",
                "description": "IA no dia a dia, como funciona e o que é mito ou verdade.",
                "lessons": [
                    {
                        "title": "Introdução: IA no Seu Dia a Dia",
                        "body": extract_section(ia_lines, 55, 70),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Fundamentos: Como a IA Funciona",
                        "body": extract_section(ia_lines, 71, 104),
                    },
                ],
            },
            {
                "title": "Ferramentas Gratuitas no Celular",
                "description": "ChatGPT, Google Gemini e assistentes de voz acessíveis pelo celular.",
                "lessons": [
                    {
                        "title": "Geração de Textos e Conteúdos de Divulgação",
                        "body": extract_section(ia_lines, 105, 119),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Criação de Imagens e Materiais Visuais",
                        "body": extract_section(ia_lines, 120, 134),
                    },
                    {
                        "title": "Atendimento ao Cliente e Pesquisa de Políticas",
                        "body": extract_section(ia_lines, 135, 151),
                    },
                ],
            },
            {
                "title": "IA para seu Negócio",
                "description": "Descrições de produtos, atendimento, marketing e organização financeira com IA.",
                "lessons": [
                    {
                        "title": "Organização Financeira com Suporte da IA",
                        "body": extract_section(ia_lines, 152, 163),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Monitoramento de Clima e Condições Agrícolas",
                        "body": extract_section(ia_lines, 164, 168),
                    },
                ],
            },
            {
                "title": "Uso Responsável da IA",
                "description": "Privacidade, verificação de informações e o futuro do trabalho com IA.",
                "lessons": [
                    {
                        "title": "Precauções Essenciais no Uso da IA",
                        "body": extract_section(ia_lines, 169, 176),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Experiências Locais e Considerações Finais",
                        "body": extract_section(ia_lines, 177, 210),
                    },
                ],
            },
        ],
    }

    # ── 7. SIM — SERVIÇO DE INSPEÇÃO MUNICIPAL ──
    sim_lines = read_cartilha("sim.md")

    sim = {
        "title": "SIM — Serviço de Inspeção Municipal para Pequenos Produtores",
        "short_introduction": "Regularize seus produtos alimentares com o SIM e SIMA para vender com segurança e acessar novos mercados.",
        "description": "<p>Esta cartilha orienta pequenos produtores sobre como regularizar produtos de origem animal e agroindustrial através do SIM (Serviço de Inspeção Municipal) e SIMA. Aprenda boas práticas de fabricação, rotulagem e como obter certificação para vender em feiras, mercados e programas governamentais.</p>",
        "instructor": TUTORES["sahaa"],
        "tts_voice": TTS_VOICES["feminina"],
        "cartilha": "sim.md",
        "docx": os.path.join(DOCX_DIR, "SIM (Sahaa)/Cartilha.docx"),
        "chapters": [
            {
                "title": "Introdução ao SIM",
                "description": "O que é o SIM/SIMA, por que regularizar e a legislação básica.",
                "lessons": [
                    {
                        "title": "Introdução: O que é o SIM e o SIMA",
                        "body": extract_section(sim_lines, 43, 69),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Fundamentos Teóricos: Regularização Sanitária",
                        "body": extract_section(sim_lines, 60, 92),
                    },
                ],
            },
            {
                "title": "Processo de Registro",
                "description": "Passo a passo para registrar seus produtos, documentos necessários e custos.",
                "lessons": [
                    {
                        "title": "Passo a Passo para Regularização",
                        "body": extract_section(sim_lines, 93, 131),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Como Organizar seu Negócio",
                        "body": extract_section(sim_lines, 122, 165),
                    },
                ],
            },
            {
                "title": "Boas Práticas de Fabricação",
                "description": "Higiene, instalações, rotulagem e transporte seguro de alimentos.",
                "lessons": [
                    {
                        "title": "Boas Práticas, Rotulagem e Transporte",
                        "body": extract_section(sim_lines, 132, 200),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Dicas Práticas e Estratégias do Dia a Dia",
                        "body": extract_section(sim_lines, 192, 228),
                    },
                ],
            },
            {
                "title": "SIMA e Consórcios Municipais",
                "description": "Vantagens da participação em consórcios, procedimentos e experiências locais.",
                "lessons": [
                    {
                        "title": "SIMA e Consórcios Municipais",
                        "body": extract_section(sim_lines, 229, 285),
                        "include_in_preview": 1,
                    },
                    {
                        "title": "Experiências Locais no Tocantins",
                        "body": extract_section(sim_lines, 286, len(sim_lines)),
                    },
                ],
            },
        ],
    }

    return [agricultura, audiovisual, financas, financas_idade, associativismo, ia, sim]


# ─── DELETION ─────────────────────────────────────────────────────

def delete_old_courses():
    """Delete old courses and all their children."""
    print("\n=== DELETANDO CURSOS ANTIGOS ===")

    for slug in OLD_COURSE_SLUGS:
        print(f"\n  Deletando curso: {slug}")

        # Get chapters
        try:
            chapters = api_get("Course Chapter", {
                "filters": json.dumps([["course", "=", slug]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": 100,
            })
            for ch in chapters.get("data", []):
                # Get lessons for this chapter
                try:
                    lessons = api_get("Course Lesson", {
                        "filters": json.dumps([["chapter", "=", ch["name"]]]),
                        "fields": json.dumps(["name"]),
                        "limit_page_length": 100,
                    })
                    for lesson in lessons.get("data", []):
                        api_delete("Course Lesson", lesson["name"])
                        print(f"    Deleted lesson: {lesson['name']}")
                except Exception as e:
                    print(f"    Error listing lessons: {e}")

                result = api_delete("Course Chapter", ch["name"])
                if result is not None:
                    print(f"    Deleted chapter: {ch['name']}")
        except Exception as e:
            print(f"    Error listing chapters: {e}")

        # Delete enrollments
        try:
            enrollments = api_get("LMS Enrollment", {
                "filters": json.dumps([["course", "=", slug]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": 500,
            })
            for enr in enrollments.get("data", []):
                api_delete("LMS Enrollment", enr["name"])
        except Exception:
            pass

        # Delete the course itself
        result = api_delete("LMS Course", slug)
        if result is not None:
            print(f"  ✓ Curso deletado: {slug}")
        else:
            print(f"  ⚠ Curso não pôde ser deletado (pode ter dependências): {slug}")
        time.sleep(0.3)


# ─── CREATION ─────────────────────────────────────────────────────

def create_course(course_def):
    """Create a complete course with chapters and lessons."""
    title = course_def["title"]
    print(f"\n=== CRIANDO CURSO: {title} ===")

    # 1. Create Course
    course_data = {
        "title": title,
        "short_introduction": course_def["short_introduction"],
        "description": course_def["description"],
        "published": 1,
        "status": "Approved",
        "paid_course": 0,
        "currency": "BRL",
        "instructors": [{"instructor": course_def["instructor"]}],
    }

    result = api_post("LMS Course", course_data)
    course_slug = result["data"]["name"]
    print(f"  ✓ Curso criado: {course_slug}")
    time.sleep(0.5)

    # 2. Extract images from DOCX
    img_dir = f"/tmp/tds_images/{course_slug}"
    images = []
    if os.path.exists(course_def.get("docx", "")):
        images = extract_docx_images(course_def["docx"], img_dir)

    # Upload images and get URLs
    image_urls = []
    for img_path in images[:10]:  # Limit to first 10 images
        try:
            url = upload_file(img_path, "LMS Course", course_slug, "image")
            image_urls.append(url)
            print(f"    ✓ Image uploaded: {os.path.basename(img_path)}")
        except Exception as e:
            print(f"    ✗ Image upload failed: {e}")

    # Set course cover image if available
    if image_urls:
        try:
            requests.put(
                f"{FRAPPE_URL}/api/resource/LMS Course/{course_slug}",
                headers=HEADERS,
                json={"image": image_urls[0]}
            )
            print(f"  ✓ Cover image set")
        except Exception:
            pass

    # 3. Create Chapters and Lessons
    img_idx = 1  # Start from 2nd image (1st is cover)

    for ch_idx, chapter_def in enumerate(course_def["chapters"], 1):
        # Create Chapter
        chapter_data = {
            "title": chapter_def["title"],
            "course": course_slug,
            "description": chapter_def.get("description", ""),
            "idx": ch_idx,
        }
        ch_result = api_post("Course Chapter", chapter_data)
        chapter_name = ch_result["data"]["name"]
        print(f"  ✓ Capítulo {ch_idx}: {chapter_def['title']}")
        time.sleep(0.3)

        for l_idx, lesson_def in enumerate(chapter_def["lessons"], 1):
            # Prepare body with images if available
            body = clean_body(lesson_def.get("body", ""))

            # Add an image if available
            if img_idx < len(image_urls):
                body += f"\n\n![Ilustração]({image_urls[img_idx]})"
                img_idx += 1

            # Ensure body is not empty
            if not body or len(body) < 20:
                body = f"## {lesson_def['title']}\n\nConteúdo em desenvolvimento."

            lesson_data = {
                "title": lesson_def["title"],
                "chapter": chapter_name,
                "course": course_slug,
                "body": body,
                "content": '{"blocks": []}',
                "published": 1,
                "idx": l_idx,
                "include_in_preview": lesson_def.get("include_in_preview", 0),
            }

            l_result = api_post("Course Lesson", lesson_data)
            lesson_name = l_result["data"]["name"]
            print(f"    ✓ Lição {ch_idx}.{l_idx}: {lesson_def['title']} ({len(body)} chars)")
            time.sleep(0.3)

            # Generate TTS audio
            audio_dir = f"/tmp/tds_audio/{course_slug}"
            os.makedirs(audio_dir, exist_ok=True)
            audio_path = os.path.join(audio_dir, f"lesson_{ch_idx}_{l_idx}.mp3")

            if generate_lesson_audio(body, course_def["tts_voice"], audio_path):
                try:
                    audio_url = upload_file(audio_path, "Course Lesson", lesson_name, "")
                    # Append audio player to lesson body
                    updated_body = body + f'\n\n---\n🔊 **Ouça esta lição:**\n<audio controls src="{audio_url}"></audio>'
                    requests.put(
                        f"{FRAPPE_URL}/api/resource/Course Lesson/{lesson_name}",
                        headers=HEADERS,
                        json={"body": updated_body}
                    )
                    print(f"      ✓ Áudio TTS gerado e anexado")
                except Exception as e:
                    print(f"      ✗ Áudio upload falhou: {e}")

    return course_slug


# ─── BATCH ASSOCIATION ────────────────────────────────────────────

BATCHES = {
    "Agricultura Sustentável": "turma-tds-agricultura-sustent-vel-2026",
    "Audiovisual": "turma-tds-audiovisual-e-conte-do-digital-2026",
    "Finanças e Empreendedorismo": "turma-tds-finan-as-e-empreendedorismo-2026",
    "Associativismo e Cooperativismo": "turma-tds-associativismo-e-cooperativismo-2026",
    "IA no meu Bolso": "turma-tds-ia-no-meu-bolso-2026",
    "SIM": "turma-tds-sim-e-inspe-o-alimentar-2026",
}


# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("TDS — Kreativ Education: Recriação dos 7 Cursos")
    print("=" * 60)

    # Test API connection
    print("\nTestando conexão com Frappe LMS...")
    try:
        r = requests.get(f"{FRAPPE_URL}/api/method/frappe.client.get_count?doctype=LMS Course",
                        headers=HEADERS)
        r.raise_for_status()
        print(f"  ✓ Conectado. Cursos existentes: {r.json().get('message', '?')}")
    except Exception as e:
        print(f"  ✗ Erro de conexão: {e}")
        sys.exit(1)

    # Step 1: Delete old courses
    if "--skip-delete" not in sys.argv:
        delete_old_courses()

    # Step 2: Build course definitions
    print("\n\nCarregando conteúdo das cartilhas...")
    courses = build_courses()
    print(f"  ✓ {len(courses)} cursos definidos")

    # Step 3: Create courses
    created_slugs = []
    for course in courses:
        try:
            slug = create_course(course)
            created_slugs.append(slug)
        except Exception as e:
            print(f"\n  ✗ ERRO criando {course['title']}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("RESUMO DA CRIAÇÃO")
    print("=" * 60)
    for slug in created_slugs:
        print(f"  ✓ {FRAPPE_URL}/lms/courses/{slug}")

    print(f"\n  Total: {len(created_slugs)}/{len(courses)} cursos criados")
    print(f"\n  Próximo passo: verificar no navegador e associar às turmas (batches)")

    # Export course slugs for reference
    with open("/tmp/tds_created_courses.json", "w") as f:
        json.dump(created_slugs, f, indent=2)
    print(f"  Slugs salvos em /tmp/tds_created_courses.json")


if __name__ == "__main__":
    main()
