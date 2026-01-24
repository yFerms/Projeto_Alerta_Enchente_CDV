import telebot
from telebot import types
import json
import os

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
TOKEN_CONTROLE = "8452015218:AAFd0WC9gQ7kKiLqtSo0HYRao_BzlT-GiAU" # Pegue no BotFather
ARQUIVO_TRAVA = "trava_instagram.json"

bot = telebot.TeleBot(TOKEN_CONTROLE)

# Lista de IDs permitidos (Opcional: Coloque seu ID aqui para ninguém mais mexer)
# ADMINS = [123456789] 

# ==============================================================================
# FUNÇÕES DE ESTADO
# ==============================================================================
def ler_estado():
    if os.path.exists(ARQUIVO_TRAVA):
        try:
            with open(ARQUIVO_TRAVA, "r") as f:
                dados = json.load(f)
                return dados.get("ativo", True)
        except:
            return True # Padrão é ligado se der erro
    return True # Padrão é ligado se não existir arquivo

def salvar_estado(ativo):
    with open(ARQUIVO_TRAVA, "w") as f:
        json.dump({"ativo": ativo}, f)

def criar_teclado():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_on = types.KeyboardButton("🟢 ATIVAR POSTAGENS")
    btn_off = types.KeyboardButton("🔴 DESATIVAR TUDO")
    btn_status = types.KeyboardButton("❓ Status Atual")
    markup.add(btn_on, btn_off, btn_status)
    return markup

# ==============================================================================
# COMANDOS DO BOT
# ==============================================================================
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "👮‍♂️ **Painel de Controle - Instagram**\n\nUse os botões para ligar ou desligar as postagens automáticas.", 
                 parse_mode="Markdown", reply_markup=criar_teclado())

@bot.message_handler(func=lambda message: message.text == "🟢 ATIVAR POSTAGENS")
def ativar(message):
    salvar_estado(True)
    bot.reply_to(message, "✅ **SISTEMA ATIVADO!**\nO robô voltará a postar no Instagram se houver alertas.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🔴 DESATIVAR TUDO")
def desativar(message):
    salvar_estado(False)
    bot.reply_to(message, "⛔ **SISTEMA TRAVADO!**\nNenhuma postagem será feita no Instagram até você reativar.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "❓ Status Atual")
def status(message):
    ativo = ler_estado()
    estado = "✅ ONLINE" if ativo else "⛔ PAUSADO"
    bot.reply_to(message, f"Status do Sistema: **{estado}**", parse_mode="Markdown")

print("👮‍♂️ Bot de Controle Iniciado...")
bot.polling()