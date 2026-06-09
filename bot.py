#!/usr/bin/env python3
"""ScoutAI Bot v3 – Dados Reais + IA"""

import os, json, logging, requests
from datetime import datetime
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ── CONFIGURAÇÃO ────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
RAPIDAPI_KEY   = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST  = os.getenv("RAPIDAPI_HOST", "free-api-live-football-data.p.rapidapi.com")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_TOKEN e GROQ_API_KEY são obrigatórios!")

groq_client = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
DIAS  = ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira",
         "Sexta-feira","Sábado","Domingo"]

def data_hoje():
    n = datetime.now()
    return f"{DIAS[n.weekday()]}, {n.day:02d} de {MESES[n.month-1]} de {n.year}"

def data_iso():
    return datetime.now().strftime("%Y-%m-%d")

def hora_agora():
    return datetime.now().strftime("%H:%M")

# ── API FUTEBOL REAL ─────────────────────────────────────
HEADERS = {
    "x-rapidapi-key":  RAPIDAPI_KEY or "",
    "x-rapidapi-host": RAPIDAPI_HOST,
    "Content-Type":    "application/json"
}

def buscar_jogos_hoje():
    """Busca jogos reais do dia actual."""
    try:
        url = f"https://{RAPIDAPI_HOST}/get-matches-by-date"
        r = requests.get(url, headers=HEADERS,
                        params={"date": data_iso()}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.error(f"Erro API jogos: {e}")
    return None

def buscar_ao_vivo():
    """Busca jogos ao vivo agora."""
    try:
        url = f"https://{RAPIDAPI_HOST}/get-live-scores"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.error(f"Erro API ao vivo: {e}")
    return None

def buscar_classificacao(liga_id):
    """Busca classificação de uma liga."""
    try:
        url = f"https://{RAPIDAPI_HOST}/get-league-standings"
        r = requests.get(url, headers=HEADERS,
                        params={"league_id": liga_id}, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.error(f"Erro API classificação: {e}")
    return None

# ── IA GROQ ──────────────────────────────────────────────
def ia_analisar_jogo(casa, fora, liga, dados_extra=""):
    prompt = f"""Hoje é {data_hoje()}. És um analista desportivo especializado em apostas.
Analisa este jogo real: {casa} vs {fora} — {liga}
{f'Dados adicionais: {dados_extra}' if dados_extra else ''}

Responde APENAS com JSON válido:
{{
  "palpite_principal": "Vitória Casa | Empate | Vitória Fora | Ambas Marcam | Acima 2.5",
  "probabilidade_casa": 55,
  "probabilidade_empate": 25,
  "probabilidade_fora": 20,
  "confianca": 72,
  "previsao_golos": "2-1",
  "forma_casa": "V V E V D",
  "forma_fora": "D E V D V",
  "opcoes": [
    {{"tipo": "Dupla Chance 1X",    "odd": "1.40", "conf": 80}},
    {{"tipo": "Ambas Marcam – Sim", "odd": "1.85", "conf": 68}},
    {{"tipo": "Acima 2.5 Golos",   "odd": "1.80", "conf": 65}},
    {{"tipo": "Vitória Casa",       "odd": "2.10", "conf": 55}},
    {{"tipo": "Abaixo 3.5 Golos",  "odd": "1.50", "conf": 75}}
  ],
  "analise": "Análise detalhada em 3 frases em Português sobre este jogo real.",
  "aviso": null
}}"""
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0.6, max_tokens=1000
    )
    raw = r.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)

