
import os
import json
import base64
import subprocess
import tempfile
import datetime
import xml.etree.ElementTree as ET
from typing import Union, Dict, Any, Optional
from pathlib import Path
import json5
from PIL import Image, ImageDraw, ImageFont
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

    def generate_plantuml_image(self, plantuml_code: str, output_filename: str = None, java_path: str = None) -> str:
        """
        使用 plantuml.jar 生成图像文件

        Args:
            plantuml_code: PlantUML 代码字符串
            output_filename: 输出文件名（可选，默认自动生成）
            java_path: Java 可执行文件路径（可选，默认使用系统 PATH 中的 java）

        Returns:
            生成的图像文件路径

        Raises:
            Exception: 当 PlantUML 生成失败时抛出异常
        """
        try:
            # 确保输出目录存在
            output_dir = Path("jpg_output")
            output_dir.mkdir(exist_ok=True)

            # 生成输出文件名
            if output_filename is None:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"plantuml_{timestamp}.jpg"

            # 确保文件名以 .jpg 结尾
            if not output_filename.lower().endswith('.jpg'):
                output_filename += '.jpg'

            output_path = output_dir / output_filename

            # 创建临时 PlantUML 文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.puml', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(plantuml_code)
                temp_puml_path = temp_file.name

            try:
                # 检查 plantuml.jar 是否存在
                plantuml_jar_path = Path("plantuml.jar")
                if not plantuml_jar_path.exists():
                    raise FileNotFoundError("plantuml.jar 文件不存在，请确保文件在当前目录下")

                # 确定 Java 可执行文件路径
                if java_path:
                    java_executable = java_path
                else:
                    # 尝试常见的 Java 路径
                    possible_java_paths = [
                        "java",  # 系统 PATH 中的 java
                        "jdk-25.0.1/bin/java",  # 用户提到的路径
                        "jdk-25.0.1/bin/java.exe",  # Windows 版本
                        os.path.expanduser("~/jdk-25.0.1/bin/java"),  # 用户目录下
                        os.path.expanduser("~/jdk-25.0.1/bin/java.exe"),  # Windows 用户目录
                    ]

                    java_executable = None
                    for java_cmd in possible_java_paths:
                        try:
                            # 测试 Java 命令是否可用
                            result = subprocess.run([java_cmd, "-version"],
                                                    capture_output=True,
                                                    timeout=5)
                            if result.returncode == 0:
                                java_executable = java_cmd
                                break
                        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                            continue

                    if not java_executable:
                        raise FileNotFoundError("Java 未找到。请安装 Java 或使用 java_path 参数指定 Java 路径")

                # 构建 Java 命令
                # 注意：PlantUML 默认生成 PNG，我们需要转换为 JPG
                cmd = [
                    java_executable, "-jar", str(plantuml_jar_path),
                    "-tpng",  # 先生成 PNG，然后转换为 JPG
                    "-o", str(output_dir.absolute()),
                    temp_puml_path
                ]

                # 执行 PlantUML 命令
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30  # 30秒超时
                )

                if result.returncode != 0:
                    error_msg = f"PlantUML 执行失败 (返回码: {result.returncode})"
                    if result.stderr:
                        error_msg += f"\n错误信息: {result.stderr}"
                    if result.stdout:
                        error_msg += f"\n输出信息: {result.stdout}"
                    raise Exception(error_msg)

                # PlantUML 默认会根据输入文件名生成输出文件
                # 例如：temp_xxx.puml -> temp_xxx.png
                temp_name = Path(temp_puml_path).stem
                generated_png_file = output_dir / f"{temp_name}.png"

                # 检查生成的 PNG 文件是否存在
                if not generated_png_file.exists():
                    raise Exception(f"PlantUML 图像生成失败：未找到输出文件 {generated_png_file}")

                # 将 PNG 转换为 JPG
                from PIL import Image
                with Image.open(generated_png_file) as img:
                    # 转换为 RGB 模式（JPG 不支持透明度）
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # 创建白色背景
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')

                    # 保存为 JPG
                    img.save(output_path, 'JPEG', quality=90)

                # 删除临时 PNG 文件
                if generated_png_file.exists():
                    generated_png_file.unlink()

                return str(output_path.absolute())

            finally:
                # 清理临时文件
                if os.path.exists(temp_puml_path):
                    os.unlink(temp_puml_path)

        except subprocess.TimeoutExpired:
            raise Exception("PlantUML 执行超时（超过30秒）")
        except FileNotFoundError as e:
            if "java" in str(e).lower():
                raise Exception("Java 未找到。请安装 Java 或使用 java_path 参数指定 Java 路径")
            else:
                raise Exception(f"文件未找到: {str(e)}")
        except Exception as e:
            raise Exception(f"生成 PlantUML 图像失败: {str(e)}")


    
    def analyze_uml_errors(self, image_path: str) -> Dict[str, Any]:
        """
        分析UML图像中的错误
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            包含错误分析结果的字典，格式如下：
            {
                "errors": [
                    {
                        "region": {
                            "description": "错误位置描述",
                            "coordinates": {"x1": float, "y1": float, "x2": float, "y2": float}
                        },
                        "type": "错误类型",
                        "element": "涉及的UML元素",
                        "error_description": "详细错误说明",
                        "suggestion": "修复建议"
                    }
                ],
                "summary": {
                    "total_errors": int,
                    "severity_level": "严重程度"
                },
                "raw_xml_response": "原始XML响应"
            }
        """
        try:
            # 验证图片文件
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            # 图像预处理（复用现有逻辑）
            with Image.open(image_path) as img:
                # 转换为RGB格式（如果需要）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 如果图片太大，调整大小以节省API调用成本
                max_size = (1024, 1024)
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 保存处理后的图片到临时文件
                temp_path = "temp_error_analysis_image.jpg"
                img.save(temp_path, "JPEG", quality=85)
            
            # 将图片转换为base64
            with open(temp_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # 构建纠错提示词
            error_analysis_prompt = """分析提供的UML图像，识别图中的错误，并以XML格式输出结果。XML结构应如下：

<uml_analysis>
  <errors>
    <error>
      <region>
        <description>错误位置的文字描述</description>
        <coordinates>
          <x1>左上角x坐标</x1>
          <y1>左上角y坐标</y1>
          <x2>右下角x坐标</x2>
          <y2>右下角y坐标</y2>
        </coordinates>
      </region>
      <type>错误类型</type>
      <element>涉及的UML元素</element>
      <error_description>详细的错误说明</error_description>
      <suggestion>修复建议</suggestion>
    </error>
    <!-- 更多error元素 -->
  </errors>
  <summary>
    <total_errors>错误总数</total_errors>
    <severity_level>整体严重程度</severity_level>
  </summary>
</uml_analysis>

要求：
1. 对于每个错误，提供以下信息：
   - region: 包含位置描述和坐标列表
     * description: 描述错误在图像中的位置（如"类User与类Account之间的关联线"）
     * coordinates: 包含四个坐标值(x1,y1,x2,y2)，表示错误区域的边界框
       - x1,y1: 边界框左上角坐标
       - x2,y2: 边界框右下角坐标
       - 坐标值范围应为0-100，表示相对于图像尺寸的百分比位置
   - type: 错误类型（如"语法错误"、"语义错误"、"一致性错误"、"设计规范违反"等）
   - element: 涉及的UML元素（如"类"、"关联"、"继承"、"依赖"、"属性"、"操作"等）
   - error_description: 详细的错误说明
   - suggestion: 具体的修复建议

2. 如果没有发现错误，输出：
<uml_analysis>
  <errors>
    <!-- 无错误 -->
  </errors>
  <summary>
    <total_errors>0</total_errors>
    <severity_level>无错误</severity_level>
  </summary>
</uml_analysis>

3. 确保XML格式良好，便于程序解析。"""
            
            # 调用GPT-4o进行错误分析
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": error_analysis_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请分析这个UML图并识别其中的错误。"
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
            
            # 获取响应内容
            content = response.choices[0].message.content
            
            # 解析XML响应
            parsed_result = self._parse_error_analysis_xml(content)
            parsed_result["raw_xml_response"] = content
            
            return parsed_result
            
        except Exception as e:
            raise Exception(f"UML错误分析失败: {str(e)}")
    
    def _parse_error_analysis_xml(self, xml_content: str) -> Dict[str, Any]:
        """
        解析错误分析的XML响应
        
        Args:
            xml_content: XML格式的响应内容
            
        Returns:
            解析后的Python字典
        """
        try:
            # 提取XML部分
            xml_text = xml_content
            if "```xml" in xml_content:
                xml_start = xml_content.find("```xml") + 6
                xml_end = xml_content.find("```", xml_start)
                xml_text = xml_content[xml_start:xml_end].strip()
            elif "```" in xml_content:
                xml_start = xml_content.find("```") + 3
                xml_end = xml_content.find("```", xml_start)
                xml_text = xml_content[xml_start:xml_end].strip()
            elif "<uml_analysis>" in xml_content:
                # 直接提取XML部分
                xml_start = xml_content.find("<uml_analysis>")
                xml_end = xml_content.find("</uml_analysis>") + len("</uml_analysis>")
                xml_text = xml_content[xml_start:xml_end]
            
            # 解析XML
            root = ET.fromstring(xml_text)
            
            # 提取错误信息
            errors = []
            errors_element = root.find("errors")
            if errors_element is not None:
                for error_elem in errors_element.findall("error"):
                    error_data = {}
                    
                    # 提取region信息
                    region_elem = error_elem.find("region")
                    if region_elem is not None:
                        region_data = {}
                        
                        desc_elem = region_elem.find("description")
                        if desc_elem is not None:
                            region_data["description"] = desc_elem.text or ""
                        
                        coords_elem = region_elem.find("coordinates")
                        if coords_elem is not None:
                            coordinates = {}
                            for coord in ["x1", "y1", "x2", "y2"]:
                                coord_elem = coords_elem.find(coord)
                                if coord_elem is not None:
                                    try:
                                        coordinates[coord] = float(coord_elem.text or 0)
                                    except ValueError:
                                        coordinates[coord] = 0.0
                            region_data["coordinates"] = coordinates
                        
                        error_data["region"] = region_data
                    
                    # 提取其他字段
                    for field in ["type", "element", "error_description", "suggestion"]:
                        field_elem = error_elem.find(field)
                        if field_elem is not None:
                            error_data[field] = field_elem.text or ""
                    
                    errors.append(error_data)
            
            # 提取摘要信息
            summary = {}
            summary_elem = root.find("summary")
            if summary_elem is not None:
                total_errors_elem = summary_elem.find("total_errors")
                if total_errors_elem is not None:
                    try:
                        summary["total_errors"] = int(total_errors_elem.text or 0)
                    except ValueError:
                        summary["total_errors"] = len(errors)
                
                severity_elem = summary_elem.find("severity_level")
                if severity_elem is not None:
                    summary["severity_level"] = severity_elem.text or "未知"
            
            return {
                "errors": errors,
                "summary": summary
            }
            
        except ET.ParseError as e:
            # XML解析失败，返回基本结构
            return {
                "errors": [],
                "summary": {
                    "total_errors": 0,
                    "severity_level": "解析失败"
                },
                "parse_error": f"XML解析失败: {str(e)}",
                "raw_content": xml_content
            }
        except Exception as e:
            # 其他解析错误
            return {
                "errors": [],
                "summary": {
                    "total_errors": 0,
                    "severity_level": "解析失败"
                },
                "parse_error": f"解析错误: {str(e)}",
                "raw_content": xml_content
            }
    
    def annotate_image_with_errors(self, image_path: str, error_analysis: Dict[str, Any], output_path: str = None) -> str:
        """
        根据错误分析结果标注图像中的错误区域
        
        Args:
            image_path: 原始图像文件路径
            error_analysis: 错误分析结果字典
            output_path: 输出标注图像的路径（可选，默认自动生成）
            
        Returns:
            标注后的图像文件路径
        """
        try:
            # 验证输入文件
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            # 打开原始图像
            with Image.open(image_path) as img:
                # 转换为RGB模式以确保兼容性
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 创建绘图对象
                draw = ImageDraw.Draw(img)
                
                # 获取图像尺寸
                img_width, img_height = img.size
                
                # 定义错误类型对应的颜色
                error_colors = {
                    "语法错误": "#FF0000",      # 红色
                    "语义错误": "#FF8C00",      # 橙色
                    "一致性错误": "#FFD700",    # 金色
                    "设计规范违反": "#FF1493",  # 深粉色
                    "其他": "#8A2BE2"          # 蓝紫色
                }
                
                # 尝试加载字体（优先支持中文字体）
                font = None
                font_paths = [
                    # Windows中文字体（优先）
                    "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
                    "C:/Windows/Fonts/simsun.ttc",    # 宋体
                    "C:/Windows/Fonts/simhei.ttf",    # 黑体
                    "C:/Windows/Fonts/simkai.ttf",    # 楷体
                    "C:/Windows/Fonts/simfang.ttf",   # 仿宋
                    # Linux中文字体
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    "/System/Library/Fonts/PingFang.ttc",  # macOS中文字体
                    # Windows英文字体（备选）
                    "C:/Windows/Fonts/arial.ttf",
                    "C:/Windows/Fonts/calibri.ttf",
                    # 相对路径尝试
                    "arial.ttf",
                    "msyh.ttc",
                    "simsun.ttc"
                ]
                
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, 16)
                        print(f"✅ 成功加载字体: {font_path}")
                        break
                    except (OSError, IOError):
                        continue
                
                # 如果所有字体都加载失败，使用默认字体
                if font is None:
                    try:
                        # 尝试加载默认字体，指定更大的尺寸
                        font = ImageFont.load_default()
                        print("⚠️  使用默认字体（可能不支持中文）")
                    except:
                        # 最后的备选方案
                        font = ImageFont.load_default()
                        print("⚠️  使用系统默认字体")
                
                # 标注每个错误区域
                errors = error_analysis.get("errors", [])
                for i, error in enumerate(errors, 1):
                    region = error.get("region", {})
                    coordinates = region.get("coordinates", {})
                    
                    # 获取坐标（百分比转换为像素）
                    x1 = int(coordinates.get("x1", 0) * img_width / 100)
                    y1 = int(coordinates.get("y1", 0) * img_height / 100)
                    x2 = int(coordinates.get("x2", 0) * img_width / 100)
                    y2 = int(coordinates.get("y2", 0) * img_height / 100)
                    
                    # 确保坐标有效
                    x1, x2 = min(x1, x2), max(x1, x2)
                    y1, y2 = min(y1, y2), max(y1, y2)
                    
                    # 如果坐标为0，跳过该错误
                    if x1 == x2 and y1 == y2:
                        continue
                    
                    # 获取错误类型对应的颜色
                    error_type = error.get("type", "其他")
                    color = error_colors.get(error_type, error_colors["其他"])
                    
                    # 绘制错误区域边框
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                    
                    # 绘制错误编号和类型
                    label = f"{i}. {error_type}"
                    
                    # 计算标签位置
                    label_x = x1
                    label_y = max(0, y1 - 30)
                    
                    # 绘制标签背景和文字
                    try:
                        bbox = draw.textbbox((label_x, label_y), label, font=font)
                        # 扩展背景框以提供更好的可读性
                        padding = 2
                        bg_bbox = [bbox[0] - padding, bbox[1] - padding,
                                  bbox[2] + padding, bbox[3] + padding]
                        draw.rectangle(bg_bbox, fill=color)
                        draw.text((label_x, label_y), label, fill="white", font=font)
                    except:
                        # 如果textbbox不可用，使用简单的文本绘制
                        draw.text((label_x, label_y), label, fill=color, font=font)
                
                # 生成输出文件路径
                if output_path is None:
                    input_path = Path(image_path)
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = input_path.parent / f"{input_path.stem}_annotated_{timestamp}.jpg"
                
                # 确保输出目录存在
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 保存标注后的图像
                img.save(output_path, "JPEG", quality=90)
                
                return str(output_path.absolute())
                
        except Exception as e:
            raise Exception(f"图像标注失败: {str(e)}")
    
    def generate_corrected_uml(self, image_path: str) -> Dict[str, Any]:
        """
        根据错误分析结果生成修正后的UML代码
        
        Args:
            image_path: 原始图像文件路径
            
        Returns:
            包含原始UML代码、错误分析和修正后UML代码的字典
        """
        try:
            # 首先进行错误分析
            error_analysis = self.analyze_uml_errors(image_path)
            
            # 然后解析原始图像获取UML结构
            original_uml_data = self.parse_image_to_uml(image_path)
            original_plantuml_code = self.generate_plantuml_code(original_uml_data)
            
            # 构建修正提示词
            correction_prompt = f"""你是一个专业的UML设计专家。我将提供：
1. 原始的PlantUML代码
2. 错误分析结果

请根据错误分析结果，生成修正后的PlantUML代码。

原始PlantUML代码：
```plantuml
{original_plantuml_code}
```

错误分析结果：
{json.dumps(error_analysis, ensure_ascii=False, indent=2)}

请提供修正后的PlantUML代码，确保：
1. 修复所有识别出的错误
2. 保持UML图的完整性和可读性
3. 遵循UML设计最佳实践
4. 在代码中添加注释说明修改的地方

请以以下格式返回：
```plantuml
修正后的PlantUML代码
```

修改说明：
- 修改1：具体说明
- 修改2：具体说明
..."""
            
            # 调用GPT-4o生成修正后的代码
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的UML设计专家，擅长分析和修正UML图中的错误。"
                    },
                    {
                        "role": "user",
                        "content": correction_prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            # 解析响应
            content = response.choices[0].message.content
            
            # 提取修正后的PlantUML代码
            corrected_code = ""
            modification_notes = ""
            
            if "```plantuml" in content:
                # 提取PlantUML代码块
                code_start = content.find("```plantuml") + 11
                code_end = content.find("```", code_start)
                corrected_code = content[code_start:code_end].strip()
                
                # 提取修改说明
                notes_start = content.find("修改说明：")
                if notes_start != -1:
                    modification_notes = content[notes_start:].strip()
            else:
                # 如果没有找到代码块，使用整个响应
                corrected_code = content
                modification_notes = "未找到明确的修改说明"
            
            # 生成时间戳
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            return {
                "timestamp": timestamp,
                "original_image_path": image_path,
                "original_uml": original_uml_data,
                "original_plantuml": original_plantuml_code,
                "error_analysis": error_analysis,
                "corrected_plantuml": corrected_code,
                "modification_notes": modification_notes,
                "raw_gpt_response": content,
                "summary": {
                    "total_errors_found": error_analysis.get("summary", {}).get("total_errors", 0),
                    "severity_level": error_analysis.get("summary", {}).get("severity_level", "未知"),
                    "corrections_applied": len([line for line in modification_notes.split('\n') if line.strip().startswith('- 修改')])
                }
            }
            
        except Exception as e:
            raise Exception(f"生成修正UML代码失败: {str(e)}")


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
