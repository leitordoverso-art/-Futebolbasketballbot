#!/usr/bin/env python3
"""
ScoutAI Bot – Palpites Desportivos com IA
Bot Telegram que gera previsões de futebol e basquetebol usando Claude AI.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, time
import google.generativeai as genai

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    JobQueue,
)

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8974398857:AAHYDMCxjBu6T-ZaVakSbUPbfNOy9C0FmKI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6LNxHFIkS_ArRI4_POyDQlYJnsOOu9CwHqy0Y48smvi7w")
CANAL_ID = os.getenv("CANAL_ID", "")          # opcional: ID do canal para envio automático
HORA_ENVIO_AUTO = time(hour=9, minute=0)       # hora do envio automático diário (09:00)

genai.configure(api_key=GEMINI_API_KEY)
model_gemini = genai.GenerativeModel("gemini-1.5-flash")

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
    "all":        ("🌐 Todas as Ligas",          "Mundial, Bélgica, Países Baixos, Bulgária, Argélia, EUA, UEFA, África e outras"),
    "world":      ("🌍 Mundial / Internacionais", "Jogos internacionais e Copas do Mundo"),
    "belgium":    ("🇧🇪 Bélgica – Pro League",   "Primeira Liga da Bélgica"),
    "netherlands":("🇳🇱 Países Baixos – Eredivisie", "Eredivisie da Holanda"),
    "bulgaria":   ("🇧🇬 Bulgária – Parva Liga",  "Primeira Liga da Bulgária"),
    "algeria":    ("🇩🇿 Argélia – Ligue 1",      "Ligue Professionnelle 1 da Argélia"),
    "usa_soccer": ("🇺🇸 EUA – MLS",              "Major League Soccer dos EUA"),
    "nba":        ("🏀 NBA – Basquetebol",        "National Basketball Association"),
    "euro":       ("🏆 UEFA / Champions",         "Champions League, Europa League, Conference League"),
    "africa":     ("🌍 África (CAF)",             "Ligas africanas e competições CAF"),
    "other":      ("🌐 Outras Ligas",             "Outras ligas europeias e mundiais"),
}


# ─────────────────────────────────────────────
# GERAÇÃO DE PALPITES COM IA
# ─────────────────────────────────────────────
def gerar_palpites(liga_id: str = "all", desporto: str = "all") -> dict:
    """Chama a API Claude e devolve os palpites em formato dict."""
    hoje = datetime.now().strftime("%A, %d de %B de %Y")
    liga_nome, liga_desc = LIGAS.get(liga_id, LIGAS["all"])

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
  "resumo": "Resumo do dia desportivo em 2 frases curtas.",
  "jogos": [
    {{
      "liga": "nome da liga",
      "hora": "HH:MM",
      "casa": "Equipa Casa",
      "fora": "Equipa Fora",
      "palpite_principal": "Vitória Casa | Empate | Vitória Fora | Ambas Marcam | Acima 2.5",
      "confianca": 75,
      "opcoes": [
        {{"tipo": "Dupla Chance 1X",    "odd": "1.35"}},
        {{"tipo": "Ambas Marcam – Sim", "odd": "1.80"}},
        {{"tipo": "Acima 2.5 Golos",   "odd": "1.75"}},
        {{"tipo": "Vitória Casa",       "odd": "2.10"}}
      ],
      "analise": "Análise de 2 frases: forma das equipas e confrontos directos.",
      "aviso": "Aviso sobre risco ou lesões (ou null)"
    }}
  ]
}}

Usa odds realistas entre 1.20 e 4.50. Confiança entre 45 e 92. Texto em Português de Moçambique."""

    log.info(f"Gerando palpites — liga={liga_id} desporto={desporto}")
    try:
        response = model_gemini.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        log.error(f"Erro Gemini: {type(e).__name__}: {e}")
        raise


# ─────────────────────────────────────────────
# FORMATAÇÃO DAS MENSAGENS
# ─────────────────────────────────────────────
def emoji_confianca(v: int) -> str:
    if v >= 80: return "🟢"
    if v >= 65: return "🟡"
    if v >= 50: return "🟠"
    return "🔴"

