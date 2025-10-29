#!/usr/bin/env python3
"""
PlantUML 图像生成示例
演示如何使用 UMLParser 类生成 PlantUML 图像
"""

from main import UMLParser

def example_basic_usage():
    """基本使用示例"""
    print("🔧 基本使用示例")
    
    # 创建解析器实例
    parser = UMLParser("dummy_key", "dummy_url")
    
    # 定义 PlantUML 代码
    plantuml_code = """@startuml
title 用户管理系统

class User {
  - id: int
  - username: string
  - email: string
  - password: string
  --
  + login(username, password): boolean
  + logout(): void
  + updateProfile(email): void
}

class UserManager {
  - users: List<User>
  --
  + createUser(username, email, password): User
  + deleteUser(id): boolean
  + findUser(username): User
}

UserManager --> User : manages

@enduml"""
    
    try:
        # 生成图像（自动检测 Java 路径）
        image_path = parser.generate_plantuml_image(plantuml_code)
        print(f"✅ 图像生成成功: {image_path}")
        
        # 生成自定义文件名的图像
        custom_image_path = parser.generate_plantuml_image(
            plantuml_code, 
            "user_management_system"
        )
        print(f"✅ 自定义文件名图像生成成功: {custom_image_path}")
        
    except Exception as e:
        print(f"❌ 生成失败: {str(e)}")

def example_with_custom_java_path():
    """使用自定义 Java 路径的示例"""
    print("\n🔧 自定义 Java 路径示例")
    
    parser = UMLParser("dummy_key", "dummy_url")
    
    plantuml_code = """@startuml
class Order {
  + id: string
  + amount: double
  + status: OrderStatus
}

enum OrderStatus {
  PENDING
  CONFIRMED
  SHIPPED
  DELIVERED
  CANCELLED
}

Order --> OrderStatus
@enduml"""
    
    try:
        # 指定 Java 路径（根据您的系统调整）
        java_path = "jdk-25.0.1/bin/java.exe"  # Windows
        # java_path = "jdk-25.0.1/bin/java"    # Linux/Mac
        
        image_path = parser.generate_plantuml_image(
            plantuml_code,
            "order_system",
            java_path=java_path
        )
        print(f"✅ 使用自定义 Java 路径生成成功: {image_path}")
        
    except Exception as e:
        print(f"❌ 生成失败: {str(e)}")
        print("💡 提示: 请根据您的系统调整 java_path 参数")

def example_integration_workflow():
    """完整工作流程示例：从 StarUML 到图像"""
    print("\n🔧 完整工作流程示例")
    
    parser = UMLParser("dummy_key", "dummy_url")
    
    try:
        # 1. 解析 StarUML 文件（如果存在）
        staruml_file = "test/sample_model.mdj"
        if os.path.exists(staruml_file):
            print("📁 解析 StarUML 文件...")
            uml_data = parser.parse_staruml_file(staruml_file)
            
            # 2. 生成 PlantUML 代码
            print("📝 生成 PlantUML 代码...")
            plantuml_code = parser.generate_plantuml_code(uml_data)
            
            # 3. 生成图像
            print("🖼️  生成图像...")
            image_path = parser.generate_plantuml_image(
                plantuml_code,
                "workflow_result"
            )
            
            print(f"✅ 完整工作流程成功!")
            print(f"   StarUML 文件 -> PlantUML 代码 -> JPG 图像")
            print(f"   最终图像: {image_path}")
        else:
            print("⚠️  跳过工作流程示例: 未找到 StarUML 示例文件")
            
    except Exception as e:
        print(f"❌ 工作流程失败: {str(e)}")

if __name__ == "__main__":
    import os
    
    print("🚀 PlantUML 图像生成示例")
    print("=" * 50)
    
    # 运行示例
    example_basic_usage()
    example_with_custom_java_path()
    example_integration_workflow()
    
    print("\n" + "=" * 50)
    print("📁 生成的图像保存在 jpg_output/ 目录中")
    print("💡 提示: 确保已安装 Java 并且 plantuml.jar 在当前目录")