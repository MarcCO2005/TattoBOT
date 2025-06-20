import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from google_calendar import GoogleCalendarManager
from datetime import datetime, timedelta, date
import calendar as pycalendar

TOKEN = '7551871687:AAFziyofUUqgIGkumgv5BmesS0zO-FjC0LE'
DB_PATH = 'citas.db'
OWNER_ID = "522262079"  # Cambia esto por tu user_id real si es necesario
AGREGAR_HORARIO, ELEGIR_MES, ELEGIR_DIA, ESPERAR_HORA_HORARIO = 100, 101, 102, 103

# Estados de la conversaci
NOMBRE, TELEFONO, CONTACTAR, SOLICITAR_CITA, FECHA, HORA, CONFIRMAR = range(7)

contact_info_text = """
📌 Dirección: Calle del Tatuaje, 123
📞 Teléfono: +34 123 456 789

"""

contact_info_buttons = [
    [
        InlineKeyboardButton("📍 Google Maps", url="https://www.google.com"),
        InlineKeyboardButton("✉️ Email", url="https://www.google.com"),
        InlineKeyboardButton("📸 Instagram", url="https://www.google.com"),
        InlineKeyboardButton("🌐 Web", url="https://www.google.com")
    ]
]

calendar = GoogleCalendarManager()

# --- FUNCIONES DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS fechas_disponibles (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS horas_disponibles (id INTEGER PRIMARY KEY AUTOINCREMENT, hora TEXT UNIQUE)''')
    conn.commit()
    conn.close()

def init_pending_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS citas_pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            telefono TEXT,
            fecha TEXT,
            hora TEXT,
            estado TEXT DEFAULT 'pendiente',
            user_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_available_dates():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT fecha FROM fechas_disponibles ORDER BY fecha')
    fechas = [row[0] for row in c.fetchall()]
    conn.close()
    return fechas

def get_available_times():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT hora FROM horas_disponibles ORDER BY hora')
    horas = [row[0] for row in c.fetchall()]
    conn.close()
    return horas

def add_sample_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Fechas de ejemplo
    sample_dates = ["2025-06-20", "2025-06-21", "2025-06-22"]
    for fecha in sample_dates:
        c.execute('INSERT OR IGNORE INTO fechas_disponibles (fecha) VALUES (?)', (fecha,))
    # Horas de ejemplo
    sample_times = ["10:00", "12:00", "15:00", "17:00"]
    for hora in sample_times:
        c.execute('INSERT OR IGNORE INTO horas_disponibles (hora) VALUES (?)', (hora,))
    conn.commit()
    conn.close()

