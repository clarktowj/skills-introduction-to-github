import os
from typing import List
from common.models import BIMComponent, BIMComponentType
from framework.exceptions import ModelingError

class IFCExporter:
    def __init__(self):
        pass
    
    def export(self, components: List[BIMComponent], output_path: str) -> str:
        try:
            ifc_content = self._generate_ifc_content(components)
            
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ifc_content)
            
            return output_path
        
        except Exception as e:
            raise ModelingError(f"Failed to export IFC file: {str(e)}")
    
    def _generate_ifc_content(self, components: List[BIMComponent]) -> str:
        header = self._generate_header()
        entities = self._generate_entities(components)
        footer = self._generate_footer()
        
        return f"{header}\n{entities}\n{footer}"
    
    def _generate_header(self) -> str:
        return """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('Exported from MechElecAI','2024-01-01',('MechElecAI'),(''),'MechElecAI IFC Exporter','','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;"""
    
    def _generate_entities(self, components: List[BIMComponent]) -> str:
        entities = []
        entity_id = 100
        
        entities.append(f"#1=IFCPROJECT('2X2u2$t4X7Z8NOew3FNldB',#2,'MechElecAI Project','','',#3,#4,$,$);")
        entities.append(f"#2=IFCOWNERHISTORY(#5,#6,$,.NOCHANGE.,$,#6,$,$);")
        entities.append(f"#3=IFCDATEANDTIME('2024-01-01','00:00:00');")
        entities.append(f"#4=IFCSIUNIT(*,.METRE.,$,.M.);")
        entities.append(f"#5=IFCPERSON('','','MechElecAI',$,$,$,$,$);")
        entities.append(f"#6=IFCORGANIZATION('MechElecAI','','','');")
        
        entity_id = 100
        for component in components:
            entity_lines = self._generate_component_entity(component, entity_id)
            entities.extend(entity_lines)
            entity_id += 10
        
        return '\n'.join(entities)
    
    def _generate_component_entity(self, component: BIMComponent, base_id: int) -> List[str]:
        lines = []
        
        ifc_type = self._map_bim_type_to_ifc(component.type)
        
        lines.append(f"#{base_id}=IFCBUILDINGELEMENTPROXY('{component.id}',#2,'{component.name}','',#{base_id+1},#{base_id+2},#{base_id+3});")
        lines.append(f"#{base_id+1}=IFCLOCALPLACEMENT($,#{base_id+2});")
        lines.append(f"#{base_id+2}=IFCAXIS2PLACEMENT3D(#{base_id+3},#{base_id+4},#{base_id+5});")
        lines.append(f"#{base_id+3}=IFCCARTESIANPOINT({component.position.x},{component.position.y},{component.position.z});")
        lines.append(f"#{base_id+4}=IFCDIRECTION(0.,0.,1.);")
        lines.append(f"#{base_id+5}=IFCDIRECTION(1.,0.,0.);")
        
        return lines
    
    def _map_bim_type_to_ifc(self, bim_type: BIMComponentType) -> str:
        mapping = {
            BIMComponentType.CABINET: 'ElectricalDistributionBoard',
            BIMComponentType.EQUIPMENT: 'Equipment',
            BIMComponentType.DISTRIBUTION_BOX: 'ElectricalPanel',
            BIMComponentType.CABLE: 'CableCarrier',
            BIMComponentType.CABLE_TRAY: 'CableTray',
            BIMComponentType.PIPE: 'PipeSegment',
            BIMComponentType.FIXTURE: 'Fixture',
            BIMComponentType.OTHER: 'BuildingElementProxy'
        }
        return mapping.get(bim_type, 'BuildingElementProxy')
    
    def _generate_footer(self) -> str:
        return """ENDSEC;
END-ISO-10303-21;"""