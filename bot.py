#!/usr/bin/env python3
import os, json, logging
from datetime import datetime
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_TOKEN e GROQ_API_KEY sao obrigatorios!")

groq_client = Groq(api_key=GROQ_API_KEY)
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

MESES = ["Janeiro","Fevereiro","Marco","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
DIAS  = ["Segunda-feira","Terca-feira","Quarta-feira","Quinta-feira",
         "Sexta-feira","Sabado","Domingo"]

def data_pt():
    n = datetime.now()
    return f"{DIAS[n.weekday()]}, {n.day:02d} de {MESES[n.month-1]} de {n.year}"

def hora_atual():
    return datetime.now().strftime("%H:%M")

def emoji_conf(v):
    if v >= 80: return "verde"
    if v >= 65: return "amarelo"
    if v >= 50: return "laranja"
    return "vermelho"

def circulo(v):
    if v >= 80: return "\U0001F7E2"
    if v >= 65: return "\U0001F7E1"
    if v >= 50: return "\U0001F7E0"
    return "\U0001F534"

def barra(p):
    c = round(p / 10)
    return chr(9608)*c + chr(9617)*(10-c)

# MENUS
def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Futebol", callback_data="m:futebol"),
         InlineKeyboardButton("Basquetebol", callback_data="m:basket")],
        [InlineKeyboardButton("Ligas Principais", callback_data="m:ligas"),
         InlineKeyboardButton("Mundial", callback_data="m:mundial")],
        [InlineKeyboardButton("Todos os Paises", callback_data="m:todos"),
         InlineKeyboardButton("Previsoes IA", callback_data="m:previsoes")],
        [InlineKeyboardButton("Notificacoes", callback_data="m:notif"),
         InlineKeyboardButton("Falar com IA", callback_data="m:chat")],
        [InlineKeyboardButton("Palpites do Dia", callback_data="m:palpites")],
    ])

def menu_futebol():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Champions League", callback_data="f:champions"),
         InlineKeyboardButton("La Liga", callback_data="f:laliga")],
        [InlineKeyboardButton("Premier League", callback_data="f:premier"),
         InlineKeyboardButton("Serie A", callback_data="f:seriea")],
        [InlineKeyboardButton("Bundesliga", callback_data="f:bundesliga"),
         InlineKeyboardButton("Ligue 1", callback_data="f:ligue1")],
        [InlineKeyboardButton("Belgica", callback_data="f:belgium"),
         InlineKeyboardButton("Eredivisie", callback_data="f:eredivisie")],
        [InlineKeyboardButton("Algeria", callback_data="f:algeria"),
         InlineKeyboardButton("Bulgaria", callback_data="f:bulgaria")],
        [InlineKeyboardButton("Portugal", callback_data="f:portugal"),
         InlineKeyboardButton("Africa CAF", callback_data="f:africa")],
        [InlineKeyboardButton("MLS", callback_data="f:mls"),
         InlineKeyboardButton("Todas as Ligas", callback_data="f:all")],
        [InlineKeyboardButton("Voltar", callback_data="m:inicio")],
    ])

def menu_basket():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("NBA Hoje", callback_data="b:nba"),
         InlineKeyboardButton("NBA Playoffs", callback_data="b:playoffs")],
        [InlineKeyboardButton("EuroLeague", callback_data="b:euro"),
         InlineKeyboardButton("Todas as Ligas", callback_data="b:all")],
        [InlineKeyboardButton("Voltar", callback_data="m:inicio")],
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
        InlineKeyboardButton("Recarregar", callback_data="reload"),
        InlineKeyboardButton("Menu", callback_data="m:inicio"),
    ])
    return InlineKeyboardMarkup(botoes)

LIGAS_MAP = {
    "champions":"UEFA Champions League","laliga":"La Liga Espanha",
    "premier":"Premier League Inglaterra","seriea":"Serie A Italia",
    "bundesliga":"Bundesliga Alemanha","ligue1":"Ligue 1 Franca",
    "belgium":"Pro League Belgica","eredivisie":"Eredivisie Paises Baixos",
    "algeria":"Ligue 1 Algeria","bulgaria":"Parva Liga Bulgaria",
    "portugal":"Liga Portugal","africa":"Ligas Africanas CAF",
    "mls":"MLS Estados Unidos","all":"Todas as Ligas de Futebol",
}
BASKET_MAP = {
    "nba":"NBA","playoffs":"NBA Playoffs",
    "euro":"EuroLeague","all":"Todas as Ligas de Basquetebol",
}

