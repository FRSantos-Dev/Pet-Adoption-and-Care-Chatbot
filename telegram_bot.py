import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime
import shutil
from animal_manager import AnimalManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get bot owner ID from environment variable
BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', '0'))

# Image directories
IMAGE_DIR = "images"
DOGS_DIR = os.path.join(IMAGE_DIR, "dogs")
CATS_DIR = os.path.join(IMAGE_DIR, "cats")
OTHERS_DIR = os.path.join(IMAGE_DIR, "others")

# Ensure directories exist
os.makedirs(DOGS_DIR, exist_ok=True)
os.makedirs(CATS_DIR, exist_ok=True)
os.makedirs(OTHERS_DIR, exist_ok=True)

# Initialize animal manager
animal_manager = AnimalManager()

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
        self.user_info = {}
        self.animal_type = None
        self.animal_images = []
        self.selected_animal_id = None

    def start_interview(self, user_info, animal_type, animal_id=None):
        self.answers = {}
        self.current_question = 0
        self.is_interview_active = True
        self.user_info = user_info
        self.animal_type = animal_type
        self.animal_images = []
        self.selected_animal_id = animal_id
        return QUESTIONS[0]

    def answer_question(self, answer):
        self.answers[QUESTIONS[self.current_question]] = answer
        self.current_question += 1
        
        if self.current_question < len(QUESTIONS):
            return QUESTIONS[self.current_question]
        else:
            self.is_interview_active = False
            return None

    def add_image(self, image_path):
        self.animal_images.append(image_path)

    def get_target_dir(self):
        if self.animal_type == 'dog':
            return DOGS_DIR
        elif self.animal_type == 'cat':
            return CATS_DIR
        else:
            return OTHERS_DIR

    def generate_pdf(self, user_id):
        try:
            filename = f"adoption_interview_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            
            # Add title
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 750, "Formulário de Entrevista para Adoção")
            
            # Add date
            c.setFont("Helvetica", 12)
            c.drawString(50, 720, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            # Add user info
            c.drawString(50, 690, f"ID do Usuário: {user_id}")
            if 'username' in self.user_info:
                c.drawString(50, 670, f"Username: @{self.user_info['username']}")
            if 'first_name' in self.user_info:
                c.drawString(50, 650, f"Nome: {self.user_info['first_name']}")
            if 'last_name' in self.user_info:
                c.drawString(50, 630, f"Sobrenome: {self.user_info['last_name']}")
            
            # Add animal info if selected
            if self.selected_animal_id:
                animal = animal_manager.get_animal(self.animal_type, self.selected_animal_id)
                if animal:
                    c.drawString(50, 610, f"Animal: {animal['name']} (ID: {animal['id']})")
            
            # Add questions and answers
            y = 580
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
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise

# Create interview instance
interview = AdoptionInterview()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("Cachorro 🐕", callback_data='animal_dog')],
            [InlineKeyboardButton("Gato 🐈", callback_data='animal_cat')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Olá! Sou um bot para entrevista de adoção de animais. "
            "Por favor, selecione o tipo de animal que você deseja adotar:",
            reply_markup=reply_markup
        )
        logger.info(f"User {update.effective_user.id} started the bot")
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("Desculpe, ocorreu um erro. Por favor, tente novamente.")

