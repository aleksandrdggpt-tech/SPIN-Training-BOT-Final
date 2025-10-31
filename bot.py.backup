"""
SPIN Training Bot - Рефакторенная версия v3.0
Содержит только обработчики команд Telegram и координацию сервисов.
"""

# Загрузка переменных окружения из .env файла ПЕРВОЙ СТРОКОЙ
from dotenv import load_dotenv
load_dotenv()

import logging
import time
import os
import sys
import signal
import atexit
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatAction
from telegram.error import Conflict, NetworkError

# Импорты сервисов
from config import Config
from services.llm_service import LLMService
from services.user_service import UserService
from services.achievement_service import AchievementService
from services.training_service import TrainingService
from infrastructure.health_server import start_health_server

# Импорты движка
from engine.scenario_loader import ScenarioLoader, ScenarioValidationError
from engine.question_analyzer import QuestionAnalyzer
from engine.report_generator import ReportGenerator
from engine.case_generator import CaseGenerator

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания состояния приложения
app_instance = None
pid_file = Path("bot.pid")

# Инициализация конфигурации
config = Config()

# Инициализация сервисов
llm_service = LLMService()
user_service = UserService()
achievement_service = AchievementService()

# Инициализация движка
scenario_loader = ScenarioLoader()
question_analyzer = QuestionAnalyzer()
report_generator = ReportGenerator()

# Загрузка сценария
try:
    loaded_scenario = scenario_loader.load_scenario(config.SCENARIO_PATH)
    scenario_config = loaded_scenario.config
    case_generator = CaseGenerator(scenario_config['case_variants'])
    logger.info("Сценарий загружен успешно")
except (FileNotFoundError, ScenarioValidationError) as e:
    logger.error(f"Ошибка загрузки сценария: {e}")
    raise

# Инициализация координирующего сервиса
training_service = TrainingService(
    user_service=user_service,
    llm_service=llm_service,
    achievement_service=achievement_service,
    question_analyzer=question_analyzer,
    report_generator=report_generator,
    case_generator=case_generator,
    scenario_loader=scenario_loader
)


# ==================== УПРАВЛЕНИЕ ПРОЦЕССОМ ====================

def create_pid_file():
    """Создает PID файл для отслеживания процесса."""
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID файл создан: {pid_file}")
    except Exception as e:
        logger.error(f"Ошибка создания PID файла: {e}")


def remove_pid_file():
    """Удаляет PID файл при завершении работы."""
    try:
        if pid_file.exists():
            pid_file.unlink()
            logger.info("PID файл удален")
    except Exception as e:
        logger.error(f"Ошибка удаления PID файла: {e}")


def check_existing_process():
    """Проверяет, не запущен ли уже экземпляр бота."""
    if not pid_file.exists():
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Проверяем, существует ли процесс с этим PID
        try:
            os.kill(pid, 0)  # Отправляем сигнал 0 для проверки существования
            logger.warning(f"Бот уже запущен с PID {pid}")
            return True
        except OSError:
            # Процесс не существует, удаляем устаревший PID файл
            pid_file.unlink()
            logger.info("Удален устаревший PID файл")
            return False
    except (ValueError, FileNotFoundError):
        # PID файл поврежден или удален
        return False


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения работы."""
    logger.info(f"Получен сигнал {signum}, завершаю работу...")
    remove_pid_file()
    if app_instance:
        app_instance.stop()
    # Не завершаем процесс мгновенно, даём приложению корректно остановиться,
    # после чего main() продолжит и выполнит финализацию ресурсов


def setup_signal_handlers():
    """Настраивает обработчики сигналов."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(remove_pid_file)


# ==================== ОБРАБОТЧИКИ КОМАНД ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    t0 = time.perf_counter()
    logger.info(f"🚀 Команда /start вызвана пользователем {update.effective_user.id}")
    user_id = update.effective_user.id
    
    # Сбрасываем сессию и переводим в ожидание старта
    user_service.reset_session(user_id, scenario_config)
    
    # Отправляем приветствие
    welcome_message = scenario_loader.get_message('welcome')
    await update.message.reply_text(welcome_message)
    logger.info(f"⏱ /start handled in {int((time.perf_counter()-t0)*1000)} ms")


