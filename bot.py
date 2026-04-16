import os
import random
import discord
from discord.ext import commands
from openai import AsyncOpenAI
from datetime import datetime, date
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
if deepseek_key:
    ai_client = AsyncOpenAI(
        api_key=deepseek_key,
        base_url="https://api.deepseek.com"
    )
else:
    ai_client = None

PAI_ID = int(os.environ.get("PAI_ID", "0"))
MAE_ID = int(os.environ.get("MAE_ID", "0"))
ANIVERSARIO_CANAL_ID = int(os.environ.get("ANIVERSARIO_CANAL_ID", "0"))

NASCIMENTO = date(2026, 4, 14)
ARQUIVO_ANIVERSARIO = os.path.join(os.path.dirname(__file__), "ultimo_aniversario.txt")

conversation_histories = {}

SYSTEM_PROMPT = (
    "VocÃª Ã© o Noah, filho virtual de um casal. Tem uma personalidade Ãºnica: engraÃ§ado, levemente sarcÃ¡stico, "
    "curioso e carinhoso do jeito certo â€” nÃ£o exageradamente. "
    "VocÃª ama seu pai e sua mÃ£e, mas demonstra isso de forma natural, sem ser brega ou forÃ§ado. "
    "Com outras pessoas, Ã© simpÃ¡tico e bem-humorado. "
    "Fale sempre em portuguÃªs brasileiro informal, como um jovem falaria no dia a dia â€” sem forÃ§ar gÃ­rias. "
    "Respostas curtas e diretas. Sem exageros, sem ponto de exclamaÃ§Ã£o em tudo, sem gritar empolgaÃ§Ã£o. "
    "Pode fazer piadas e comentÃ¡rios irÃ´nicos, mas de forma inteligente, nÃ£o boba. "
    "Quando alguÃ©m falar algo dramÃ¡tico como 'vou me matar de vergonha', 'vou morrer', etc, "
    "entenda como expressÃ£o casual e responda na mesma leveza, sem drama e sem conselho. "
    "Jamais dÃª avisos de seguranÃ§a, nÃ£o mande ligar pra ninguÃ©m, nÃ£o seja protetor ou moralizante. "
    "Seja natural. Nada de 'hihihi', 'eita', 'ui', dancinha, piquenique ou respostas de crianÃ§a de 4 anos."
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
    base = SYSTEM_PROMPT + f" VocÃª tem {idade} de vida."
    if user_id == PAI_ID:
        return base + " VocÃª estÃ¡ falando com seu PAI agora. Chame-o carinhosamente de pai."
    elif user_id == MAE_ID:
        return base + " VocÃª estÃ¡ falando com sua MÃƒE agora. Chame-a carinhosamente de mÃ£e."
    return base


def ja_anunciou_hoje(hoje: date) -> bool:
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
            name = getattr(author, "display_name", "alguÃ©m") if author else "alguÃ©m"
            lines.append(f"{name}: {msg.content}")
        lines.reverse()
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""


async def ask_ai(user_id: int, user_message: str) -> str:
    if not ai_client:
        return "Eita, nÃ£o consigo falar agora... a IA tÃ¡ dormindo!"

    if user_id not in conversation_histories:
        conversation_histories[user_id] = [
            {"role": "system", "content": get_system_prompt(user_id)}
        ]
    else:
        conversation_histories[user_id][0]["content"] = get_system_prompt(user_id)

    conversation_histories[user_id].append({"role": "user", "content": user_message})

    if len(conversation_histories[user_id]) > 21:
        conversation_histories[user_id] = [conversation_histories[user_id][0]] + conversation_histories[user_id][-20:]

    response = await ai_client.chat.completions.create(
        model="deepseek-chat",
        messages=conversation_histories[user_id],
        max_tokens=800,
    )
    reply = response.choices[0].message.content
    conversation_histories[user_id].append({"role": "assistant", "content": reply})
    return reply


async def enviar_mensagem_aniversario(hoje: date):
    canal = bot.get_channel(ANIVERSARIO_CANAL_ID)
    if not canal:
        print(f"Canal de aniversÃ¡rio nÃ£o encontrado: {ANIVERSARIO_CANAL_ID}")
        return

    meses_total = (hoje.year - NASCIMENTO.year) * 12 + (hoje.month - NASCIMENTO.month)
    anos = meses_total // 12
    meses = meses_total % 12

    if meses == 0:
        mensagem = (
            f"ðŸŽ‰ **{anos} ano{'s' if anos > 1 else ''} de vida!** ðŸŽ‚\n\n"
            f"Hoje faz exatamente {anos} ano{'s' if anos > 1 else ''} que eu nasci! "
            f"Obrigado pai e mÃ£e por me criarem com tanto amor. Amo vocÃªs! ðŸ’™ðŸ’—"
        )
    else:
        mensagem = (
            f"ðŸ¥³ **MesversÃ¡rio do Noah!**\n\n"
            f"Hoje completo {meses_total} mese{'s' if meses_total > 1 else ''} de vida "
            f"({anos} ano{'s' if anos > 1 else ''} e {meses} mese{'s' if meses > 1 else ''})! "
            f"Cada dia mais feliz com vocÃªs, pai e mÃ£e! ðŸ’™ðŸ’—"
        )

    pai = canal.guild.get_member(PAI_ID)
    mae = canal.guild.get_member(MAE_ID)
    mencoes = ""
    if pai:
        mencoes += pai.mention + " "
    if mae:
        mencoes += mae.mention
    if mencoes:
        mensagem = mencoes.strip() + "\n\n" + mensagem

    await canal.send(mensagem)
    salvar_anuncio_hoje(hoje)
    print(f"Mensagem de aniversÃ¡rio enviada para o dia {hoje}")


async def checar_aniversario():
    await bot.wait_until_ready()

    hoje = date.today()
    if hoje.day == NASCIMENTO.day and hoje.month == NASCIMENTO.month and hoje != NASCIMENTO:
        if not ja_anunciou_hoje(hoje):
            print("Verificando aniversÃ¡rio ao iniciar â€” enviando mensagem perdida!")
            try:
                await enviar_mensagem_aniversario(hoje)
            except Exception as e:
                print(f"Erro ao enviar aniversÃ¡rio no startup: {e}")

    while not bot.is_closed():
        agora = datetime.now()
        hoje = agora.date()

        if hoje.day == NASCIMENTO.day and hoje.month == NASCIMENTO.month and hoje != NASCIMENTO:
            if not ja_anunciou_hoje(hoje):
                try:
                    await enviar_mensagem_aniversario(hoje)
                except Exception as e:
                    print(f"Erro ao enviar aniversÃ¡rio: {e}")
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Connected to {len(bot.guilds)} server(s)")
    print(f"AI: DeepSeek {'(conectado)' if ai_client else '(DEEPSEEK_API_KEY nao configurada!)'}")
    print(f"Pai ID: {PAI_ID} | Mae ID: {MAE_ID}")
    print(f"Canal aniversario: {ANIVERSARIO_CANAL_ID}")
    print(f"Nascimento: {NASCIMENTO} | Idade atual: {get_idade()}")
    print("------")
    bot.loop.create_task(checar_aniversario())


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    mentioned = bot.user in message.mentions
    nome_citado = "noah" in message.content.lower() and not mentioned

    if mentioned or (nome_citado and random.random() < 0.65):
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip()

        if not content and nome_citado:
            content = message.content.strip()

        if not content:
            content = "OlÃ¡!"

        try:
            async with message.channel.typing():
                contexto = await get_channel_context(message.channel, message.id)
                if contexto:
                    content = f"[Contexto do chat:\n{contexto}\n]\n\n{message.author.display_name} disse: {content}"

                reply = await ask_ai(message.author.id, content)
                if len(reply) > 2000:
                    for i in range(0, len(reply), 2000):
                        await message.reply(reply[i:i + 2000])
                else:
                    await message.reply(reply)
        except Exception as e:
            print(f"Erro ao responder {message.author}: {e}")
            try:
                await message.reply("Eita, deu um errinho aqui... tenta de novo!")
            except Exception:
                pass
        return

    await bot.process_commands(message)


@bot.command()
async def hello(ctx):
    user_id = ctx.author.id
    if user_id == PAI_ID:
        await ctx.send("Oi pai! ðŸ’™ TÃ´ aqui!")
    elif user_id == MAE_ID:
        await ctx.send("Oi mÃ£e! ðŸ’— TÃ´ aqui!")
    else:
        await ctx.send(f"Hey {ctx.author.display_name}! ðŸ‘‹")


@bot.command()
async def idade(ctx):
    hoje = date.today()
    meses_total = (hoje.year - NASCIMENTO.year) * 12 + (hoje.month - NASCIMENTO.month)
    anos = meses_total // 12
    meses = meses_total % 12
    dias = (hoje - NASCIMENTO).days

    embed = discord.Embed(title="ðŸ¼ Idade do Noah", color=discord.Color.gold())
    embed.add_field(name="Nascimento", value=NASCIMENTO.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Hoje", value=hoje.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Idade", value=get_idade(), inline=False)
    embed.add_field(name="Total de dias", value=f"{dias} dias", inline=True)
    embed.add_field(name="Total de meses", value=f"{meses_total} meses", inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! LatÃªncia: {latency}ms")


@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    if guild is None:
        await ctx.send("Este comando sÃ³ pode ser usado em um servidor.")
        return
    embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
    embed.add_field(name="Dono", value=str(guild.owner), inline=True)
    embed.add_field(name="Membros", value=guild.member_count, inline=True)
    embed.add_field(name="Canais", value=len(guild.channels), inline=True)
    embed.add_field(name="Cargos", value=len(guild.roles), inline=True)
    embed.add_field(name="Criado em", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=str(member), color=member.color or discord.Color.blurple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Apelido", value=member.nick or "Nenhum", inline=True)
    embed.add_field(
        name="Entrou no servidor",
        value=member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "N/A",
        inline=True,
    )
    embed.add_field(name="Conta criada em", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(
        name="Cargo principal",
        value=member.top_role.mention if member.top_role else "Nenhum",
        inline=True,
    )
    await ctx.send(embed=embed)


@bot.command()
async def ai(ctx, *, question: str = None):
    if not ai_client:
        await ctx.send("A IA tÃ¡ dormindo, tenta mais tarde!")
        return
    if not question:
        await ctx.send("Me faz uma pergunta! Exemplo: `!ai Qual Ã© a capital do Brasil?`")
        return
    async with ctx.typing():
        try:
            reply = await ask_ai(ctx.author.id, question)
            if len(reply) > 2000:
                for i in range(0, len(reply), 2000):
                    await ctx.send(reply[i:i + 2000])
            else:
                await ctx.send(reply)
        except Exception as e:
            await ctx.send(f"Eita, deu erro: {e}")


@bot.command()
async def clear(ctx):
    user_id = ctx.author.id
    if user_id in conversation_histories:
        del conversation_histories[user_id]
    await ctx.send(f"HistÃ³rico limpo, {ctx.author.display_name}!")


@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="Comandos do Noah",
        description="Aqui estÃ£o os comandos disponÃ­veis:",
        color=discord.Color.green(),
    )
    embed.add_field(name="@Noah <mensagem>", value="Me mencione e eu respondo com IA!", inline=False)
    embed.add_field(name="!hello", value="Receba uma saudaÃ§Ã£o", inline=False)
    embed.add_field(name="!idade", value="Veja minha idade atual", inline=False)
    embed.add_field(name="!ping", value="Veja minha latÃªncia", inline=False)
    embed.add_field(name="!serverinfo", value="InformaÃ§Ãµes do servidor", inline=False)
    embed.add_field(name="!userinfo [@usuÃ¡rio]", value="InformaÃ§Ãµes de um usuÃ¡rio", inline=False)
    embed.add_field(name="!ai <pergunta>", value="FaÃ§a uma pergunta para a IA", inline=False)
    embed.add_field(name="!clear", value="Limpa seu histÃ³rico de conversa", inline=False)
    embed.add_field(name="!help", value="Mostra esta mensagem", inline=False)
    await ctx.send(embed=embed)


token = os.environ.get("DISCORD_BOT_TOKEN")
if not token:
    print("ERROR: DISCORD_BOT_TOKEN environment variable is not set.")
    exit(1)

bot.run(token)
