from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime

class Coordinate(BaseModel):
    x: float = Field(..., description="X坐标")
    y: float = Field(..., description="Y坐标")
    z: float = Field(0.0, description="Z坐标，默认0")

class DeviceType(str, Enum):
    CABINET = "cabinet"
    EQUIPMENT = "equipment"
    DISTRIBUTION_BOX = "distribution_box"
    SWITCH = "switch"
    SOCKET = "socket"
    LIGHTING = "lighting"
    OTHER = "other"

class DeviceModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="设备唯一标识")
    component_id: Optional[str] = Field(None, description="关联的BIM构件ID")
    name: str = Field(..., description="设备名称")
    type: DeviceType = Field(..., description="设备类型")
    spec: str = Field("", description="设备规格型号")
    coordinates: Coordinate = Field(..., description="设备位置坐标")
    quantity: int = Field(1, description="设备数量")
    layer: str = Field("", description="所在图层")
    block_name: Optional[str] = Field(None, description="图块名称")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="额外属性")
    created_at: datetime = Field(default_factory=datetime.now)

class CableType(str, Enum):
    POWER = "power"
    CONTROL = "control"
    SIGNAL = "signal"
    COMMUNICATION = "communication"
    OTHER = "other"

class LayingMethod(str, Enum):
    TRUNKING = "trunking"
    PIPE = "pipe"
    DIRECT_BURIAL = "direct_burial"
    CABLE_TRAY = "cable_tray"
    WALL = "wall"
    CEILING = "ceiling"

class CableModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="线缆唯一标识")
    component_id: Optional[str] = Field(None, description="关联的BIM构件ID")
    model: str = Field(..., description="线缆型号")
    type: CableType = Field(..., description="线缆类型")
    start_point: Coordinate = Field(..., description="起点坐标")
    end_point: Coordinate = Field(..., description="终点坐标")
    length: float = Field(0.0, description="实际长度")
    reserved_length: float = Field(0.0, description="预留长度")
    total_length: float = Field(0.0, description="总长度（实际+预留）")
    laying_method: LayingMethod = Field(LayingMethod.CABLE_TRAY, description="敷设方式")
    core_count: int = Field(1, description="芯数")
    cross_section: float = Field(1.0, description="截面面积 mm²")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="额外属性")
    created_at: datetime = Field(default_factory=datetime.now)

class LayerInfo(BaseModel):
    name: str = Field(..., description="图层名称")
    color: Optional[str] = Field(None, description="图层颜色")
    line_type: Optional[str] = Field(None, description="线型")
    visible: bool = Field(True, description="是否可见")
    locked: bool = Field(False, description="是否锁定")

class BlockInfo(BaseModel):
    name: str = Field(..., description="图块名称")
    insertion_point: Coordinate = Field(..., description="插入点")
    rotation: float = Field(0.0, description="旋转角度")
    scale: float = Field(1.0, description="缩放比例")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="图块属性")

class LineInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="线条唯一标识")
    start_point: Coordinate = Field(..., description="起点")
    end_point: Coordinate = Field(..., description="终点")
    layer: str = Field("", description="所在图层")
    line_type: Optional[str] = Field(None, description="线型")
    color: Optional[str] = Field(None, description="颜色")

class TextInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="文字唯一标识")
    content: str = Field(..., description="文字内容")
    position: Coordinate = Field(..., description="位置")
    layer: str = Field("", description="所在图层")
    font_size: float = Field(10.0, description="字体大小")
    rotation: float = Field(0.0, description="旋转角度")

class DrawingData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="图纸唯一标识")
    filename: str = Field(..., description="原始文件名")
    file_type: str = Field(..., description="文件类型（dxf/pdf/image）")
    width: float = Field(0.0, description="图纸宽度")
    height: float = Field(0.0, description="图纸高度")
    layers: List[LayerInfo] = Field(default_factory=list, description="图层信息")
    blocks: List[BlockInfo] = Field(default_factory=list, description="图块信息")
    lines: List[LineInfo] = Field(default_factory=list, description="线条信息")
    texts: List[TextInfo] = Field(default_factory=list, description="文字信息")
    devices: List[DeviceModel] = Field(default_factory=list, description="识别到的设备")
    cables: List[CableModel] = Field(default_factory=list, description="识别到的线缆")
    trunkings: List[Dict[str, Any]] = Field(default_factory=list, description="识别到的桥架")
    created_at: datetime = Field(default_factory=datetime.now)
    parsed_at: Optional[datetime] = Field(None, description="解析时间")

class QuantityItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="工程量项唯一标识")
    component_id: str = Field(..., description="关联的构件ID")
    code: str = Field("", description="定额编号")
    name: str = Field(..., description="项目名称")
    unit: str = Field(..., description="计量单位")
    quantity: float = Field(0.0, description="数量")
    unit_price: float = Field(0.0, description="单价")
    total_price: float = Field(0.0, description="合价")
    category: str = Field("", description="分类")
    sub_category: str = Field("", description="子分类")
    description: str = Field("", description="项目描述")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="额外属性")

class CalculationResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="算量结果唯一标识")
    drawing_id: str = Field(..., description="关联的图纸ID")
    devices: List[QuantityItem] = Field(default_factory=list, description="设备工程量")
    cables: List[QuantityItem] = Field(default_factory=list, description="线缆工程量")
    trunkings: List[QuantityItem] = Field(default_factory=list, description="桥架工程量")
    pipes: List[QuantityItem] = Field(default_factory=list, description="配管工程量")
    accessories: List[QuantityItem] = Field(default_factory=list, description="辅材工程量")
    total_cost: float = Field(0.0, description="总造价")
    calculated_at: datetime = Field(default_factory=datetime.now)
    rule_version: str = Field("", description="使用的规则版本")

class BIMComponentType(str, Enum):
    CABINET = "cabinet"
    EQUIPMENT = "equipment"
    DISTRIBUTION_BOX = "distribution_box"
    CABLE = "cable"
    CABLE_TRAY = "cable_tray"
    PIPE = "pipe"
    FIXTURE = "fixture"
    OTHER = "other"

class BIMComponent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="构件唯一标识")
    name: str = Field(..., description="构件名称")
    type: BIMComponentType = Field(..., description="构件类型")
    position: Coordinate = Field(..., description="位置坐标")
    dimensions: Tuple[float, float, float] = Field((1.0, 1.0, 1.0), description="尺寸")
    rotation: Tuple[float, float, float] = Field((0.0, 0.0, 0.0), description="旋转角度")
    quantity_id: Optional[str] = Field(None, description="关联的工程量ID")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="额外属性")
    created_at: datetime = Field(default_factory=datetime.now)

class AuditIssueType(str, Enum):
    MISSING_DEVICE = "missing_device"
    WRONG_DEVICE = "wrong_device"
    MISSING_CABLE = "missing_cable"
    WRONG_CABLE_LENGTH = "wrong_cable_length"
    WRONG_CABLE_MODEL = "wrong_cable_model"
    MODEL_QUANTITY_MISMATCH = "model_quantity_mismatch"
    SPECIFICATION_ERROR = "specification_error"
    LAYING_LOGIC_ERROR = "laying_logic_error"
    DIMENSION_ERROR = "dimension_error"
    OTHER = "other"

class AuditIssue(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="问题唯一标识")
    type: AuditIssueType = Field(..., description="问题类型")
    severity: str = Field("medium", description="严重程度: low/medium/high/critical")
    description: str = Field(..., description="问题描述")
    location: Optional[Coordinate] = Field(None, description="问题位置")
    suggestion: str = Field("", description="修正建议")
    related_component_id: Optional[str] = Field(None, description="关联构件ID")
    related_quantity_id: Optional[str] = Field(None, description="关联工程量ID")

class AuditResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="审核结果唯一标识")
    calculation_id: str = Field(..., description="关联的算量结果ID")
    drawing_id: str = Field(..., description="关联的图纸ID")
    issues: List[AuditIssue] = Field(default_factory=list, description="发现的问题")
    passed: bool = Field(False, description="是否通过审核")
    audit_score: float = Field(100.0, description="审核分数")
    audit_time: datetime = Field(default_factory=datetime.now)
    ai_version: str = Field("", description="AI版本")

class ListSummary(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="清单唯一标识")
    project_name: str = Field("", description="项目名称")
    project_code: str = Field("", description="项目编号")
    calculation_id: str = Field(..., description="关联的算量结果ID")
    audit_id: Optional[str] = Field(None, description="关联的审核结果ID")
    items: List[QuantityItem] = Field(default_factory=list, description="清单项目")
    total_quantity: float = Field(0.0, description="总数量")
    total_cost: float = Field(0.0, description="总造价")
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = Field("draft", description="状态: draft/reviewed/approved")

class TaskConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    task_name: str = Field(..., description="任务名称")
    input_files: List[str] = Field(default_factory=list, description="输入文件路径列表")
    output_path: str = Field("./outputs", description="输出路径")
    rule_version: str = Field("latest", description="规则版本")
    enable_audit: bool = Field(True, description="是否启用AI审核")
    enable_modeling: bool = Field(True, description="是否启用BIM建模")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="额外参数")

class TaskResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    task_id: str = Field(default_factory=lambda: str(uuid4()), description="任务唯一标识")
    task_name: str = Field(..., description="任务名称")
    status: str = Field("completed", description="状态: pending/running/completed/failed")
    drawing_data: Optional[DrawingData] = Field(None, description="解析后的图纸数据")
    calculation_result: Optional[CalculationResult] = Field(None, description="算量结果")
    bim_components: List[BIMComponent] = Field(default_factory=list, description="BIM构件")
    audit_result: Optional[AuditResult] = Field(None, description="审核结果")
    list_summary: Optional[ListSummary] = Field(None, description="清单汇总")
    output_files: List[str] = Field(default_factory=list, description="输出文件列表")
    error_message: Optional[str] = Field(None, description="错误信息")
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None, description="完成时间")