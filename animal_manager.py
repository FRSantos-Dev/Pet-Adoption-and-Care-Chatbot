import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AnimalManager:
    def __init__(self, data_file):
        self.data_file = data_file
        self.animals = self._load_data()

    def _load_data(self):
        """Load animal data from JSON file"""
        try:
            if not os.path.exists(self.data_file):
                logger.warning(f"Data file {self.data_file} not found. Creating new file.")
                self.animals = {"dogs": [], "cats": [], "others": []}
                self._save_data()
                return self.animals
            
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading data file: {str(e)}")
            return {"dogs": [], "cats": [], "others": []}

    def _save_data(self):
        """Save animal data to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.animals, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Error saving data file: {str(e)}")
            raise

    def add_animal(self, animal_type, animal_data):
        """Add a new animal to the database"""
        if animal_type not in self.animals:
            raise ValueError(f"Invalid animal type: {animal_type}")
        
        # Generate new ID
        if not self.animals[animal_type]:
            new_id = 1
        else:
            new_id = max(animal['id'] for animal in self.animals[animal_type]) + 1
        
        animal_data['id'] = new_id
        animal_data['adoption_status'] = 'Disponível'
        animal_data['photos'] = []
        
        self.animals[animal_type].append(animal_data)
        self._save_data()
        return new_id

    def update_animal(self, animal_type, animal_id, updates):
        """Update animal information"""
        for animal in self.animals[animal_type]:
            if animal['id'] == animal_id:
                animal.update(updates)
                self._save_data()
                return True
        return False

    def get_animal(self, animal_type, animal_id):
        """Get animal information by ID"""
        for animal in self.animals[animal_type]:
            if animal['id'] == animal_id:
                return animal
        return None

    def get_available_animals(self, animal_type):
        """Get list of available animals of a specific type"""
        return [animal for animal in self.animals[animal_type] 
                if animal['adoption_status'] == 'Disponível']

    def add_photo(self, animal_type, animal_id, photo_path):
        """Add photo path to animal's photo list"""
        try:
            for animal in self.animals[animal_type]:
                if animal['id'] == animal_id:
                    # Convert to relative path if it's an absolute path
                    if os.path.isabs(photo_path):
                        photo_path = os.path.relpath(photo_path, os.path.dirname(self.data_file))
                    animal['photos'].append(photo_path)
                    self._save_data()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error adding photo: {str(e)}")
            return False

    def get_photo_path(self, photo_path):
        """Convert relative photo path to absolute path"""
        try:
            if not os.path.isabs(photo_path):
                return os.path.join(os.path.dirname(self.data_file), photo_path)
            return photo_path
        except Exception as e:
            logger.error(f"Error getting photo path: {str(e)}")
            return photo_path

    def update_adoption_status(self, animal_type, animal_id, status):
        """Update animal's adoption status"""
        valid_statuses = ['Disponível', 'Em processo', 'Adotado']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        return self.update_animal(animal_type, animal_id, {'adoption_status': status})

    def generate_animal_card(self, animal):
        """Generate a formatted text card with animal information"""
        card = f"""
🐾 *{animal['name']}* 🐾

*Informações Básicas:*
• Tipo: {animal.get('species', 'Cão/Gato')}
• Raça: {animal['breed']}
• Idade: {animal['age']} anos
• Gênero: {animal['gender']}
• Porte: {animal['size']}

*Saúde:*
• Vacinado: {'Sim' if animal['health']['vaccinated'] else 'Não'}
• Vermifugado: {'Sim' if animal['health']['dewormed'] else 'Não'}
• Castrado: {'Sim' if animal['health']['castrated'] else 'Não'}
• Necessidades especiais: {'Sim' if animal['health']['special_needs'] else 'Não'}
• Observações: {animal['health']['health_notes']}

*Comportamento:*
• Temperamento: {animal['behavior']['temperament']}
• Nível de energia: {animal['behavior']['energy_level']}
• Bom com crianças: {'Sim' if animal['behavior']['good_with_kids'] else 'Não'}
• Observações: {animal['behavior']['behavior_notes']}

*História:*
{animal['history']}

*Status de Adoção:*
{animal['adoption_status']}
"""
        return card

    def search_animals(self, animal_type, criteria):
        """Search animals based on criteria"""
        results = []
        for animal in self.animals[animal_type]:
            match = True
            for key, value in criteria.items():
                if key in animal:
                    if isinstance(animal[key], dict):
                        if key in ['health', 'behavior']:
                            for subkey, subvalue in value.items():
                                if subkey in animal[key] and animal[key][subkey] != subvalue:
                                    match = False
                                    break
                    elif animal[key] != value:
                        match = False
                        break
            if match:
                results.append(animal)
        return results 