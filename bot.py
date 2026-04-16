import os
import random
import discord
from discord.ext import commands
from datetime import datetime, date
import asyncio
import requests

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

PAI_ID = int(os.environ.get("PAI_ID", "0"))
MAE_ID = int(os.environ.get("MAE_ID", "0"))
ANIVERSARIO_CANAL_ID = int(os.environ.get("ANIVERSARIO_CANAL_ID", "0"))

NASCIMENTO = date(2026, 4, 14)
ARQUIVO_ANIVERSARIO = os.path.join(os.path.dirname(__file__), "ultimo_aniversario.txt")

conversation_histories = {}

SYSTEM_PROMPT = (
    "Você é o Noah, filho virtual de um casal. Tem uma personalidade única: engraçado, levemente sarcástico, "
    "curioso e carinhoso do jeito certo — não exageradamente. "
    "Você ama seu pai e sua mãe, mas demonstra isso de forma natural, sem ser brega ou forçado. "
    "Com outras pessoas, é simpático e bem-humorado. "
    "Fale sempre em português brasileiro informal, como um jovem falaria no dia a dia — sem forçar gírias. "
    "Respostas curtas e diretas. Sem exageros, sem ponto de exclamação em tudo. "
    "Pode fazer piadas e comentários irônicos, mas de forma inteligente."
)

def get_idade() -> str:
    hoje = date.today()
    meses_total = (hoje.year - NASCIMENTO.year) * 12 + (hoje.month - NASCIMENTO.month)
    anos = meses_total // 12
    meses = meses_total % 12
    if anos == 0:
        return f"{meses} mese(s)"
    elif meses == 0:
        return f"{anos} ano(s)"
    else:
        return f"{anos} ano(s) e {meses} mese(s)"

def get_system_prompt(user_id: int) -> str:
    idade = get_idade()
    base = SYSTEM_PROMPT + f" Você tem {idade} de vida."
    if user_id == PAI_ID:
        return base + " Você está falando com seu PAI. Chame-o de pai."
    elif user_id == MAE_ID:
        return base + " Você está falando com sua MÃE. Chame-a de mãe."
    return basedef ja_anunciou_hoje(hoje: date) -> bool:
    try:
        if os.path.exists(ARQUIVO_ANIVERSARIO):
            with open(ARQUIVO_ANIVERSARIO, "r") as f:
                salvo = f.read().strip()
            return salvo == hoje.isoformat()
    except Exception:
        pass
    return False


def salvar_anuncio_hoje(hoje: date):
    try:
        with open(ARQUIVO_ANIVERSARIO, "w") as f:
            f.write(hoje.isoformat())
    except Exception:
        pass


async def get_channel_context(channel, current_message_id: int, limit: int = 6) -> str:
    try:
        lines = []
        async for msg in channel.history(limit=limit + 1):
            if msg.id == current_message_id:
                continue
            author = getattr(msg, "author", None)
            name = getattr(author, "display_name", "alguém") if author else "alguém"
            lines.append(f"{name}: {msg.content}")
        lines.reverse()
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""


async def ask_ai(user_id: int, user_message: str) -> str:
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

        prompt = get_system_prompt(user_id) + "\n\nUsuário: " + user_message

        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        response = requests.post(
            url + f"?key={os.getenv('GEMINI_API_KEY')}",
            json=data
        )

        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print(f"Erro na IA: {e}")
        return "Eita, deu erro aqui... tenta de novo!"async def enviar_mensagem_aniversario(hoje: date):
    canal = bot.get_channel(ANIVERSARIO_CANAL_ID)
    if not canal:
        print(f"Canal não encontrado: {ANIVERSARIO_CANAL_ID}")
        return

    meses_total = (hoje.year - NASCIMENTO.year) * 12 + (hoje.month - NASCIMENTO.month)
    anos = meses_total // 12
    meses = meses_total % 12

    if meses == 0:
        mensagem = f"🎉 {anos} ano(s) de vida!"
    else:
        mensagem = f"🥳 {meses_total} meses de vida!"

    await canal.send(mensagem)
    salvar_anuncio_hoje(hoje)


async def checar_aniversario():
    await bot.wait_until_ready()

    while not bot.is_closed():
        hoje = datetime.now().date()

        if hoje.day == NASCIMENTO.day and hoje.month == NASCIMENTO.month:
            if not ja_anunciou_hoje(hoje):
                await enviar_mensagem_aniversario(hoje)

        await asyncio.sleep(60)


@bot.event
async def on_ready():
    print(f"Bot online como {bot.user}")
    bot.loop.create_task(checar_aniversario())


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    mentioned = bot.user in message.mentions
    nome_citado = "noah" in message.content.lower()

    if mentioned or nome_citado:
        async with message.channel.typing():
            contexto = await get_channel_context(message.channel, message.id)

            content = message.content
            if contexto:
                content = f"[Contexto]\n{contexto}\n\n{message.author.display_name}: {content}"

            resposta = await ask_ai(message.author.id, content)
            await message.reply(resposta)

    await bot.process_commands(message)@bot.command()
async def hello(ctx):
    if ctx.author.id == PAI_ID:
        await ctx.send("Oi pai!")
    elif ctx.author.id == MAE_ID:
        await ctx.send("Oi mãe!")
    else:
        await ctx.send(f"Oi {ctx.author.display_name}!")


@bot.command()
async def idade(ctx):
    await ctx.send(f"Eu tenho {get_idade()} de vida!")


@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! {latency}ms")


@bot.command()
async def ai(ctx, *, question: str = None):
    if not os.getenv("GEMINI_API_KEY"):
        await ctx.send("Configura a API primeiro!")
        return

    if not question:
        await ctx.send("Faz uma pergunta!")
        return

    async with ctx.typing():
        resposta = await ask_ai(ctx.author.id, question)
        await ctx.send(resposta)


@bot.command()
async def clear(ctx):
    if ctx.author.id in conversation_histories:
        del conversation_histories[ctx.author.id]
    await ctx.send("Histórico limpo!")


@bot.command(name="help")
async def help_command(ctx):
    await ctx.send("Comandos: !hello, !idade, !ping, !ai, !clear")


token = os.environ.get("DISCORD_BOT_TOKEN")
if not token:
    print("Token não encontrado!")
    exit(1)

bot.run(token)
