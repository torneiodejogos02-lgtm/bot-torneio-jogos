import discord
from discord.ext import commands, tasks
import asyncio
import datetime
from datetime import time
import pytz
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import io
import os
from collections import defaultdict
import numpy as np
import json
from dotenv import load_dotenv

# ==================== HEALTH CHECK PARA RENDER ====================
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "🤖 Bot Discord Online - Torneio de Jogos"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True  # Faz a thread morrer quando o main thread morrer
    t.start()

# ==================== CONFIGURAÇÃO SEGURA ====================
load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==================== CONFIGURAÇÃO GOOGLE SHEETS ====================
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

def get_google_credentials():
    """Obtém credenciais do Google Sheets de forma segura"""
    try:
        # 1. Tenta pegar das variáveis de ambiente (Render)
        google_creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        if google_creds_json:
            creds_dict = json.loads(google_creds_json)
            print("✅ Credenciais Google carregadas de variável de ambiente")
            return Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        
        # 2. Fallback para arquivo local (desenvolvimento)
        if os.path.exists('credentials.json'):
            print("✅ Credenciais Google carregadas de arquivo local")
            return Credentials.from_service_account_file('credentials.json', scopes=SCOPE)
        
        print("⚠️  Nenhuma credencial Google encontrada")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao carregar credenciais Google: {e}")
        return None

CREDS = get_google_credentials()
CLIENT = gspread.authorize(CREDS) if CREDS else None

# ==================== CONFIGURAÇÕES ====================
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1ZYr0YdPCuBaEUarOowllx8s4t2bgPYLEdp7OxF6RF0w')
CANAL_RELATORIOS_ID = int(os.environ.get('CANAL_RELATORIOS_ID', '1413645028366090341'))

# Dicionário para armazenar respostas temporariamente
respostas_temp = {}

# Sistema de exclusão de usuários
USUARIOS_EXCLUIDOS = set()
ARQUIVO_EXCLUSAO = "usuarios_excluidos.txt"

# Opções de sentimentos com emojis
SENTIMENTOS = {
    '😟': 'Muito Triste',
    '🙁': 'Triste',
    '😐': 'Neutro',
    '😊': 'Feliz',
    '😁': 'Muito Feliz'
}

# Dias da semana em português
DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

# ==================== FUNÇÕES AUXILIARES ====================
def carregar_usuarios_excluidos():
    global USUARIOS_EXCLUIDOS
    try:
        if os.path.exists(ARQUIVO_EXCLUSAO):
            with open(ARQUIVO_EXCLUSAO, 'r') as f:
                USUARIOS_EXCLUIDOS = set(line.strip() for line in f if line.strip())
            print(f"✅ Carregados {len(USUARIOS_EXCLUIDOS)} usuários excluídos")
    except Exception as e:
        print(f"❌ Erro ao carregar usuários excluídos: {e}")

def salvar_usuarios_excluidos():
    try:
        # Só salva localmente se não estiver no Render
        if not os.environ.get('RENDER'):
            with open(ARQUIVO_EXCLUSAO, 'w') as f:
                for user_id in USUARIOS_EXCLUIDOS:
                    f.write(f"{user_id}\n")
            print(f"💾 Usuários excluídos salvos: {len(USUARIOS_EXCLUIDOS)}")
    except Exception as e:
        print(f"❌ Erro ao salvar usuários excluídos: {e}")

# ==================== EVENTOS DO BOT ====================
@bot.event
async def on_ready():
    keep_alive()  # ⬅️ HEALTH CHECK PARA RENDER
    print(f'{bot.user} está online!')
    print(f'Conectado aos servidores: {[guild.name for guild in bot.guilds]}')
    carregar_usuarios_excluidos()
    
    # Inicia a tarefa agendada para enviar mensagens às 9h
    if not enviar_pesquisa.is_running():
        enviar_pesquisa.start()
    # Inicia a tarefa agendada para enviar relatórios aos domingos
    if not enviar_relatorio.is_running():
        enviar_relatorio.start()

