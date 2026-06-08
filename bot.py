#!/usr/bin/env python3
"""
ScoutAI Bot – Palpites Desportivos com IA (Groq)
"""

import os
import json
import logging
from datetime import datetime
from groq import Groq

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ─────────────────────────────────────────────
# CONFIGURAÇÃO — tokens vêm do Railway (Variables)
# ─────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ TELEGRAM_TOKEN e GROQ_API_KEY têm de estar definidos nas Variables do Railway!")

client_groq = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# LIGAS DISPONÍVEIS
# ─────────────────────────────────────────────
LIGAS = {
    "all":         ("🌐 Todas as Ligas",              "Mundial, Bélgica, Países Baixos, Bulgária, Argélia, EUA, UEFA, África e outras"),
    "world":       ("🌍 Mundial / Internacionais",    "Jogos internacionais e Copas do Mundo"),
    "belgium":     ("🇧🇪 Bélgica – Pro League",      "Primeira Liga da Bélgica"),
    "netherlands": ("🇳🇱 Países Baixos – Eredivisie","Eredivisie da Holanda"),
    "bulgaria":    ("🇧🇬 Bulgária – Parva Liga",     "Primeira Liga da Bulgária"),
    "algeria":     ("🇩🇿 Argélia – Ligue 1",         "Ligue Professionnelle 1 da Argélia"),
    "usa_soccer":  ("🇺🇸 EUA – MLS",                 "Major League Soccer dos EUA"),
    "nba":         ("🏀 NBA – Basquetebol",           "National Basketball Association"),
    "euro":        ("🏆 UEFA / Champions",            "Champions League, Europa League, Conference League"),
    "africa":      ("🌍 África (CAF)",                "Ligas africanas e competições CAF"),
    "other":       ("🌐 Outras Ligas",                "Outras ligas europeias e mundiais"),
}


# ─────────────────────────────────────────────
# GERAÇÃO DE PALPITES COM IA
# ─────────────────────────────────────────────
def gerar_palpites(liga_id: str = "all", desporto: str = "all") -> dict:
    hoje = datetime.now().strftime("%A, %d de %B de %Y")
    _, liga_desc = LIGAS.get(liga_id, LIGAS["all"])

    if desporto == "basketball":
        desc_desporto = "basquetebol (NBA)"
        num_jogos = "8 a 10"
    elif desporto == "football":
        desc_desporto = "futebol"
        num_jogos = "10 a 12"
    else:
        desc_desporto = "futebol e basquetebol"
        num_jogos = "12 a 15"

    prompt = f"""Hoje é {hoje}. És um analista desportivo especializado em apostas.
Gera {num_jogos} jogos de {desc_desporto} que tipicamente ocorrem hoje nas ligas: {liga_desc}.

Responde APENAS com JSON válido, sem texto, sem markdown. Formato:
{{
  "data": "{hoje}",
  "resumo": "Resumo do dia em 2 frases.",
  "jogos": [
    {{
      "liga": "nome da liga",
      "hora": "HH:MM",
      "casa": "Equipa Casa",
      "fora": "Equipa Fora",
      "palpite_principal": "Vitória Casa",
      "confianca": 75,
      "opcoes": [
        {{"tipo": "Dupla Chance 1X",    "odd": "1.35"}},
        {{"tipo": "Ambas Marcam – Sim", "odd": "1.80"}},
        {{"tipo": "Acima 2.5 Golos",   "odd": "1.75"}},
        {{"tipo": "Vitória Casa",       "odd": "2.10"}}
      ],
      "analise": "Análise de 2 frases sobre forma e confrontos.",
      "aviso": null
    }}
  ]
}}
Odds entre 1.20 e 4.50. Confiança entre 45 e 92. Texto em Português."""

    log.info(f"Gerando palpites — liga={liga_id} desporto={desporto}")
    resposta = client_groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )
    raw = resposta.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ─────────────────────────────────────────────
