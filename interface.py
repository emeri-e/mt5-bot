import asyncio
import threading
import logging
# from aiogram import Bot, Dispatcher, types
# from aiogram.types import Message
# from aiogram.filters import CommandStart, Command
# from aiogram.enums.parse_mode import ParseMode
# from aiogram.client.default import DefaultBotProperties
# from aiogram.utils.markdown import hbold
import MetaTrader5 as mt5
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import MessageHandler, filters

from functions import load_accounts
from mt5.utils import initialize_mt5, shutdown_mt5
from config import base

# === Logger ===
logger = logging.getLogger("mybot")
# logging.basicConfig(level=logging.INFO)

# === Shared Resources ===
ACCOUNTS = load_accounts()


# # === Aiogram Bot Setup ===
# BOT_TOKEN = base.BOT_TOKEN

# bot = Bot(
#     token=BOT_TOKEN,
#     default=DefaultBotProperties(parse_mode=ParseMode.HTML)
# )
# dp = Dispatcher()


ORDER_STATES = {
    mt5.ORDER_STATE_STARTED: "started",
    mt5.ORDER_STATE_PLACED: "placed",
    mt5.ORDER_STATE_FILLED: "filled",
    mt5.ORDER_STATE_CANCELED: "canceled",
    mt5.ORDER_STATE_PARTIAL: "partial",
    mt5.ORDER_STATE_REJECTED: "rejected",
    mt5.ORDER_STATE_EXPIRED: "expired",
}



# === MT5 Helpers ===

@base.mt5_locked
def get_all_positions():
    orders = mt5.orders_get()
    positions = mt5.positions_get()
    return (orders or () ) + (positions or () )

@base.mt5_locked
def close_all_positions():
    success = False
    all_items = get_all_positions()
    price_info_cache = {}  # To avoid repeat calls for symbol price

    for item in all_items:
        order_id = item.ticket
        symbol = item.symbol
        # volume = item.volume_current
        order_type = item.type
        state = item.state if hasattr(item, "state") else mt5.ORDER_STATE_FILLED  # assume filled for positions
        magic = item.magic if hasattr(item, "magic") else 0

        if isinstance(item, mt5.TradePosition):
            volume = item.volume
        elif isinstance(item, mt5.TradeOrder):
            volume = item.volume_current
        else:
            # Unknown type
            volume = 'unknown'
            continue
        if symbol not in price_info_cache:
            price_info_cache[symbol] = mt5.symbol_info_tick(symbol)

        price_info = price_info_cache[symbol]
        if not price_info:
            continue

        if state == mt5.ORDER_STATE_FILLED:
            close_type = mt5.ORDER_TYPE_SELL if order_type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = price_info.bid if order_type == mt5.ORDER_TYPE_BUY else price_info.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": order_id,
                "symbol": symbol,
                "volume": volume,
                "type": close_type,
                "price": price,
                "deviation": 10,
                "magic": magic,
            }

        elif state == mt5.ORDER_STATE_PLACED:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order_id,
                "symbol": symbol,
                "magic": magic,
            }

        else:
            continue

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            success = True

    return success


# # === Telegram Bot Commands ===

# @dp.message(CommandStart())
# async def cmd_start(message: Message):
#     await message.answer("✅ MT5 Interface Bot Active.\nUse /positions or /closeall")


# @dp.message(Command("positions"))
# async def cmd_positions(message: Message):
#     output = []
#     for acc in ACCOUNTS:
#         login, password, server, username = acc["login"], acc["password"], acc["server"], acc["username"]
#         if initialize_mt5(int(login), password, server):
#             positions = get_all_positions()
#             shutdown_mt5()
#             if positions:
#                 details = "\n".join([
#                     f"{p.symbol} | Vol: {p.volume_current} | Entry: {getattr(p, 'price_open', '-'):.5f} | "
#                     f"SL: {getattr(p, 'sl', '-'):.5f} | TP: {getattr(p, 'tp', '-'):.5f} | "
#                     f"State: {ORDER_STATES.get(p.state, 'unknown')}"
#                     for p in positions
#                 ])
#                 output.append(f"{hbold(username)}:\n{details}")
#             else:
#                 output.append(f"{hbold(username)}: No open or placed positions")
#         else:
#             output.append(f"{hbold(username)}: mt5 login failed")
#     await message.answer("\n\n".join(output))