@tasks.loop(hours=24)
async def enviar_pesquisa():
    agora = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    
    # ENVIA APENAS SEGUNDA A SEXTA (0-4 = Segunda a Sexta)
    if agora.hour == 9 and agora.minute == 0 and agora.weekday() < 5:
        print("Enviando pesquisas diárias para todos os membros...")
        
        for guild in bot.guilds:
            for member in guild.members:
                if not member.bot and str(member.id) not in USUARIOS_EXCLUIDOS:
                    try:
                        embed = discord.Embed(
                            title="🎮 Pesquisa de Bem-Estar Diária - Torneio de Jogos",
                            description=f"Bom dia, {member.display_name}! Como você está se sentindo hoje?",
                            color=0x00ff00
                        )
                        
                        embed.add_field(
                            name="Como responder:",
                            value="Reaja com um dos emojis abaixo para indicar seu sentimento:",
                            inline=False
                        )
                        
                        sentimentos_texto = "\n".join([f"{emoji} - {sentimento}" for emoji, sentimento in SENTIMENTOS.items()])
                        embed.add_field(
                            name="Opções:",
                            value=sentimentos_texto,
                            inline=False
                        )
                        
                        embed.add_field(
                            name="📝 Me conte o motivo:",
                            value="Após escolher seu sentimento, responda esta mensagem com o motivo.",
                            inline=False
                        )
                        
                        msg = await member.send(embed=embed)
                        
                        for emoji in SENTIMENTOS.keys():
                            await msg.add_reaction(emoji)
                            
                        respostas_temp[member.id] = {
                            'message_id': msg.id,
                            'sentimento': None,
                            'motivo': None,
                            'username': f"{member.name}#{member.discriminator}"
                        }
                        
                        print(f"Mensagem enviada para {member.display_name}")
                        
                    except discord.Forbidden:
                        print(f"Não foi possível enviar mensagem para {member.display_name} (privadas desativadas)")
                    except Exception as e:
                        print(f"Erro ao enviar mensagem para {member.display_name}: {e}")
                elif str(member.id) in USUARIOS_EXCLUIDOS:
                    print(f"⏭️ Pulando {member.display_name} (usuário excluído)")
    
    elif agora.hour == 9 and agora.minute == 0:
        print("⏭️ Fim de semana - pulando envio de pesquisas")

@enviar_pesquisa.before_loop
async def before_enviar_pesquisa():
    await bot.wait_until_ready()
    print("Agendando envio diário para 9h (horário de Brasília) - apenas dias úteis")
    
    agora = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    if agora.time() > time(9, 0):
        proximo_dia = agora + datetime.timedelta(days=1)
        data_alvo = datetime.datetime.combine(proximo_dia.date(), time(9, 0))
    else:
        data_alvo = datetime.datetime.combine(agora.date(), time(9, 0))
    
    data_alvo = pytz.timezone('America/Sao_Paulo').localize(data_alvo)
    await discord.utils.sleep_until(data_alvo)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
        
    if isinstance(reaction.message.channel, discord.DMChannel) and reaction.message.author == bot.user:
        if str(reaction.emoji) in SENTIMENTOS:
            if user.id in respostas_temp:
                respostas_temp[user.id]['sentimento'] = str(reaction.emoji)
                
                for emoji in SENTIMENTOS.keys():
                    if str(emoji) != str(reaction.emoji):
                        await reaction.message.remove_reaction(emoji, user)
                
                if respostas_temp[user.id]['motivo'] is None:
                    await user.send("💬 **Agora, me conte o motivo para estar se sentindo assim:**\n*(Responda esta mensagem com o motivo)*")

@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel) and message.author != bot.user:
        if message.author.id in respostas_temp:
            if respostas_temp[message.author.id]['motivo'] is None:
                respostas_temp[message.author.id]['motivo'] = message.content
                
                await message.channel.send("🎮 **Muito obrigado por passar seu feedback! Espero que tenhamos um ótimo dia gamer!** 🎮")
                
                await enviar_para_canal_relatorios(message.author)
                await salvar_no_google_sheets(message.author)
    
    await bot.process_commands(message)

