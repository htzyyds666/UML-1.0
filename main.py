
import os
import json
import base64
from typing import Union, Dict, Any, Optional
from pathlib import Path
import json5
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class UMLParser:
    """UML解析器，支持StarUML文件和图片解析"""
    
    def __init__(self, openai_api_key: str = None, openai_base_url: str = None):
        """
        初始化UML解析器
        
        Args:
            openai_api_key: OpenAI API密钥，如果不提供则从环境变量OPENAI_API_KEY获取
            openai_base_url: OpenAI API基础URL，如果不提供则从环境变量OPENAI_BASE_URL获取
        """
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = openai_base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if not self.api_key:
            raise ValueError("OpenAI API密钥未设置。请设置OPENAI_API_KEY环境变量或传入api_key参数")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def parse_staruml_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析StarUML文件(.mdj格式)
        
        Args:
            file_path: StarUML文件路径
            
        Returns:
            解析后的UML结构字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # StarUML文件是JSON格式
                staruml_data = json.load(f)
            
            # 提取UML元素
            uml_structure = self._extract_uml_elements(staruml_data)
            return {
                "source_type": "staruml",
                "file_path": file_path,
                "uml_structure": uml_structure,
                "raw_data": staruml_data
            }
        except Exception as e:
            raise Exception(f"解析StarUML文件失败: {str(e)}")
    
    def parse_image_to_uml(self, image_path: str) -> Dict[str, Any]:
        """
        使用GPT-4o解析图片中的UML图
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            解析后的UML结构字典
        """
        try:
            # 验证图片文件
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            # 打开并验证图片
            with Image.open(image_path) as img:
                # 转换为RGB格式（如果需要）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 如果图片太大，调整大小以节省API调用成本
                max_size = (1024, 1024)
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 保存处理后的图片到临时文件
                temp_path = "temp_processed_image.jpg"
                img.save(temp_path, "JPEG", quality=85)
            
            # 将图片转换为base64
            with open(temp_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # 调用GPT-4o进行图片分析
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """你是一个专业的UML图分析专家。请分析图片中的UML图，并提取以下信息：
1. UML图的类型（类图、时序图、用例图等）
2. 所有的类、接口、枚举等元素
3. 类的属性和方法
4. 类之间的关系（继承、实现、关联、依赖等）
5. 关系的多重性和标签

请以JSON格式返回结果，包含以下结构：
{
    "diagram_type": "类图/时序图/用例图等",
    "elements": [
        {
            "type": "class/interface/enum",
            "name": "元素名称",
            "attributes": ["属性列表"],
            "methods": ["方法列表"],
            "stereotypes": ["构造型列表"]
        }
    ],
    "relationships": [
        {
            "type": "inheritance/implementation/association/dependency",
            "source": "源元素名称",
            "target": "目标元素名称",
            "multiplicity": "多重性",
            "label": "关系标签"
        }
    ],
    "notes": ["图中的注释或说明"]
}"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请分析这个UML图并提取其结构信息。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            # 解析GPT-4o的响应
            content = response.choices[0].message.content
            
            # 尝试提取JSON部分
            try:
                # 查找JSON代码块
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                else:
                    json_content = content.strip()
                
                uml_structure = json.loads(json_content)
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试使用json5
                try:
                    uml_structure = json5.loads(json_content)
                except:
                    # 如果仍然失败，返回原始文本
                    uml_structure = {
                        "diagram_type": "unknown",
                        "raw_analysis": content,
                        "elements": [],
                        "relationships": [],
                        "notes": ["GPT-4o分析结果解析失败，请查看raw_analysis字段"]
                    }
            
            return {
                "source_type": "image",
                "file_path": image_path,
                "uml_structure": uml_structure,
                "raw_gpt_response": content
            }
            
        except Exception as e:
            raise Exception(f"解析图片UML失败: {str(e)}")
    
    def _extract_uml_elements(self, staruml_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从StarUML数据中提取UML元素
        
        Args:
            staruml_data: StarUML原始数据
            
        Returns:
            提取的UML结构
        """
        elements = []
        relationships = []
        
        def traverse_elements(obj, parent_name=""):
            if isinstance(obj, dict):
                # 检查是否是UML元素
                if obj.get("_type") in ["UMLClass", "UMLInterface", "UMLEnumeration"]:
                    element = {
                        "type": obj.get("_type", "").replace("UML", "").lower(),
                        "name": obj.get("name", "Unknown"),
                        "attributes": [],
                        "methods": [],
                        "stereotypes": []
                    }
                    
                    # 提取属性
                    if "attributes" in obj:
                        for attr in obj["attributes"]:
                            if isinstance(attr, dict) and attr.get("name"):
                                attr_str = f"{attr.get('visibility', '')} {attr.get('name', '')}"
                                if attr.get("type"):
                                    attr_str += f": {attr.get('type')}"
                                element["attributes"].append(attr_str.strip())
                    
                    # 提取方法
                    if "operations" in obj:
                        for op in obj["operations"]:
                            if isinstance(op, dict) and op.get("name"):
                                method_str = f"{op.get('visibility', '')} {op.get('name', '')}()"
                                if op.get("returnType"):
                                    method_str = method_str[:-2] + f": {op.get('returnType')}"
                                element["methods"].append(method_str.strip())
                    
                    elements.append(element)
                
                # 检查关系
                elif obj.get("_type") in ["UMLGeneralization", "UMLAssociation", "UMLDependency", "UMLRealization"]:
                    relationship = {
                        "type": obj.get("_type", "").replace("UML", "").lower(),
                        "source": obj.get("source", {}).get("name", "Unknown"),
                        "target": obj.get("target", {}).get("name", "Unknown"),
                        "multiplicity": obj.get("multiplicity", ""),
                        "label": obj.get("name", "")
                    }
                    relationships.append(relationship)
                
                # 递归遍历子元素
                for key, value in obj.items():
                    if key not in ["_type", "_id", "_parent"]:
                        traverse_elements(value, obj.get("name", parent_name))
            
            elif isinstance(obj, list):
                for item in obj:
                    traverse_elements(item, parent_name)
        
        traverse_elements(staruml_data)
        
        return {
            "diagram_type": "class_diagram",  # StarUML通常是类图
            "elements": elements,
            "relationships": relationships,
            "notes": []
        }
    
    def generate_plantuml_code(self, uml_data: Dict[str, Any]) -> str:
        """
        根据解析的UML数据生成PlantUML代码
        
        Args:
            uml_data: 解析后的UML数据
            
        Returns:
            PlantUML代码字符串
        """
        uml_structure = uml_data.get("uml_structure", {})
        diagram_type = uml_structure.get("diagram_type", "class_diagram")
        
        plantuml_code = ["@startuml"]
        
        # 添加标题
        plantuml_code.append(f"title {diagram_type.replace('_', ' ').title()}")
        plantuml_code.append("")
        
        # 生成元素定义
        for element in uml_structure.get("elements", []):
            element_type = element.get("type", "class")
            element_name = element.get("name", "Unknown")
            
            if element_type == "class":
                plantuml_code.append(f"class {element_name} {{")
            elif element_type == "interface":
                plantuml_code.append(f"interface {element_name} {{")
            elif element_type == "enum" or element_type == "enumeration":
                plantuml_code.append(f"enum {element_name} {{")
            else:
                plantuml_code.append(f"class {element_name} {{")
            
            # 添加属性
            for attr in element.get("attributes", []):
                plantuml_code.append(f"  {attr}")
            
            if element.get("attributes") and element.get("methods"):
                plantuml_code.append("  --")
            
            # 添加方法
            for method in element.get("methods", []):
                plantuml_code.append(f"  {method}")
            
            plantuml_code.append("}")
            plantuml_code.append("")
        
        # 生成关系
        for rel in uml_structure.get("relationships", []):
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "association")
            label = rel.get("label", "")
            multiplicity = rel.get("multiplicity", "")
            
            if rel_type == "inheritance" or rel_type == "generalization":
                arrow = "--|>"
            elif rel_type == "implementation" or rel_type == "realization":
                arrow = "..|>"
            elif rel_type == "association":
                arrow = "-->"
            elif rel_type == "dependency":
                arrow = "..>"
            else:
                arrow = "-->"
            
            rel_line = f"{source} {arrow} {target}"
            if label:
                rel_line += f" : {label}"
            if multiplicity:
                rel_line += f" [{multiplicity}]"
            
            plantuml_code.append(rel_line)
        
        # 添加注释
        for note in uml_structure.get("notes", []):
            plantuml_code.append(f"note top : {note}")
        
        plantuml_code.append("@enduml")
        
        return "\n".join(plantuml_code)


