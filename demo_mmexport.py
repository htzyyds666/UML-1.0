#!/usr/bin/env python3
"""
专门演示使用mmexport1761537933264.jpg的UML纠错功能
"""

import os
from main import UMLParser

def demo_uml_error_correction():
    """演示UML错误分析、图像标注和代码纠错功能"""
    
    # 指定测试图片
    test_image = "mmexport1761537933264.jpg"
    
    if not os.path.exists(test_image):
        print(f"❌ 测试图片不存在: {test_image}")
        return
    
    print("🚀 UML纠错功能演示")
    print("=" * 50)
    print(f"📷 使用测试图片: {test_image}")
    
    # 检查API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 请设置OPENAI_API_KEY环境变量")
        return
    
    try:
        # 初始化解析器
        parser = UMLParser()
        
        # 1. 错误分析
        print("\n🔍 步骤1: 分析UML错误...")
        error_analysis = parser.analyze_uml_errors(test_image)
        
        print(f"✅ 错误分析完成!")
        print(f"   发现错误数量: {error_analysis['summary']['total_errors']}")
        print(f"   严重程度: {error_analysis['summary']['severity_level']}")
        
        # 显示错误详情
        errors = error_analysis.get("errors", [])
        for i, error in enumerate(errors, 1):
            print(f"\n   错误 {i}: {error.get('type', '未知')}")
            print(f"   元素: {error.get('element', '未知')}")
            print(f"   位置: {error.get('region', {}).get('description', '未知')}")
            coords = error.get('region', {}).get('coordinates', {})
            if coords:
                print(f"   坐标: ({coords.get('x1', 0):.1f}, {coords.get('y1', 0):.1f}) - ({coords.get('x2', 0):.1f}, {coords.get('y2', 0):.1f})")
            print(f"   描述: {error.get('error_description', '无描述')[:100]}...")
        
        # 2. 图像标注
        print("\n🎨 步骤2: 标注错误区域...")
        annotated_path = parser.annotate_image_with_errors(test_image, error_analysis)
        
        print(f"✅ 图像标注完成!")
        print(f"   标注图片保存至: {annotated_path}")
        print(f"   标注包含错误类型文字标签")
        
        # 3. 生成修正后的UML代码
        print("\n🔧 步骤3: 生成修正后的UML代码...")
        correction_result = parser.generate_corrected_uml(test_image)
        
        print(f"✅ UML代码纠错完成!")
        print(f"   原始UML元素数: {len(correction_result.get('original_uml', {}).get('uml_structure', {}).get('elements', []))}")
        print(f"   发现错误数: {len(correction_result.get('error_analysis', {}).get('errors', []))}")
        
        # 显示修正后的代码预览
        corrected_code = correction_result.get('corrected_plantuml', '')
        if corrected_code:
            print(f"   修正后PlantUML代码长度: {len(corrected_code)} 字符")
            print("\n   修正后代码预览:")
            lines = corrected_code.split('\n')[:15]  # 显示前15行
            for line in lines:
                print(f"     {line}")
            if len(corrected_code.split('\n')) > 15:
                print("     ...")
        
        # 保存结果
        import json
        result_file = "mmexport_correction_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(correction_result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 完整纠错结果已保存到: {result_file}")
        
        print("\n🎉 演示完成!")
        print(f"📁 生成的文件:")
        print(f"   - 标注图片: {annotated_path}")
        print(f"   - 纠错结果: {result_file}")
        
    except Exception as e:
        print(f"❌ 演示失败: {str(e)}")

if __name__ == "__main__":
    demo_uml_error_correction()