async def enviar_para_canal_relatorios(user):
    canal_relatorios = bot.get_channel(CANAL_RELATORIOS_ID)
    
    if canal_relatorios:
        try:
            embed = discord.Embed(
                title="📊 Nova Resposta de Bem-Estar",
                color=0x3498db,
                timestamp=datetime.datetime.now()
            )
            
            embed.set_author(name=respostas_temp[user.id]['username'], icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.add_field(
                name="😊 Sentimento",
                value=SENTIMENTOS[respostas_temp[user.id]['sentimento']],
                inline=True
            )
            embed.add_field(
                name="📅 Data",
                value=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                inline=True
            )
            embed.add_field(
                name="📝 Motivo",
                value=respostas_temp[user.id]['motivo'][:1024],
                inline=False
            )
            
            await canal_relatorios.send(embed=embed)
            print(f"Resposta de {user.display_name} enviada para o canal de relatórios")
            
        except Exception as e:
            print(f"Erro ao enviar para canal de relatórios: {e}")

async def salvar_no_google_sheets(user):
    if not CLIENT:
        print("❌ Google Sheets não disponível - pulando salvamento")
        return
        
    try:
        sheet = CLIENT.open_by_key(SPREADSHEET_ID).sheet1
        
        dados = [
            datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            user.id,
            respostas_temp[user.id]['username'],
            SENTIMENTOS[respostas_temp[user.id]['sentimento']],
            respostas_temp[user.id]['motivo']
        ]
        
        sheet.append_row(dados)
        print(f"Dados de {user.display_name} salvos no Google Sheets")
        
        # Remove do dicionário temporário
        del respostas_temp[user.id]
        
    except Exception as e:
        print(f"Erro ao salvar no Google Sheets: {e}")

@tasks.loop(hours=24)
async def enviar_relatorio():
    agora = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
    if agora.weekday() == 6 and agora.hour == 10:  # Domingo às 10h
        print("Gerando relatórios semanais...")
        await gerar_relatorios_semanais()

async def gerar_relatorios_semanais():
    if not CLIENT:
        print("❌ Google Sheets não disponível - pulando relatório")
        return
        
    try:
        sheet = CLIENT.open_by_key(SPREADSHEET_ID).sheet1
        dados = sheet.get_all_values()
        
        if dados and len(dados) > 1:
            dados_por_usuario = defaultdict(list)
            
            for linha in dados[1:]:
                if len(linha) >= 5:
                    try:
                        usuario_id = linha[1]
                        usuario_nome = linha[2]
                        sentimento = linha[3]
                        motivo = linha[4]
                        
                        data = datetime.datetime.strptime(linha[0], "%d/%m/%Y %H:%M:%S")
                        
                        if data >= datetime.datetime.now() - datetime.timedelta(days=7):
                            dados_por_usuario[usuario_id].append({
                                'data': data,
                                'sentimento': sentimento,
                                'usuario': usuario_nome,
                                'motivo': motivo
                            })
                    except (IndexError, ValueError):
                        continue
            
            for usuario_id, registros in dados_por_usuario.items():
                if registros:
                    registros.sort(key=lambda x: x['data'])
                    
                    # Prepara dados para o gráfico
                    datas = [r['data'] for r in registros]
                    dias_semana = [DIAS_SEMANA[r['data'].weekday()] for r in registros]
                    datas_formatadas = [r['data'].strftime("%d/%m") for r in registros]
                    labels_x = [f"{dias_semana[i]}\n{datas_formatadas[i]}" for i in range(len(datas))]
                    
                    sentimentos_valores = []
                    for r in registros:
                        sentimento = r['sentimento']
                        if sentimento == 'Muito Triste':
                            sentimentos_valores.append(1)
                        elif sentimento == 'Triste':
                            sentimentos_valores.append(2)
                        elif sentimento == 'Neutro':
                            sentimentos_valores.append(3)
                        elif sentimento == 'Feliz':
                            sentimentos_valores.append(4)
                        elif sentimento == 'Muito Feliz':
                            sentimentos_valores.append(5)
                        else:
                            sentimentos_valores.append(3)
                    
                    # Cria o gráfico com visualização melhorada
                    plt.figure(figsize=(12, 8))
                    
                    # Gráfico de linha principal
                    plt.plot(labels_x, sentimentos_valores, marker='o', linestyle='-', 
                            color='#3498db', linewidth=3, markersize=10, markerfacecolor='#e74c3c', 
                            markeredgecolor='#c0392b', markeredgewidth=2)
                    
                    # Preenchimento abaixo da linha
                    plt.fill_between(labels_x, sentimentos_valores, alpha=0.2, color='#3498db')
                    
                                        # Configurações do gráfico
                    plt.title(f"📈 Evolução de Sentimentos - {registros[0]['usuario']}\nSemana: {datas_formatadas[0]} a {datas_formatadas[-1]}", 
                             fontsize=16, fontweight='bold', pad=20, color='#2c3e50')
                    
                    plt.xlabel('Dia da Semana', fontsize=12, fontweight='bold', color='#34495e')
                    plt.ylabel('Nível de Bem-Estar', fontsize=12, fontweight='bold', color='#34495e')
                    
                    plt.ylim(0.8, 5.2)
                    plt.yticks([1, 2, 3, 4, 5], 
                              ['😟 Muito Triste', '🙁 Triste', '😐 Neutro', '😊 Feliz', '😁 Muito Feliz'], 
                              fontsize=10)
                    
                    # Grid e estilo
                    plt.grid(True, alpha=0.3, linestyle='--')
                    plt.gca().set_facecolor('#f8f9fa')
                    plt.gca().spines['top'].set_visible(False)
                    plt.gca().spines['right'].set_visible(False)
                    
                    # Adiciona valores nos pontos
                    for i, (x, y) in enumerate(zip(labels_x, sentimentos_valores)):
                        plt.annotate(f'{y}', (x, y), textcoords="offset points", 
                                    xytext=(0,10), ha='center', fontweight='bold', fontsize=11)
                    
                    plt.tight_layout()
                    
                    # Salva o gráfico
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', 
                               facecolor=plt.gcf().get_facecolor())
                    buf.seek(0)
                    
                    # Envia para o canal
                    canal_relatorios = bot.get_channel(CANAL_RELATORIOS_ID)
                    if canal_relatorios:
                        # Cria embed com estatísticas
                        embed = discord.Embed(
                            title="📊 Relatório Semanal de Bem-Estar",
                            description=f"**{registros[0]['usuario']}** - {len(registros)} resposta(s) esta semana",
                            color=0x3498db
                        )
                        
                        # Estatísticas detalhadas
                        contagem_sentimentos = defaultdict(int)
                        for r in registros:
                            contagem_sentimentos[r['sentimento']] += 1
                        
                        # Emojis para os sentimentos
                        emoji_map = {
                            'Muito Triste': '😟',
                            'Triste': '🙁',
                            'Neutro': '😐',
                            'Feliz': '😊',
                            'Muito Feliz': '😁'
                        }
                        
                        resumo_texto = "\n".join([f"{emoji_map[senti]} {senti}: {count} vez(es)" 
                                                for senti, count in contagem_sentimentos.items()])
                        
                        # Média semanal
                        media_semanal = sum(sentimentos_valores) / len(sentimentos_valores)
                        embed.add_field(name="📋 Resumo Semanal", value=resumo_texto, inline=False)
                        embed.add_field(name="📈 Média Semanal", value=f"{media_semanal:.2f} / 5.00", inline=True)
                        
                        # Sentimento predominante
                        sentimento_pred = max(contagem_sentimentos.items(), key=lambda x: x[1])[0]
                        embed.add_field(name="⭐ Predominante", value=f"{emoji_map[sentimento_pred]} {sentimento_pred}", inline=True)
                        
                        await canal_relatorios.send(embed=embed)
                        await canal_relatorios.send(
                            file=discord.File(buf, filename=f"relatorio_{usuario_id}.png")
                        )
                    
                    plt.close()
                    print(f"Relatório gerado para {registros[0]['usuario']}")
                
    except Exception as e:
        print(f"Erro ao gerar relatórios: {e}")

