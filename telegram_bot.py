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
from image_compressor import ImageCompressor
from database_interface import DatabaseInterface, UserInfo
from typing import Dict, Any, Optional, List
from database_manager import DatabaseManager

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

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")
DOGS_DIR = os.path.join(IMAGE_DIR, "dogs")
CATS_DIR = os.path.join(IMAGE_DIR, "cats")
OTHERS_DIR = os.path.join(IMAGE_DIR, "others")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure directories exist
try:
    os.makedirs(DOGS_DIR, exist_ok=True)
    os.makedirs(CATS_DIR, exist_ok=True)
    os.makedirs(OTHERS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info("All required directories created successfully")
except Exception as e:
    logger.error(f"Error creating directories: {str(e)}")
    raise

# Initialize animal manager with absolute path
animal_manager = AnimalManager(os.path.join(DATA_DIR, 'animals.json'))

# Initialize image compressor
image_compressor = ImageCompressor(max_size_kb=500, quality=85)

# Initialize database manager
db_manager = DatabaseManager()

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
    def __init__(self, db_manager: DatabaseInterface):
        self.answers: Dict[str, str] = {}
        self.current_question: int = 0
        self.is_interview_active: bool = False
        self.user_info: UserInfo = {}
        self.animal_type: Optional[str] = None
        self.animal_images: List[str] = []
        self.selected_animal_id: Optional[int] = None
        self.db_manager = db_manager

    def start_interview(self, user_info: UserInfo, animal_type: str, animal_id: Optional[int] = None) -> str:
        self.answers = {}
        self.current_question = 0
        self.is_interview_active = True
        self.user_info = user_info
        self.animal_type = animal_type
        self.animal_images = []
        self.selected_animal_id = animal_id
        return QUESTIONS[0]

    def answer_question(self, answer: str) -> Optional[str]:
        self.answers[QUESTIONS[self.current_question]] = answer
        self.current_question += 1
        
        if self.current_question < len(QUESTIONS):
            return QUESTIONS[self.current_question]
        else:
            self.is_interview_active = False
            return None

    def add_image(self, image_path: str) -> None:
        self.animal_images.append(image_path)

    def get_target_dir(self) -> str:
        try:
            if self.animal_type == 'dog':
                return DOGS_DIR
            elif self.animal_type == 'cat':
                return CATS_DIR
            else:
                return OTHERS_DIR
        except Exception as e:
            logger.error(f"Error getting target directory: {str(e)}")
            return IMAGE_DIR

    def generate_pdf(self, user_id: int) -> str:
        try:
            # Create PDF filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"adoption_interview_{user_id}_{timestamp}.pdf"
            filepath = os.path.join(DATA_DIR, filename)
            
            # Create PDF
            c = canvas.Canvas(filepath, pagesize=letter)
            
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
            
            # Save and close PDF
            c.save()
            return filepath
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise

# Initialize interview system
interview = AdoptionInterview(db_manager)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get all available animals
        try:
            dogs = animal_manager.get_available_animals('dogs')
            cats = animal_manager.get_available_animals('cats')
        except Exception as e:
            logger.error(f"Error getting available animals: {str(e)}")
            await update.message.reply_text(
                "Desculpe, ocorreu um erro ao carregar os animais disponíveis. "
                "Por favor, tente novamente mais tarde."
            )
            return
        
        if not dogs and not cats:
            await update.message.reply_text(
                "Desculpe, não há animais disponíveis para adoção no momento."
            )
            return

        # Send welcome message
        welcome_text = (
            "🐾 Bem-vindo ao Bot de Adoção de Animais! 🐾\n\n"
            "Aqui estão os animais disponíveis para adoção:"
        )
        await update.message.reply_text(welcome_text)

        # Show cats first
        if cats:
            await update.message.reply_text("🐈 Gatos disponíveis:")
            for cat in cats:
                try:
                    # Send cat photos first
                    if cat['photos']:
                        for photo_path in cat['photos']:
                            try:
                                abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), photo_path)
                                if os.path.exists(abs_path):
                                    # Compress the image before sending
                                    compressed_image = image_compressor.compress_image(abs_path)
                                    await context.bot.send_photo(
                                        chat_id=update.effective_chat.id,
                                        photo=compressed_image,
                                        caption=f"🐱 {cat['name']} - {cat['breed']}\nIdade: {cat['age']} anos\nGênero: {cat['gender']}\nPorte: {cat['size']}"
                                    )
                            except Exception as e:
                                logger.error(f"Error sending cat photo {cat['name']}: {str(e)}")
                                continue
                    
                    # Send cat information
                    cat_card = animal_manager.generate_animal_card(cat)
                    keyboard = [
                        [InlineKeyboardButton("Iniciar Entrevista", callback_data=f'start_interview_cat_{cat["id"]}')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        cat_card,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error processing cat {cat['name']}: {str(e)}")
                    continue

        # Show dogs
        if dogs:
            await update.message.reply_text("🐕 Cachorros disponíveis:")
            for dog in dogs:
                try:
                    # Send dog photos first
                    if dog['photos']:
                        for photo_path in dog['photos']:
                            try:
                                abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), photo_path)
                                if os.path.exists(abs_path):
                                    # Compress the image before sending
                                    compressed_image = image_compressor.compress_image(abs_path)
                                    await context.bot.send_photo(
                                        chat_id=update.effective_chat.id,
                                        photo=compressed_image,
                                        caption=f"🐶 {dog['name']} - {dog['breed']}\nIdade: {dog['age']} anos\nGênero: {dog['gender']}\nPorte: {dog['size']}"
                                    )
                            except Exception as e:
                                logger.error(f"Error sending dog photo {dog['name']}: {str(e)}")
                                continue
                    
                    # Send dog information
                    dog_card = animal_manager.generate_animal_card(dog)
                    keyboard = [
                        [InlineKeyboardButton("Iniciar Entrevista", callback_data=f'start_interview_dog_{dog["id"]}')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        dog_card,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error processing dog {dog['name']}: {str(e)}")
                    continue

        # Add filter options
        filter_text = (
            "\n🔍 Você pode filtrar os animais por tipo:"
        )
        keyboard = [
            [InlineKeyboardButton("Cachorros 🐕", callback_data='animal_dog')],
            [InlineKeyboardButton("Gatos 🐈", callback_data='animal_cat')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(filter_text, reply_markup=reply_markup)

        logger.info(f"User {update.effective_user.id} started the bot successfully")
    except Exception as e:
        logger.error(f"Critical error in start command: {str(e)}")
        await update.message.reply_text(
            "Desculpe, ocorreu um erro inesperado. "
            "Por favor, tente novamente mais tarde."
        )

async def show_available_animals(update: Update, context: ContextTypes.DEFAULT_TYPE, animal_type: str):
    try:
        if animal_type not in ['dog', 'cat']:
            raise ValueError(f"Invalid animal type: {animal_type}")

        animals = animal_manager.get_available_animals(animal_type)
        if not animals:
            await update.callback_query.message.reply_text(
                f"Desculpe, não há {animal_type}s disponíveis para adoção no momento."
            )
            return

        # Send message about available animals
        animal_emoji = "🐕" if animal_type == "dog" else "🐈"
        await update.callback_query.message.reply_text(
            f"Aqui estão os {animal_type}s disponíveis para adoção:"
        )

        for animal in animals:
            try:
                # Send animal photos first
                if animal['photos']:
                    for photo_path in animal['photos']:
                        try:
                            abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), photo_path)
                            if os.path.exists(abs_path):
                                # Compress the image before sending
                                compressed_image = image_compressor.compress_image(abs_path)
                                await context.bot.send_photo(
                                    chat_id=update.effective_chat.id,
                                    photo=compressed_image,
                                    caption=f"{animal_emoji} {animal['name']} - {animal['breed']}\nIdade: {animal['age']} anos\nGênero: {animal['gender']}\nPorte: {animal['size']}"
                                )
                        except Exception as e:
                            logger.error(f"Error sending animal photo: {str(e)}")
                            continue
                
                # Send animal information
                animal_card = animal_manager.generate_animal_card(animal)
                keyboard = [
                    [InlineKeyboardButton("Iniciar Entrevista", callback_data=f'start_interview_{animal_type}_{animal["id"]}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.message.reply_text(
                    animal_card,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Error processing animal {animal['name']}: {str(e)}")
                continue

        # Add back button
        keyboard = [[InlineKeyboardButton("Voltar", callback_data='back_to_types')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.reply_text(
            "Selecione uma opção:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error showing available animals: {str(e)}")
        await update.callback_query.message.reply_text(
            "Desculpe, ocorreu um erro ao mostrar os animais disponíveis. "
            "Por favor, tente novamente."
        )

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
            try:
                animal_type = query.data.split('_')[1]
                if animal_type not in ['dog', 'cat']:
                    raise ValueError(f"Invalid animal type: {animal_type}")
                await show_available_animals(update, context, animal_type)
            except Exception as e:
                logger.error(f"Error in animal selection: {str(e)}")
                await query.message.reply_text(
                    "Desculpe, ocorreu um erro ao mostrar os animais. "
                    "Por favor, tente novamente."
                )
        
        elif query.data.startswith('list_'):
            try:
                animal_type = query.data.split('_')[1]
                if animal_type not in ['dog', 'cat']:
                    raise ValueError(f"Invalid animal type: {animal_type}")
                await show_available_animals(update, context, animal_type)
            except Exception as e:
                logger.error(f"Error listing animals: {str(e)}")
                await query.message.reply_text(
                    "Desculpe, ocorreu um erro ao listar os animais. "
                    "Por favor, tente novamente."
                )
        
        elif query.data.startswith('select_animal_'):
            try:
                _, _, animal_type, animal_id = query.data.split('_')
                if animal_type not in ['dog', 'cat']:
                    raise ValueError(f"Invalid animal type: {animal_type}")
                await show_animal_details(update, context, animal_type, int(animal_id))
            except Exception as e:
                logger.error(f"Error showing animal details: {str(e)}")
                await query.message.reply_text(
                    "Desculpe, ocorreu um erro ao mostrar os detalhes do animal. "
                    "Por favor, tente novamente."
                )
        
        elif query.data.startswith('start_interview_'):
            try:
                _, _, animal_type, animal_id = query.data.split('_')
                if animal_type not in ['dog', 'cat']:
                    raise ValueError(f"Invalid animal type: {animal_type}")
                
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
                logger.error(f"Error starting interview: {str(e)}")
                await query.message.reply_text(
                    "Desculpe, ocorreu um erro ao iniciar a entrevista. "
                    "Por favor, tente novamente."
                )
    
    except Exception as e:
        logger.error(f"Error in button handler: {str(e)}")
        await query.message.reply_text(
            "Desculpe, ocorreu um erro inesperado. "
            "Por favor, tente novamente mais tarde."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if interview.is_interview_active:
            # Check if the message contains a photo
            if update.message.photo:
                try:
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
                    
                    # Compress the image before adding to interview
                    compressed_image = image_compressor.compress_image(file_path)
                    with open(file_path, 'wb') as f:
                        f.write(compressed_image)
                    
                    interview.add_image(file_path)
                    
                    await update.message.reply_text("Foto recebida! Por favor, continue respondendo às perguntas.")
                    return
                except Exception as e:
                    logger.error(f"Error handling photo: {str(e)}")
                    await update.message.reply_text(
                        "Desculpe, ocorreu um erro ao processar a foto. "
                        "Por favor, tente enviar novamente ou continue com a entrevista."
                    )
                    return

            try:
                # Verifica se a resposta está vazia ou contém apenas espaços
                if not update.message.text or update.message.text.strip() == "":
                    await update.message.reply_text(
                        "Por favor, forneça uma resposta válida. "
                        "Não é possível aceitar respostas vazias."
                    )
                    return

                # Verifica se a resposta é muito curta (menos de 2 caracteres)
                if len(update.message.text.strip()) < 2:
                    await update.message.reply_text(
                        "Por favor, forneça uma resposta mais detalhada. "
                        "Sua resposta deve ter pelo menos 2 caracteres."
                    )
                    return

                # Verifica se a resposta contém apenas caracteres especiais ou números
                if not any(c.isalpha() for c in update.message.text):
                    await update.message.reply_text(
                        "Por favor, forneça uma resposta com texto. "
                        "Não é possível aceitar apenas números ou caracteres especiais."
                    )
                    return

                # Verifica se a pergunta atual é sobre idade
                current_question = QUESTIONS[interview.current_question]
                if "idade" in current_question.lower():
                    try:
                        # Remove espaços e caracteres não numéricos
                        age_str = ''.join(filter(str.isdigit, update.message.text.strip()))
                        
                        # Verifica se a string resultante está vazia
                        if not age_str:
                            await update.message.reply_text(
                                "Por favor, forneça sua idade em números inteiros. "
                                "Por exemplo: 25"
                            )
                            return
                        
                        # Converte para inteiro
                        age = int(age_str)
                        
                        # Verifica se a idade está em um intervalo razoável (0-120)
                        if age < 0 or age > 120:
                            await update.message.reply_text(
                                "Por favor, forneça uma idade válida entre 0 e 120 anos."
                            )
                            return
                            
                        # Atualiza a resposta com o número inteiro
                        update.message.text = str(age)
                        
                    except ValueError:
                        await update.message.reply_text(
                            "Por favor, forneça sua idade em números inteiros. "
                            "Por exemplo: 25"
                        )
                        return

                next_question = interview.answer_question(update.message.text)
                
                if next_question:
                    await update.message.reply_text(next_question)
                else:
                    # Interview is complete, generate PDF
                    try:
                        pdf_file = interview.generate_pdf(update.effective_user.id)
                        
                        # Save interview to database
                        user_info = {
                            'id': update.effective_user.id,
                            'username': update.effective_user.username,
                            'first_name': update.effective_user.first_name,
                            'last_name': update.effective_user.last_name
                        }
                        interview_id = interview.db_manager.save_interview(
                            user_info,
                            interview.animal_type,
                            interview.selected_animal_id,
                            interview.answers,
                            pdf_file,
                            interview.animal_images
                        )
                        
                        # Send confirmation to interviewee
                        await update.message.reply_text(
                            "Obrigado por completar a entrevista! "
                            "Seu formulário será analisado pela nossa equipe."
                        )
                        
                        # Send PDF to bot owner
                        if BOT_OWNER_ID:
                            try:
                                # Send PDF to bot owner's chat
                                with open(pdf_file, 'rb') as pdf:
                                    await context.bot.send_document(
                                        chat_id=BOT_OWNER_ID,
                                        document=pdf,
                                        caption=f"📄 Nova entrevista de adoção\n\n"
                                               f"👤 Usuário: {update.effective_user.first_name} (@{update.effective_user.username})\n"
                                               f"📱 ID: {update.effective_user.id}\n"
                                               f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                                               f"🐾 Animal: {animal['name'] if animal else 'Não especificado'}\n"
                                               f"📋 ID da Entrevista: {interview_id}"
                                    )
                                
                                # Send images to bot owner
                                for image_path in interview.animal_images:
                                    try:
                                        if os.path.exists(image_path):
                                            # Compress the image before sending
                                            compressed_image = image_compressor.compress_image(image_path)
                                            await context.bot.send_photo(
                                                chat_id=BOT_OWNER_ID,
                                                photo=compressed_image,
                                                caption=f"📸 Foto do animal enviada por {update.effective_user.first_name}"
                                            )
                                    except Exception as e:
                                        logger.error(f"Error sending photo to owner: {str(e)}")
                                        continue
                                
                                # Send notification to bot owner's phone number if available
                                try:
                                    owner_info = await context.bot.get_chat(BOT_OWNER_ID)
                                    if owner_info.phone_number:
                                        await context.bot.send_message(
                                            chat_id=BOT_OWNER_ID,
                                            text=f"📱 Notificação por SMS:\n\n"
                                                 f"Nova entrevista de adoção recebida!\n"
                                                 f"Usuário: {update.effective_user.first_name}\n"
                                                 f"Animal: {animal['name'] if animal else 'Não especificado'}\n"
                                                 f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                                                 f"ID da Entrevista: {interview_id}"
                                        )
                                except Exception as e:
                                    logger.error(f"Error sending SMS notification: {str(e)}")
                            except Exception as e:
                                logger.error(f"Error sending PDF to owner: {str(e)}")
                        else:
                            logger.error("BOT_OWNER_ID not set")
                        
                        # Clean up files
                        try:
                            if os.path.exists(pdf_file):
                                os.remove(pdf_file)
                            for image_path in interview.animal_images:
                                if os.path.exists(image_path):
                                    os.remove(image_path)
                        except Exception as e:
                            logger.error(f"Error cleaning up files: {str(e)}")
                        
                        logger.info(f"User {update.effective_user.id} completed the interview")

                        # Show available animals to the user
                        try:
                            available_animals = animal_manager.get_available_animals(interview.animal_type)
                            if available_animals:
                                await update.message.reply_text(
                                    "Aqui estão outros animais disponíveis para adoção:"
                                )
                                
                                for animal in available_animals:
                                    try:
                                        # Send animal photos first
                                        if animal['photos']:
                                            for photo_path in animal['photos']:
                                                try:
                                                    abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), photo_path)
                                                    if os.path.exists(abs_path):
                                                        # Compress the image before sending
                                                        compressed_image = image_compressor.compress_image(abs_path)
                                                        await context.bot.send_photo(
                                                            chat_id=update.effective_chat.id,
                                                            photo=compressed_image,
                                                            caption=f"🐱 {animal['name']} - {animal['breed']}\nIdade: {animal['age']} anos\nGênero: {animal['gender']}\nPorte: {animal['size']}"
                                                        )
                                                except Exception as e:
                                                    logger.error(f"Error sending animal photo: {str(e)}")
                                                    continue
                                        
                                        # Send animal information
                                        animal_card = animal_manager.generate_animal_card(animal)
                                        keyboard = [
                                            [InlineKeyboardButton("Iniciar Entrevista", callback_data=f'start_interview_{interview.animal_type}_{animal["id"]}')]
                                        ]
                                        reply_markup = InlineKeyboardMarkup(keyboard)
                                        
                                        await update.message.reply_text(
                                            animal_card,
                                            parse_mode='Markdown',
                                            reply_markup=reply_markup
                                        )
                                    except Exception as e:
                                        logger.error(f"Error processing animal {animal['name']}: {str(e)}")
                                        continue
                            else:
                                await update.message.reply_text(
                                    "No momento, não há outros animais disponíveis para adoção."
                                )
                        except Exception as e:
                            logger.error(f"Error showing available animals: {str(e)}")
                            await update.message.reply_text(
                                "Desculpe, ocorreu um erro ao mostrar outros animais disponíveis."
                            )
                    except Exception as e:
                        logger.error(f"Error in interview completion: {str(e)}")
                        await update.message.reply_text(
                            "Desculpe, ocorreu um erro ao gerar o PDF da entrevista. "
                            "Por favor, tente novamente mais tarde."
                        )
            except Exception as e:
                logger.error(f"Error processing interview answer: {str(e)}")
                await update.message.reply_text(
                    "Desculpe, não foi possível entender sua resposta. "
                    "Por favor, tente novamente com uma resposta mais clara."
                )
        else:
            # Se não estiver em uma entrevista ativa, mostra as opções disponíveis
            welcome_text = (
                "🐾 Bem-vindo ao Bot de Adoção de Animais! 🐾\n\n"
                "Para começar, use o comando /start ou selecione uma das opções abaixo:"
            )
            
            keyboard = [
                [InlineKeyboardButton("Cachorro 🐕", callback_data='animal_dog')],
                [InlineKeyboardButton("Gato 🐈", callback_data='animal_cat')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Critical error in message handler: {str(e)}")
        await update.message.reply_text(
            "Desculpe, ocorreu um erro inesperado. "
            "Por favor, tente novamente mais tarde."
        )

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
    finally:
        # Close database connection
        interview.db_manager.close()

if __name__ == '__main__':
    main()


def db_config():
    return None