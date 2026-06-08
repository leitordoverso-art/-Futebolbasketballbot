#!/usr/bin/env python3
"""ScoutAI Bot v2 – Palpites Desportivos Avançados"""

import os, json, logging
from datetime import datetime
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ── CONFIGURAÇÃO ────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_TOKEN e GROQ_API_KEY são obrigatórios!")

groq = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
DIAS_PT = ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira",
           "Sexta-feira","Sábado","Domingo"]

def data_pt():
    n = datetime.now()
    dia_semana = DIAS_PT[n.weekday()]
    return f"{dia_semana}, {n.day:02d} de {MESES[n.month-1]} de {n.year}"

def hora_atual():
    return datetime.now().strftime("%H:%M")

# ── MENUS ────────────────────────────────────────────────────
def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Futebol",         callback_data="m:futebol"),
         InlineKeyboardButton("🏀 Basquetebol",     callback_data="m:basket")],
        [InlineKeyboardButton("🏆 Ligas Principais",callback_data="m:ligas"),
         InlineKeyboardButton("🌍 Mundial",         callback_data="m:mundial")],
        [InlineKeyboardButton("🌐 Todos os Países", callback_data="m:todos"),
         InlineKeyboardButton("📊 Previsões IA",   callback_data="m:previsoes")],
        [InlineKeyboardButton("🔔 Notificações",   callback_data="m:notif"),
         InlineKeyboardButton("💬 Falar com IA",   callback_data="m:chat")],
        [InlineKeyboardButton("🎯 Palpites do Dia",callback_data="m:palpites")],
    ])

def menu_futebol():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Champions League", callback_data="f:champions"),
         InlineKeyboardButton("🇪🇸 La Liga",          callback_data="f:laliga")],
        [InlineKeyboardButton("🇬🇧 Premier League",   callback_data="f:premier"),
         InlineKeyboardButton("🇮🇹 Serie A",          callback_data="f:seriea")],
        [InlineKeyboardButton("🇩🇪 Bundesliga",       callback_data="f:bundesliga"),
         InlineKeyboardButton("🇫🇷 Ligue 1",         callback_data="f:ligue1")],
        [InlineKeyboardButton("🇧🇪 Bélgica",          callback_data="f:belgium"),
         InlineKeyboardButton("🇳🇱 Eredivisie",       callback_data="f:eredivisie")],
        [InlineKeyboardButton("🇩🇿 Argélia",          callback_data="f:algeria"),
         InlineKeyboardButton("🇧🇬 Bulgária",         callback_data="f:bulgaria")],
        [InlineKeyboardButton("🇵🇹 Portugal",         callback_data="f:portugal"),
         InlineKeyboardButton("🌍 África (CAF)",      callback_data="f:africa")],
        [InlineKeyboardButton("🇺🇸 MLS",              callback_data="f:mls"),
         InlineKeyboardButton("🌐 Todas as Ligas",   callback_data="f:all")],
        [InlineKeyboardButton("◀️ Voltar",            callback_data="m:inicio")],
    ])

def menu_basket():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏀 NBA – Hoje",        callback_data="b:nba"),
         InlineKeyboardButton("🏆 NBA Playoffs",     callback_data="b:playoffs")],
        [InlineKeyboardButton("🌍 EuroLeague",        callback_data="b:euro"),
         InlineKeyboardButton("🌐 Todas as Ligas",   callback_data="b:all")],
        [InlineKeyboardButton("◀️ Voltar",            callback_data="m:inicio")],
    ])

def menu_jogos(total):
    linha, botoes = [], []
    for i in range(1, total+1):
        linha.append(InlineKeyboardButton(f"#{i}", callback_data=f"j:{i-1}"))
        if len(linha) == 5: botoes.append(linha); linha = []
    if linha: botoes.append(linha)
    botoes.append([
        InlineKeyboardButton("🔄 Recarregar", callback_data="reload"),
        InlineKeyboardButton("🏠 Menu",       callback_data="m:inicio"),
    ])
    return InlineKeyboardMarkup(botoes)

# ── IA: GERAR PALPITES ───────────────────────────────────────
def ia_palpites(liga: str, desporto: str = "futebol", quantidade: str = "10 a 13") -> dict:
    hoje = data_pt()
    prompt = f"""Hoje é {hoje}. És um analista desportivo especializado em apostas desportivas.
Gera {quantidade} jogos reais e típicos de {desporto} para hoje na(s) liga(s): {liga}.

Responde APENAS com JSON válido. Sem markdown. Sem explicações. Formato exacto:
{{
  "data": "{hoje}",
  "hora_geracao": "{hora_atual()}",
  "liga_principal": "{liga}",
  "resumo": "Resumo do dia em 2 frases em Português.",
  "jogos": [
    {{
      "numero": 1,
      "liga": "Nome da Liga",
      "pais": "País/Região",
      "hora_jogo": "HH:MM",
      "casa": "Nome Equipa Casa",
      "fora": "Nome Equipa Fora",
      "palpite_principal": "Vitória Casa | Empate | Vitória Fora | Ambas Marcam | Acima 2.5",
      "probabilidade_casa": 65,
      "probabilidade_empate": 20,
      "probabilidade_fora": 15,
      "confianca": 78,
      "opcoes_aposta": [
        {{"tipo": "Dupla Chance 1X",     "odd": "1.35", "confianca": 85}},
        {{"tipo": "Ambas Marcam – Sim",  "odd": "1.80", "confianca": 70}},
        {{"tipo": "Acima 2.5 Golos",    "odd": "1.75", "confianca": 72}},
        {{"tipo": "Vitória Casa",        "odd": "2.10", "confianca": 65}},
        {{"tipo": "Abaixo 3.5 Golos",   "odd": "1.45", "confianca": 80}}
      ],
      "forma_casa": "V V E V V",
      "forma_fora": "E D V E D",
      "analise": "Análise detalhada de 3 frases sobre forma, confrontos directos e motivação.",
      "previsao_golos": "2-1",
      "aviso": null
    }}
  ]
}}
Odds realistas 1.15-5.00. Probabilidades somam 100%. Texto em Português de Moçambique."""

    log.info(f"IA palpites: {liga}")
    r = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7, max_tokens=4000
    )
    raw = r.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)

def ia_chat(pergunta: str, historico: list) -> str:
    msgs = [{"role":"system","content":
        "És o ScoutAI, um assistente desportivo especializado em futebol, basquetebol e apostas. "
        "Respondes sempre em Português de Moçambique. És amigável, directo e muito conhecedor de desporto. "
        "Podes dar conselhos sobre apostas, análise de jogos, estatísticas e previsões."}]
    msgs += historico[-6:]
    msgs.append({"role":"user","content":pergunta})
    r = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=msgs, temperature=0.8, max_tokens=500
    )
    return r.choices[0].message.content.strip()

# ── FORMATAÇÃO ───────────────────────────────────────────────
def emoji_conf(v):
    if v >= 80: return "🟢"
    if v >= 65: return "🟡"
    if v >= 50: return "🟠"
    return "🔴"

def barra_prob(p, total=10):
    cheio = round(p / total)
    return "█" * cheio + "░" * (total - cheio)

