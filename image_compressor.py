import os
from PIL import Image
import logging
from io import BytesIO

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ImageCompressor:
    def __init__(self, max_size_kb=500, quality=85):
        """
        Inicializa o compressor de imagens.
        
        Args:
            max_size_kb (int): Tamanho máximo desejado em KB
            quality (int): Qualidade da compressão (0-100)
        """
        self.max_size_kb = max_size_kb
        self.quality = quality

    def compress_image(self, image_path):
        """
        Comprime uma imagem mantendo uma boa qualidade visual.
        
        Args:
            image_path (str): Caminho para a imagem original
            
        Returns:
            bytes: Imagem comprimida em bytes
        """
        try:
            # Abre a imagem
            with Image.open(image_path) as img:
                # Converte para RGB se necessário
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Obtém o tamanho original
                original_size = os.path.getsize(image_path) / 1024  # em KB
                
                # Se já estiver menor que o tamanho máximo, retorna a original
                if original_size <= self.max_size_kb:
                    logger.info(f"Imagem já está dentro do tamanho máximo ({original_size:.2f}KB)")
                    with open(image_path, 'rb') as f:
                        return f.read()
                
                # Calcula o fator de redução necessário
                reduction_factor = (self.max_size_kb / original_size) ** 0.5
                
                # Redimensiona a imagem mantendo a proporção
                new_width = int(img.width * reduction_factor)
                new_height = int(img.height * reduction_factor)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Salva a imagem comprimida em memória
                output = BytesIO()
                img.save(output, format='JPEG', quality=self.quality, optimize=True)
                compressed_data = output.getvalue()
                
                # Verifica o tamanho final
                final_size = len(compressed_data) / 1024  # em KB
                logger.info(f"Imagem comprimida: {original_size:.2f}KB -> {final_size:.2f}KB")
                
                return compressed_data
                
        except Exception as e:
            logger.error(f"Erro ao comprimir imagem {image_path}: {str(e)}")
            # Em caso de erro, retorna a imagem original
            with open(image_path, 'rb') as f:
                return f.read()

    def compress_image_to_file(self, input_path, output_path):
        """
        Comprime uma imagem e salva em um novo arquivo.
        
        Args:
            input_path (str): Caminho para a imagem original
            output_path (str): Caminho para salvar a imagem comprimida
        """
        try:
            compressed_data = self.compress_image(input_path)
            with open(output_path, 'wb') as f:
                f.write(compressed_data)
            logger.info(f"Imagem comprimida salva em: {output_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar imagem comprimida: {str(e)}")
            raise

# Exemplo de uso
if __name__ == "__main__":
    # Cria uma instância do compressor
    compressor = ImageCompressor(max_size_kb=500, quality=85)
    
    # Exemplo de compressão
    input_image = "exemplo.jpg"
    output_image = "exemplo_comprimido.jpg"
    
    if os.path.exists(input_image):
        compressor.compress_image_to_file(input_image, output_image)
    else:
        logger.error(f"Arquivo {input_image} não encontrado") 