async def scenario_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о текущем сценарии."""
    t0 = time.perf_counter()
    try:
        # Берём структурированный блок scenario_info из конфигурации и формируем текст сами
        s_info = scenario_config.get('scenario_info', {})
        name = s_info.get('name', 'Unknown')
        version = s_info.get('version', '')
        description = s_info.get('description', '')
        info_text = f"Сценарий: {name}\nВерсия: {version}\n\n{description}".strip()
        await update.message.reply_text(info_text)
    except Exception as e:
        logger.error(f"Ошибка получения информации о сценарии: {e}")
        await update.message.reply_text(scenario_loader.get_message('error_generic'))
    finally:
        logger.info(f"⏱ /scenario handled in {int((time.perf_counter()-t0)*1000)} ms")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя."""
    t0 = time.perf_counter()
    user_id = update.effective_user.id
    user_data = user_service.get_user_data(user_id)
    stats = user_data['stats']
    
    stats_text = f"""📊 ВАША СТАТИСТИКА:

🎯 Тренировок пройдено: {stats['total_trainings']}
❓ Всего вопросов задано: {stats['total_questions']}
🏆 Лучший результат: {stats['best_score']} баллов
⭐ Текущий уровень: {stats['current_level']}
💎 Опыт (XP): {stats['total_xp']}

Используйте /rank для детальной информации о достижениях."""
    
    await update.message.reply_text(stats_text)
    logger.info(f"⏱ /stats handled in {int((time.perf_counter()-t0)*1000)} ms")


async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детальную информацию о ранге и достижениях."""
    t0 = time.perf_counter()
    user_id = update.effective_user.id
    user_data = user_service.get_user_data(user_id)
    stats = user_data['stats']
    
    # Получаем информацию об уровне
    levels = scenario_config.get('ranking', {}).get('levels', [])
    current_level = stats.get('current_level', 1)
    level_data = next((l for l in levels if l.get('level') == current_level), levels[0] if levels else {})
    
    # Формируем сообщение о ранге
    rank_text = f"""⭐ ВАШ РАНГ:

{level_data.get('emoji', '')} Уровень {current_level}: {level_data.get('name', '')}
💎 Опыт (XP): {stats['total_xp']}
📝 {level_data.get('description', '')}

🎖️ ДОСТИЖЕНИЯ:
"""
    
    # Добавляем информацию о достижениях
    achievements = scenario_config.get('achievements', {}).get('list', [])
    unlocked_achievements = stats.get('achievements_unlocked', [])
    
    for ach in achievements:
        if ach.get('id') in unlocked_achievements:
            rank_text += f"✅ {ach.get('emoji', '')} {ach.get('name', '')} - {ach.get('description', '')}\n"
        else:
            rank_text += f"🔒 {ach.get('emoji', '')} {ach.get('name', '')} - {ach.get('description', '')}\n"
    
    await update.message.reply_text(rank_text)
    logger.info(f"⏱ /rank handled in {int((time.perf_counter()-t0)*1000)} ms")


async def case_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о текущем кейсе."""
    t0 = time.perf_counter()
    user_id = update.effective_user.id
    user_data = user_service.get_user_data(user_id)
    session = user_data['session']
    
    if not session.get('case_data'):
        await update.message.reply_text("Сначала начните тренировку командой /start")
        logger.info(f"⏱ /case handled in {int((time.perf_counter()-t0)*1000)} ms")
        return
    
    case_data = session['case_data']
    case_info = f"""📋 ИНФОРМАЦИЯ О КЕЙСЕ:

👤 Должность: {case_data['position']}
🏢 Компания: {case_data['company']['type']}
📦 Продукт: {case_data['product']['name']}
💰 Объём: {case_data['volume']}
🔄 Частота: {case_data.get('frequency', 'Не указано')}
📊 Поставщиков: {case_data.get('suppliers_count', 'Не указано')}
⚡ Срочность: {case_data.get('urgency', 'Не указано')}"""
    
    await update.message.reply_text(case_info)
    logger.info(f"⏱ /case handled in {int((time.perf_counter()-t0)*1000)} ms")