# FORMATAÇÃO
# ─────────────────────────────────────────────
def emoji_conf(v: int) -> str:
    if v >= 80: return "🟢"
    if v >= 65: return "🟡"
    if v >= 50: return "🟠"
    return "🔴"

def formatar_resumo(dados: dict) -> str:
    linhas = [
        "⚽🏀 *SCOUTAI – PALPITES DO DIA*",
        f"📅 _{dados.get('data', '')}_\n",
        f"📊 {dados.get('resumo', '')}\n",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    for j in dados.get("jogos", []):
        ec = emoji_conf(j["confianca"])
        linhas.append(
            f"{ec} *{j['casa']} vs {j['fora']}*\n"
            f"   🕐 {j['hora']}  |  🏆 {j['liga']}\n"
            f"   🎯 *{j['palpite_principal']}*  ({j['confianca']}%)\n"
        )
    linhas += [
        "━━━━━━━━━━━━━━━━━━━━━",
        "📌 Usa /detalhes para análise completa.",
        "⚠️ _Aposte com responsabilidade._"
    ]
    return "\n".join(linhas)

def formatar_jogo(j: dict, numero: int) -> str:
    ec = emoji_conf(j["confianca"])
    opcoes = "\n".join(f"   • {o['tipo']} → odd *{o['odd']}*" for o in j.get("opcoes", []))
    aviso = f"\n⚠️ _{j['aviso']}_" if j.get("aviso") else ""
    return (
        f"*JOGO #{numero} – {j['liga']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏟️ *{j['casa']}* vs *{j['fora']}*\n"
        f"🕐 Hora: {j['hora']}\n\n"
        f"{ec} *Palpite Principal:* {j['palpite_principal']}  ({j['confianca']}%)\n\n"
        f"💰 *Opções de Aposta:*\n{opcoes}\n\n"
        f"🔍 *Análise:*\n_{j['analise']}_{aviso}"
    )


# ─────────────────────────────────────────────
# TECLADOS
# ─────────────────────────────────────────────
def teclado_ligas() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(v[0], callback_data=f"liga:{k}")]
        for k, v in LIGAS.items()
    ])

def teclado_desporto() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⚽ Futebol",    callback_data="sport:football"),
        InlineKeyboardButton("🏀 Basketball", callback_data="sport:basketball"),
        InlineKeyboardButton("⚽🏀 Ambos",    callback_data="sport:all"),
    ]])

def teclado_jogos(total: int) -> InlineKeyboardMarkup:
    linha, botoes = [], []
    for i in range(1, total + 1):
        linha.append(InlineKeyboardButton(f"#{i}", callback_data=f"jogo:{i-1}"))
        if len(linha) == 5:
            botoes.append(linha); linha = []
    if linha:
        botoes.append(linha)
    botoes.append([InlineKeyboardButton("🔄 Recarregar", callback_data="reload")])
    return InlineKeyboardMarkup(botoes)


# ─────────────────────────────────────────────
# COMANDOS
# ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bem-vindo ao ScoutAI!*\n\n"
        "Sou o teu assistente de palpites desportivos com IA.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Comandos:*\n"
        "/jogos – Palpites do dia\n"
        "/futebol – Apenas futebol\n"
        "/basketball – Apenas NBA\n"
        "/ligas – Escolher liga\n"
        "/detalhes – Análise completa\n"
        "/ajuda – Ver esta mensagem\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ _Palpites gerados por IA. Aposte com responsabilidade._",
        parse_mode="Markdown"
    )

async def cmd_ajuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, ctx)

async def cmd_jogos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ A analisar jogos com IA...")
    try:
        dados = gerar_palpites("all", "all")
        ctx.user_data["jogos"] = dados
        await msg.edit_text(formatar_resumo(dados), parse_mode="Markdown",
                            reply_markup=teclado_jogos(len(dados["jogos"])))
    except Exception as e:
        log.error(f"Erro jogos: {e}")
        await msg.edit_text("❌ Erro ao gerar palpites. Tenta /jogos novamente.")

async def cmd_futebol(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ A carregar futebol...")
    try:
        dados = gerar_palpites("all", "football")
        ctx.user_data["jogos"] = dados
        await msg.edit_text(formatar_resumo(dados), parse_mode="Markdown",
                            reply_markup=teclado_jogos(len(dados["jogos"])))
    except Exception as e:
        log.error(f"Erro futebol: {e}")
        await msg.edit_text("❌ Erro ao carregar futebol. Tenta /futebol novamente.")

async def cmd_basketball(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ A carregar NBA...")
    try:
        dados = gerar_palpites("nba", "basketball")
        ctx.user_data["jogos"] = dados
        await msg.edit_text(formatar_resumo(dados), parse_mode="Markdown",
                            reply_markup=teclado_jogos(len(dados["jogos"])))
    except Exception as e:
        log.error(f"Erro basketball: {e}")
        await msg.edit_text("❌ Erro ao carregar NBA. Tenta /basketball novamente.")

async def cmd_ligas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏆 *Escolhe a liga:*",
                                    parse_mode="Markdown",
                                    reply_markup=teclado_ligas())

async def cmd_detalhes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = ctx.user_data.get("jogos")
    if not dados:
        await update.message.reply_text("⚠️ Primeiro usa /jogos para carregar os jogos.")
        return
    await update.message.reply_text("📋 *Escolhe o jogo:*",
                                    parse_mode="Markdown",
                                    reply_markup=teclado_jogos(len(dados["jogos"])))


# ─────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("jogo:"):
        idx = int(data.split(":")[1])
        dados = ctx.user_data.get("jogos")
        if not dados or idx >= len(dados["jogos"]):
            await query.message.reply_text("⚠️ Usa /jogos para recarregar.")
            return
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Voltar", callback_data="voltar_lista")
        ]])
        await query.message.reply_text(
            formatar_jogo(dados["jogos"][idx], idx + 1),
            parse_mode="Markdown", reply_markup=teclado
        )

    elif data == "voltar_lista":
        dados = ctx.user_data.get("jogos")
        if dados:
            await query.message.reply_text(
                formatar_resumo(dados), parse_mode="Markdown",
                reply_markup=teclado_jogos(len(dados["jogos"]))
            )

    elif data.startswith("liga:"):
        liga_id = data.split(":")[1]
        ctx.user_data["liga_sel"] = liga_id
        await query.message.reply_text(
            f"✅ Liga: *{LIGAS[liga_id][0]}*\n\nEscolhe o desporto:",
            parse_mode="Markdown", reply_markup=teclado_desporto()
        )

    elif data.startswith("sport:"):
        sport_id = data.split(":")[1]
        liga_id = ctx.user_data.get("liga_sel", "all")
        msg = await query.message.reply_text("⏳ A gerar palpites...")
        try:
            dados = gerar_palpites(liga_id, sport_id)
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_resumo(dados), parse_mode="Markdown",
                                reply_markup=teclado_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(f"Erro sport: {e}")
            await msg.edit_text("❌ Erro. Tenta novamente.")

    elif data == "reload":
        liga_id = ctx.user_data.get("liga_sel", "all")
        msg = await query.message.reply_text("🔄 A recarregar...")
        try:
            dados = gerar_palpites(liga_id, "all")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_resumo(dados), parse_mode="Markdown",
                                reply_markup=teclado_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(f"Erro reload: {e}")
            await msg.edit_text("❌ Erro. Tenta /jogos.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    log.info("ScoutAI Bot a iniciar...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("ajuda",      cmd_ajuda))
    app.add_handler(CommandHandler("jogos",      cmd_jogos))
    app.add_handler(CommandHandler("futebol",    cmd_futebol))
    app.add_handler(CommandHandler("basketball", cmd_basketball))
    app.add_handler(CommandHandler("ligas",      cmd_ligas))
    app.add_handler(CommandHandler("detalhes",   cmd_detalhes))
    app.add_handler(CallbackQueryHandler(callback_handler))

    log.info("Bot a correr!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