# ==================== COMANDOS ====================
@bot.command()
@commands.has_permissions(administrator=True)
async def testar_pesquisa(ctx):
    """Comando para testar o envio da pesquisa imediatamente"""
    await ctx.send("🚀 **Iniciando teste de envio de pesquisa...**")
    
    membros_enviados = 0
    membros_erro = 0
    membros_excluidos = 0
    
    for member in ctx.guild.members:
        if not member.bot:
            if str(member.id) in USUARIOS_EXCLUIDOS:
                membros_excluidos += 1
                continue
                
            try:
                embed = discord.Embed(
                    title="🎮 TESTE - Pesquisa de Bem-Estar Diária",
                    description=f"Bom dia, {member.display_name}! Como você está se sentindo hoje?",
                    color=0xffcc00
                )
                
                embed.add_field(
                    name="Como responder:",
                    value="Reaja com um dos emojis abaixo para indicar seu sentimento:",
                    inline=False
                )
                
                sentimentos_texto = "\n".join([f"{emoji} - {sentimento}" for emoji, sentimento in SENTIMENTOS.items()])
                embed.add_field(
                    name="Opções:",
                    value=sentimentos_texto,
                    inline=False
                )
                
                embed.add_field(
                    name="📝 Me conte o motivo:",
                    value="Após escolher seu sentimento, responda esta mensagem com o motivo.",
                    inline=False
                )
                
                embed.set_footer(text="🚨 ESTE É UM TESTE - Mensagem enviada fora do horário regular")
                
                msg = await member.send(embed=embed)
                
                for emoji in SENTIMENTOS.keys():
                    await msg.add_reaction(emoji)
                    
                respostas_temp[member.id] = {
                    'message_id': msg.id,
                    'sentimento': None,
                    'motivo': None,
                    'username': f"{member.name}#{member.discriminator}"
                }
                
                membros_enviados += 1
                print(f"✅ Mensagem de TESTE enviada para {member.display_name}")
                
            except discord.Forbidden:
                print(f"❌ Não foi possível enviar mensagem para {member.display_name} (privadas desativadas)")
                membros_erro += 1
            except Exception as e:
                print(f"❌ Erro ao enviar mensagem para {member.display_name}: {e}")
                membros_erro += 1
    
    embed_resumo = discord.Embed(
        title="📊 Resultado do Teste de Envio",
        color=0x00ff00 if membros_erro == 0 else 0xff9900
    )
    embed_resumo.add_field(name="✅ Mensagens Enviadas", value=str(membros_enviados), inline=True)
    embed_resumo.add_field(name="❌ Erros no Envio", value=str(membros_erro), inline=True)
    embed_resumo.add_field(name="⏭️ Usuários Excluídos", value=str(membros_excluidos), inline=True)
    embed_resumo.add_field(name="👥 Total de Membros", value=str(len([m for m in ctx.guild.members if not m.bot])), inline=True)
    
    await ctx.send(embed=embed_resumo)