def ia_palpites_simulados(liga, desporto="futebol", qtd="10 a 13"):
    prompt = f"""Hoje é {data_hoje()}, hora actual: {hora_agora()}.
És analista desportivo. Gera {qtd} jogos típicos de {desporto} para hoje em: {liga}.
Responde APENAS com JSON:
{{
  "data": "{data_hoje()}",
  "hora": "{hora_agora()}",
  "resumo": "Resumo do dia em 2 frases.",
  "jogos": [{{
    "liga": "Liga", "pais": "País", "hora_jogo": "HH:MM",
    "casa": "Equipa A", "fora": "Equipa B",
    "palpite_principal": "Vitória Casa",
    "prob_casa": 60, "prob_empate": 20, "prob_fora": 20,
    "confianca": 75, "previsao": "2-1",
    "forma_casa": "V V E V V", "forma_fora": "D E V D E",
    "opcoes": [
      {{"tipo":"Dupla Chance 1X","odd":"1.35","conf":82}},
      {{"tipo":"Ambas Marcam – Sim","odd":"1.80","conf":70}},
      {{"tipo":"Acima 2.5 Golos","odd":"1.75","conf":68}},
      {{"tipo":"Vitória Casa","odd":"2.10","conf":60}}
    ],
    "analise": "Análise de 2-3 frases em Português.",
    "aviso": null
  }}]
}}
Texto em Português. Odds 1.15-5.00. Probabilidades somam 100."""
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7, max_tokens=4000
    )
    raw = r.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)

def ia_chat(pergunta, historico):
    msgs = [{"role":"system","content":
        f"Hoje é {data_hoje()}. És o ScoutAI, assistente desportivo especializado em futebol, "
        "basquetebol e apostas. Tens conhecimento do Mundial 2026 que começa a 11 de Junho de 2026 "
        "nos EUA, Canadá e México. Respondes sempre em Português de Moçambique. "
        "És directo, amigável e muito conhecedor de desporto. "
        "Quando perguntarem sobre jogos do dia, referes que podem usar /jogos para ver dados reais."}]
    msgs += historico[-8:]
    msgs.append({"role":"user","content":pergunta})
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=msgs, temperature=0.8, max_tokens=600
    )
    return r.choices[0].message.content.strip()

# ── FORMATAR MENSAGENS ───────────────────────────────────
def ec(v):
    if v >= 80: return "🟢"
    if v >= 65: return "🟡"
    if v >= 50: return "🟠"
    return "🔴"

def barra(p, t=8):
    c = round(p*t/100)
    return "█"*c + "░"*(t-c)

