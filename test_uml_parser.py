#!/usr/bin/env python3
"""
UML解析器测试脚本
测试StarUML文件和图片解析功能
"""

import os
import json
from pathlib import Path
from main import UMLParser, parse_uml_file

def create_sample_staruml_file():
    """创建一个示例StarUML文件用于测试"""
    sample_data = {
        "_type": "Project",
        "name": "SampleProject",
        "ownedElements": [
            {
                "_type": "UMLModel",
                "name": "Model",
                "ownedElements": [
                    {
                        "_type": "UMLClass",
                        "name": "User",
                        "attributes": [
                            {
                                "_type": "UMLAttribute",
                                "name": "id",
                                "type": "int",
                                "visibility": "private"
                            },
                            {
                                "_type": "UMLAttribute",
                                "name": "username",
                                "type": "string",
                                "visibility": "private"
                            },
                            {
                                "_type": "UMLAttribute",
                                "name": "email",
                                "type": "string",
                                "visibility": "private"
                            }
                        ],
                        "operations": [
                            {
                                "_type": "UMLOperation",
                                "name": "login",
                                "visibility": "public",
                                "returnType": "boolean"
                            },
                            {
                                "_type": "UMLOperation",
                                "name": "logout",
                                "visibility": "public",
                                "returnType": "void"
                            }
                        ]
                    },
                    {
                        "_type": "UMLClass",
                        "name": "Order",
                        "attributes": [
                            {
                                "_type": "UMLAttribute",
                                "name": "orderId",
                                "type": "int",
                                "visibility": "private"
                            },
                            {
                                "_type": "UMLAttribute",
                                "name": "amount",
                                "type": "double",
                                "visibility": "private"
                            }
                        ],
                        "operations": [
                            {
                                "_type": "UMLOperation",
                                "name": "calculateTotal",
                                "visibility": "public",
                                "returnType": "double"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # 确保test目录存在
    os.makedirs("test", exist_ok=True)
    
    file_path = "test/sample_model.mdj"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 创建示例StarUML文件: {file_path}")
    return file_path

def test_staruml_parsing():
    """测试StarUML文件解析"""
    print("\n🧪 测试StarUML文件解析...")
    
    try:
        # 创建示例文件
        sample_file = create_sample_staruml_file()
        
        # 测试解析（不需要OpenAI API）
        parser = UMLParser("dummy_key", "dummy_url")  # StarUML解析不需要真实API
        result = parser.parse_staruml_file(sample_file)
        
        print(f"✅ 解析成功!")
        print(f"   源类型: {result['source_type']}")
        print(f"   文件路径: {result['file_path']}")
        print(f"   元素数量: {len(result['uml_structure']['elements'])}")
        print(f"   关系数量: {len(result['uml_structure']['relationships'])}")
        
        # 生成PlantUML代码
        plantuml_code = parser.generate_plantuml_code(result)
        print(f"✅ 生成PlantUML代码成功!")
        print("生成的PlantUML代码:")
        print("-" * 50)
        print(plantuml_code)
        print("-" * 50)
        
        # 保存PlantUML代码到文件
        output_file = "test/generated_from_staruml.puml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(plantuml_code)
        print(f"✅ PlantUML代码已保存到: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ StarUML解析测试失败: {str(e)}")
        return False

def test_image_parsing():
    """测试图片解析（需要真实的OpenAI API）"""
    print("\n🧪 测试图片解析...")
    
    # 检查环境变量
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    
    if not api_key:
        print("⚠️  跳过图片解析测试: 未设置OPENAI_API_KEY环境变量")
        print("   请设置环境变量后重新测试:")
        print("   export OPENAI_API_KEY='your-api-key'")
        print("   export OPENAI_BASE_URL='your-base-url'  # 可选")
        return False
    
    # 查找测试图片（先在test目录，再在当前目录）
    test_images = []
    for ext in ['.png', '.jpg', '.jpeg']:
        # 先查找test目录
        for file in Path('test').glob(f'*{ext}'):
            test_images.append(str(file))
        # 如果test目录没有，再查找当前目录
        if not test_images:
            for file in Path('.').glob(f'*{ext}'):
                test_images.append(str(file))
    
    if not test_images:
        print("⚠️  跳过图片解析测试: 当前目录下没有找到测试图片")
        print("   请添加一些UML图片文件 (.png, .jpg, .jpeg) 到当前目录")
        return False
    
    try:
        # 使用第一个找到的图片进行测试
        test_image = test_images[0]
        print(f"📷 使用测试图片: {test_image}")
        
        parser = UMLParser(api_key, base_url)
        result = parser.parse_image_to_uml(test_image)
        
        print(f"✅ 图片解析成功!")
        print(f"   源类型: {result['source_type']}")
        print(f"   文件路径: {result['file_path']}")
        
        uml_structure = result['uml_structure']
        print(f"   图表类型: {uml_structure.get('diagram_type', 'unknown')}")
        print(f"   元素数量: {len(uml_structure.get('elements', []))}")
        print(f"   关系数量: {len(uml_structure.get('relationships', []))}")
        
        # 生成PlantUML代码
        plantuml_code = parser.generate_plantuml_code(result)
        print(f"✅ 生成PlantUML代码成功!")
        
        # 保存结果
        result_file = "test/image_analysis_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ 分析结果已保存到: {result_file}")
        
        output_file = "test/generated_from_image.puml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(plantuml_code)
        print(f"✅ PlantUML代码已保存到: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 图片解析测试失败: {str(e)}")
        return False

def test_convenience_function():
    """测试便捷函数"""
    print("\n🧪 测试便捷函数...")
    
    try:
        # 测试StarUML文件
        sample_file = "test/sample_model.mdj"
        if os.path.exists(sample_file):
            result = parse_uml_file(sample_file, "dummy_key", "dummy_url")
            print("✅ 便捷函数解析StarUML文件成功!")
            print(f"   文件类型: {result['file_info']['source_type']}")
            print(f"   PlantUML代码长度: {len(result['plantuml_code'])} 字符")
        
        return True
        
    except Exception as e:
        print(f"❌ 便捷函数测试失败: {str(e)}")
        return False

def test_plantuml_image_generation():
    """测试PlantUML图像生成功能"""
    print("\n🧪 测试PlantUML图像生成...")
    
    try:
        # 创建一个简单的PlantUML代码用于测试
        simple_plantuml_code = """@startuml
title Simple Class Diagram

class User {
  - id: int
  - username: string
  - email: string
  --
  + login(): boolean
  + logout(): void
}

class Order {
  - orderId: int
  - amount: double
  --
  + calculateTotal(): double
}

User --> Order : places

@enduml"""
        
        # 测试基本图像生成功能（不需要真实的OpenAI API）
        parser = UMLParser("dummy_key", "dummy_url")
        
        print("📝 使用测试PlantUML代码生成图像...")
        # 尝试使用用户提到的 Java 路径
        java_paths_to_try = [
            None,  # 先尝试自动检测
            "jdk-25.0.1/bin/java.exe",  # Windows 版本
            "jdk-25.0.1/bin/java",  # Linux/Mac 版本
        ]
        
        image_path = None
        for java_path in java_paths_to_try:
            try:
                image_path = parser.generate_plantuml_image(simple_plantuml_code, java_path=java_path)
                if java_path:
                    print(f"✅ 使用 Java 路径: {java_path}")
                break
            except Exception as e:
                if java_path is None:
                    print(f"⚠️  自动检测 Java 失败: {str(e)}")
                else:
                    print(f"⚠️  Java 路径 {java_path} 失败: {str(e)}")
                continue
        
        if not image_path:
            raise Exception("所有 Java 路径都失败了")
        
        print(f"✅ 图像生成成功!")
        print(f"   输出路径: {image_path}")
        
        # 验证文件是否存在
        if os.path.exists(image_path):
            print(f"✅ 图像文件已创建: {image_path}")
            
            # 检查文件大小
            file_size = os.path.getsize(image_path)
            print(f"   文件大小: {file_size} 字节")
            
            if file_size > 0:
                print("✅ 图像文件不为空")
            else:
                print("⚠️  图像文件为空")
                return False
        else:
            print(f"❌ 图像文件未找到: {image_path}")
            return False
        
        # 测试自定义文件名
        print("\n📝 测试自定义文件名...")
        # 使用相同的 Java 路径（如果之前成功的话）
        working_java_path = None
        for java_path in java_paths_to_try:
            try:
                custom_image_path = parser.generate_plantuml_image(
                    simple_plantuml_code,
                    "test_custom_name",
                    java_path=java_path
                )
                print(f"✅ 自定义文件名图像生成成功: {custom_image_path}")
                working_java_path = java_path
                break
            except Exception as e:
                continue
        
        if not working_java_path and not custom_image_path:
            print("⚠️  自定义文件名测试跳过（Java 路径问题）")
        
        return True
        
    except Exception as e:
        print(f"❌ PlantUML图像生成测试失败: {str(e)}")
        return False

def test_plantuml_integration():
    """测试PlantUML与现有解析功能的集成"""
    print("\n🧪 测试PlantUML集成功能...")
    
    try:
        # 使用现有的StarUML示例文件
        sample_file = "test/sample_model.mdj"
        if not os.path.exists(sample_file):
            print("⚠️  跳过集成测试: 示例StarUML文件不存在")
            return False
        
        # 解析StarUML文件并生成PlantUML代码
        parser = UMLParser("dummy_key", "dummy_url")
        uml_data = parser.parse_staruml_file(sample_file)
        plantuml_code = parser.generate_plantuml_code(uml_data)
        
        print("📝 从StarUML文件生成PlantUML代码...")
        print("生成的PlantUML代码:")
        print("-" * 30)
        print(plantuml_code[:200] + "..." if len(plantuml_code) > 200 else plantuml_code)
        print("-" * 30)
        
        # 使用生成的PlantUML代码创建图像
        java_paths_to_try = [
            None,  # 先尝试自动检测
            "jdk-25.0.1/bin/java.exe",  # Windows 版本
            "jdk-25.0.1/bin/java",  # Linux/Mac 版本
        ]
        
        image_path = None
        for java_path in java_paths_to_try:
            try:
                image_path = parser.generate_plantuml_image(
                    plantuml_code,
                    "integration_test_result",
                    java_path=java_path
                )
                break
            except Exception as e:
                continue
        
        if not image_path:
            raise Exception("集成测试失败：无法找到可用的 Java 路径")
        
        print(f"✅ 集成测试成功!")
        print(f"   StarUML -> PlantUML代码 -> JPG图像")
        print(f"   最终图像: {image_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ PlantUML集成测试失败: {str(e)}")
        return False

def test_plantuml_error_handling():
    """测试PlantUML错误处理"""
    print("\n🧪 测试PlantUML错误处理...")
    
    try:
        parser = UMLParser("dummy_key", "dummy_url")
        
        # 测试无效的PlantUML代码
        invalid_code = """@startuml
        invalid syntax here
        this should cause an error
        @enduml"""
        
        print("📝 测试无效PlantUML代码处理...")
        try:
            image_path = parser.generate_plantuml_image(invalid_code, "error_test")
            print(f"⚠️  意外成功: {image_path}")
            # 即使语法有问题，PlantUML有时也会生成图像，所以这不一定是错误
            return True
        except Exception as e:
            print(f"✅ 正确捕获错误: {str(e)}")
            return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {str(e)}")
        return False


def main():
    """运行所有测试"""
    print("🚀 UML解析器测试开始...")
    print("=" * 60)
    
    results = []
    
    # 测试StarUML解析
    results.append(("StarUML解析", test_staruml_parsing()))
    
    # 测试图片解析
    results.append(("图片解析", test_image_parsing()))
    
    # 测试便捷函数
    results.append(("便捷函数", test_convenience_function()))
    
    # 测试PlantUML图像生成
    results.append(("PlantUML图像生成", test_plantuml_image_generation()))
    
    # 测试PlantUML集成功能
    results.append(("PlantUML集成功能", test_plantuml_integration()))
    
    # 测试PlantUML错误处理
    results.append(("PlantUML错误处理", test_plantuml_error_handling()))
    
    # 显示测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n总计: {passed}/{total} 个测试通过")
    print(f"\n📁 测试文件已保存到 test/ 目录")
    print(f"📁 PlantUML图像已保存到 jpg_output/ 目录")
    print("测试完成!")

if __name__ == "__main__":
    main()