def formatar_resumo(dados: dict) -> str:
    """Mensagem curta com a lista de jogos do dia."""
    linhas = [
        "⚽🏀 *SCOUTAI – PALPITES DO DIA*",
        f"📅 _{dados.get('data', '')}_ \n",
        f"📊 {dados.get('resumo', '')}\n",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    for i, j in enumerate(dados.get("jogos", []), 1):
        ec = emoji_confianca(j["confianca"])
        linhas.append(
            f"{ec} *{j['casa']} vs {j['fora']}*\n"
            f"   🕐 {j['hora']}  |  🏆 {j['liga']}\n"
            f"   🎯 *{j['palpite_principal']}*  ({j['confianca']}%)\n"
        )
    linhas += [
        "━━━━━━━━━━━━━━━━━━━━━",
        "📌 Usa /detalhes para análise completa de cada jogo.",
        "⚠️ _Aposte com responsabilidade._"
    ]
    return "\n".join(linhas)


def formatar_jogo(j: dict, numero: int) -> str:
    """Mensagem detalhada de um jogo individual."""
    ec = emoji_confianca(j["confianca"])
    opcoes = "\n".join(
        f"   • {o['tipo']} → odd *{o['odd']}*"
        for o in j.get("opcoes", [])
    )
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
# TECLADOS INLINE
# ─────────────────────────────────────────────
def teclado_ligas() -> InlineKeyboardMarkup:
    botoes = [
        [InlineKeyboardButton(v[0], callback_data=f"liga:{k}")]
        for k, v in list(LIGAS.items())
    ]
    return InlineKeyboardMarkup(botoes)


def teclado_desporto() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⚽ Futebol",       callback_data="sport:football"),
        InlineKeyboardButton("🏀 Basquetebol",   callback_data="sport:basketball"),
        InlineKeyboardButton("⚽🏀 Ambos",        callback_data="sport:all"),
    ]])


def teclado_jogos(total: int) -> InlineKeyboardMarkup:
    """Botões numerados para ver detalhes de cada jogo."""
    linha, botoes = [], []
    for i in range(1, total + 1):
        linha.append(InlineKeyboardButton(f"#{i}", callback_data=f"jogo:{i-1}"))
        if len(linha) == 5:
            botoes.append(linha); linha = []
    if linha:
        botoes.append(linha)
    botoes.append([InlineKeyboardButton("🔄 Novo Carregamento", callback_data="reload")])
    return InlineKeyboardMarkup(botoes)


# ─────────────────────────────────────────────
# HANDLERS DE COMANDOS
# ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    texto = (
        "👋 *Bem-vindo ao ScoutAI!*\n\n"
        "Sou o teu assistente de palpites desportivos com IA.\n\n"
        "🤖 Uso inteligência artificial para analisar jogos de futebol e basquetebol "
        "e gerar palpites com confiança.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 *Comandos disponíveis:*\n"
        "/jogos – Palpites do dia (todas as ligas)\n"
        "/futebol – Apenas jogos de futebol\n"
        "/basketball – Apenas jogos de NBA\n"
        "/ligas – Escolher uma liga específica\n"
        "/detalhes – Ver análise completa dos jogos\n"
        "/ajuda – Ver esta mensagem\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ _Os palpites são gerados por IA. Aposte com responsabilidade._"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


async def cmd_ajuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, ctx)


async def cmd_jogos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ A analisar jogos com IA... aguarda um momento.")
    try:
        dados = gerar_palpites("all", "all")
        ctx.user_data["jogos"] = dados
        texto = formatar_resumo(dados)
        teclado = teclado_jogos(len(dados["jogos"]))
        await msg.edit_text(texto, parse_mode="Markdown", reply_markup=teclado)
    except Exception as e:
        log.error(f"Erro em cmd_jogos: {e}")
        await msg.edit_text("❌ Erro ao gerar palpites. Tenta novamente com /jogos.")


