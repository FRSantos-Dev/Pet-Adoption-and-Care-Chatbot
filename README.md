# Pet Adoption and Care Chatbot

A Telegram bot for managing pet adoption interviews and care information.

## Features

- View available animals (cats and dogs)
- Start adoption interviews
- Generate PDF reports of interviews
- Store interview data in PostgreSQL database
- Send interview results to bot owner

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Pet-Adoption-and-Care-Chatbot.git
cd Pet-Adoption-and-Care-Chatbot
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a PostgreSQL database:
```sql
CREATE DATABASE pet_adoption;
```

5. Configure the environment variables:
- Copy `.env.example` to `.env`
- Update the values in `.env` with your configuration:
  - Database credentials
  - Telegram bot token
  - Bot owner ID

## Usage

1. Start the bot:
```bash
python telegram_bot.py
```

2. In Telegram:
- Search for your bot
- Send `/start` to begin
- Follow the prompts to view animals and start interviews

## Project Structure

- `telegram_bot.py`: Main bot implementation
- `database.py`: Database management
- `animal_manager.py`: Animal data management
- `data/`: Directory for animal data and images
- `interviews/`: Directory for generated PDFs

## License

MIT License