def ia_palpites(liga, desporto="futebol", quantidade="10 a 13"):
    hoje = data_pt()
    hora = hora_atual()
    prompt = (
        f"Hoje e {hoje}. Es um analista desportivo especializado em apostas.\n"
        f"Gera {quantidade} jogos reais de {desporto} para hoje na(s) liga(s): {liga}.\n\n"
        "Responde APENAS com JSON valido. Sem markdown. Sem explicacoes. Formato:\n"
        "{\n"
        f"  \"data\": \"{hoje}\",\n"
        f"  \"hora_geracao\": \"{hora}\",\n"
        f"  \"liga_principal\": \"{liga}\",\n"
        "  \"resumo\": \"Resumo do dia em 2 frases em Portugues.\",\n"
        "  \"jogos\": [\n"
        "    {\n"
        "      \"numero\": 1,\n"
        "      \"liga\": \"Nome da Liga\",\n"
        "      \"pais\": \"Pais\",\n"
        "      \"hora_jogo\": \"HH:MM\",\n"
        "      \"casa\": \"Equipa Casa\",\n"
        "      \"fora\": \"Equipa Fora\",\n"
        "      \"palpite_principal\": \"Vitoria Casa\",\n"
        "      \"probabilidade_casa\": 65,\n"
        "      \"probabilidade_empate\": 20,\n"
        "      \"probabilidade_fora\": 15,\n"
        "      \"confianca\": 78,\n"
        "      \"opcoes_aposta\": [\n"
        "        {\"tipo\": \"Dupla Chance 1X\", \"odd\": \"1.35\", \"confianca\": 85},\n"
        "        {\"tipo\": \"Ambas Marcam Sim\", \"odd\": \"1.80\", \"confianca\": 70},\n"
        "        {\"tipo\": \"Acima 2.5 Golos\", \"odd\": \"1.75\", \"confianca\": 72},\n"
        "        {\"tipo\": \"Vitoria Casa\", \"odd\": \"2.10\", \"confianca\": 65},\n"
        "        {\"tipo\": \"Abaixo 3.5 Golos\", \"odd\": \"1.45\", \"confianca\": 80}\n"
        "      ],\n"
        "      \"forma_casa\": \"V V E V V\",\n"
        "      \"forma_fora\": \"E D V E D\",\n"
        "      \"analise\": \"Analise de 3 frases sobre forma e confrontos.\",\n"
        "      \"previsao_golos\": \"2-1\",\n"
        "      \"aviso\": null\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Odds 1.15-5.00. Probabilidades somam 100. Texto em Portugues."
    )
    log.info(f"IA palpites: {liga}")
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7, max_tokens=4000
    )
    raw = r.choices[0].message.content.strip()
    raw = raw.replace("```json","").replace("```","").strip()
    return json.loads(raw)

def ia_chat(pergunta, historico):
    msgs = [{"role":"system","content":(
        "Es o ScoutAI, assistente desportivo especializado em futebol, basquetebol e apostas. "
        "Respondes em Portugues de Mocambique. Es amigavel e muito conhecedor de desporto. "
        "Podes dar conselhos sobre apostas, analise de jogos, estatisticas e previsoes."
    )}]
    msgs += historico[-6:]
    msgs.append({"role":"user","content":pergunta})
    r = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=msgs, temperature=0.8, max_tokens=500
    )
    return r.choices[0].message.content.strip()

def formatar_lista(dados):
    linhas = [
        "SCOUTAI - PALPITES DO DIA",
        f"Data: {dados.get('data','')}",
        f"Gerado as: {dados.get('hora_geracao','')}",
        f"Liga: {dados.get('liga_principal','')}",
        "",
        dados.get("resumo",""),
        "",
        "=" * 25,
    ]
    for j in dados.get("jogos",[]):
        c = circulo(j["confianca"])
        linhas.append(
            f"{c} *{j['casa']} vs {j['fora']}*\n"
            f"  Hora: {j['hora_jogo']} | {j['liga']} ({j['pais']})\n"
            f"  Palpite: *{j['palpite_principal']}* | Confianca: {j['confianca']}%\n"
            f"  Casa {j['probabilidade_casa']}% | Empate {j['probabilidade_empate']}% | Fora {j['probabilidade_fora']}%\n"
        )
    linhas += [
        "=" * 25,
        "Clica num numero para analise completa",
        "_Aposte com responsabilidade._"
    ]
    return "\n".join(linhas)

