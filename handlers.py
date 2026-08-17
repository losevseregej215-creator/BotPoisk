from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile
import aiohttp
import os
import tempfile

from config import BOT_TOKEN, SITE_URL
from db import get_profile, save_profile, delete_profile
from models import UserProfile
from keyboards import main_menu_keyboard, profile_action_keyboard, cancel_keyboard

router = Router()

# Состояния для создания анкеты
class ProfileStates(StatesGroup):
    waiting_name = State()
    waiting_bio = State()
    waiting_games = State()
    waiting_avatar = State()

# -------------------- /start --------------------
@router.message(Command("start"))
async def cmd_start(message: Message):
    user = get_profile(message.from_user.id)
    if user:
        await message.answer(
            f"👋 Привет! У тебя уже есть анкета.\n"
            f"Имя: {user.display_name or user.username or 'не указано'}\n"
            f"Игры: {', '.join(user.games) if user.games else 'не указаны'}"
        )
        # Можно показать меню
        await message.answer("Что хочешь сделать?", reply_markup=main_menu_keyboard())
    else:
        await message.answer(
            "👋 Здравствуйте! Это бот Mio — поиск людей по общим играм.\n"
            "Ты можешь создать анкету или импортировать её с сайта Mio.",
            reply_markup=main_menu_keyboard()
        )

# -------------------- Кнопка "Создать анкету" --------------------
@router.callback_query(F.data == "create_profile")
async def create_profile_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 Давай создадим анкету.\n"
        "Введите твой никнейм (или отправь /cancel для отмены)."
    )
    await state.set_state(ProfileStates.waiting_name)
    await callback.answer()

@router.message(ProfileStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(
        "Теперь расскажи о себе (био):",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(ProfileStates.waiting_bio)

@router.message(ProfileStates.waiting_bio)
async def process_bio(message: Message, state: FSMContext):
    await state.update_data(bio=message.text)
    await message.answer(
        "Перечисли игры, в которые ты играешь, через запятую (например: Dota 2, CS2, Minecraft):",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(ProfileStates.waiting_games)

@router.message(ProfileStates.waiting_games)
async def process_games(message: Message, state: FSMContext):
    games = [g.strip() for g in message.text.split(",") if g.strip()]
    await state.update_data(games=games)
    await message.answer(
        "Отправь фото для аватара (или нажми /skip, чтобы пропустить):",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(ProfileStates.waiting_avatar)

@router.message(ProfileStates.waiting_avatar, F.photo)
async def process_avatar(message: Message, state: FSMContext):
    # Скачиваем фото и загружаем на какой-нибудь хостинг (например, Telegram)
    # Для простоты сохраним file_id, но он не вечный. Лучше загрузить на внешний хостинг.
    # Мы просто сохраним file_id как временное решение.
    file_id = message.photo[-1].file_id
    await state.update_data(avatar_file_id=file_id)
    await finish_profile_creation(message, state)

@router.message(ProfileStates.waiting_avatar, F.text == "/skip")
async def skip_avatar(message: Message, state: FSMContext):
    await state.update_data(avatar_file_id=None)
    await finish_profile_creation(message, state)

async def finish_profile_creation(message: Message, state: FSMContext):
    data = await state.get_data()
    profile = UserProfile(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        display_name=data.get("name"),
        bio=data.get("bio"),
        games=data.get("games", []),
        avatar_url=data.get("avatar_file_id")  # сохраняем file_id для отправки
    )
    save_profile(profile)
    await message.answer("✅ Анкета создана!", reply_markup=main_menu_keyboard())
    await state.clear()
    # Показываем анкету
    await show_profile(message, profile)

# -------------------- Кнопка "Взять с Mio" --------------------
@router.callback_query(F.data == "import_from_site")
async def import_from_site(callback: CallbackQuery):
    tg_id = callback.from_user.id
    # Генерируем ссылку на сайт с параметром tg_id
    import_url = f"{SITE_URL}/import.php?tg_id={tg_id}"
    await callback.message.edit_text(
        f"🔗 Перейди по ссылке на сайт, чтобы импортировать анкету с Mio:\n{import_url}\n\n"
        "После подтверждения на сайте, данные придут в бот.",
        reply_markup=None
    )
    await callback.answer()

# -------------------- Приём данных от сайта (через sendMessage) --------------------
# Эта функция не является обработчиком команды, она вызывается извне.
# Мы будем использовать метод sendMessage из бота, но для демонстрации
# создадим обработчик для сообщений с определённым форматом (например, команда /import_data ...).
# Но лучше использовать прямой вызов API.

# Однако мы можем сделать эндпоинт, который будет принимать POST-запросы от сайта.
# Для этого потребуется веб-сервер (aiohttp), но для простоты пусть сайт отправляет сообщение через Bot API.
# Это самый простой способ.

# Мы создадим обработчик, который будет ожидать сообщение с текстом, начинающимся с "IMPORT_DATA:".
# Это небезопасно, но для демонстрации подойдёт.
# В реальном проекте используйте секретный ключ.

@router.message(F.text.startswith("IMPORT_DATA:"))
async def handle_import_data(message: Message):
    # Формат: IMPORT_DATA:{"display_name":"...", "avatar_url":"...", "bio":"...", "games":[...]}
    try:
        import json
        data_str = message.text.split(":", 1)[1]
        data = json.loads(data_str)
        tg_id = message.from_user.id
        # Проверяем, что это тот же пользователь (можно по совпадению с параметром)
        # Сохраняем профиль
        profile = UserProfile(
            tg_id=tg_id,
            username=message.from_user.username,
            display_name=data.get("display_name"),
            avatar_url=data.get("avatar_url"),
            bio=data.get("bio"),
            games=data.get("games", [])
        )
        save_profile(profile)
        await message.answer("✅ Анкета импортирована с сайта!", reply_markup=main_menu_keyboard())
        await show_profile(message, profile)
    except Exception as e:
        await message.answer(f"❌ Ошибка импорта: {e}")

# -------------------- Показ профиля --------------------
async def show_profile(message: Message, profile: UserProfile):
    text = f"👤 <b>{profile.display_name or profile.username}</b>\n"
    if profile.bio:
        text += f"📝 {profile.bio}\n"
    if profile.games:
        text += f"🎮 Игры: {', '.join(profile.games)}\n"
    # Если есть аватар
    if profile.avatar_url:
        # Если это file_id (Telegram), отправляем фото
        if profile.avatar_url.startswith("AgAC"):
            await message.answer_photo(photo=profile.avatar_url, caption=text, parse_mode="HTML")
        else:
            # Если это URL, отправляем как фото
            await message.answer_photo(photo=profile.avatar_url, caption=text, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

# -------------------- Отмена --------------------
@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.", reply_markup=main_menu_keyboard())
    await callback.answer()

# -------------------- Обработка неизвестных команд --------------------
@router.message()
async def unknown(message: Message):
    await message.answer("Используй /start для начала.", reply_markup=main_menu_keyboard())