# --- FLUJO DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    if user_id == OWNER_ID:
        keyboard = [
            [InlineKeyboardButton("Revisar citas pendientes", callback_data="panel_revisar")],
            [InlineKeyboardButton("Agregar horario disponible", callback_data="panel_agregar_horario")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Panel de propietario:\n¿Qué quieres hacer?",
            reply_markup=reply_markup
        )
        return AGREGAR_HORARIO
    else:
        await update.message.reply_text("¡Bienvenido! ¿Cómo te llamas?")
        return NOMBRE

async def pedir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data if context.user_data is not None else {}
    if update.message and update.message.text:
        user_data['nombre'] = update.message.text
        await update.message.reply_text("¿Cuál es tu número de teléfono?")
        return TELEFONO
    else:
        print("update.message o update.message.text es None en pedir_telefono")
        return ConversationHandler.END

async def pedir_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data if context.user_data is not None else {}
    if update.message and update.message.text:
        user_data['telefono'] = update.message.text
        keyboard = [
            [InlineKeyboardButton("Contactar", callback_data=str(CONTACTAR))],
            [InlineKeyboardButton("Solicitar cita", callback_data=str(SOLICITAR_CITA))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        nombre = user_data.get('nombre', 'Usuario')
        await update.message.reply_text(
            f"¡Gracias, {nombre}! ¿Qué quieres hacer?",
            reply_markup=reply_markup
        )
        return CONTACTAR
    else:
        print("update.message o update.message.text es None en pedir_menu")
        return ConversationHandler.END

async def contactar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    reply_markup = InlineKeyboardMarkup(contact_info_buttons)
    if query is not None:
        await query.answer()
        await query.edit_message_text(text=contact_info_text, reply_markup=reply_markup)
    else:
        print("callback_query es None en contactar")
    return ConversationHandler.END

async def solicitar_cita(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is not None:
        await query.answer()
        keyboard = []
        fechas = get_available_dates()
        for date in fechas:
            keyboard.append([InlineKeyboardButton(date, callback_data=f"fecha_{date}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Selecciona una fecha para tu cita:", reply_markup=reply_markup)
    else:
        print("callback_query es None en solicitar_cita")
    return FECHA

async def seleccionar_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_data = context.user_data if context.user_data is not None else {}
    if query is not None and query.data:
        await query.answer()
        if '_' in query.data:
            selected_date = query.data.split('_', 1)[1]
            user_data['fecha'] = selected_date
            keyboard = []
            horas = get_available_times()
            for time in horas:
                keyboard.append([InlineKeyboardButton(time, callback_data=f"hora_{time}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="Selecciona una hora para tu cita:", reply_markup=reply_markup)
        else:
            print("query.data no tiene el formato esperado en seleccionar_fecha")
    else:
        print("callback_query o query.data es None en seleccionar_fecha")
    return HORA

async def seleccionar_hora(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_data = context.user_data if context.user_data is not None else {}
    if query is not None and query.data:
        await query.answer()
        if '_' in query.data:
            selected_time = query.data.split('_', 1)[1]
            user_data['hora'] = selected_time
            keyboard = [
                [InlineKeyboardButton("Confirmar", callback_data="confirmar")],
                [InlineKeyboardButton("Cancelar", callback_data="cancelar")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            fecha = user_data.get('fecha', 'NO_FECHA')
            hora = user_data.get('hora', 'NO_HORA')
            await query.edit_message_text(text=f"¿Confirmas tu cita para el {fecha} a las {hora}?", reply_markup=reply_markup)
        else:
            print("query.data no tiene el formato esperado en seleccionar_hora")
    else:
        print("callback_query o query.data es None en seleccionar_hora")
    return CONFIRMAR

async def confirmar_cita(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_data = context.user_data if context.user_data is not None else {}
    if query is not None and query.data:
        await query.answer()
        if query.data == "confirmar":
            fecha = user_data.get('fecha', None)
            hora = user_data.get('hora', None)
            nombre = user_data.get('nombre', 'Sin nombre')
            telefono = user_data.get('telefono', 'Sin teléfono')
            user_id = update.effective_user.id if update.effective_user else None
            if fecha and hora:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    # Verificar si ya tiene una cita pendiente
                    c.execute('SELECT id FROM citas_pendientes WHERE user_id = ? AND estado = "pendiente"', (user_id,))
                    row = c.fetchone()
                    if row:
                        cita_id = row[0]
                        keyboard = [[InlineKeyboardButton("Cancelar cita", callback_data=f"cancelar_cita_{cita_id}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(
                            text="Ya tienes una cita pendiente de aceptación.\n\nPuedes cancelarla para reservar otra.",
                            reply_markup=reply_markup
                        )
                        conn.close()
                        return ConversationHandler.END
                    # Si no tiene cita pendiente, la guarda
                    c.execute('''
                        INSERT INTO citas_pendientes (nombre, telefono, fecha, hora, user_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (nombre, telefono, fecha, hora, user_id))
                    cita_id = c.lastrowid
                    conn.commit()
                    conn.close()
                    keyboard = [[InlineKeyboardButton("Cancelar cita", callback_data=f"cancelar_cita_{cita_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        text=f"✅ Cita enviada para revisión.\nTe confirmaremos si ha sido aceptada.",
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    print(f"Error al guardar la cita pendiente: {e}")
                    await query.edit_message_text(text=f"❌ Error al guardar la cita: {e}")
            else:
                await query.edit_message_text(text="❌ Faltan datos para crear la cita.")
        else:
            await query.edit_message_text(text="❌ Cita cancelada.")
    else:
        print("callback_query o query.data es None en confirmar_cita")
    return ConversationHandler.END

async def cancelar_cita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is not None and query.data and query.data.startswith("cancelar_cita_"):
        await query.answer()
        cita_id = int(query.data.split('_')[-1])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM citas_pendientes WHERE id = ?', (cita_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text("❌ Tu cita pendiente ha sido cancelada. Ahora puedes reservar otra.")
    else:
        await query.edit_message_text("No se pudo cancelar la cita.")

async def revisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id if update.effective_chat else None
    if str(update.effective_user.id) != OWNER_ID:
        if update.message:
            await update.message.reply_text("No tienes permisos para esto.")
        elif update.callback_query and chat_id:
            await context.bot.send_message(chat_id=chat_id, text="No tienes permisos para esto.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, nombre, telefono, fecha, hora FROM citas_pendientes WHERE estado = 'pendiente'")
    citas = c.fetchall()
    conn.close()

    if not citas:
        if update.message:
            await update.message.reply_text("No hay citas pendientes.")
        elif update.callback_query and chat_id:
            await context.bot.send_message(chat_id=chat_id, text="No hay citas pendientes.")
        return

    for cita in citas:
        id, nombre, telefono, fecha, hora = cita
        keyboard = [
            [InlineKeyboardButton("✅ Aceptar", callback_data=f"aceptar_{id}"),
             InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"📅 Cita #{id}:\n👤 {nombre}\n📞 {telefono}\n📆 {fecha} a las 🕒 {hora}"
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query and chat_id:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

async def gestionar_cita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, cita_id = query.data.split('_')
    cita_id = int(cita_id)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if action == "aceptar":
        c.execute("SELECT nombre, telefono, fecha, hora, user_id FROM citas_pendientes WHERE id = ?", (cita_id,))
        row = c.fetchone()
        if row:
            nombre, telefono, fecha, hora, user_id = row
            start_dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
            end_dt = start_dt + timedelta(hours=1)
            descripcion = f'Cita reservada por {nombre}, teléfono: {telefono}.'
            link = calendar.create_event(
                summary='Cita de tatuaje',
                description=descripcion,
                start_time=start_dt.isoformat(),
                end_time=end_dt.isoformat(),
                timezone='Europe/Madrid'
            )
            c.execute("UPDATE citas_pendientes SET estado = 'aceptada' WHERE id = ?", (cita_id,))
            await query.edit_message_text(f"✅ Cita #{cita_id} aceptada y añadida a Google Calendar.\n[Ver evento]({link})", parse_mode='Markdown')
            # Notificar al cliente
            if user_id:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ Tu cita para el {fecha} a las {hora} ha sido aceptada. ¡Te esperamos!"
                    )
                except Exception as e:
                    print(f'No se pudo notificar al usuario: {e}')
        else:
            await query.edit_message_text("❌ No se encontró la cita.")
    elif action == "rechazar":
        c.execute("UPDATE citas_pendientes SET estado = 'rechazada' WHERE id = ?", (cita_id,))
        await query.edit_message_text(f"❌ Cita #{cita_id} rechazada.")
    conn.commit()
    conn.close()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Operación cancelada.')
    return ConversationHandler.END

# Handler para el panel de propietario
async def panel_propietario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is not None and query.data:
        await query.answer()
        if query.data == "panel_revisar":
            await revisar(update, context)
            return AGREGAR_HORARIO
        elif query.data == "panel_agregar_horario":
            # Mostrar los 12 meses del año como botones + volver
            meses = [
                [InlineKeyboardButton("Enero", callback_data="mes_01")],
                [InlineKeyboardButton("Febrero", callback_data="mes_02")],
                [InlineKeyboardButton("Marzo", callback_data="mes_03")],
                [InlineKeyboardButton("Abril", callback_data="mes_04")],
                [InlineKeyboardButton("Mayo", callback_data="mes_05")],
                [InlineKeyboardButton("Junio", callback_data="mes_06")],
                [InlineKeyboardButton("Julio", callback_data="mes_07")],
                [InlineKeyboardButton("Agosto", callback_data="mes_08")],
                [InlineKeyboardButton("Septiembre", callback_data="mes_09")],
                [InlineKeyboardButton("Octubre", callback_data="mes_10")],
                [InlineKeyboardButton("Noviembre", callback_data="mes_11")],
                [InlineKeyboardButton("Diciembre", callback_data="mes_12")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="volver_panel_propietario")]
            ]
            reply_markup = InlineKeyboardMarkup(meses)
            await query.edit_message_text("Selecciona el mes para el nuevo horario:", reply_markup=reply_markup)
            return ELEGIR_MES
    return AGREGAR_HORARIO

async def elegir_mes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is not None and query.data:
        if query.data == "volver_panel_propietario":
            # Volver al panel propietario
            keyboard = [
                [InlineKeyboardButton("Revisar citas pendientes", callback_data="panel_revisar")],
                [InlineKeyboardButton("Agregar horario disponible", callback_data="panel_agregar_horario")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Panel de propietario:\n¿Qué quieres hacer?",
                reply_markup=reply_markup
            )
            return AGREGAR_HORARIO
        if query.data.startswith("mes_"):
            await query.answer()
            mes = int(query.data[4:])
            hoy = date.today()
            year = hoy.year
            context.user_data['nuevo_mes'] = mes
            context.user_data['nuevo_ano'] = year
            # Mostrar los días del mes seleccionado + volver
            month_days = pycalendar.monthrange(year, mes)[1]
            days_keyboard = []
            week = []
            for d in range(1, month_days + 1):
                week.append(InlineKeyboardButton(str(d), callback_data=f"dia_{year}-{mes:02d}-{d:02d}"))
                if len(week) == 7:
                    days_keyboard.append(week)
                    week = []
            if week:
                days_keyboard.append(week)
            days_keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="volver_elegir_mes")])
            reply_markup = InlineKeyboardMarkup(days_keyboard)
            await query.edit_message_text(f"Selecciona el día para el nuevo horario ({year}-{mes:02d}):", reply_markup=reply_markup)
            return ELEGIR_DIA
    await query.edit_message_text("Error al seleccionar el mes. Intenta de nuevo.")
    return AGREGAR_HORARIO

async def elegir_dia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is not None and query.data:
        if query.data == "volver_elegir_mes":
            # Volver a la selección de mes
            meses = [
                [InlineKeyboardButton("Enero", callback_data="mes_01")],
                [InlineKeyboardButton("Febrero", callback_data="mes_02")],
                [InlineKeyboardButton("Marzo", callback_data="mes_03")],
                [InlineKeyboardButton("Abril", callback_data="mes_04")],
                [InlineKeyboardButton("Mayo", callback_data="mes_05")],
                [InlineKeyboardButton("Junio", callback_data="mes_06")],
                [InlineKeyboardButton("Julio", callback_data="mes_07")],
                [InlineKeyboardButton("Agosto", callback_data="mes_08")],
                [InlineKeyboardButton("Septiembre", callback_data="mes_09")],
                [InlineKeyboardButton("Octubre", callback_data="mes_10")],
                [InlineKeyboardButton("Noviembre", callback_data="mes_11")],
                [InlineKeyboardButton("Diciembre", callback_data="mes_12")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="volver_panel_propietario")]
            ]
            reply_markup = InlineKeyboardMarkup(meses)
            await query.edit_message_text("Selecciona el mes para el nuevo horario:", reply_markup=reply_markup)
            return ELEGIR_MES
        if query.data.startswith("dia_"):
            await query.answer()
            fecha_elegida = query.data[4:]
            context.user_data['nueva_fecha'] = fecha_elegida
            await query.edit_message_text(f"Has elegido el día {fecha_elegida}. Ahora introduce la hora (HH:MM):")
            return ESPERAR_HORA_HORARIO
    await query.edit_message_text("Error al seleccionar el día. Intenta de nuevo.")
    return AGREGAR_HORARIO

async def esperar_hora_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message and update.message.text:
        nueva_fecha = context.user_data.get('nueva_fecha')
        nueva_hora = update.message.text.strip()
        # Guardar en la base de datos
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO fechas_disponibles (fecha) VALUES (?)', (nueva_fecha,))
        c.execute('INSERT OR IGNORE INTO horas_disponibles (hora) VALUES (?)', (nueva_hora,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Horario añadido: {nueva_fecha} a las {nueva_hora}")
        # Volver al panel de propietario
        keyboard = [
            [InlineKeyboardButton("Revisar citas pendientes", callback_data="panel_revisar")],
            [InlineKeyboardButton("Agregar horario disponible", callback_data="panel_agregar_horario")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Panel de propietario:\n¿Qué quieres hacer?",
            reply_markup=reply_markup
        )
        return AGREGAR_HORARIO
    else:
        await update.message.reply_text("Por favor, introduce una hora válida.")
        return ESPERAR_HORA_HORARIO

def main() -> None:
    init_db()
    add_sample_data()
    init_pending_table()
    application = ApplicationBuilder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_telefono)],
            TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_menu)],
            CONTACTAR: [CallbackQueryHandler(contactar, pattern=f"^{CONTACTAR}$"),
                        CallbackQueryHandler(solicitar_cita, pattern=f"^{SOLICITAR_CITA}$")],
            FECHA: [CallbackQueryHandler(seleccionar_fecha, pattern="^fecha_")],
            HORA: [CallbackQueryHandler(seleccionar_hora, pattern="^hora_")],
            CONFIRMAR: [CallbackQueryHandler(confirmar_cita, pattern="^(confirmar|cancelar)$")],
            AGREGAR_HORARIO: [CallbackQueryHandler(panel_propietario, pattern="^panel_"),],
            ELEGIR_MES: [CallbackQueryHandler(elegir_mes, pattern=r"^(mes_\d{2}|volver_panel_propietario)$")],
            ELEGIR_DIA: [CallbackQueryHandler(elegir_dia, pattern=r"^(dia_\d{4}-\d{2}-\d{2}|volver_elegir_mes)$")],
            ESPERAR_HORA_HORARIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, esperar_hora_horario)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("revisar", revisar))
    application.add_handler(CallbackQueryHandler(gestionar_cita, pattern="^(aceptar_|rechazar_)"))
    application.add_handler(CallbackQueryHandler(cancelar_cita, pattern="^cancelar_cita_\d+$"))
    application.run_polling()

if __name__ == '__main__':
    main()
