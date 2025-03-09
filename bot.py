import os
import time
import telebot
from dotenv import load_dotenv
from web3 import Web3

# Load variabel dari file .env
load_dotenv()

# Ambil variabel lingkungan
BOT_TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
MONAD_RPC = os.getenv("MONAD_RPC")
ETHEREUM_RPC = os.getenv("ETHEREUM_RPC")
CLAIM_AMOUNT = float(os.getenv("CLAIM_AMOUNT", 0.02))
MIN_ETH_BALANCE = float(os.getenv("MIN_ETH_BALANCE", 0.0005))

# Inisialisasi Web3
web3_monad = Web3(Web3.HTTPProvider(MONAD_RPC))
web3_eth = Web3(Web3.HTTPProvider(ETHEREUM_RPC))

# Cek apakah koneksi ke blockchain berhasil
if not web3_monad.is_connected() or not web3_eth.is_connected():
    raise Exception("Gagal terhubung ke salah satu RPC (Monad atau Ethereum Mainnet).")

# Inisialisasi bot Telegram
bot = telebot.TeleBot(BOT_TOKEN)

# Fungsi untuk mengecek saldo ETH di Ethereum Mainnet
def check_eth_balance(user_address):
    balance = web3_eth.eth.get_balance(user_address)
    balance_eth = web3_eth.from_wei(balance, 'ether')
    return balance_eth >= MIN_ETH_BALANCE

# Fungsi untuk mengirim MON ke pengguna
def send_monad(user_address):
    try:
        # Pastikan saldo wallet cukup untuk transaksi
        sender_balance = web3_monad.eth.get_balance(WALLET_ADDRESS)
        if sender_balance < web3_monad.to_wei(CLAIM_AMOUNT, 'ether'):
            return "Faucet kehabisan dana, coba lagi nanti."

        # Buat transaksi
        nonce = web3_monad.eth.get_transaction_count(WALLET_ADDRESS)
        tx = {
            'nonce': nonce,
            'to': user_address,
            'value': web3_monad.to_wei(CLAIM_AMOUNT, 'ether'),
            'gas': 21000,
            'gasPrice': web3_monad.eth.gas_price
        }

        # Tanda tangan transaksi
        signed_tx = web3_monad.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3_monad.eth.send_raw_transaction(signed_tx.rawTransaction)

        return f"✅ Transaksi sukses! Tx Hash: {web3_monad.to_hex(tx_hash)}"

    except Exception as e:
        return f"❌ Gagal mengirim MON: {str(e)}"

# Handler untuk perintah /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🚀 Selamat datang di Monad Faucet!\nKirim alamat wallet Monad Testnet Anda untuk klaim.")

# Handler untuk menangani alamat wallet yang dikirim pengguna
@bot.message_handler(func=lambda message: True)
def handle_wallet_address(message):
    user_address = message.text.strip()

    # Validasi alamat
    if not Web3.is_address(user_address):
        bot.reply_to(message, "⚠️ Alamat tidak valid. Harap kirim alamat wallet Monad Testnet yang benar.")
        return

    # Cek saldo ETH Mainnet
    if not check_eth_balance(user_address):
        bot.reply_to(message, f"❌ Anda harus memiliki setidaknya {MIN_ETH_BALANCE} ETH di Ethereum Mainnet untuk klaim.")
        return

    # Kirim MON ke pengguna
    response = send_monad(user_address)
    bot.reply_to(message, response)

# Jalankan bot
print("Bot berjalan...")
bot.polling()