def fmt_lista(dados, fonte="IA"):
    tag = "🌐 Dados Reais" if fonte=="real" else "🤖 Análise IA"
    linhas = [
        f"⚽🏀 *SCOUTAI – PALPITES DO DIA*  {tag}",
        f"📅 _{dados.get('data', data_hoje())}_",
        f"🕐 Gerado às {dados.get('hora', hora_agora())}\n",
        f"📊 _{dados.get('resumo','')}_\n",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    for j in dados.get("jogos",[]):
        c = j.get("confianca", j.get("conf",70))
        linhas.append(
            f"{ec(c)} *{j['casa']} vs {j['fora']}*\n"
            f"   🕐 {j.get('hora_jogo','--:--')}  |  🏆 {j['liga']} ({j.get('pais','')})\n"
            f"   🎯 *{j['palpite_principal']}*  — {c}%\n"
            f"   📈 C:{j.get('prob_casa','-')}% E:{j.get('prob_empate','-')}% F:{j.get('prob_fora','-')}%\n"
        )
    linhas += ["━━━━━━━━━━━━━━━━━━━━━",
               "👆 Clica num número para análise completa",
               "⚠️ _Aposte com responsabilidade._"]
    return "\n".join(linhas)

def fmt_jogo(j, num):
    c = j.get("confianca", j.get("conf",70))
    pc = j.get("prob_casa",0)
    pe = j.get("prob_empate",0)
    pf = j.get("prob_fora",0)
    ops = "\n".join(
        f"   {ec(o.get('conf',60))} {o['tipo']} → odd *{o['odd']}* ({o.get('conf',60)}%)"
        for o in j.get("opcoes",[])
    )
    av = f"\n⚠️ _{j['aviso']}_" if j.get("aviso") else ""
    return (
        f"*🏟️ JOGO #{num} – {j['liga']}*\n"
        f"🌍 {j.get('pais','')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ *{j['casa']}* vs *{j['fora']}*\n"
        f"🕐 Hora: *{j.get('hora_jogo','--:--')}*\n\n"
        f"📊 *Probabilidades:*\n"
        f"  🏠 Casa:   {barra(pc)} {pc}%\n"
        f"  🤝 Empate: {barra(pe)} {pe}%\n"
        f"  ✈️ Fora:   {barra(pf)} {pf}%\n\n"
        f"⚽ Forma Casa: `{j.get('forma_casa','—')}`\n"
        f"✈️ Forma Fora: `{j.get('forma_fora','—')}`\n\n"
        f"{ec(c)} *Palpite:* {j['palpite_principal']} ({c}%)\n"
        f"🎯 *Resultado previsto:* {j.get('previsao', j.get('previsao_golos','—'))}\n\n"
        f"💰 *Opções de Aposta:*\n{ops}\n\n"
        f"🔍 *Análise:*\n_{j.get('analise','—')}_{av}"
    )

def fmt_ao_vivo(jogos_raw):
    if not jogos_raw:
        return "🔴 Nenhum jogo ao vivo neste momento.\n\nUsa /jogos para ver os jogos do dia."
    linhas = ["🔴 *JOGOS AO VIVO AGORA*\n━━━━━━━━━━━━━━━━━━━━━"]
    for j in jogos_raw[:15]:
        ht = j.get("home_team", j.get("homeTeam","?"))
        at = j.get("away_team", j.get("awayTeam","?"))
        hs = j.get("home_score", j.get("homeScore","?"))
        as_ = j.get("away_score", j.get("awayScore","?"))
        min_ = j.get("minute", j.get("elapsed","?"))
        liga = j.get("league", j.get("competition",""))
        linhas.append(f"🔴 *{ht} {hs} - {as_} {at}*\n   ⏱️ {min_}'  |  🏆 {liga}\n")
    return "\n".join(linhas)

# ── MENUS ────────────────────────────────────────────────
def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 Ao Vivo Agora",    callback_data="ao_vivo"),
         InlineKeyboardButton("📅 Jogos de Hoje",    callback_data="hoje")],
        [InlineKeyboardButton("⚽ Futebol",           callback_data="m:fut"),
         InlineKeyboardButton("🏀 Basquetebol",      callback_data="m:nba")],
        [InlineKeyboardButton("🌍 Mundial 2026",      callback_data="m:mundial"),
         InlineKeyboardButton("🏆 Ligas Principais", callback_data="m:ligas")],
        [InlineKeyboardButton("🎯 Palpites IA",       callback_data="m:palpites"),
         InlineKeyboardButton("📊 Previsões",         callback_data="m:previsoes")],
        [InlineKeyboardButton("💬 Falar com IA",      callback_data="m:chat"),
         InlineKeyboardButton("❓ Ajuda",             callback_data="m:ajuda")],
    ])

def menu_futebol():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Champions League",  callback_data="f:champions"),
         InlineKeyboardButton("🇬🇧 Premier League",   callback_data="f:premier")],
        [InlineKeyboardButton("🇪🇸 La Liga",           callback_data="f:laliga"),
         InlineKeyboardButton("🇮🇹 Serie A",           callback_data="f:seriea")],
        [InlineKeyboardButton("🇩🇪 Bundesliga",        callback_data="f:bundesliga"),
         InlineKeyboardButton("🇫🇷 Ligue 1",          callback_data="f:ligue1")],
        [InlineKeyboardButton("🇧🇪 Bélgica",           callback_data="f:belgium"),
         InlineKeyboardButton("🇳🇱 Eredivisie",        callback_data="f:eredivisie")],
        [InlineKeyboardButton("🇩🇿 Argélia",           callback_data="f:algeria"),
         InlineKeyboardButton("🇧🇬 Bulgária",          callback_data="f:bulgaria")],
        [InlineKeyboardButton("🇵🇹 Portugal",          callback_data="f:portugal"),
         InlineKeyboardButton("🇲🇿 África/CAF",        callback_data="f:africa")],
        [InlineKeyboardButton("🇺🇸 MLS",               callback_data="f:mls"),
         InlineKeyboardButton("🌐 Todas",              callback_data="f:all")],
        [InlineKeyboardButton("◀️ Voltar",             callback_data="inicio")],
    ])