def formatar_jogo(j, num):
    c = circulo(j["confianca"])
    opcoes_txt = "\n".join(
        f"  {circulo(o['confianca'])} {o['tipo']} -> odd *{o['odd']}* ({o['confianca']}%)"
        for o in j.get("opcoes_aposta",[])
    )
    pc = j["probabilidade_casa"]
    pe = j["probabilidade_empate"]
    pf = j["probabilidade_fora"]
    aviso_txt = f"\nAviso: _{j['aviso']}_" if j.get("aviso") else ""
    return (
        f"*JOGO #{num} - {j['liga']}*\n"
        f"Pais: {j['pais']}\n"
        f"{'='*25}\n"
        f"*{j['casa']}* vs *{j['fora']}*\n"
        f"Hora: *{j['hora_jogo']}*\n\n"
        f"*Probabilidades:*\n"
        f"  Casa:   {barra(pc)} {pc}%\n"
        f"  Empate: {barra(pe)} {pe}%\n"
        f"  Fora:   {barra(pf)} {pf}%\n\n"
        f"Forma Casa: `{j.get('forma_casa','N/A')}`\n"
        f"Forma Fora: `{j.get('forma_fora','N/A')}`\n\n"
        f"{c} *Palpite:* {j['palpite_principal']} ({j['confianca']}%)\n"
        f"Resultado Previsto: *{j.get('previsao_golos','N/A')}*\n\n"
        f"*Opcoes de Aposta:*\n{opcoes_txt}\n\n"
        f"*Analise:*\n_{j['analise']}_{aviso_txt}"
    )

# HANDLERS
async def cmd_start(u, ctx):
    ctx.user_data["modo_chat"] = False
    await u.message.reply_text(
        f"Bem-vindo ao *ScoutAI!*\n\n"
        f"Data: _{data_pt()}_\n\n"
        "Sou o teu assistente de palpites com IA.\n"
        "Analiso futebol e basquetebol de todo o mundo!\n\n"
        "Escolhe uma opcao:",
        parse_mode="Markdown",
        reply_markup=menu_principal()
    )

async def cmd_ajuda(u, ctx):
    await cmd_start(u, ctx)

async def cmd_jogos(u, ctx):
    msg = await u.message.reply_text("A gerar palpites com IA...")
    try:
        dados = ia_palpites("Mundial, Belgica, Paises Baixos, Bulgaria, Algeria, MLS, UEFA, Africa")
        ctx.user_data["jogos"] = dados
        await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                            reply_markup=menu_jogos(len(dados["jogos"])))
    except Exception as e:
        log.error(f"Erro jogos: {e}")
        await msg.edit_text("Erro ao gerar palpites. Tenta /jogos novamente.")

async def cmd_futebol(u, ctx):
    await u.message.reply_text("Escolhe a Liga:", reply_markup=menu_futebol())

async def cmd_basketball(u, ctx):
    await u.message.reply_text("Escolhe a Liga:", reply_markup=menu_basket())

async def cmd_chat(u, ctx):
    ctx.user_data["modo_chat"] = True
    ctx.user_data["historico"] = []
    await u.message.reply_text(
        "*Modo Chat IA activado!*\n\n"
        "Podes perguntar sobre:\n"
        "- Analise de equipas\n"
        "- Conselhos de apostas\n"
        "- Estatisticas e resultados\n"
        "- Previsoes especiais\n\n"
        "Escreve a tua pergunta! Para voltar usa /start",
        parse_mode="Markdown"
    )

async def handler_texto(u, ctx):
    if not ctx.user_data.get("modo_chat"):
        await u.message.reply_text(
            "Para falar comigo usa /chat ou clica em *Falar com IA* no menu.",
            parse_mode="Markdown", reply_markup=menu_principal()
        )
        return
    hist = ctx.user_data.get("historico", [])
    await u.message.reply_chat_action("typing")
    try:
        resp = ia_chat(u.message.text, hist)
        hist.append({"role":"user","content":u.message.text})
        hist.append({"role":"assistant","content":resp})
        ctx.user_data["historico"] = hist[-10:]
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("Menu Principal", callback_data="m:inicio"),
            InlineKeyboardButton("Ver Palpites", callback_data="m:palpites"),
        ]])
        await u.message.reply_text(resp, reply_markup=teclado)
    except Exception as e:
        log.error(f"Erro chat: {e}")
        await u.message.reply_text("Erro. Tenta novamente.")

