import fitz
import os
from typing import List, Dict, Any
from common.models import DrawingData, LayerInfo, BlockInfo, LineInfo, TextInfo, Coordinate
from framework.exceptions import ParseError

class PDFParser:
    def __init__(self):
        pass
    
    def parse(self, file_path: str) -> DrawingData:
        if not os.path.exists(file_path):
            raise ParseError(f"File not found: {file_path}")
        
        try:
            doc = fitz.open(file_path)
            
            drawing_data = DrawingData(
                filename=os.path.basename(file_path),
                file_type='pdf'
            )
            
            self._extract_content(doc, drawing_data)
            
            return drawing_data
        
        except Exception as e:
            raise ParseError(f"Failed to parse PDF file: {str(e)}")
    
    def _extract_content(self, doc: fitz.Document, drawing_data: DrawingData) -> None:
        for page in doc:
            self._extract_page_text(page, drawing_data)
            self._extract_page_drawings(page, drawing_data)
    
    def _extract_page_text(self, page: fitz.Page, drawing_data: DrawingData) -> None:
        text_blocks = page.get_text("blocks")
        
        for block in text_blocks:
            x0, y0, x1, y1, text, _, _ = block
            
            drawing_data.texts.append(TextInfo(
                content=text.strip(),
                position=Coordinate(
                    x=(x0 + x1) / 2,
                    y=(y0 + y1) / 2,
                    z=0.0
                ),
                font_size=y1 - y0
            ))
    
    def _extract_page_drawings(self, page: fitz.Page, drawing_data: DrawingData) -> None:
        drawings = page.get_drawings()
        
        for drawing in drawings:
            if 'items' in drawing:
                for item in drawing['items']:
                    if item[0] == 'l':
                        self._parse_line(item, drawing_data)
                    elif item[0] == 're':
                        self._parse_rectangle(item, drawing_data)
    
    def _parse_line(self, item: tuple, drawing_data: DrawingData) -> None:
        _, x0, y0, x1, y1, _, _, _ = item
        
        drawing_data.lines.append(LineInfo(
            start_point=Coordinate(x=x0, y=y0, z=0.0),
            end_point=Coordinate(x=x1, y=y1, z=0.0)
        ))
    
    def _parse_rectangle(self, item: tuple, drawing_data: DrawingData) -> None:
        _, x0, y0, x1, y1, _, _, _ = item
        
        drawing_data.lines.extend([
            LineInfo(start_point=Coordinate(x=x0, y=y0, z=0.0), end_point=Coordinate(x=x1, y=y0, z=0.0)),
            LineInfo(start_point=Coordinate(x=x1, y=y0, z=0.0), end_point=Coordinate(x=x1, y=y1, z=0.0)),
            LineInfo(start_point=Coordinate(x=x1, y=y1, z=0.0), end_point=Coordinate(x=x0, y=y1, z=0.0)),
            LineInfo(start_point=Coordinate(x=x0, y=y1, z=0.0), end_point=Coordinate(x=x0, y=y0, z=0.0))
        ])
    
    def _check_vector_pdf(self, file_path: str) -> bool:
        try:
            doc = fitz.open(file_path)
            for page in doc:
                if len(page.get_drawings()) > 0:
                    return True
            return False
        except:
            return False