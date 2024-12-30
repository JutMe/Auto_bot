from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import mysql.connector

# Database setup
conn = mysql.connector.connect(
    host="Hostname",
    user="Username",
    password="Password",
    database="Database"
)
c = conn.cursor()

# Create necessary tables (if they don't already exist)
c.execute('''CREATE TABLE IF NOT EXISTS assignment
             (idAssignment INT AUTO_INCREMENT PRIMARY KEY, Assignment_Name VARCHAR(45), 
              Company_Name VARCHAR(45), Language VARCHAR(45), Requirements VARCHAR(100), 
              Pay_details INT, Due_Date DATE, Assigned TINYINT, Assigned_emp_id INT, 
              Updates VARCHAR(100))''')

c.execute('''CREATE TABLE IF NOT EXISTS emp_details
             (EMP_ID INT AUTO_INCREMENT PRIMARY KEY, Emp_Name VARCHAR(45), 
              Languages VARCHAR(45), Assignments_taken INT)''')

conn.commit()

# Function to check if a user is authorized
def is_authorized(user_id: int) -> bool:
    c.execute("SELECT authorized FROM users WHERE user_id = %s", (user_id,))
    result = c.fetchone()
    return result is not None and result[0]

# Authorize user if not already authorized
def authorize_user(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    c.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    if c.fetchone() is None:
        c.execute("INSERT INTO users (user_id, authorized) VALUES (%s, FALSE)", (user_id,))
        conn.commit()
        update.message.reply_text('You are not authorized to use this bot. Please contact the admin for access.')
    else:
        update.message.reply_text('You are already registered. Please wait for authorization.')

# Start command handler
async def start(update: Update, context: CallbackContext) -> None:
    if is_authorized(update.message.from_user.id):
        await update.message.reply_text('Hello! I am your friendly bot. How can I assist you today?')
    else:
        authorize_user(update, context)

# Help command handler
async def help_command(update: Update, context: CallbackContext) -> None:
    if is_authorized(update.message.from_user.id):
        await update.message.reply_text('You can use the following commands:\n/start - Start the bot\n/help - Get help\n/addtask <task> - Add a new task\n/listtasks - List all tasks\n/updatetask <id> <status> - Update task status\n/listemployees - List all employees\n/report - Generate operational report')
    else:
        await update.message.reply_text('You are not authorized to use this bot.')

# Add task command handler
async def add_task(update: Update, context: CallbackContext) -> None:
    if is_authorized(update.message.from_user.id):
        try:
            task_name = context.args[0]
            company_name = context.args[1]
            language = context.args[2]
            requirements = context.args[3]
            pay_details = int(context.args[4])
            due_date = context.args[5]
            c.execute("INSERT INTO assignment (Assignment_Name, Company_Name, Language, Requirements, Pay_details, Due_Date, Assigned) VALUES (%s, %s, %s, %s, %s, %s, 0)", 
                      (task_name, company_name, language, requirements, pay_details, due_date))
            conn.commit()
            await update.message.reply_text(f'Task "{task_name}" added.')
        except (IndexError, ValueError):
            await update.message.reply_text('Usage: /addtask <task_name> <company_name> <language> <requirements> <pay_details> <due_date>')

    else:
        await update.message.reply_text('You are not authorized to use this bot.')

# List tasks command handler
async def list_tasks(update: Update, context: CallbackContext) -> None:
    if is_authorized(update.message.from_user.id):
        c.execute("SELECT idAssignment, Assignment_Name, Company_Name, Language, Pay_details, Due_Date, Assigned FROM assignment")
        tasks = c.fetchall()
        if tasks:
            message = '\n'.join([f'{task[0]}. {task[1]} - {task[2]} ({task[3]}) - {task[4]} USD - Due: {task[5]} - Assigned: {task[6]}' for task in tasks])
            await update.message.reply_text(message)
        else:
            await update.message.reply_text('No tasks found.')
    else:
        await update.message.reply_text('You are not authorized to use this bot.')

# Update task command handler
async def update_task(update: Update, context: CallbackContext) -> None:
    if is_authorized(update.message.from_user.id):
        try:
            task_id = int(context.args[0])
            status = context.args[1]
            if status == 'assigned':
                emp_id = int(context.args[2])  # Emp ID to assign the task
                c.execute("UPDATE assignment SET Assigned = 1, Assigned_emp_id = %s WHERE idAssignment = %s", (emp_id, task_id))
                c.execute("UPDATE emp_details SET Assignments_taken = Assignments_taken + 1 WHERE EMP_ID = %s", (emp_id,))
            elif status == 'pending':
                c.execute("UPDATE assignment SET Assigned = 0, Assigned_emp_id = NULL WHERE idAssignment = %s", (task_id,))
            conn.commit()
            await update.message.reply_text(f'Task {task_id} updated to "{status}".')
        except (IndexError, ValueError):
            await update.message.reply_text('Usage: /updatetask <id> <status> [emp_id if assigned]')
    else:
        await update.message.reply_text('You are not authorized to use this bot.')

# List employees command handler
async def list_employees(update: Update, context: CallbackContext) -> None:
    if is_authorized(update.message.from_user.id):
        c.execute("SELECT EMP_ID, Emp_Name, Languages, Assignments_taken FROM emp_details")
        employees = c.fetchall()
        if employees:
            message = '\n'.join([f'{emp[0]}. {emp[1]} - Languages: {emp[2]} - Assignments: {emp[3]}' for emp in employees])
            await update.message.reply_text(message)
        else:
            await update.message.reply_text('No employees found.')
    else:
        await update.message.reply_text('You are not authorized to use this bot.')

# Generate report command handler
async def generate_report(update: Update, context: CallbackContext) -> None:
    if is_authorized(update.message.from_user.id):
        c.execute("SELECT Assigned, COUNT(*) FROM assignment GROUP BY Assigned")
        stats = c.fetchall()
        report = 'Operational Report:\n'
        for stat in stats:
            report += f'{stat[0]}: {stat[1]}\n'
        await update.message.reply_text(report)
    else:
        await update.message.reply_text('You are not authorized to use this bot.')

# Main function to set up the bot
def main() -> None:
    application = Application.builder().token("Token").build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addtask", add_task))
    application.add_handler(CommandHandler("listtasks", list_tasks))
    application.add_handler(CommandHandler("updatetask", update_task))
    application.add_handler(CommandHandler("listemployees", list_employees))
    application.add_handler(CommandHandler("report", generate_report))

    # Start polling
    application.run_polling()

if __name__ == '__main__':
    main()