def menu_ligas():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 Mundial 2026",      callback_data="m:mundial"),
         InlineKeyboardButton("🏆 Champions",         callback_data="f:champions")],
        [InlineKeyboardButton("🇬🇧 Premier League",   callback_data="f:premier"),
         InlineKeyboardButton("🇪🇸 La Liga",          callback_data="f:laliga")],
        [InlineKeyboardButton("🇮🇹 Serie A",          callback_data="f:seriea"),
         InlineKeyboardButton("🇩🇪 Bundesliga",       callback_data="f:bundesliga")],
        [InlineKeyboardButton("🏀 NBA",               callback_data="m:nba"),
         InlineKeyboardButton("🌐 Todas as Ligas",    callback_data="f:all")],
        [InlineKeyboardButton("◀️ Voltar",            callback_data="inicio")],
    ])

def menu_jogos(total):
    linha, botoes = [], []
    for i in range(1, total+1):
        linha.append(InlineKeyboardButton(f"#{i}", callback_data=f"j:{i-1}"))
        if len(linha) == 5:
            botoes.append(linha)
            linha = []
    if linha:
        botoes.append(linha)
    botoes.append([
        InlineKeyboardButton("🔄 Actualizar", callback_data="reload"),
        InlineKeyboardButton("🔴 Ao Vivo",    callback_data="ao_vivo"),
        InlineKeyboardButton("🏠 Menu",       callback_data="inicio"),
    ])
    return InlineKeyboardMarkup(botoes)

def menu_voltar():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀️ Voltar à Lista", callback_data="voltar"),
        InlineKeyboardButton("🏠 Menu",           callback_data="inicio"),
    ]])

LIGAS_MAP = {
    "champions":  "UEFA Champions League",
    "premier":    "Premier League Inglaterra",
    "laliga":     "La Liga Espanha",
    "seriea":     "Serie A Itália",
    "bundesliga": "Bundesliga Alemanha",
    "ligue1":     "Ligue 1 França",
    "belgium":    "Pro League Bélgica",
    "eredivisie": "Eredivisie Países Baixos",
    "algeria":    "Ligue 1 Argélia",
    "bulgaria":   "Parva Liga Bulgária",
    "portugal":   "Liga Portugal",
    "africa":     "Ligas Africanas CAF",
    "mls":        "MLS Estados Unidos",
    "all":        "Todas as Ligas Mundiais",
}

