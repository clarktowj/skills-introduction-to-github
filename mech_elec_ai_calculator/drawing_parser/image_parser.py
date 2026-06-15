import cv2
import numpy as np
import os
from typing import List, Dict, Any
from common.models import DrawingData, LineInfo, TextInfo, Coordinate
from framework.exceptions import ParseError

class ImageParser:
    def __init__(self):
        self._yolo_model = None
    
    def parse(self, file_path: str) -> DrawingData:
        if not os.path.exists(file_path):
            raise ParseError(f"File not found: {file_path}")
        
        try:
            image = cv2.imread(file_path)
            
            if image is None:
                raise ParseError(f"Failed to read image file: {file_path}")
            
            drawing_data = DrawingData(
                filename=os.path.basename(file_path),
                file_type='image'
            )
            
            self._extract_lines(image, drawing_data)
            self._extract_texts(image, drawing_data)
            
            return drawing_data
        
        except Exception as e:
            raise ParseError(f"Failed to parse image file: {str(e)}")
    
    def _extract_lines(self, image: np.ndarray, drawing_data: DrawingData) -> None:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=10, maxLineGap=10)
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                
                drawing_data.lines.append(LineInfo(
                    start_point=Coordinate(x=float(x1), y=float(y1), z=0.0),
                    end_point=Coordinate(x=float(x2), y=float(y2), z=0.0)
                ))
    
    def _extract_texts(self, image: np.ndarray, drawing_data: DrawingData) -> None:
        try:
            import pytesseract
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            if text:
                drawing_data.texts.append(TextInfo(
                    content=text,
                    position=Coordinate(x=0.0, y=0.0, z=0.0)
                ))
        except ImportError:
            pass
        except Exception:
            pass
    
    def _detect_objects(self, image: np.ndarray) -> List[Dict[str, Any]]:
        if self._yolo_model is None:
            return []
        
        results = self._yolo_model(image)
        detections = []
        
        for result in results.xyxy[0]:
            x1, y1, x2, y2, conf, cls = result
            detections.append({
                'x1': float(x1),
                'y1': float(y1),
                'x2': float(x2),
                'y2': float(y2),
                'confidence': float(conf),
                'class': int(cls)
            })
        
        return detections