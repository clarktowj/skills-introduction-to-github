"""
3D BIM 几何生成器

从图纸识别结果（设备/线缆/桥架）生成三维BIM构件：
  • 电柜/配电箱 → 立方体 (BoxGeometry)
  • 线缆         → 圆柱体线条 (CylinderGeometry along path)
  • 桥架         → 矩形条 (BoxGeometry)
  • 开关/插座    → 小立方体

坐标系统：
  • 输入坐标：CAD/PDF原始坐标（通常为毫米或绘图单位）
  • 输出坐标：自动缩放为 BIM 米制单位 (meters)
  • 默认缩放系数：CAD坐标 / 1000 → 米
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from common.models import (
    BIMComponent, BIMComponentType,
    DeviceModel, CableModel, DrawingData,
    Coordinate, QuantityItem, CalculationResult
)
from framework.exceptions import ModelingError


@dataclass
class Geometry3D:
    """3D几何描述 —— 用于 Three.js 可视化与 IFC 导出"""
    shape_type: str  # 'box' | 'cylinder' | 'line'
    position: Tuple[float, float, float]  # 中心位置 (x, y, z) 米
    dimensions: Tuple[float, float, float]  # 宽 x 深 x 高 (米)
    color: str = '#888888'  # RGB 颜色
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # 弧度
    path_points: Optional[List[Tuple[float, float, float]]] = None  # 线缆路径
    radius: float = 0.05  # 线缆/圆柱体半径


class BIMGenerator:
    """3D BIM 构件生成器"""

    # 设备类型 → 标准尺寸 (米)
    DEVICE_DIMENSIONS: Dict[str, Tuple[float, float, float]] = {
        'cabinet': (0.8, 0.6, 2.0),           # 配电柜: 宽x深x高
        'equipment': (1.0, 1.0, 1.0),          # 一般设备
        'distribution_box': (0.4, 0.25, 0.5),  # 配电箱
        'switch': (0.1, 0.05, 0.1),            # 开关
        'socket': (0.08, 0.04, 0.08),          # 插座
        'lighting': (0.3, 0.3, 0.1),           # 照明灯具
        'other': (0.5, 0.5, 0.5),              # 其他
    }

    # 设备类型 → 颜色 (HEX)
    DEVICE_COLORS: Dict[str, str] = {
        'cabinet': '#2E86AB',          # 深青蓝
        'equipment': '#F18F01',        # 橙色
        'distribution_box': '#6FAE5A', # 绿色
        'switch': '#C73E1D',           # 红色
        'socket': '#3B1F2B',           # 深紫
        'lighting': '#F4D35E',         # 黄色
        'other': '#8A8A8A',            # 灰色
    }

    # 线缆类型 → 颜色
    CABLE_COLORS: Dict[str, str] = {
        'power': '#D62828',             # 红色 - 电力
        'control': '#2D6A4F',           # 绿色 - 控制
        'signal': '#1D3557',            # 蓝色 - 信号
        'communication': '#6A4C93',     # 紫色 - 通信
        'other': '#888888',
    }

    # 桥架颜色
    TRAY_COLOR = '#A3A380'
    PIPE_COLOR = '#6B705C'

    def __init__(self, scale_factor: float = 1.0):
        """
        Args:
            scale_factor: CAD坐标到米的缩放系数。CAD图纸单位为mm时用0.001
        """
        self._scale_factor = scale_factor
        self._components: List[BIMComponent] = []
        self._geometries: Dict[str, Geometry3D] = {}
        self._id_counter = 0

    # ============ 主生成入口 ============

    def generate_from_drawing(
        self,
        drawing_data: DrawingData
    ) -> Tuple[List[BIMComponent], Dict[str, Geometry3D]]:
        """
        从图纸识别结果生成完整BIM模型

        Returns:
            (components, geometries)  —— 构件列表及3D几何描述
        """
        try:
            self._components.clear()
            self._geometries.clear()

            # 1. 生成设备构件（立方体）
            for device in drawing_data.devices:
                comp, geom = self._create_device_component(device, drawing_data)
                if comp:
                    self._components.append(comp)
                    self._geometries[comp.id] = geom

            # 2. 生成线缆构件（线条/圆柱体）
            for cable in drawing_data.cables:
                comp, geom = self._create_cable_component(cable, drawing_data)
                if comp:
                    self._components.append(comp)
                    self._geometries[comp.id] = geom

            # 3. 生成桥架/线槽构件（矩形条）
            for trunking in drawing_data.trunkings:
                comp, geom = self._create_trunking_component(trunking, drawing_data)
                if comp:
                    self._components.append(comp)
                    self._geometries[comp.id] = geom

            return self._components, self._geometries

        except Exception as e:
            raise ModelingError(f"BIM建模失败: {str(e)}")

    def generate_from_calculation(
        self,
        calculation: CalculationResult,
        drawing_data: Optional[DrawingData] = None
    ) -> Tuple[List[BIMComponent], Dict[str, Geometry3D]]:
        """
        从算量结果生成BIM模型（DEMO模式：自动排布置）

        当没有图纸坐标信息时，自动按分类排列构件
        """
        try:
            self._components.clear()
            self._geometries.clear()

            x_cursor = {'cabinet': 0.0, 'cable': 0.0, 'tray': 0.0, 'pipe': 0.0, 'other': 0.0}
            y_cursor = 0.0

            # 设备 → 底部一排立方体
            for item in calculation.devices:
                dev_type = self._infer_type_from_name(item.name, item.category)
                dims = self.DEVICE_DIMENSIONS.get(dev_type, self.DEVICE_DIMENSIONS['other'])
                color = self.DEVICE_COLORS.get(dev_type, self.DEVICE_COLORS['other'])

                position = (x_cursor['cabinet'], 0.0, 0.0)
                x_cursor['cabinet'] += dims[0] + 1.0  # 间距1米

                comp = BIMComponent(
                    id=self._next_id(),
                    name=item.name,
                    type=BIMComponentType(dev_type) if dev_type in [e.value for e in BIMComponentType]
                         else BIMComponentType.EQUIPMENT,
                    position=Coordinate(x=position[0], y=position[1], z=position[2]),
                    dimensions=dims,
                    rotation=(0.0, 0.0, 0.0),
                    quantity_id=item.id,
                    attributes={
                        'code': item.code,
                        'quantity': item.quantity,
                        'unit': item.unit,
                        'unit_price': item.unit_price,
                        'total_price': item.total_price,
                        'category': item.category,
                        'drawing_id': drawing_data.id if drawing_data else '',
                    }
                )
                geom = Geometry3D(
                    shape_type='box',
                    position=position,
                    dimensions=dims,
                    color=color
                )
                self._components.append(comp)
                self._geometries[comp.id] = geom

            # 线缆 → 空中排布（Z轴升高）
            for item in calculation.cables:
                cable_length = max(0.5, item.quantity if item.quantity < 1000 else 5.0)
                position = (x_cursor['cable'], 2.0, 1.5)
                x_cursor['cable'] += 2.0

                comp = BIMComponent(
                    id=self._next_id(),
                    name=item.name,
                    type=BIMComponentType.CABLE,
                    position=Coordinate(x=position[0], y=position[1], z=position[2]),
                    dimensions=(cable_length, 0.05, 0.05),
                    quantity_id=item.id,
                    attributes={
                        'code': item.code,
                        'quantity': item.quantity,
                        'unit': item.unit,
                        'unit_price': item.unit_price,
                        'total_price': item.total_price,
                        'length': item.quantity,
                    }
                )
                geom = Geometry3D(
                    shape_type='cylinder',
                    position=position,
                    dimensions=(cable_length, 0.05, 0.05),
                    color=self.CABLE_COLORS.get(item.category.lower(), self.CABLE_COLORS['power']),
                    radius=0.03
                )
                self._components.append(comp)
                self._geometries[comp.id] = geom

            # 桥架 → 顶部一排
            for item in calculation.trunkings:
                tray_length = max(1.0, min(item.quantity, 10.0))
                position = (x_cursor['tray'], 3.5, 0.0)
                x_cursor['tray'] += tray_length + 0.5

                comp = BIMComponent(
                    id=self._next_id(),
                    name=item.name,
                    type=BIMComponentType.CABLE_TRAY,
                    position=Coordinate(x=position[0], y=position[1], z=position[2]),
                    dimensions=(tray_length, 0.3, 0.1),
                    quantity_id=item.id,
                    attributes={
                        'code': item.code,
                        'quantity': item.quantity,
                        'unit': item.unit,
                        'unit_price': item.unit_price,
                        'total_price': item.total_price,
                    }
                )
                geom = Geometry3D(
                    shape_type='box',
                    position=position,
                    dimensions=(tray_length, 0.3, 0.1),
                    color=self.TRAY_COLOR
                )
                self._components.append(comp)
                self._geometries[comp.id] = geom

            # 配管
            for item in calculation.pipes:
                pipe_length = max(1.0, min(item.quantity, 10.0))
                position = (x_cursor['pipe'], 3.2, 0.0)
                x_cursor['pipe'] += pipe_length + 0.5

                comp = BIMComponent(
                    id=self._next_id(),
                    name=item.name,
                    type=BIMComponentType.PIPE,
                    position=Coordinate(x=position[0], y=position[1], z=position[2]),
                    dimensions=(pipe_length, 0.05, 0.05),
                    quantity_id=item.id,
                    attributes={
                        'code': item.code,
                        'quantity': item.quantity,
                        'unit': item.unit,
                        'unit_price': item.unit_price,
                        'total_price': item.total_price,
                    }
                )
                geom = Geometry3D(
                    shape_type='cylinder',
                    position=position,
                    dimensions=(pipe_length, 0.05, 0.05),
                    color=self.PIPE_COLOR,
                    radius=0.02
                )
                self._components.append(comp)
                self._geometries[comp.id] = geom

            return self._components, self._geometries

        except Exception as e:
            raise ModelingError(f"从算量结果生成BIM失败: {str(e)}")

    # ============ 设备构件生成 ============

    def _create_device_component(
        self,
        device: DeviceModel,
        drawing_data: DrawingData
    ) -> Tuple[Optional[BIMComponent], Optional[Geometry3D]]:
        """创建设备3D构件（立方体）"""
        try:
            dev_type = device.type.value
            dims = self.DEVICE_DIMENSIONS.get(dev_type, self.DEVICE_DIMENSIONS['other'])
            color = self.DEVICE_COLORS.get(dev_type, self.DEVICE_COLORS['other'])

            # 将CAD坐标缩放到米制
            pos = self._scale_coordinate(device.coordinates)

            comp_id = self._next_id()

            comp = BIMComponent(
                id=comp_id,
                name=device.name,
                type=self._map_device_type(dev_type),
                position=Coordinate(x=pos[0], y=pos[1], z=pos[2]),
                dimensions=dims,
                rotation=(0.0, 0.0, 0.0),
                attributes={
                    'device_type': dev_type,
                    'spec': device.spec,
                    'quantity': device.quantity,
                    'block_name': device.block_name or '',
                    'drawing_id': drawing_data.id,
                }
            )

            # 将设备的 component_id 设为 BIM 构件 ID（用于反向绑定）
            # DeviceModel 是 Pydantic，需通过 attributes 间接绑定
            comp.attributes['device_id'] = device.id

            geom = Geometry3D(
                shape_type='box',
                position=pos,
                dimensions=dims,
                color=color
            )

            return comp, geom

        except Exception as e:
            print(f"[WARN] 设备 '{device.name}' 建模失败: {e}")
            return None, None

    # ============ 线缆构件生成 ============

    def _create_cable_component(
        self,
        cable: CableModel,
        drawing_data: DrawingData
    ) -> Tuple[Optional[BIMComponent], Optional[Geometry3D]]:
        """创建线缆3D构件（圆柱体/线条）"""
        try:
            cable_type = cable.type.value
            color = self.CABLE_COLORS.get(cable_type, self.CABLE_COLORS['other'])

            # 起点/终点坐标（缩放为米）
            sp = self._scale_coordinate(cable.start_point)
            ep = self._scale_coordinate(cable.end_point)

            # 若起止点相同（PDF解析常见问题），生成一个默认长度
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(sp, ep)))
            if dist < 0.1:
                # 沿X方向生成一条线缆
                ep = (sp[0] + max(1.0, cable.length * self._scale_factor * 0.1), sp[1], sp[2])

            # 线缆升到Z轴高度（模拟桥架敷设）
            z_height = 2.5 if cable.laying_method.value == 'cable_tray' else 1.0 \
                if hasattr(cable.laying_method, 'value') else 2.0
            sp = (sp[0], sp[1], z_height)
            ep = (ep[0], ep[1], z_height)

            # 中心点
            mid = ((sp[0] + ep[0]) / 2, (sp[1] + ep[1]) / 2, (sp[2] + ep[2]) / 2)
            length = math.sqrt(sum((a - b) ** 2 for a, b in zip(sp, ep)))
            length = max(0.5, length)  # 最小0.5米

            comp_id = self._next_id()
            cable_radius = max(0.02, min(0.08, cable.cross_section / 500))

            comp = BIMComponent(
                id=comp_id,
                name=f"{cable.model} ({cable_type})",
                type=BIMComponentType.CABLE,
                position=Coordinate(x=mid[0], y=mid[1], z=mid[2]),
                dimensions=(length, cable_radius * 2, cable_radius * 2),
                rotation=(0.0, 0.0, 0.0),
                attributes={
                    'cable_type': cable_type,
                    'model': cable.model,
                    'length': cable.length,
                    'laying_method': cable.laying_method.value if hasattr(cable.laying_method, 'value') else str(cable.laying_method),
                    'core_count': cable.core_count,
                    'cross_section': cable.cross_section,
                    'drawing_id': drawing_data.id,
                }
            )

            geom = Geometry3D(
                shape_type='cylinder',
                position=mid,
                dimensions=(length, cable_radius * 2, cable_radius * 2),
                color=color,
                path_points=[sp, ep],
                radius=cable_radius
            )

            return comp, geom

        except Exception as e:
            print(f"[WARN] 线缆建模失败: {e}")
            return None, None

    # ============ 桥架构件生成 ============

    def _create_trunking_component(
        self,
        trunking: Dict[str, Any],
        drawing_data: DrawingData
    ) -> Tuple[Optional[BIMComponent], Optional[Geometry3D]]:
        """创建桥架3D构件（矩形条）"""
        try:
            t_type = trunking.get('type', 'cable_tray')
            name = trunking.get('name', '桥架')
            length_m = max(1.0, float(trunking.get('length', 3.0)) * self._scale_factor)
            length_m = min(length_m, 20.0)  # 最大20米显示长度

            # 桥架放到 Z=3.0 高度
            comp_id = self._next_id()

            # 自动排列，避免重叠
            x_pos = float(len(self._components)) * 0.5
            position = (x_pos, 0.0, 3.0)

            dims = (length_m, 0.3, 0.1)  # 长 x 宽 x 高
            color = self.TRAY_COLOR if t_type == 'cable_tray' else self.PIPE_COLOR
            bim_type = BIMComponentType.CABLE_TRAY if t_type == 'cable_tray' else BIMComponentType.PIPE

            comp = BIMComponent(
                id=comp_id,
                name=name,
                type=bim_type,
                position=Coordinate(x=position[0], y=position[1], z=position[2]),
                dimensions=dims,
                rotation=(0.0, 0.0, 0.0),
                attributes={
                    'type': t_type,
                    'length': trunking.get('length', 0),
                    'line_count': trunking.get('line_count', 0),
                    'drawing_id': drawing_data.id,
                }
            )

            geom = Geometry3D(
                shape_type='box',
                position=position,
                dimensions=dims,
                color=color
            )

            return comp, geom

        except Exception as e:
            print(f"[WARN] 桥架建模失败: {e}")
            return None, None

    # ============ 辅助方法 ============

    def _scale_coordinate(self, coord: Coordinate) -> Tuple[float, float, float]:
        """将CAD坐标缩放到米制"""
        return (
            float(coord.x) * self._scale_factor,
            float(coord.y) * self._scale_factor,
            float(coord.z) * self._scale_factor
        )

    def _next_id(self) -> str:
        """生成递增的可读ID（同时保留UUID兼容）"""
        import uuid
        self._id_counter += 1
        return f"BIM-{self._id_counter:04d}-{uuid.uuid4().hex[:6]}"

    @staticmethod
    def _map_device_type(device_type: str) -> BIMComponentType:
        mapping = {
            'cabinet': BIMComponentType.CABINET,
            'equipment': BIMComponentType.EQUIPMENT,
            'distribution_box': BIMComponentType.DISTRIBUTION_BOX,
            'switch': BIMComponentType.FIXTURE,
            'socket': BIMComponentType.FIXTURE,
            'lighting': BIMComponentType.FIXTURE,
            'other': BIMComponentType.OTHER,
        }
        return mapping.get(device_type, BIMComponentType.OTHER)

    @staticmethod
    def _infer_type_from_name(name: str, category: str) -> str:
        n = str(name).lower()
        cat = str(category).lower()
        if '配电柜' in name or '开关柜' in name or 'cabinet' in n or '配电柜' in cat:
            return 'cabinet'
        if '配电箱' in name or '配电盘' in name or 'panel' in n or '配电箱' in cat:
            return 'distribution_box'
        if '电机' in name or '马达' in name or 'motor' in n or 'equipment' in cat:
            return 'equipment'
        if '开关' in name or 'switch' in n or '开关' in cat:
            return 'switch'
        if '插座' in name or 'socket' in n or '插座' in cat:
            return 'socket'
        if '灯' in name or '照明' in name or 'light' in n or 'lighting' in cat:
            return 'lighting'
        return 'equipment'

    # ============ 输出属性 ============

    @property
    def components(self) -> List[BIMComponent]:
        return self._components

    @property
    def geometries(self) -> Dict[str, Geometry3D]:
        return self._geometries

    def get_summary(self) -> Dict[str, Any]:
        """返回模型统计信息"""
        by_type: Dict[str, int] = {}
        for comp in self._components:
            t = comp.type.value if hasattr(comp.type, 'value') else str(comp.type)
            by_type[t] = by_type.get(t, 0) + 1
        return {
            'total_components': len(self._components),
            'by_type': by_type,
        }
