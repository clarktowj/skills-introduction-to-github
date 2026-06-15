from typing import Dict, Any, Optional
from datetime import datetime
from common.models import TaskConfig, TaskResult, DrawingData, CalculationResult, AuditResult, ListSummary, BIMComponent
from framework.app import Application
from framework.exceptions import AppStartupError
from drawing_parser.drawing_processor import DrawingProcessor
from electrical_calculator.calculator import ElectricalCalculator
from bim_modeling.bim_generator import BIMGenerator
from bim_modeling.model_manager import ModelManager
from list_summary.summary_generator import SummaryGenerator
from list_summary.excel_exporter import ExcelExporter
from openhuman_audit.audit_client import OpenHumanClient  # renamed from OpenHumanAuditClient
from rule_engine.rule_manager import RuleManager

class TaskScheduler:
    def __init__(self):
        self._app = Application()
        self._rule_manager = RuleManager()
    
    def execute(self, task_config: TaskConfig) -> TaskResult:
        result = TaskResult(task_name=task_config.task_name)
        
        try:
            self._app.initialize()
            
            self._rule_manager.load_rules(task_config.rule_version)
            
            drawing_data = self._step_parse_drawing(task_config.input_files)
            result.drawing_data = drawing_data
            
            calculation_result = self._step_calculate(drawing_data)
            result.calculation_result = calculation_result
            
            if task_config.enable_modeling:
                bim_components = self._step_generate_bim(drawing_data, calculation_result)
                result.bim_components = bim_components
            
            if task_config.enable_audit:
                audit_result = self._step_audit(drawing_data, calculation_result)
                result.audit_result = audit_result
            
            list_summary = self._step_generate_summary(calculation_result, result.audit_result)
            result.list_summary = list_summary
            
            output_files = self._step_export(task_config.output_path, list_summary, result.bim_components)
            result.output_files = output_files
            
            result.status = "completed"
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            self._app.logger.error(f"Task failed: {str(e)}")
        
        result.completed_at = datetime.now()
        
        return result
    
    def _step_parse_drawing(self, input_files: list) -> DrawingData:
        processor = DrawingProcessor()
        
        if not input_files:
            raise ValueError("No input files provided")
        
        first_file = input_files[0]
        
        self._app.logger.info(f"Parsing drawing: {first_file}")
        
        return processor.process(first_file)
    
    def _step_calculate(self, drawing_data: DrawingData) -> CalculationResult:
        calculator = ElectricalCalculator()
        
        self._app.logger.info("Performing electrical quantity calculation")
        
        return calculator.calculate(drawing_data)
    
    def _step_generate_bim(self, drawing_data: DrawingData, calculation: CalculationResult) -> list:
        generator = BIMGenerator()
        
        self._app.logger.info("Generating BIM model")
        
        components = generator.generate_from_drawing(
            drawing_data.devices,
            drawing_data.cables
        )
        
        manager = ModelManager()
        manager.add_components(components)
        
        try:
            manager.validate_quantity_binding(calculation)
            self._app.logger.info("Quantity-model binding validation passed")
        except Exception as e:
            self._app.logger.warning(f"Binding validation warning: {str(e)}")
        
        return components
    
    def _step_audit(self, drawing_data: DrawingData, calculation: CalculationResult) -> Optional[AuditResult]:
        try:
            audit_client = OpenHumanClient()
            
            self._app.logger.info("Starting AI audit")
            
            return audit_client.audit(drawing_data, calculation)
        except Exception as e:
            self._app.logger.warning(f"Audit skipped: {str(e)}")
            return None
    
    def _step_generate_summary(self, calculation: CalculationResult, audit: Optional[AuditResult]) -> ListSummary:
        generator = SummaryGenerator()
        
        self._app.logger.info("Generating quantity list summary")
        
        return generator.generate(
            calculation,
            audit,
            project_name="Electrical Project",
            project_code="EP-001"
        )
    
    def _step_export(self, output_path: str, summary: ListSummary, bim_components: list) -> list:
        output_files = []
        
        excel_path = f"{output_path}/工程量清单.xlsx"
        exporter = ExcelExporter()
        exported_path = exporter.export(summary, excel_path)
        output_files.append(exported_path)
        
        self._app.logger.info(f"Exported to: {exported_path}")
        
        if bim_components:
            from bim_modeling.ifc_exporter import IFCExporter
            
            ifc_path = f"{output_path}/model.ifc"
            ifc_exporter = IFCExporter()
            ifc_exported_path = ifc_exporter.export(bim_components, ifc_path)
            output_files.append(ifc_exported_path)
            
            self._app.logger.info(f"Exported IFC model to: {ifc_exported_path}")
        
        return output_files