async def caseinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Алиас команды для информации о кейсе (/caseinfo)."""
    return await case_command(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам бота."""
    t0 = time.perf_counter()
    help_text = """📖 ДОСТУПНЫЕ КОМАНДЫ:

🎯 Основные:
/start - Начать новую тренировку
/stats - Ваша общая статистика
/rank - Детальная информация о ранге и достижениях
/caseinfo - Информация о текущем кейсе

🔧 Дополнительные:
/author - Контакты автора и полезные ссылки
/help - Показать эту справку

💬 Команды в чате:
• "начать" или "старт" - начать тренировку
• "ДА" - получить обратную связь по последнему вопросу
• "завершить" - завершить тренировку и получить отчёт

🎯 Цель: Задавайте SPIN-вопросы клиенту, чтобы выявить его потребности и достичь целевой ясности!"""
    
    await update.message.reply_text(help_text)
    logger.info(f"⏱ /help handled in {int((time.perf_counter()-t0)*1000)} ms")


async def author_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Контакты автора и полезные ссылки."""
    t0 = time.perf_counter()
    text = (
        "Автор бота - Готальский Александр\n\n"
        "🚀 ПОЛЕЗНЫЙ КОНТЕНТ ПО ПРОДЖАМ И ИИ:\n"
        "вы сможете найти на канале Тактика Кутузова @TaktikaKutuzova  \n\n"
        "Хотите научиться работать с ИИ или вам нужна ИИ автоматизация для ускорения работы, пишите на @gotaleks"
    )
    await update.message.reply_text(text)
    logger.info(f"⏱ /author handled in {int((time.perf_counter()-t0)*1000)} ms")


async def validate_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка конфигурации на логические ошибки."""
    t0 = time.perf_counter()
    # Разрешаем только админам
    user_id = update.effective_user.id
    if config.ADMIN_USER_IDS and user_id not in config.ADMIN_USER_IDS:
        logger.warning(f"Пользователь {user_id} попытался вызвать /validate без прав")
        return
    await update.message.reply_text("🔍 Проверяю конфигурацию...")
    
    errors = []
    warnings = []
    
    # Проверка 1: У каждого типа компании есть совместимые продукты
    for company in case_generator.variants['companies']:
        compatible_products = [
            p for p in case_generator.variants['products']
            if company['type'] in p.get('compatible_companies', [])
        ]
        if not compatible_products:
            errors.append(f"❌ {company['type']}: нет совместимых продуктов!")
    
    # Проверка 2: У каждого размера есть должности (если задан positions_by_size)
    positions_by_size = case_generator.variants.get('positions_by_size', {})
    for size in case_generator.variants['company_sizes']:
        if positions_by_size and not positions_by_size.get(size):
            errors.append(f"❌ {size}: нет должностей!")
    
    # Формируем ответ
    if errors:
        response = "❌ ОШИБКИ КОНФИГУРАЦИИ:\n" + "\n".join(errors)
    elif warnings:
        response = "⚠️ ПРЕДУПРЕЖДЕНИЯ:\n" + "\n".join(warnings) + "\n\n✅ Критических ошибок не найдено."
    else:
        response = "✅ Конфигурация корректна!"
    
    await update.message.reply_text(response)
    logger.info(f"⏱ /validate handled in {int((time.perf_counter()-t0)*1000)} ms")