@bot.command()
@commands.has_permissions(administrator=True)
async def testar_relatorio(ctx):
    """Comando para testar a geração de relatório imediatamente"""
    await ctx.send("📊 **Iniciando teste de geração de relatório...**")
    
    try:
        await gerar_relatorios_semanais()
        await ctx.send("✅ **Relatório de teste gerado com sucesso!**")
    except Exception as e:
        await ctx.send(f"❌ **Erro ao gerar relatório:** {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def status(ctx):
    embed = discord.Embed(
        title="🤖 Status do Bot",
        description="Bot está online e funcionando perfeitamente!",
        color=0x2ecc71
    )
    embed.add_field(name="Próxima pesquisa", value="9h (horário de Brasília) - Dias úteis", inline=True)
    embed.add_field(name="Próximo relatório", value="Domingo às 10h", inline=True)
    embed.add_field(name="Membros no servidor", value=len(ctx.guild.members), inline=True)
    embed.add_field(name="Usuários excluídos", value=len(USUARIOS_EXCLUIDOS), inline=True)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def excluir_usuario(ctx, usuario: discord.Member = None):
    """Exclui um usuário de receber as mensagens diárias"""
    if usuario is None:
        await ctx.send("❌ **Você precisa mencionar um usuário!** Exemplo: `!excluir_usuario @username`")
        return
    
    if str(usuario.id) in USUARIOS_EXCLUIDOS:
        await ctx.send(f"❌ **{usuario.display_name}** já está na lista de exclusão.")
        return
    
    USUARIOS_EXCLUIDOS.add(str(usuario.id))
    salvar_usuarios_excluidos()
    
    embed = discord.Embed(
        title="✅ Usuário Excluído",
        description=f"**{usuario.display_name}** não receberá mais as mensagens diárias.",
        color=0xff0000
    )
    embed.add_field(name="ID do Usuário", value=usuario.id, inline=True)
    embed.add_field(name="Total de Exclusões", value=len(USUARIOS_EXCLUIDOS), inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def incluir_usuario(ctx, usuario: discord.Member = None):
    """Remove a exclusão de um usuário"""
    if usuario is None:
        await ctx.send("❌ **Você precisa mencionar um usuário!** Exemplo: `!incluir_usuario @username`")
        return
    
    if str(usuario.id) not in USUARIOS_EXCLUIDOS:
        await ctx.send(f"❌ **{usuario.display_name}** não está na lista de exclusão.")
        return
    
    USUARIOS_EXCLUIDOS.discard(str(usuario.id))
    salvar_usuarios_excluidos()
    
    embed = discord.Embed(
        title="✅ Usuário Incluído",
        description=f"**{usuario.display_name}** voltará a receber as mensagens diárias.",
        color=0x00ff00
    )
    embed.add_field(name="ID do Usuário", value=usuario.id, inline=True)
    embed.add_field(name="Total de Exclusões", value=len(USUARIOS_EXCLUIDOS), inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def lista_exclusoes(ctx):
    """Mostra todos os usuários excluídos"""
    if not USUARIOS_EXCLUIDOS:
        await ctx.send("✅ **Nenhum usuário excluído.** Todos receberão as mensagens diárias.")
        return
    
    embed = discord.Embed(
        title="📋 Lista de Usuários Excluídos",
        description=f"Total: {len(USUARIOS_EXCLUIDOS)} usuário(s)",
        color=0xff9900
    )
    
    usuarios_info = []
    for user_id in USUARIOS_EXCLUIDOS:
        try:
            usuario = await bot.fetch_user(int(user_id))
            usuarios_info.append(f"{usuario.name} (`{user_id}`)")
        except:
            usuarios_info.append(f"*Usuário não encontrado* (`{user_id}`)")
    
    for i in range(0, len(usuarios_info), 10):
        chunk = usuarios_info[i:i + 10]
        embed.add_field(
            name=f"Usuários Excluídos {i//10 + 1}",
            value="\n".join(chunk),
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def limpar_exclusoes(ctx):
    """Remove todas as exclusões"""
    if not USUARIOS_EXCLUIDOS:
        await ctx.send("✅ **Não há exclusões para limpar.**")
        return
    
    confirmacao = await ctx.send(f"⚠️ **Tem certeza que deseja remover TODAS as {len(USUARIOS_EXCLUIDOS)} exclusões?** Reaja com ✅ para confirmar.")
    await confirmacao.add_reaction('✅')
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '✅' and reaction.message.id == confirmacao.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        
        USUARIOS_EXCLUIDOS.clear()
        salvar_usuarios_excluidos()
        await ctx.send("✅ **Todas as exclusões foram removidas!** Todos os usuários receberão mensagens.")
        
    except asyncio.TimeoutError:
        await ctx.send("❌ **Tempo esgotado.** Operação cancelada.")

# ==================== INICIALIZAÇÃO ====================
TOKEN = os.environ.get('DISCORD_TOKEN')
if not TOKEN:
    print("❌ ERRO: Token do Discord não encontrado!")
    print("💡 Configure a variável de ambiente DISCORD_TOKEN")
else:
    print("✅ Token do Discord carregado com sucesso!")
    bot.run(TOKEN)