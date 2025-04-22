import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime

# Load environment variables
load_dotenv()

# Interview questions in Portuguese
QUESTIONS = [
    "Qual é o seu nome completo?",
    "Qual é a sua idade?",
    "Qual é o seu endereço?",
    "Você mora em casa ou apartamento?",
    "Você tem outros animais em casa? Se sim, quais?",
    "Todos os moradores da casa concordam com a adoção?",
    "Você já teve animais antes? Se sim, o que aconteceu com eles?",
    "Quanto tempo o animal ficará sozinho em casa?",
    "Você tem condições financeiras para arcar com os custos do animal?",
    "Qual é o seu principal motivo para adotar um animal?"
]

class AdoptionInterview:
    def __init__(self):
        self.answers = {}
        self.current_question = 0
        self.is_interview_active = False

    def start_interview(self):
        self.answers = {}
        self.current_question = 0
        self.is_interview_active = True
        return QUESTIONS[0]

    def answer_question(self, answer):
        self.answers[QUESTIONS[self.current_question]] = answer
        self.current_question += 1
        
        if self.current_question < len(QUESTIONS):
            return QUESTIONS[self.current_question]
        else:
            self.is_interview_active = False
            return None

    def generate_pdf(self, user_id):
        filename = f"adoption_interview_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Add title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, "Formulário de Entrevista para Adoção")
        
        # Add date
        c.setFont("Helvetica", 12)
        c.drawString(50, 720, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        # Add questions and answers
        y = 680
        c.setFont("Helvetica-Bold", 12)
        for question, answer in self.answers.items():
            if y < 50:  # New page if we're running out of space
                c.showPage()
                y = 750
                c.setFont("Helvetica-Bold", 12)
            
            c.drawString(50, y, question)
            y -= 20
            c.setFont("Helvetica", 12)
            c.drawString(50, y, f"Resposta: {answer}")
            y -= 40
            c.setFont("Helvetica-Bold", 12)
        
        c.save()
        return filename

# Create interview instance
interview = AdoptionInterview()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Iniciar Entrevista", callback_data='start_interview')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Olá! Sou um bot para entrevista de adoção de animais. "
        "Vou te ajudar a preencher o formulário de adoção.",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_interview':
        first_question = interview.start_interview()
        await query.message.reply_text(first_question)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if interview.is_interview_active:
        next_question = interview.answer_question(update.message.text)
        
        if next_question:
            await update.message.reply_text(next_question)
        else:
            # Interview is complete, generate PDF
            pdf_file = interview.generate_pdf(update.effective_user.id)
            await update.message.reply_text(
                "Obrigado por completar a entrevista! "
                "Aqui está o seu formulário de adoção:"
            )
            await update.message.reply_document(document=open(pdf_file, 'rb'))
            os.remove(pdf_file)  # Clean up the file after sending
    else:
        await update.message.reply_text(
            "Por favor, use o comando /start para iniciar a entrevista de adoção."
        )

def main():
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 