def formatar_lista(dados):
    linhas = [
        "⚽🏀 *SCOUTAI – PALPITES DO DIA*",
        f"📅 _{dados.get('data','')}_",
        f"🕐 Gerado às {dados.get('hora_geracao','')}",
        f"🏆 _{dados.get('liga_principal','')}_\n",
        f"📊 {dados.get('resumo','')}\n",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    for j in dados.get("jogos",[]):
        ec = emoji_conf(j["confianca"])
        linhas.append(
            f"{ec} *{j['casa']} vs {j['fora']}*\n"
            f"   🕐 {j['hora_jogo']}  |  🏆 {j['liga']} ({j['pais']})\n"
            f"   🎯 *{j['palpite_principal']}*  — Confiança: {j['confianca']}%\n"
            f"   📈 Casa {j['probabilidade_casa']}% | Empate {j['probabilidade_empate']}% | Fora {j['probabilidade_fora']}%\n"
        )
    linhas += [
        "━━━━━━━━━━━━━━━━━━━━━",
        "👆 Clica num número para análise completa",
        "⚠️ _Aposte com responsabilidade._"
    ]
    return "\n".join(linhas)

def formatar_jogo(j, num):
    ec = emoji_conf(j["confianca"])
    opcoes = "\n".join(
        f"   {emoji_conf(o['confianca'])} {o['tipo']} → odd *{o['odd']}* ({o['confianca']}%)"
        for o in j.get("opcoes_aposta",[])
    )
    pc = j['probabilidade_casa']
    pe = j['probabilidade_empate']
    pf = j['probabilidade_fora']
    aviso = f"\n⚠️ _{j['aviso']}_" if j.get("aviso") else ""
    return (
        f"*🏟️ JOGO #{num} – {j['liga']}*\n"
        f"🌍 {j['pais']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ *{j['casa']}* vs *{j['fora']}*\n"
        f"🕐 Hora: *{j['hora_jogo']}*\n\n"
        f"📊 *Probabilidades:*\n"
        f"  🏠 Casa:  {barra_prob(pc)} {pc}%\n"
        f"  🤝 Empate: {barra_prob(pe)} {pe}%\n"
        f"  ✈️ Fora:  {barra_prob(pf)} {pf}%\n\n"
        f"⚽ Forma Casa: `{j.get('forma_casa','—')}`\n"
        f"✈️ Forma Fora: `{j.get('forma_fora','—')}`\n\n"
        f"{ec} *Palpite Principal:* {j['palpite_principal']} ({j['confianca']}%)\n"
        f"🎯 *Resultado Previsto:* {j.get('previsao_golos','—')}\n\n"
        f"💰 *Opções de Aposta:*\n{opcoes}\n\n"
        f"🔍 *Análise:*\n_{j['analise']}_{aviso}"
    )

# ── HANDLERS ─────────────────────────────────────────────────
async def cmd_start(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["modo_chat"] = False
    await u.message.reply_text(
        f"👋 *Bem-vindo ao ScoutAI!* 🤖⚽🏀\n\n"
        f"📅 _{data_pt()}_\n\n"
        f"Sou o teu assistente de palpites desportivos com Inteligência Artificial.\n"
        f"Analiso jogos, gero previsões e palpites com odds para futebol e basquetebol.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *Escolhe uma opção:*",
        parse_mode="Markdown",
        reply_markup=menu_principal()
    )

async def cmd_ajuda(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(u, ctx)

async def cmd_jogos(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await u.message.reply_text("⏳ A gerar palpites do dia com IA...")
    try:
        dados = ia_palpites("Mundial, Bélgica, Países Baixos, Bulgária, Argélia, MLS, UEFA, África")
        ctx.user_data["jogos"] = dados
        await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                            reply_markup=menu_jogos(len(dados["jogos"])))
    except Exception as e:
        log.error(f"Erro jogos: {e}")
        await msg.edit_text("❌ Erro ao gerar palpites. Tenta /jogos novamente.")

async def cmd_futebol(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("⚽ *Escolhe a Liga de Futebol:*",
                               parse_mode="Markdown", reply_markup=menu_futebol())

async def cmd_basketball(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await u.message.reply_text("🏀 *Escolhe a Liga de Basquetebol:*",
                               parse_mode="Markdown", reply_markup=menu_basket())

async def cmd_chat(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["modo_chat"] = True
    ctx.user_data["historico"] = []
    await u.message.reply_text(
        "💬 *Modo Chat activado!*\n\n"
        "Podes falar comigo sobre:\n"
        "• Análise de jogos e equipas\n"
        "• Conselhos de apostas\n"
        "• Estatísticas e resultados\n"
        "• Qualquer dúvida desportiva\n\n"
        "Escreve a tua pergunta! Para sair usa /start",
        parse_mode="Markdown"
    )

# ── HANDLER DE MENSAGENS DE TEXTO (chat IA) ──────────────────
async def handler_texto(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("modo_chat"):
        await u.message.reply_text(
            "💬 Para falar comigo clica em *Falar com IA* no menu ou usa /chat",
            parse_mode="Markdown", reply_markup=menu_principal()
        )
        return
    hist = ctx.user_data.get("historico", [])
    pergunta = u.message.text
    await u.message.reply_chat_action("typing")
    try:
        resposta = ia_chat(pergunta, hist)
        hist.append({"role":"user","content":pergunta})
        hist.append({"role":"assistant","content":resposta})
        ctx.user_data["historico"] = hist[-10:]
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menu Principal", callback_data="m:inicio"),
            InlineKeyboardButton("🎯 Ver Palpites",   callback_data="m:palpites"),
        ]])
        await u.message.reply_text(resposta, reply_markup=teclado)
    except Exception as e:
        log.error(f"Erro chat: {e}")
        await u.message.reply_text("❌ Erro. Tenta novamente.")

# ── CALLBACKS ─────────────────────────────────────────────────
LIGAS_MAP = {
    "champions": "UEFA Champions League",
    "laliga":    "La Liga Espanha",
    "premier":   "Premier League Inglaterra",
    "seriea":    "Serie A Itália",
    "bundesliga":"Bundesliga Alemanha",
    "ligue1":    "Ligue 1 França",
    "belgium":   "Pro League Bélgica",
    "eredivisie":"Eredivisie Países Baixos",
    "algeria":   "Ligue 1 Argélia",
    "bulgaria":  "Parva Liga Bulgária",
    "portugal":  "Liga Portugal",
    "africa":    "Ligas Africanas CAF",
    "mls":       "MLS Estados Unidos",
    "all":       "Todas as Ligas de Futebol",
}
BASKET_MAP = {
    "nba":      "NBA",
    "playoffs": "NBA Playoffs",
    "euro":     "EuroLeague",
    "all":      "Todas as Ligas de Basquetebol",
}

async def callback(u: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    d = q.data

    # ── MENU PRINCIPAL ──
    if d == "m:inicio":
        ctx.user_data["modo_chat"] = False
        await q.message.reply_text(
            f"🏠 *Menu Principal*\n📅 _{data_pt()}_\n\n👇 Escolhe uma opção:",
            parse_mode="Markdown", reply_markup=menu_principal()
        )

    elif d == "m:futebol":
        await q.message.reply_text("⚽ *Ligas de Futebol:*",
                                   parse_mode="Markdown", reply_markup=menu_futebol())

    elif d == "m:basket":
        await q.message.reply_text("🏀 *Ligas de Basquetebol:*",
                                   parse_mode="Markdown", reply_markup=menu_basket())

    elif d == "m:mundial":
        msg = await q.message.reply_text("⏳ A carregar jogos do Mundial...")
        try:
            dados = ia_palpites("Copa do Mundo FIFA, eliminatórias mundiais, jogos internacionais")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif d == "m:todos":
        msg = await q.message.reply_text("⏳ A carregar jogos de todos os países...")
        try:
            dados = ia_palpites("Todas as ligas mundiais — Europa, África, Américas, Ásia", quantidade="15 a 18")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif d == "m:palpites":
        msg = await q.message.reply_text("⏳ A gerar palpites do dia...")
        try:
            dados = ia_palpites("Mundial, Bélgica, Países Baixos, Bulgária, Argélia, MLS, UEFA, África")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif d == "m:previsoes":
        msg = await q.message.reply_text("⏳ A gerar previsões especiais da IA...")
        try:
            dados = ia_palpites("Jogos mais importantes do dia — Champions, Premier, NBA, Mundial")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif d == "m:notif":
        await q.message.reply_text(
            "🔔 *Notificações em Tempo Real*\n\n"
            "Para activar notificações automáticas:\n\n"
            "⏰ O bot envia palpites todos os dias às *09:00*\n"
            "📊 Actualizações de jogos importantes\n"
            "🔴 Alertas de resultados ao intervalo\n\n"
            "➡️ Para receber notificações, adiciona este bot ao teu canal ou grupo Telegram "
            "e o administrador configura o envio automático.\n\n"
            "📌 Usa /jogos para ver os palpites agora!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎯 Ver Palpites Agora", callback_data="m:palpites"),
                InlineKeyboardButton("🏠 Menu",              callback_data="m:inicio"),
            ]])
        )

    elif d == "m:chat":
        ctx.user_data["modo_chat"] = True
        ctx.user_data["historico"] = []
        await q.message.reply_text(
            "💬 *Modo Chat IA activado!*\n\n"
            "Podes perguntar-me sobre:\n"
            "• 📊 Análise de equipas e jogadores\n"
            "• 💰 Conselhos de apostas\n"
            "• 📈 Estatísticas e histórico\n"
            "• 🏆 Notícias desportivas\n"
            "• 🎯 Previsões especiais\n\n"
            "✏️ *Escreve a tua pergunta agora!*\n"
            "_Para voltar ao menu usa /start_",
            parse_mode="Markdown"
        )

    # ── LIGAS FUTEBOL ──
    elif d.startswith("f:"):
        liga_key = d.split(":")[1]
        liga_nome = LIGAS_MAP.get(liga_key, "Futebol")
        msg = await q.message.reply_text(f"⏳ A carregar {liga_nome}...")
        try:
            dados = ia_palpites(liga_nome)
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    # ── LIGAS BASKET ──
    elif d.startswith("b:"):
        liga_key = d.split(":")[1]
        liga_nome = BASKET_MAP.get(liga_key, "NBA")
        msg = await q.message.reply_text(f"⏳ A carregar {liga_nome}...")
        try:
            dados = ia_palpites(liga_nome, desporto="basquetebol", quantidade="8 a 10")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("❌ Erro. Tenta novamente.")

    # ── JOGO INDIVIDUAL ──
    elif d.startswith("j:"):
        idx = int(d.split(":")[1])
        dados = ctx.user_data.get("jogos")
        if not dados or idx >= len(dados["jogos"]):
            await q.message.reply_text("⚠️ Usa /jogos para recarregar.")
            return
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Voltar à Lista", callback_data="voltar"),
            InlineKeyboardButton("🏠 Menu",           callback_data="m:inicio"),
        ]])
        await q.message.reply_text(
            formatar_jogo(dados["jogos"][idx], idx+1),
            parse_mode="Markdown", reply_markup=teclado
        )

    elif d == "voltar":
        dados = ctx.user_data.get("jogos")
        if dados:
            await q.message.reply_text(formatar_lista(dados), parse_mode="Markdown",
                       
