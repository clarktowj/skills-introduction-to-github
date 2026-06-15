import os
from typing import Optional
from common.models import DrawingData
from framework.exceptions import ParseError
from rule_engine.rule_manager import RuleManager
from drawing_parser.dxf_parser import DXFParser
from drawing_parser.pdf_parser import PDFParser
from drawing_parser.image_parser import ImageParser


class DrawingProcessor:
    """
    统一图纸处理入口
    
    支持格式：DXF, PDF, 图像(PNG/JPG/BMP)
    自动根据文件扩展名选择解析器
    所有格式输出统一的 DrawingData 结构
    """

    def __init__(self, rule_manager: RuleManager = None):
        if rule_manager is None:
            rule_manager = RuleManager()
            rule_manager.load_rules()

        self._rule_manager = rule_manager
        self._dxf_parser = DXFParser(rule_manager)
        self._pdf_parser = PDFParser(rule_manager)
        self._image_parser = ImageParser()

    def process(self, file_path: str) -> DrawingData:
        if not os.path.exists(file_path):
            raise ParseError(f"File not found: {file_path}")

        ext = self._get_file_extension(file_path)

        if ext == '.dxf':
            return self._dxf_parser.parse(file_path)
        elif ext == '.pdf':
            return self._pdf_parser.parse(file_path)
        elif ext in ('.jpg', '.jpeg', '.png', '.bmp', '.tiff'):
            return self._image_parser.parse(file_path)
        else:
            raise ParseError(f"Unsupported file type: {ext}")

    @staticmethod
    def _get_file_extension(file_path: str) -> str:
        return os.path.splitext(file_path)[1].lower()

    def is_supported(self, file_path: str) -> bool:
        ext = self._get_file_extension(file_path)
        return ext in ('.dxf', '.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff')