async def cmd_futebol(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ A carregar jogos de futebol...")
    try:
        dados = gerar_palpites("all", "football")
        ctx.user_data["jogos"] = dados
        texto = formatar_resumo(dados)
        teclado = teclado_jogos(len(dados["jogos"]))
        await msg.edit_text(texto, parse_mode="Markdown", reply_markup=teclado)
    except Exception as e:
        log.error(f"Erro em cmd_futebol: {e}")
        await msg.edit_text("❌ Erro ao carregar futebol. Tenta /futebol novamente.")


async def cmd_basketball(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ A carregar jogos de NBA...")
    try:
        dados = gerar_palpites("nba", "basketball")
        ctx.user_data["jogos"] = dados
        texto = formatar_resumo(dados)
        teclado = teclado_jogos(len(dados["jogos"]))
        await msg.edit_text(texto, parse_mode="Markdown", reply_markup=teclado)
    except Exception as e:
        log.error(f"Erro em cmd_basketball: {e}")
        await msg.edit_text("❌ Erro ao carregar NBA. Tenta /basketball novamente.")


async def cmd_ligas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏆 *Escolhe a liga:*",
        parse_mode="Markdown",
        reply_markup=teclado_ligas()
    )


async def cmd_detalhes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = ctx.user_data.get("jogos")
    if not dados:
        await update.message.reply_text("⚠️ Primeiro usa /jogos para carregar os jogos do dia.")
        return
    teclado = teclado_jogos(len(dados["jogos"]))
    await update.message.reply_text(
        "📋 *Escolhe o jogo para ver a análise completa:*",
        parse_mode="Markdown",
        reply_markup=teclado
    )


# ─────────────────────────────────────────────
# HANDLER DE CALLBACKS (botões inline)
# ─────────────────────────────────────────────
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # --- Ver jogo individual ---
    if data.startswith("jogo:"):
        idx = int(data.split(":")[1])
        dados = ctx.user_data.get("jogos")
        if not dados or idx >= len(dados["jogos"]):
            await query.message.reply_text("⚠️ Dados expirados. Usa /jogos novamente.")
            return
        jogo = dados["jogos"][idx]
        texto = formatar_jogo(jogo, idx + 1)
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Voltar à lista", callback_data="voltar_lista")
        ]])
        await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=teclado)

    # --- Voltar à lista ---
    elif data == "voltar_lista":
        dados = ctx.user_data.get("jogos")
        if dados:
            teclado = teclado_jogos(len(dados["jogos"]))
            await query.message.reply_text(
                formatar_resumo(dados),
                parse_mode="Markdown",
                reply_markup=teclado
            )

    # --- Escolha de liga ---
    elif data.startswith("liga:"):
        liga_id = data.split(":")[1]
        ctx.user_data["liga_sel"] = liga_id
        await query.message.reply_text(
            f"✅ Liga seleccionada: *{LIGAS[liga_id][0]}*\n\nAgora escolhe o desporto:",
            parse_mode="Markdown",
            reply_markup=teclado_desporto()
        )

    # --- Escolha de desporto ---
    elif data.startswith("sport:"):
        sport_id = data.split(":")[1]
        liga_id = ctx.user_data.get("liga_sel", "all")
        msg = await query.message.reply_text("⏳ A gerar palpites com IA...")
        try:
            dados = gerar_palpites(liga_id, sport_id)
            ctx.user_data["jogos"] = dados
            texto = formatar_resumo(dados)
            teclado = teclado_jogos(len(dados["jogos"]))
            await msg.edit_text(texto, parse_mode="Markdown", reply_markup=teclado)
        except Exception as e:
            log.error(f"Erro no callback sport: {e}")
            await msg.edit_text("❌ Erro ao gerar palpites. Tenta novamente.")

    # --- Recarregar ---
    elif data == "reload":
        liga_id = ctx.user_data.get("liga_sel", "all")
        msg = await query.message.reply_text("🔄 A recarregar palpites...")
        try:
            dados = gerar_palpites(liga_id, "all")
            ctx.user_data["jogos"] = dados
            texto = formatar_resumo(dados)
            teclado = teclado_jogos(len(dados["jogos"]))
            await msg.edit_text(texto, parse_mode="Markdown", reply_markup=teclado)
        except Exception as e:
            log.error(f"Erro no reload: {e}")
            await msg.edit_text("❌ Erro ao recarregar. Tenta /jogos.")


# ─────────────────────────────────────────────
# ENVIO AUTOMÁTICO DIÁRIO (opcional)
# ─────────────────────────────────────────────
async def envio_automatico(ctx: ContextTypes.DEFAULT_TYPE):
    """Enviado automaticamente todos os dias às 09:00 para o canal configurado."""
    if not CANAL_ID:
        return
    try:
        dados = gerar_palpites("all", "all")
        texto = formatar_resumo(dados)
        await ctx.bot.send_message(chat_id=CANAL_ID, text=texto, parse_mode="Markdown")
        log.info("Envio automático diário concluído.")
    except Exception as e:
        log.error(f"Erro no envio automático: {e}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    log.info("ScoutAI Bot a iniciar...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("ajuda",      cmd_ajuda))
    app.add_handler(CommandHandler("jogos",      cmd_jogos))
    app.add_handler(CommandHandler("futebol",    cmd_futebol))
    app.add_handler(CommandHandler("basketball", cmd_basketball))
    app.add_handler(CommandHandler("ligas",      cmd_ligas))
    app.add_handler(CommandHandler("detalhes",   cmd_detalhes))

    # Botões inline
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Envio automático diário às 09:00
    if CANAL_ID:
        app.job_queue.run_daily(envio_automatico, time=HORA_ENVIO_AUTO)
        log.info(f"Envio automático activado para o canal {CANAL_ID} às 09:00.")

    log.info("Bot a correr. Prime Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
