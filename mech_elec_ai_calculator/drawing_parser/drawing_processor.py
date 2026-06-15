import os
from typing import Optional
from common.models import DrawingData
from framework.exceptions import ParseError
from .dxf_parser import DXFParser
from .pdf_parser import PDFParser
from .image_parser import ImageParser

class DrawingProcessor:
    def __init__(self):
        self._dxf_parser = DXFParser()
        self._pdf_parser = PDFParser()
        self._image_parser = ImageParser()
    
    def process(self, file_path: str) -> DrawingData:
        ext = self._get_file_extension(file_path)
        
        if ext == '.dxf':
            return self._dxf_parser.parse(file_path)
        elif ext == '.pdf':
            return self._pdf_parser.parse(file_path)
        elif ext in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff'):
            return self._image_parser.parse(file_path)
        else:
            raise ParseError(f"Unsupported file type: {ext}")
    
    def _get_file_extension(self, file_path: str) -> str:
        return os.path.splitext(file_path)[1].lower()
    
    def is_supported(self, file_path: str) -> bool:
        ext = self._get_file_extension(file_path)
        return ext in ('.dxf', '.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff')