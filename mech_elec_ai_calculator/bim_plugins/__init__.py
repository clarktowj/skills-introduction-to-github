"""
BIM AI 自动识图建模插件框架
=============================

支持的宿主环境 (Hosts):
  • AutoCAD      -> LISP/NET Plugin
  • 天正电气/建筑 -> CAD二次开发
  • Revit        -> Revit API (.NET)
  • Navisworks   -> 模型审阅
  • 浏览器/Web   -> WebGL/Three.js

插件工作流程:
  1. 宿主软件调用插件入口 (CAD命令: AIMODEL, Revit按钮)
  2. 插件调用本系统的 drawing_parser 识别图元
  3. 通过 bim_modeling 生成3D BIM构件
  4. 将 BIM 构件写回宿主CAD文件
  5. 返回建模进度和日志给用户
"""

import os
import json
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

from common.models import DrawingData, BIMComponent, QuantityItem, CalculationResult
from framework.exceptions import ParseError, ModelingError


# ============ 插件上下文 ============
@dataclass
class PluginContext:
    """插件运行时上下文"""
    plugin_id: str
    host_type: str           # 'autocad' | 'revit' | 'tianzheng' | 'web'
    host_version: str
    project_id: str
    user_id: str
    drawing_path: str
    temp_dir: str
    config: Dict[str, Any] = field(default_factory=dict)
    callbacks: Dict[str, Callable] = field(default_factory=dict)

    # 运行时状态
    drawing_data: Optional[DrawingData] = None
    calc_result: Optional[CalculationResult] = None
    bim_components: List[BIMComponent] = field(default_factory=list)
    progress: float = 0.0
    logs: List[str] = field(default_factory=list)

    def log(self, msg: str, level: str = 'info') -> None:
        ts = datetime.now().strftime('%H:%M:%S')
        entry = f"[{ts}] [{level}] {msg}"
        self.logs.append(entry)
        cb = self.callbacks.get('on_log')
        if cb:
            try: cb(entry)
            except Exception: pass

    def update_progress(self, pct: float, msg: str = '') -> None:
        self.progress = pct
        cb = self.callbacks.get('on_progress')
        if cb:
            try: cb(pct, msg)
            except Exception: pass
        if msg:
            self.log(f"进度 {pct:.0f}% - {msg}")


# ============ 插件基类 ============
class BIMPluginBase:
    """所有BIM建模插件的抽象基类"""
    plugin_name: str = "Base"
    plugin_id: str = "base"
    supported_hosts: List[str] = []

    def __init__(self, ctx: PluginContext):
        self.ctx = ctx
        self.components: List[BIMComponent] = []

    # 由具体子类实现宿主相关逻辑
    def parse_drawing(self) -> DrawingData:
        raise NotImplementedError

    def create_bim_entities(self, components: List[BIMComponent]) -> bool:
        raise NotImplementedError

    def write_back_to_host(self, components: List[BIMComponent]) -> bool:
        raise NotImplementedError

    # 通用流程
    def run(self) -> Dict[str, Any]:
        start = time.time()
        self.ctx.log(f"插件启动: {self.plugin_name}")

        # 1) 识图
        self.ctx.update_progress(10, '解析图纸')
        drawing = self.parse_drawing()
        self.ctx.drawing_data = drawing

        # 2) 算量
        self.ctx.update_progress(40, '执行算量')
        from electrical_calculator.calculator import ElectricalCalculator
        calc = ElectricalCalculator()
        self.ctx.calc_result = calc.calculate(drawing)

        # 3) 生成BIM构件
        self.ctx.update_progress(65, '生成BIM构件')
        from bim_modeling.bim_generator import BIMGenerator
        bim_gen = BIMGenerator(scale_factor=1.0)
        components, geometries = bim_gen.generate_from_drawing(drawing)
        self.ctx.bim_components = components
        self.components = components

        # 4) 写回宿主
        self.ctx.update_progress(85, '写入BIM实体到宿主')
        ok = self.create_bim_entities(components)

        elapsed = time.time() - start
        self.ctx.update_progress(100, f'完成 ({len(components)} 个构件)')
        self.ctx.log(f"建模完成: {len(components)} 个构件, 耗时 {elapsed:.1f}s")

        return {
            'ok': ok,
            'elapsed_sec': elapsed,
            'component_count': len(components),
            'total_cost': self.ctx.calc_result.total_cost,
        }


# ============ AutoCAD LISP 插件 ============
class AutoCADPlugin(BIMPluginBase):
    plugin_name = "AutoCAD AI 建模插件"
    plugin_id = "autocad"
    supported_hosts = ['autocad', 'tianzheng']

    def __init__(self, ctx: PluginContext):
        super().__init__(ctx)

    def parse_drawing(self) -> DrawingData:
        ext = os.path.splitext(self.ctx.drawing_path)[1].lower()
        if ext == '.dxf':
            from drawing_parser.dxf_parser import DXFParser
            return DXFParser().parse(self.ctx.drawing_path)
        elif ext == '.pdf':
            from drawing_parser.pdf_parser import PDFParser
            return PDFParser().parse(self.ctx.drawing_path)
        # dwg 通过外部转换（真实环境下使用 ODA File Converter / ObjectDBX）
        elif ext == '.dwg':
            dxf_path = self._convert_dwg_to_dxf(self.ctx.drawing_path)
            from drawing_parser.dxf_parser import DXFParser
            return DXFParser().parse(dxf_path)
        else:
            raise ParseError(f"不支持的图纸格式: {ext}")

    def _convert_dwg_to_dxf(self, dwg_path: str) -> str:
        """实际项目中通过 ODA File Converter 或 AutoCAD COM 自动化转换"""
        dxf_path = os.path.join(self.ctx.temp_dir, os.path.basename(dwg_path) + '.dxf')
        # stub: 若无真实 DWG 工具，假设原文件是 DXF 兼容
        if not os.path.exists(dxf_path):
            if os.path.exists(dwg_path):
                import shutil
                shutil.copyfile(dwg_path, dxf_path)
        return dxf_path

    def create_bim_entities(self, components: List[BIMComponent]) -> bool:
        """
        生成 AutoCAD 3D 实体脚本 (LISP/Script)

        输出 .scr 脚本文件，用户在 AutoCAD 中运行 (SCRIPT 命令)
        或通过 .NET/COM API 直接插入
        """
        lines = []
        lines.append('; AI BIM Modeling Script')
        lines.append(f'; Generated at {datetime.now().isoformat()}')
        lines.append('; 运行方式: AutoCAD 中执行 "SCRIPT" 命令选择本文件')
        lines.append('(vl-load-com)')
        lines.append('(setvar "OSMODE" 0)')

        # 为每种构件类型创建图层
        layers = {'cabinet': 'A-EQUIP-CABINET',
                  'distribution_box': 'A-EQUIP-PANEL',
                  'equipment': 'A-EQUIP',
                  'fixture': 'A-FIXTURE',
                  'cable': 'A-CABLE',
                  'cable_tray': 'A-CABLE-TRAY',
                  'pipe': 'A-PIPE'}

        for layer in set(layers.values()):
            lines.append(f'(command "_-LAYER" "_M" "{layer}" "")')

        for comp in components:
            layer = layers.get(comp.type.value if hasattr(comp.type, 'value') else str(comp.type), 'A-BIM-DEFAULT')
            lines.append(f'(command "_-LAYER" "_S" "{layer}" "")')
            w, d, h = comp.dimensions
            # 以中心点插入 BOX3D
            lines.append(f'; BIM-COMPONENT id={comp.id} name={comp.name} type={comp.type}')
            lines.append(f'(command "_BOX" '
                         f'"{comp.position.x - w/2:.2f},{comp.position.y - d/2:.2f},0" '
                         f'"{comp.position.x + w/2:.2f},{comp.position.y + d/2:.2f},0" '
                         f'"{h:.2f}")')
            # 添加属性
            lines.append(f'(setq e (entlast))')
            total_price = comp.attributes.get('total_price', 0) if isinstance(comp.attributes, dict) else 0
            quantity = comp.attributes.get('quantity', 1) if isinstance(comp.attributes, dict) else 1
            lines.append(f'(command "_-ATTDEF" " " "{comp.name}" "{quantity}" '
                         f'"{comp.position.x:.2f},{comp.position.y:.2f},{h + 0.5:.2f}" "2.0" "0" "")')

        lines.append('(princ "\\nAI BIM modeling complete - entities inserted")')
        lines.append('(princ)')

        script_path = os.path.join(self.ctx.temp_dir, f'bim_{self.ctx.project_id}.scr')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        self.ctx.log(f"已生成 AutoCAD 脚本: {script_path} ({len(components)} 实体)")
        return True

    def write_back_to_host(self, components: List[BIMComponent]) -> bool:
        # 真实环境下通过 COM/.NET API 直接操作文档
        try:
            self.create_bim_entities(components)
            return True
        except Exception as e:
            self.ctx.log(f"AutoCAD 写入失败: {e}", 'error')
            return False


# ============ Revit 插件 ============
class RevitPlugin(BIMPluginBase):
    plugin_name = "Revit AI 建模插件"
    plugin_id = "revit"
    supported_hosts = ['revit']

    def parse_drawing(self) -> DrawingData:
        ext = os.path.splitext(self.ctx.drawing_path)[1].lower()
        if ext in ('.dxf', '.dwg'):
            from drawing_parser.dxf_parser import DXFParser
            path = self.ctx.drawing_path if ext == '.dxf' else self._prepare_dwg_path(self.ctx.drawing_path)
            return DXFParser().parse(path)
        elif ext == '.pdf':
            from drawing_parser.pdf_parser import PDFParser
            return PDFParser().parse(self.ctx.drawing_path)
        raise ParseError(f"不支持: {ext}")

    def _prepare_dwg_path(self, path: str) -> str:
        # 实际项目中通过 Revit API 从链接的 CAD 提取
        dxf_path = os.path.join(self.ctx.temp_dir, os.path.basename(path) + '.dxf')
        if not os.path.exists(dxf_path) and os.path.exists(path):
            import shutil
            shutil.copyfile(path, dxf_path)
        return dxf_path

    def create_bim_entities(self, components: List[BIMComponent]) -> bool:
        """
        生成 Revit .dyn (Dynamo) 脚本，用于在 Revit 中执行构件创建

        替代方案：生成 .rvt 族实例数据 JSON，通过 RevitAddin 读入
        """
        # Revit 族映射
        family_map = {
            'cabinet': '配电盘',
            'distribution_box': '配电箱',
            'equipment': '电气设备',
            'fixture': '灯具',
            'switch': '开关',
            'cable': '电缆',
            'cable_tray': '电缆桥架',
            'pipe': '配管',
        }

        dyn_data = {
            'schema_version': '2.0',
            'project': self.ctx.project_id,
            'generated_at': datetime.now().isoformat(),
            'components': []
        }

        for comp in components:
            t = comp.type.value if hasattr(comp.type, 'value') else str(comp.type)
            attrs = comp.attributes if isinstance(comp.attributes, dict) else {}
            dyn_data['components'].append({
                'id': comp.id,
                'name': comp.name,
                'family': family_map.get(t, 'GenericModel'),
                'category': 'Electrical Equipment',
                'position': {
                    'x': float(comp.position.x),
                    'y': float(comp.position.y),
                    'z': float(comp.position.z),
                },
                'dimensions': {
                    'width': float(comp.dimensions[0]),
                    'depth': float(comp.dimensions[1]),
                    'height': float(comp.dimensions[2]),
                },
                'quantity_info': {
                    'quantity': attrs.get('quantity', 1),
                    'unit': attrs.get('unit', '个'),
                    'unit_price': attrs.get('unit_price', 0),
                    'total_price': attrs.get('total_price', 0),
                    'code': attrs.get('code', ''),
                }
            })

        dyn_path = os.path.join(self.ctx.temp_dir, f'bim_revit_{self.ctx.project_id}.json')
        with open(dyn_path, 'w', encoding='utf-8') as f:
            json.dump(dyn_data, f, ensure_ascii=False, indent=2)

        self.ctx.log(f"已生成 Revit 导入脚本: {dyn_path}")
        self.ctx.log(f"在 Revit 中用 Dynamo 或自定义 Addin 读取本文件创建 {len(components)} 个构件")
        return True

    def write_back_to_host(self, components: List[BIMComponent]) -> bool:
        return self.create_bim_entities(components)


# ============ Web 浏览器插件 ============
class WebPlugin(BIMPluginBase):
    plugin_name = "Web 浏览器 AI 建模插件"
    plugin_id = "web"
    supported_hosts = ['web', 'browser']

    def parse_drawing(self) -> DrawingData:
        ext = os.path.splitext(self.ctx.drawing_path)[1].lower()
        if ext == '.dxf':
            from drawing_parser.dxf_parser import DXFParser
            return DXFParser().parse(self.ctx.drawing_path)
        elif ext == '.pdf':
            from drawing_parser.pdf_parser import PDFParser
            return PDFParser().parse(self.ctx.drawing_path)
        raise ParseError(f"不支持: {ext}")

    def create_bim_entities(self, components: List[BIMComponent]) -> bool:
        """生成 Three.js 可直接加载的 JSON 数据"""
        viewer_path = os.path.join(self.ctx.temp_dir, f'bim_web_{self.ctx.project_id}.html')
        from bim_modeling.viewer3d import Viewer3D
        from bim_modeling.model_manager import ModelManager

        mm = ModelManager()
        mm.add_components(components)
        Viewer3D().generate(mm, viewer_path)
        self.ctx.log(f"已生成 Web 3D 查看器: {viewer_path}")

        # 同时输出 JSON 数据
        data_path = os.path.join(self.ctx.temp_dir, f'bim_data_{self.ctx.project_id}.json')
        out = [
            {
                'id': c.id,
                'name': c.name,
                'type': c.type.value if hasattr(c.type, 'value') else str(c.type),
                'position': {'x': c.position.x, 'y': c.position.y, 'z': c.position.z},
                'dimensions': {
                    'w': c.dimensions[0], 'd': c.dimensions[1], 'h': c.dimensions[2]
                },
                'attributes': c.attributes if isinstance(c.attributes, dict) else {},
            }
            for c in components
        ]
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump({'components': out, 'count': len(components)}, f, ensure_ascii=False, indent=2)
        self.ctx.log(f"已生成 Web 数据文件: {data_path}")
        return True

    def write_back_to_host(self, components: List[BIMComponent]) -> bool:
        return self.create_bim_entities(components)


# ============ 插件注册表 ============
class PluginRegistry:
    """插件注册表 —— 根据图纸类型/宿主环境自动选择"""

    def __init__(self):
        self._plugins: Dict[str, BIMPluginBase] = {
            'autocad': AutoCADPlugin,
            'revit': RevitPlugin,
            'web': WebPlugin,
            'tianzheng': AutoCADPlugin,
        }

    def register(self, key: str, plugin_cls) -> None:
        self._plugins[key] = plugin_cls

    def create(self, host: str, ctx: PluginContext) -> BIMPluginBase:
        if host not in self._plugins:
            raise ModelingError(f"不支持的宿主环境: {host}")
        plugin_cls = self._plugins[host]
        return plugin_cls(ctx)

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())


# ============ 便捷 API ============
def run_pipeline_for_host(
    drawing_path: str,
    host_type: str = 'web',
    project_id: Optional[str] = None,
    user_id: str = 'demo',
    output_dir: Optional[str] = None,
    on_progress: Optional[Callable[[float, str], None]] = None,
    on_log: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    一键运行：从图纸到目标宿主环境的 BIM 建模

    Args:
        drawing_path: 图纸文件路径 (.dxf/.pdf/.dwg)
        host_type: 'autocad' | 'revit' | 'web'
        project_id: 项目ID（用于文件命名）
        output_dir: 输出目录（默认 ./outputs/plugins/）
        on_progress: 进度回调 (percent, message)
        on_log: 日志回调 (message)

    Returns:
        dict 结果报告
    """
    pid = project_id or f"PRJ-{uuid.uuid4().hex[:8].upper()}"

    temp_dir = output_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'outputs', 'plugins'
    )
    os.makedirs(temp_dir, exist_ok=True)

    ctx = PluginContext(
        plugin_id='pipeline',
        host_type=host_type,
        host_version='2024',
        project_id=pid,
        user_id=user_id,
        drawing_path=drawing_path,
        temp_dir=temp_dir,
        callbacks={'on_progress': on_progress or (lambda p, m: None),
                   'on_log': on_log or (lambda m: None)},
    )

    registry = PluginRegistry()
    plugin = registry.create(host_type, ctx)
    ctx.plugin_id = plugin.plugin_id

    result = plugin.run()

    report = {
        'project_id': pid,
        'host': host_type,
        'plugin': plugin.plugin_name,
        'drawing': os.path.basename(drawing_path),
        **result,
        'output_dir': temp_dir,
        'generated_files': [
            os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
            if f.startswith('bim_') and pid in f
        ],
        'log_tail': ctx.logs[-20:],
    }
    return report