def parse_uml_file(file_path: str, openai_api_key: str = None, openai_base_url: str = None) -> Dict[str, Any]:
    """
    解析UML文件（StarUML或图片）的便捷函数
    
    Args:
        file_path: 文件路径
        openai_api_key: OpenAI API密钥
        openai_base_url: OpenAI API基础URL
        
    Returns:
        包含解析结果和PlantUML代码的字典
    """
    parser = UMLParser(openai_api_key, openai_base_url)
    
    file_ext = Path(file_path).suffix.lower()
    
    # 根据文件扩展名选择解析方法
    if file_ext == '.mdj':
        # StarUML文件
        uml_data = parser.parse_staruml_file(file_path)
    elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']:
        # 图片文件
        uml_data = parser.parse_image_to_uml(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}。支持的格式: .mdj (StarUML), .png, .jpg, .jpeg, .bmp, .gif, .tiff")
    
    # 生成PlantUML代码
    plantuml_code = parser.generate_plantuml_code(uml_data)
    
    return {
        "uml_data": uml_data,
        "plantuml_code": plantuml_code,
        "file_info": {
            "path": file_path,
            "extension": file_ext,
            "source_type": uml_data.get("source_type", "unknown")
        }
    }


def main():
    """主函数示例"""
    print("UML解析器已就绪!")
    print("支持的功能:")
    print("1. 解析StarUML文件 (.mdj)")
    print("2. 解析UML图片 (.png, .jpg, .jpeg, .bmp, .gif, .tiff)")
    print("3. 生成PlantUML代码")
    print("\n使用方法:")
    print("from main import parse_uml_file")
    print("result = parse_uml_file('your_file.mdj')")
    print("print(result['plantuml_code'])")


if __name__ == "__main__":
    main()
