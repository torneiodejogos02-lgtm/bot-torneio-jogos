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

# ==================== CONFIGURAÇÕES SEGURAS ====================
load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configuração SEGURA do Google Sheets
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

try:
    # Tenta pegar das variáveis de ambiente (Railway)
    google_creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if google_creds_json:
        creds_dict = json.loads(google_creds_json)
        CREDS = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        print("✅ Credenciais Google carregadas de variável de ambiente")
    else:
        # Fallback para arquivo local (apenas desenvolvimento)
        CREDS = Credentials.from_service_account_file('credentials.json', scopes=SCOPE)
        print("✅ Credenciais Google carregadas de arquivo local")
except Exception as e:
    print(f"❌ Erro ao carregar credenciais Google: {e}")
    CREDS = None

if CREDS:
    CLIENT = gspread.authorize(CREDS)
else:
    CLIENT = None

SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1ZYr0YdPCuBaEUarOowllx8s4t2bgPYLEdp7OxF6RF0w')
CANAL_RELATORIOS_ID = int(os.environ.get('CANAL_RELATORIOS_ID', '1413645028366090341'))

# ... (o resto do seu código ORIGINAL aqui) ...
# [COLE TODO O SEU CÓDIGO A PARTIR DAQUI, MAS REMOVA A LINHA DO TOKEN!]

# ==================== FINAL SEGURO ====================
TOKEN = os.environ.get('DISCORD_TOKEN')
if not TOKEN:
    print("❌ ERRO: Token do Discord não encontrado!")
    print("💡 Configure a variável de ambiente DISCORD_TOKEN")
else:
    print("✅ Token do Discord carregado com sucesso!")
    bot.run(TOKEN)