# ── HANDLERS COMANDOS ─────────────────────────────────────
async def cmd_start(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["chat"] = False
    await u.message.reply_text(
        f"👋 *Bem-vindo ao ScoutAI v3!* ⚽🏀🤖\n\n"
        f"📅 _{data_hoje()}_\n"
        f"🕐 _{hora_agora()}_\n\n"
        f"🌍 *Mundial 2026 começa a 11 de Junho!*\n\n"
        f"Tenho acesso a:\n"
        f"• 📡 Dados reais de futebol\n"
        f"• 🔴 Jogos ao vivo\n"
        f"• 🤖 Análise com IA\n"
        f"• 💬 Chat desportivo\n\n"
        f"👇 *Escolhe uma opção:*",
        parse_mode="Markdown",
        reply_markup=menu_principal()
    )

async def cmd_ajuda(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(u, ctx)

async def cmd_jogos(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await u.message.reply_text("⏳ A buscar jogos reais de hoje...")
    await carregar_jogos_hoje(msg, ctx)

async def cmd_vivo(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await u.message.reply_text("🔴 A buscar jogos ao vivo...")
    await carregar_ao_vivo(msg, ctx)

async def cmd_chat(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["chat"] = True
    ctx.user_data["hist"] = []
    await u.message.reply_text(
        f"💬 *Modo Chat IA activado!*\n\n"
        f"📅 {data_hoje()}\n\n"
        f"Podes perguntar sobre:\n"
        f"• ⚽ Jogos e equipas do dia\n"
        f"• 🌍 Mundial 2026\n"
        f"• 💰 Conselhos de apostas\n"
        f"• 📊 Estatísticas e análises\n"
        f"• 🏀 NBA e basquetebol\n\n"
        f"✏️ *Escreve a tua pergunta!*\n"
        f"_Para sair usa /start_",
        parse_mode="Markdown"
    )

# ── FUNÇÕES DE CARREGAMENTO ───────────────────────────────
async def carregar_jogos_hoje(msg, ctx):
    try:
        dados_api = buscar_jogos_hoje()
        if dados_api and RAPIDAPI_KEY:
            jogos_raw = (dados_api.get("matches") or
                        dados_api.get("fixtures") or
                        dados_api.get("data") or
                        dados_api.get("events") or [])
            if jogos_raw:
                jogos = []
                for j in jogos_raw[:15]:
                    ht = j.get("home_team", j.get("homeTeam", j.get("home",{}).get("name","?")))
                    at = j.get("away_team", j.get("awayTeam", j.get("away",{}).get("name","?")))
                    liga = j.get("league", j.get("competition", j.get("tournament","Liga")))
                    hora = j.get("time", j.get("kickoff", j.get("date","--:--")))
                    if isinstance(hora, str) and "T" in hora:
                        hora = hora.split("T")[1][:5]
                    jogos.append({
                        "liga": str(liga)[:30] if isinstance(liga, str) else str(liga.get("name","Liga"))[:30],
                        "pais": j.get("country", j.get("area","Internacional")),
                        "hora_jogo": hora[:5] if len(str(hora)) >= 5 else str(hora),
                        "casa": str(ht)[:25] if isinstance(ht, str) else str(ht.get("name","?"))[:25],
                        "fora": str(at)[:25] if isinstance(at, str) else str(at.get("name","?"))[:25],
                        "palpite_principal": "Análise IA disponível",
                        "prob_casa": 45, "prob_empate": 28, "prob_fora": 27,
                        "confianca": 70,
                        "previsao": "Ver análise",
                        "forma_casa": "—", "forma_fora": "—",
                        "opcoes": [
                            {"tipo":"Dupla Chance 1X","odd":"1.40","conf":75},
                            {"tipo":"Ambas Marcam","odd":"1.85","conf":65},
                            {"tipo":"Acima 2.5","odd":"1.80","conf":62}
                        ],
                        "analise": f"Jogo real de hoje. Clica para análise IA completa de {str(ht)[:20]} vs {str(at)[:20]}.",
                        "aviso": None
                    })
                dados = {
                    "data": data_hoje(),
                    "hora": hora_agora(),
                    "resumo": f"🌐 {len(jogos)} jogos reais encontrados para hoje! Clica em cada jogo para análise IA.",
                    "jogos": jogos
                }
                ctx.user_data["jogos"] = dados
                ctx.user_data["fonte"] = "real"
                await msg.edit_text(fmt_lista(dados, "real"), parse_mode="Markdown",
                                   reply_markup=menu_jogos(len(jogos)))
                return
        raise Exception("Sem dados reais — usando IA")
    except Exception as e:
        log.info(f"API indisponível, usando IA: {e}")
        try:
            dados = ia_palpites_simulados("Mundial 2026, Premier League, La Liga, Serie A, Champions, MLS, Bélgica, Argélia")
            ctx.user_data["jogos"] = dados
            ctx.user_data["fonte"] = "ia"
            await msg.edit_text(fmt_lista(dados, "ia"), parse_mode="Markdown",
                               reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e2:
            log.error(f"Erro IA: {e2}")
            await msg.edit_text("❌ Erro ao carregar jogos. Tenta /jogos novamente.")

async def carregar_ao_vivo(msg, ctx):
    try:
        dados = buscar_ao_vivo()
        jogos_raw = None
        if dados:
            jogos_raw = (dados.get("matches") or dados.get("fixtures") or
                        dados.get("data") or dados.get("events") or [])
        texto = fmt_ao_vivo(jogos_raw if jogos_raw else None)
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Actualizar", callback_data="ao_vivo"),
            InlineKeyboardButton("📅 Jogos Hoje", callback_data="hoje"),
            InlineKeyboardButton("🏠 Menu",       callback_data="inicio"),
        ]])
        await msg.edit_text(texto, parse_mode="Markdown", reply_markup=teclado)
    except Exception as e:
        log.error(f"Erro ao vivo: {e}")
        await msg.edit_text("❌ Erro ao buscar jogos ao vivo. Tenta novamente.")

# ── HANDLER TEXTO (CHAT) ──────────────────────────────────
async def handler_texto(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("chat"):
        await u.message.reply_text(
            "💬 Usa /chat para falar comigo ou escolhe uma opção:",
            reply_markup=menu_principal()
        )
        return
    hist = ctx.user_data.get("hist", [])
    q = u.message.text
    await u.message.reply_chat_action("typing")
    try:
        resp = ia_chat(q, hist)
        hist.append({"role":"user","content":q})
        hist.append({"role":"assistant","content":resp})
        ctx.user_data["hist"] = hist[-12:]
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("📅 Jogos Hoje",  callback_data="hoje"),
            InlineKeyboardButton("🔴 Ao Vivo",     callback_data="ao_vivo"),
            InlineKeyboardButton("🏠 Menu",        callback_data="inicio"),
        ]])
        await u.message.reply_text(resp, reply_markup=teclado)
    except Exception as e:
        log.error(f"Erro chat: {e}")
        await u.message.reply_text("❌ Erro. Tenta novamente.")

# ── CALLBACKS ─────────────────────────────────────────────
async def callback(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    d = q.data

    if d == "inicio":
        ctx.user_data["chat"] = False
        await q.message.reply_text(
            f"🏠 *Menu Principal*\n📅 _{data_hoje()}_  🕐 _{hora_agora()}_\n\n👇 Escolhe:",
            parse_mode="Markdown", reply_markup=menu_principal()
        )

    elif d == "hoje":
        msg = await q.message.reply_text("⏳ A buscar jogos de hoje...")
        await carregar_jogos_hoje(msg, ctx)

    elif d == "ao_vivo":
        msg = await q.message.reply_text("🔴 A buscar jogos ao vivo...")
        await carregar_ao_vivo(msg, ctx)

    elif d == "reload":
        msg = await q.message.reply_text("🔄 A actualizar jogos...")
        await carregar_jogos_hoje(msg, ctx)

    elif d == "m:fut":
        await q.message.reply_text("⚽ *Ligas de Futebol:*",
                                   parse_mode="Markdown", reply_markup=menu_futebol())

    elif d == "m:ligas":
        await q.message.reply_text("🏆 *Ligas Principais:*",
                                   parse_mode="Markdown", reply_markup=menu_ligas())

    elif d == "m:nba":
        msg = await q.message.reply_text("🏀 A carregar NBA...")
        try:
            dados = ia_palpites_simulados("NBA Basquetebol", "basquetebol", "8 a 10")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(fmt_lista(dados), parse_mode="Markdown",
                               reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif d == "m:mundial":
        msg = await q.message.reply_text("🌍 A carregar Mundial 2026...")
        try:
            dados = ia_palpites_simulados("Copa do Mundo FIFA 2026 — EUA, Canadá, México. Fase de grupos", "futebol", "8 a 12")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(fmt_lista(dados), parse_mode="Markdown",
                               reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif d == "m:palpites":
        msg = await q.message.reply_text("🎯 A gerar palpites do dia...")
        await carregar_jogos_hoje(msg, ctx)

    elif d == "m:previsoes":
        msg = await q.message.reply_text("📊 A gerar previsões especiais...")
        try:
            dados = ia_palpites_simulados("Melhores jogos do dia — Champions, Premier League, NBA, Mundial 2026")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(fmt_lista(dados), parse_mode="Markdown",
                               reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif d == "m:chat":
        ctx.user_data["chat"] = True
        ctx.user_data["hist"] = []
        await q.message.reply_text(
            f"💬 *Chat IA activado!*\n\n"
            f"📅 {data_hoje()}\n\n"
            f"Pergunta-me sobre jogos, equipas, apostas ou o Mundial 2026!\n"
            f"_Para sair usa /start_",
            parse_mode="Markdown"
        )

    elif d == "m:ajuda":
        await q.message.reply_text(
            "❓ *Ajuda – ScoutAI v3*\n\n"
            "📌 *Comandos:*\n"
            "/start – Menu principal\n"
            "/jogos – Jogos reais de hoje\n"
            "/vivo – Jogos ao vivo agora\n"
            "/chat – Falar com IA\n"
            "/ajuda – Esta mensagem\n\n"
            "🟢 Alta confiança (80%+)\n"
            "🟡 Boa confiança (65-79%)\n"
            "🟠 Média confiança (50-64%)\n"
            "🔴 Baixa confiança (<50%)\n\n"
            "⚠️ _Aposte com responsabilidade._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Menu", callback_data="inicio")
            ]])
        )

    elif d.startswith("f:"):
        liga_nome = LIGAS_MAP.get(d.split(":")[1], "Futebol")
        msg = await q.message.reply_text(f"⏳ A carregar {liga_nome}...")
        try:
            dados = ia_palpites_simulados(liga_nome)
            ctx.user_data["jogos"] = dados
            await msg.edit_text(fmt_lista(dados), parse_mode="Markdown",
                               reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif d.startswith("j:"):
        idx = int(d.split(":")[1])
        dados = ctx.user_data.get("jogos")
        if not dados or idx >= len(dados["jogos"]):
            await q.message.reply_text("⚠️ Usa /jogos para recarregar.")
            return
        jogo = dados["jogos"][idx]
        if ctx.user_data.get("fonte") == "real":
            try:
                analise = ia_analisar_jogo(jogo["casa"], jogo["fora"], jogo["liga"])
                jogo.update(analise)
                dados["jogos"][idx] = jogo
            except Exception as e:
                log.error(f"Erro análise IA: {e}")
        await q.message.reply_text(fmt_jogo(jogo, idx+1),
                                   parse_mode="Markdown", reply_markup=menu_voltar())

    elif d == "voltar":
        dados = ctx.user_data.get("jogos")
        if dados:
            fonte = ctx.user_data.get("fonte","ia")
            await q.message.reply_text(fmt_lista(dados, fonte), parse_mode="Markdown",
                                       reply_markup=menu_jogos(len(dados["jogos"])))

# ── MAIN ──────────────────────────────────────────────────
def main():
    log.info("ScoutAI v3 a iniciar...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("ajuda",  cmd_ajuda))
    app.add_handler(CommandHandler("jogos",  cmd_jogos))
    app.add_handler(CommandHandler("vivo",   cmd_vivo))
    app.add_handler(CommandHandler("chat",   cmd_chat))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler_texto))
    log.info("Bot v3 a correr!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
