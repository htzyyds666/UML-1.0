# UML纠错功能实现计划

## 功能概述
为 `main.py` 中的 `UMLParser` 类添加一个 `analyze_uml_errors` 方法，该方法接收UML图像输入，使用OpenAI GPT-4o分析图像中的错误，并返回结构化的错误信息。

## 技术要求

### 输入
- 图像文件路径（支持常见图像格式：png, jpg, jpeg, bmp, gif, tiff）

### 输出
- Python字典结构，包含：
  - `errors`: 错误列表，每个错误包含：
    - `region`: 错误位置信息
      - `description`: 位置描述
      - `coordinates`: 坐标信息 (x1, y1, x2, y2)
    - `type`: 错误类型
    - `element`: 涉及的UML元素
    - `error_description`: 详细错误说明
    - `suggestion`: 修复建议
  - `summary`: 摘要信息
    - `total_errors`: 错误总数
    - `severity_level`: 整体严重程度
  - `raw_xml_response`: 原始XML响应（用于调试）

### 实现步骤

1. **添加依赖导入**
   - `xml.etree.ElementTree` 用于XML解析

2. **实现 `analyze_uml_errors` 方法**
   - 图像预处理（复用现有的图像处理逻辑）
   - 构建专门的纠错提示词
   - 调用OpenAI API
   - 解析XML响应
   - 转换为Python字典结构

3. **错误处理**
   - 图像文件不存在
   - OpenAI API调用失败
   - XML解析失败
   - 网络连接问题

4. **测试代码**
   - 在 `test_uml_parser.py` 中添加 `test_uml_error_analysis` 函数
   - 测试正常情况和异常情况
   - 创建或使用现有的测试图像

## 提示词设计
使用 `纠错提示词.md` 中提供的完整提示词，要求AI返回XML格式的分析结果。

## 预期的方法签名
```python
def analyze_uml_errors(self, image_path: str) -> Dict[str, Any]:
    """
    分析UML图像中的错误
    
    Args:
        image_path: 图像文件路径
        
    Returns:
        包含错误分析结果的字典
    """
```

## 集成考虑
- 复用现有的图像处理逻辑（`parse_image_to_uml` 方法中的图像预处理部分）
- 保持与现有代码风格的一致性
- 确保错误处理的健壮性