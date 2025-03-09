import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from web3 import Web3

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("8111877969:AAF2tWvGnJw2B-_Wf7TnymlZ4x4vB7M9zSA")
PRIVATE_KEY = os.getenv("ff0aab1e0e2c812b3efb176bfd3e42e28a96dc6f803cd2d4aa20850c02ce40f1")
WALLET_ADDRESS = os.getenv("0xA2D53bbDf3E89d54ce4f05e759ec5f91Af8BCe85")
MONAD_RPC = os.getenv("https://testnet-rpc.monad.xyz/")
ETHEREUM_RPC = os.getenv("https://mainnet.infura.io/v3/8ae12dcdae6e4c5ebce63791a0ce0d60")
CLAIM_AMOUNT = float(os.getenv("CLAIM_AMOUNT", 0.02))
MIN_ETH_BALANCE = float(os.getenv("MIN_ETH_BALANCE", 0.0005))

# Setup Web3
web3_monad = Web3(Web3.HTTPProvider(MONAD_RPC))
web3_eth = Web3(Web3.HTTPProvider(ETHEREUM_RPC))

wallet_address = web3_monad.to_checksum_address(WALLET_ADDRESS)
wallet_private_key = PRIVATE_KEY

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Store claimed users (anti-spam system)
claimed_users = {}

async def check_eth_balance(user_wallet):
    """ Mengecek saldo ETH di Ethereum Mainnet """
    try:
        user_wallet = web3_eth.to_checksum_address(user_wallet)
        balance = web3_eth.eth.get_balance(user_wallet)
        balance_eth = web3_eth.from_wei(balance, "ether")
        return balance_eth >= MIN_ETH_BALANCE
    except Exception as e:
        logging.error(f"Error checking ETH balance: {e}")
        return False

async def send_monad(receiver_address):
    """ Mengirim MON ke pengguna """
    try:
        receiver_address = web3_monad.to_checksum_address(receiver_address)
        sender_balance = web3_monad.eth.get_balance(wallet_address)

        if sender_balance < web3_monad.to_wei(CLAIM_AMOUNT, "ether"):
            return "⚠️ Saldo faucet tidak cukup!"

        nonce = web3_monad.eth.get_transaction_count(wallet_address)
        tx = {
            "nonce": nonce,
            "to": receiver_address,
            "value": web3_monad.to_wei(CLAIM_AMOUNT, "ether"),
            "gas": 21000,
            "gasPrice": web3_monad.eth.gas_price,
        }
        
        signed_tx = web3_monad.eth.account.sign_transaction(tx, wallet_private_key)
        tx_hash = web3_monad.eth.send_raw_transaction(signed_tx.rawTransaction)
        return f"✅ 0.02 MON telah dikirim! TxHash: {tx_hash.hex()}"

    except Exception as e:
        logging.error(f"Error: {e}")
        return "❌ Terjadi kesalahan dalam mengirim MON."

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("🚀 Selamat datang di Monad Faucet!\n\n"
                         "Gunakan /claim untuk klaim 0.02 MON setiap 24 jam.\n"
                         "Masukkan alamat wallet Monad Anda untuk menerima MON.")

@dp.message(Command("claim"))
async def claim_command(message: types.Message):
    user_id = message.from_user.id

    if user_id in claimed_users:
        await message.answer("⏳ Anda sudah klaim! Silakan coba lagi nanti.")
        return

    await message.answer("🔹 Kirimkan alamat wallet Monad Anda:")
    dp.message.register(wallet_input, user_id=user_id)

async def wallet_input(message: types.Message):
    user_id = message.from_user.id
    user_wallet = message.text.strip()

    if not web3_monad.is_address(user_wallet):
        await message.answer("⚠️ Alamat wallet tidak valid! Kirimkan alamat Monad yang benar.")
        return

    await message.answer("⏳ Mengecek saldo ETH Mainnet Anda...")

    eth_valid = await check_eth_balance(user_wallet)
    if not eth_valid:
        await message.answer("❌ Anda harus memiliki minimal 0.0005 ETH di Ethereum Mainnet untuk klaim.")
        return

    claimed_users[user_id] = True
    await message.answer("🔄 Memproses transaksi...")
    result = await send_monad(user_wallet)
    await message.answer(result)

# Start bot
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