async def callback(u, ctx):
    q = u.callback_query
    await q.answer()
    d = q.data

    if d == "m:inicio":
        ctx.user_data["modo_chat"] = False
        await q.message.reply_text(
            f"*Menu Principal*\nData: _{data_pt()}_\n\nEscolhe uma opcao:",
            parse_mode="Markdown", reply_markup=menu_principal()
        )

    elif d == "m:futebol":
        await q.message.reply_text("Ligas de Futebol:", reply_markup=menu_futebol())

    elif d == "m:basket":
        await q.message.reply_text("Ligas de Basquetebol:", reply_markup=menu_basket())

    elif d in ("m:mundial", "m:todos", "m:palpites", "m:previsoes", "m:ligas", "reload"):
        ligas_map = {
            "m:mundial":   ("Copa do Mundo FIFA, eliminatorias mundiais", "futebol"),
            "m:todos":     ("Todas as ligas mundiais Europa Africa Americas Asia", "futebol"),
            "m:palpites":  ("Mundial, Belgica, Paises Baixos, Bulgaria, Algeria, MLS, UEFA, Africa", "futebol"),
            "m:previsoes": ("Champions, Premier League, NBA, Mundial", "futebol"),
            "m:ligas":     ("Champions, Premier, La Liga, Serie A, Bundesliga, Ligue 1", "futebol"),
            "reload":      ("Mundial, Belgica, Paises Baixos, Bulgaria, Algeria, MLS, UEFA, Africa", "futebol"),
        }
        liga, desp = ligas_map[d]
        msg = await q.message.reply_text("A carregar jogos com IA...")
        try:
            dados = ia_palpites(liga, desp)
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("Erro. Tenta novamente.")

    elif d == "m:notif":
        await q.message.reply_text(
            "*Notificacoes*\n\n"
            "O bot envia palpites todos os dias as 09:00.\n"
            "Adiciona o bot ao teu canal para receber automaticamente.\n\n"
            "Usa /jogos para ver os palpites agora!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ver Palpites", callback_data="m:palpites"),
                InlineKeyboardButton("Menu", callback_data="m:inicio"),
            ]])
        )

    elif d == "m:chat":
        ctx.user_data["modo_chat"] = True
        ctx.user_data["historico"] = []
        await q.message.reply_text(
            "*Modo Chat IA activado!*\n\n"
            "Escreve a tua pergunta sobre desporto ou apostas!\n"
            "_Para voltar usa /start_",
            parse_mode="Markdown"
        )

    elif d.startswith("f:"):
        liga_nome = LIGAS_MAP.get(d.split(":")[1], "Futebol")
        msg = await q.message.reply_text(f"A carregar {liga_nome}...")
        try:
            dados = ia_palpites(liga_nome)
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("Erro. Tenta novamente.")

    elif d.startswith("b:"):
        liga_nome = BASKET_MAP.get(d.split(":")[1], "NBA")
        msg = await q.message.reply_text(f"A carregar {liga_nome}...")
        try:
            dados = ia_palpites(liga_nome, desporto="basquetebol", quantidade="8 a 10")
            ctx.user_data["jogos"] = dados
            await msg.edit_text(formatar_lista(dados), parse_mode="Markdown",
                                reply_markup=menu_jogos(len(dados["jogos"])))
        except Exception as e:
            log.error(e)
            await msg.edit_text("Erro. Tenta novamente.")

    elif d.startswith("j:"):
        idx = int(d.split(":")[1])
        dados = ctx.user_data.get("jogos")
        if not dados or idx >= len(dados["jogos"]):
            await q.message.reply_text("Usa /jogos para recarregar.")
            return
        teclado = InlineKeyboardMarkup([[
            InlineKeyboardButton("Voltar a Lista", callback_data="voltar"),
            InlineKeyboardButton("Menu", callback_data="m:inicio"),
        ]])
        await q.message.reply_text(
            formatar_jogo(dados["jogos"][idx], idx+1),
            parse_mode="Markdown", reply_markup=teclado
        )

    elif d == "voltar":
        dados = ctx.user_data.get("jogos")
        if dados:
            await q.message.reply_text(
                formatar_lista(dados), parse_mode="Markdown",
                reply_markup=menu_jogos(len(dados["jogos"]))
            )

def main():
    log.info("ScoutAI v2 a iniciar...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(CommandHandler("jogos", cmd_jogos))
    app.add_handler(CommandHandler("futebol", cmd_futebol))
    app.add_handler(CommandHandler("basketball", cmd_basketball))
    app.add_handler(CommandHandler("chat", cmd_chat))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler_texto))
    log.info("Bot a correr!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