# ==================== ОБРАБОТЧИК СООБЩЕНИЙ ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений."""
    t_msg = time.perf_counter()
    user_id = update.effective_user.id
    message_text = update.message.text
    rules = scenario_config['game_rules']
    # Всегда показываем индикатор набора при получении вопроса пользователя
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # Получаем данные пользователя
    user_data = user_service.get_user_data(user_id)
    session = user_data['session']
    
    # Обработка запуска тренировки из состояния ожидания
    if session.get('chat_state') == 'waiting_start':
        if message_text.lower() in ['начать', 'старт']:
            try:
                t_op = time.perf_counter()
                client_case = await training_service.start_training(user_id, scenario_config)
                await update.message.reply_text(client_case)
                logger.info(f"⏱ start_training handled in {int((time.perf_counter()-t_op)*1000)} ms")
            except Exception as e:
                logger.error(f"Ошибка генерации кейса: {e}")
                await update.message.reply_text('Произошла ошибка при генерации кейса. Попробуйте ещё раз написать "начать".')
        else:
            await update.message.reply_text('Напишите "начать" для старта тренировки')
        logger.info(f"⏱ message (waiting_start) handled in {int((time.perf_counter()-t_msg)*1000)} ms")
        return
    
    # Обработка запроса обратной связи
    if message_text.upper() == 'ДА':
        try:
            # Показываем пользователю, что идёт набор текста
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            # Антидублирование: если недавно запрашивали фидбек или он в процессе — отвечаем сразу
            cooldown_sec = 5
            now_ts = time.time()
            last_ts = float(session.get('last_feedback_ts') or 0)
            in_progress = bool(session.get('feedback_in_progress'))
            if in_progress or (now_ts - last_ts) < cooldown_sec:
                await update.message.reply_text('Фидбек уже генерируется, подождите пару секунд...')
                logger.info(f"Антидублирование фидбека: in_progress={in_progress} delta={now_ts - last_ts:.2f}s")
                return
            session['feedback_in_progress'] = True
            session['last_feedback_ts'] = now_ts
            t_op = time.perf_counter()
            # Попытка стриминга через GPT-5; при ошибке — синхронный путь
            sent = await update.message.reply_text('⏳ Пишу фидбек…')
            try:
                feedback_prompt = await training_service.build_feedback_prompt(user_id, scenario_config)
                chunks = []
                async for delta in llm_service.stream_feedback(feedback_prompt, 'Проанализируй ситуацию'):
                    chunks.append(delta)
                    # Обновляем сообщение батчами, чтобы не спамить Telegram API
                    if len(chunks) % 10 == 0:
                        await context.bot.edit_message_text(
                            chat_id=sent.chat_id,
                            message_id=sent.message_id,
                            text=''.join(chunks) or '…'
                        )
                # Если из стрима ничего не пришло — считаем это неуспехом и уходим в нестрим
                if not ''.join(chunks).strip():
                    raise RuntimeError('empty stream output')
                # Финальный апдейт
                final_text = ''.join(chunks).strip()
                await context.bot.edit_message_text(
                    chat_id=sent.chat_id,
                    message_id=sent.message_id,
                    text=final_text
                )
            except Exception:
                # Резервный нестриминговый путь
                feedback = await training_service.get_feedback(user_id, scenario_config)
                await context.bot.edit_message_text(
                    chat_id=sent.chat_id,
                    message_id=sent.message_id,
                    text=feedback
                )
            logger.info(f"⏱ feedback handled in {int((time.perf_counter()-t_op)*1000)} ms")
        except Exception as e:
            logger.error(f"Ошибка получения обратной связи: {e}")
            await update.message.reply_text(scenario_loader.get_message('error_generic'))
        finally:
            session['feedback_in_progress'] = False
            session['last_feedback_ts'] = time.time()
            logger.info(f"⏱ message (feedback) handled in {int((time.perf_counter()-t_msg)*1000)} ms")
        return
    
    # Обработка завершения тренировки
    if message_text.lower() == 'завершить':
        try:
            t_op = time.perf_counter()
            report = await training_service.complete_training(user_id, scenario_config)
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"⏱ complete_training handled in {int((time.perf_counter()-t_op)*1000)} ms")
        except Exception as e:
            logger.error(f"Ошибка завершения тренировки: {e}")
            await update.message.reply_text(scenario_loader.get_message('error_generic'))
        finally:
            logger.info(f"⏱ message (finish) handled in {int((time.perf_counter()-t_msg)*1000)} ms")
        return
    
    # Проверка на короткие вопросы
    if len(message_text) <= rules.get('short_question_threshold', 5):
        await update.message.reply_text('Задайте более развернутый вопрос клиенту или напишите "начать" для новой тренировки.')
        return
    
    # Проверка максимального количества вопросов
    if session['question_count'] >= rules['max_questions']:
        try:
            report = await training_service.complete_training(user_id, scenario_config)
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Ошибка завершения тренировки: {e}")
            await update.message.reply_text(scenario_loader.get_message('error_generic'))
        return
    
    # Обработка вопроса пользователя
    try:
        # Покажем индикатор набора перед генерацией первого ответа клиента
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        t_op = time.perf_counter()
        response_message = await training_service.process_question(user_id, message_text, scenario_config)
        logger.info(f"⏱ process_question handled in {int((time.perf_counter()-t_op)*1000)} ms")
        
        # Проверяем условия завершения после обработки вопроса
        is_complete, completion_reason = training_service.check_training_completion(user_id, scenario_config)
        
        if is_complete:
            if completion_reason == "clarity_reached":
                await update.message.reply_text(response_message)
                await update.message.reply_text(
                    scenario_loader.get_message('clarity_reached', clarity=session['clarity_level'])
                )
            elif completion_reason == "max_questions":
                try:
                    report = await training_service.complete_training(user_id, scenario_config)
                    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logger.error(f"Ошибка завершения тренировки: {e}")
                    await update.message.reply_text(scenario_loader.get_message('error_generic'))
        else:
            await update.message.reply_text(response_message)
    
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await update.message.reply_text(scenario_loader.get_message('error_generic'))
    finally:
        logger.info(f"⏱ message handled in {int((time.perf_counter()-t_msg)*1000)} ms")


# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

def main():
    """Главная функция приложения."""
    global app_instance
    
    # Проверка на дублирование процессов
    if check_existing_process():
        print("❌ Бот уже запущен! Остановите предыдущий экземпляр перед запуском нового.")
        print("Используйте команду: kill $(cat bot.pid)")
        return
    
    # Настройка обработчиков сигналов
    setup_signal_handlers()
    
    # Создание PID файла
    create_pid_file()
    
    # Валидация конфигурации
    try:
        config.validate()
        config.print_config()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        print(f"❌ Ошибка конфигурации: {e}")
        print("Убедитесь, что установлены переменные окружения BOT_TOKEN и хотя бы один API ключ")
        remove_pid_file()
        return
    
    try:
        # Создание приложения
        application = Application.builder().token(config.BOT_TOKEN).build()
        app_instance = application
        
        # Добавление обработчиков команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("scenario", scenario_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("rank", rank_command))
        application.add_handler(CommandHandler("case", case_command))
        application.add_handler(CommandHandler("caseinfo", caseinfo_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("validate", validate_config_command))
        application.add_handler(CommandHandler("author", author_command))
        
        # Добавление обработчика текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Запуск health check сервера
        start_health_server(config.PORT)
        
        # Запуск бота с обработкой ошибок
        logger.info("🚀 Бот запущен")
        print("✅ Бот успешно запущен!")
        print(f"📊 Health check доступен на порту {config.PORT}")
        print("🛑 Для остановки используйте Ctrl+C или команду: kill $(cat bot.pid)")
        
        # Лёгкий прогрев LLM моделей (неблокирующе)
        try:
            import asyncio as _asyncio
            _asyncio.get_event_loop().create_task(llm_service.warmup())
        except Exception:
            pass

        application.run_polling()
        
    except Conflict as e:
        logger.error(f"Конфликт с Telegram API: {e}")
        print("❌ Ошибка: Бот уже запущен в другом месте!")
        print("Убедитесь, что не запущено других экземпляров бота.")
        remove_pid_file()
        return
        
    except NetworkError as e:
        logger.error(f"Ошибка сети: {e}")
        print("❌ Ошибка сети. Проверьте подключение к интернету.")
        remove_pid_file()
        return
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
        print("\n🛑 Остановка бота...")
        remove_pid_file()
        return
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        print(f"❌ Неожиданная ошибка: {e}")
        remove_pid_file()
        return
    finally:
        # Грейсфул закрытие HTTP клиентов LLMService
        try:
            import asyncio as _asyncio
            _asyncio.run(llm_service.aclose())
        except Exception:
            pass


if __name__ == '__main__':
    main()