# @dp.message(Command("closeall"))
# async def cmd_closeall(message: Message):
#     results = []
#     for acc in ACCOUNTS:
#         login, password, server, username = acc["login"], acc["password"], acc["server"], acc["username"]
#         if initialize_mt5(int(login), password, server):
#             closed = close_all_positions()
#             shutdown_mt5()
#             results.append(f"{hbold(username)}: {'✅ Closed all' if closed else '❌ No positions or error'}")
#     await message.answer("\n".join(results))



# === Bot Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ MT5 Interface Bot Active.\nUse /positions or /closeall",
        parse_mode=ParseMode.HTML
    )


async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        chat_title = message.forward_from_chat.title or "No Title"
        await message.reply_text(
            f"📨 Forwarded from: <b>{chat_title}</b>\n🆔 Chat ID: <code>{chat_id}</code>",
            parse_mode='HTML'
        )
    else:
        await message.reply_text("This message was not forwarded from a channel or group.")

async def positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = []
    for acc in ACCOUNTS:
        login, password, server, username = acc["login"], acc["password"], acc["server"], acc["username"]
        if initialize_mt5(int(login), password, server):
            positions = get_all_positions()
            shutdown_mt5()
            if positions:
                details = "\n".join([
                    f"{p.symbol} | Vol: {p.volume if isinstance(p, mt5.TradePosition) else p.volume_current } | Entry: {getattr(p, 'price_open', '-'):.5f} | "
                    f"SL: {getattr(p, 'sl', '-'):.5f} | TP: {getattr(p, 'tp', '-'):.5f} | "
                    f"State: {ORDER_STATES.get(p.state if hasattr(p, "state") else mt5.ORDER_STATE_FILLED, 'unknown')}"
                    for p in positions
                ])
                output.append(f"<b>{username}</b>:\n{details}")
            else:
                output.append(f"<b>{username}</b>: No open or placed positions")
        else:
            output.append(f"<b>{username}</b>: mt5 login failed")

    await update.message.reply_text("\n\n".join(output), parse_mode=ParseMode.HTML)

async def closeall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = []
    for acc in ACCOUNTS:
        login, password, server, username = acc["login"], acc["password"], acc["server"], acc["username"]
        if initialize_mt5(int(login), password, server):
            closed = close_all_positions()
            shutdown_mt5()
            results.append(f"<b>{username}</b>: {'✅ Closed all' if closed else '❌ No positions or error'}")

        else:
            results.append(f"<b>{username}</b>: mt5 login failed")
    await update.message.reply_text("\n".join(results), parse_mode=ParseMode.HTML)


async def forwarded_from_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    # Check if the message is forwarded and from a chat
    if message and message.forward_origin:
        origin = message.forward_origin
        if hasattr(origin, "chat"):
            chat_id = origin.chat.id
            chat_title = origin.chat.title or "Unnamed"
            await message.reply_text(
                f"📨 Forwarded from: <b>{chat_title}</b>\n🆔 Chat ID: <code>{chat_id}</code>",
                parse_mode="HTML"
            )
        else:
            await message.reply_text("✅ This is a forwarded message, but I couldn't get the chat info.")
    else:
        await message.reply_text("This message was not forwarded from a public chat.")

# === App Setup ===
def create_bot_app():
    application = Application.builder().token(base.BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("positions", positions))
    application.add_handler(CommandHandler("closeall", closeall))

    # Add forwarded message handler (DM only)
    # application.add_handler(
    #     MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, handle_forwarded_message)
    # )
    application.add_handler(
        MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, forwarded_from_handler)
    )
    return application