async def show_available_animals(update: Update, context: ContextTypes.DEFAULT_TYPE, animal_type):
    try:
        animals = animal_manager.get_available_animals(animal_type)
        if not animals:
            await update.callback_query.message.reply_text(
                f"Desculpe, não há {animal_type}s disponíveis para adoção no momento."
            )
            return

        keyboard = []
        for animal in animals:
            keyboard.append([InlineKeyboardButton(
                f"{animal['name']} - {animal['breed']}",
                callback_data=f'select_animal_{animal_type}_{animal["id"]}'
            )])
        
        keyboard.append([InlineKeyboardButton("Voltar", callback_data='back_to_types')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.reply_text(
            f"Selecione um {animal_type} para ver mais detalhes:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error showing available animals: {str(e)}")
        await update.callback_query.message.reply_text("Desculpe, ocorreu um erro. Por favor, tente novamente.")

async def show_animal_details(update: Update, context: ContextTypes.DEFAULT_TYPE, animal_type, animal_id):
    try:
        animal = animal_manager.get_animal(animal_type, animal_id)
        if not animal:
            await update.callback_query.message.reply_text("Animal não encontrado.")
            return

        # Generate animal card
        card = animal_manager.generate_animal_card(animal)
        
        keyboard = [
            [InlineKeyboardButton("Iniciar Entrevista", callback_data=f'start_interview_{animal_type}_{animal_id}')],
            [InlineKeyboardButton("Voltar", callback_data=f'list_{animal_type}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.reply_text(
            card,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error showing animal details: {str(e)}")
        await update.callback_query.message.reply_text("Desculpe, ocorreu um erro. Por favor, tente novamente.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'back_to_types':
            keyboard = [
                [InlineKeyboardButton("Cachorro 🐕", callback_data='animal_dog')],
                [InlineKeyboardButton("Gato 🐈", callback_data='animal_cat')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "Por favor, selecione o tipo de animal que você deseja adotar:",
                reply_markup=reply_markup
            )
        
        elif query.data.startswith('animal_'):
            animal_type = query.data.split('_')[1]
            await show_available_animals(update, context, animal_type)
        
        elif query.data.startswith('list_'):
            animal_type = query.data.split('_')[1]
            await show_available_animals(update, context, animal_type)
        
        elif query.data.startswith('select_animal_'):
            _, _, animal_type, animal_id = query.data.split('_')
            await show_animal_details(update, context, animal_type, int(animal_id))
        
        elif query.data.startswith('start_interview_'):
            _, _, animal_type, animal_id = query.data.split('_')
            user_info = {
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'last_name': update.effective_user.last_name
            }
            first_question = interview.start_interview(user_info, animal_type, int(animal_id))
            await query.message.reply_text(
                f"Ótimo! Vamos começar a entrevista para adoção.\n\n"
                f"{first_question}"
            )
            logger.info(f"User {update.effective_user.id} started interview for {animal_type} {animal_id}")
    
    except Exception as e:
        logger.error(f"Error in button handler: {str(e)}")
        await query.message.reply_text("Desculpe, ocorreu um erro. Por favor, tente novamente.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if interview.is_interview_active:
            # Check if the message contains a photo
            if update.message.photo:
                # Get the largest photo
                photo = update.message.photo[-1]
                # Download the photo
                photo_file = await context.bot.get_file(photo.file_id)
                # Generate filename
                filename = f"{update.effective_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                target_dir = interview.get_target_dir()
                file_path = os.path.join(target_dir, filename)
                
                # Download and save the photo
                await photo_file.download_to_drive(file_path)
                interview.add_image(file_path)
                
                await update.message.reply_text("Foto recebida! Por favor, continue respondendo às perguntas.")
                return

            next_question = interview.answer_question(update.message.text)
            
            if next_question:
                await update.message.reply_text(next_question)
            else:
                # Interview is complete, generate PDF
                pdf_file = interview.generate_pdf(update.effective_user.id)
                
                # Send confirmation to interviewee
                await update.message.reply_text(
                    "Obrigado por completar a entrevista! "
                    "Seu formulário será analisado pela nossa equipe."
                )
                
                # Send PDF to bot owner
                if BOT_OWNER_ID:
                    await context.bot.send_document(
                        chat_id=BOT_OWNER_ID,
                        document=open(pdf_file, 'rb'),
                        caption=f"Nova entrevista de adoção de {update.effective_user.first_name} (@{update.effective_user.username})"
                    )
                    
                    # Send images to bot owner
                    for image_path in interview.animal_images:
                        await context.bot.send_photo(
                            chat_id=BOT_OWNER_ID,
                            photo=open(image_path, 'rb'),
                            caption=f"Foto do animal de {update.effective_user.first_name}"
                        )
                else:
                    logger.error("BOT_OWNER_ID not set")
                
                # Clean up files
                os.remove(pdf_file)
                for image_path in interview.animal_images:
                    os.remove(image_path)
                
                logger.info(f"User {update.effective_user.id} completed the interview")

                # Show available animals to the user
                available_animals = animal_manager.get_available_animals(interview.animal_type)
                if available_animals:
                    await update.message.reply_text(
                        "Aqui estão outros animais disponíveis para adoção:"
                    )
                    
                    for animal in available_animals:
                        # Send animal information
                        animal_card = animal_manager.generate_animal_card(animal)
                        await update.message.reply_text(
                            animal_card,
                            parse_mode='Markdown'
                        )
                        
                        # Send animal photos if available
                        if animal['photos']:
                            for photo_path in animal['photos']:
                                if os.path.exists(photo_path):
                                    await context.bot.send_photo(
                                        chat_id=update.effective_chat.id,
                                        photo=open(photo_path, 'rb'),
                                        caption=f"Foto de {animal['name']}"
                                    )
                else:
                    await update.message.reply_text(
                        "No momento, não há outros animais disponíveis para adoção."
                    )
        else:
            await update.message.reply_text(
                "Por favor, use o comando /start para iniciar a entrevista de adoção."
            )
    except Exception as e:
        logger.error(f"Error in message handler: {str(e)}")
        await update.message.reply_text("Desculpe, ocorreu um erro. Por favor, tente novamente.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Desculpe, ocorreu um erro. Por favor, tente novamente."
        )

def main():
    try:
        # Get the token from environment variable
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        if not BOT_OWNER_ID:
            raise ValueError("BOT_OWNER_ID not found in environment variables")
        
        logger.info("Starting bot...")
        # Create the Application and pass it your bot's token
        application = Application.builder().token(token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_message))
        application.add_error_handler(error_handler)

        # Start the Bot
        logger.info("Bot is running...")
        application.run_polling()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == '__main__':
    main() 