#!/usr/bin/env python3
"""
FastAPI UML服务器测试代码
测试所有API接口的功能 - 异步版本
"""

import os
import json
import time
import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import tempfile
from PIL import Image, ImageDraw

# 测试配置
BASE_URL = "http://localhost:8000"
TEST_FILES_DIR = Path("test_files")

class FastAPIServerTester:
    """FastAPI服务器测试类 - 异步版本"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = None
        self.test_task_ids = []  # 存储测试创建的任务ID，用于清理
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
        
    async def setup_test_files(self):
        """创建测试文件"""
        TEST_FILES_DIR.mkdir(exist_ok=True)
        
        # 创建测试图片
        test_image_path = TEST_FILES_DIR / "test_uml.png"
        if not test_image_path.exists():
            # 创建一个简单的测试UML图
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            # 绘制简单的类图
            draw.rectangle([100, 100, 300, 200], outline='black', width=2)
            draw.text((110, 110), "User", fill='black')
            draw.text((110, 130), "- id: int", fill='black')
            draw.text((110, 150), "- name: string", fill='black')
            draw.text((110, 170), "+ getName(): string", fill='black')
            
            draw.rectangle([400, 100, 600, 200], outline='black', width=2)
            draw.text((410, 110), "Account", fill='black')
            draw.text((410, 130), "- balance: double", fill='black')
            draw.text((410, 150), "+ deposit(amount)", fill='black')
            
            # 绘制关联线
            draw.line([300, 150, 400, 150], fill='black', width=2)
            
            img.save(test_image_path)
            print(f"✅ 创建测试图片: {test_image_path}")
        
        # 创建测试StarUML文件
        test_staruml_path = TEST_FILES_DIR / "test_model.mdj"
        if not test_staruml_path.exists():
            staruml_data = {
                "_type": "Project",
                "name": "TestProject",
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
                                        "name": "name",
                                        "type": "string",
                                        "visibility": "private"
                                    }
                                ],
                                "operations": [
                                    {
                                        "_type": "UMLOperation",
                                        "name": "getName",
                                        "returnType": "string",
                                        "visibility": "public"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            with open(test_staruml_path, 'w', encoding='utf-8') as f:
                json.dump(staruml_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 创建测试StarUML文件: {test_staruml_path}")
        
        return test_image_path, test_staruml_path
    
    async def test_server_health(self) -> bool:
        """测试服务器健康状态"""
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 服务器健康检查通过: {data['message']}")
                    return True
                else:
                    print(f"❌ 服务器健康检查失败: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ 无法连接到服务器: {str(e)}")
            return False
    
    async def test_submit_image_task(self, image_path: Path) -> str:
        """测试提交图片任务"""
        try:
            with open(image_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=image_path.name, content_type='image/png')
                data.add_field('task_type', 'image')
                
                async with self.session.post(
                    f"{self.base_url}/api/tasks/submit",
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        task_id = result['task_id']
                        self.test_task_ids.append(task_id)
                        print(f"✅ 图片任务提交成功: {task_id}")
                        return task_id
                    else:
                        text = await response.text()
                        print(f"❌ 图片任务提交失败: {response.status} - {text}")
                        return None
                
        except Exception as e:
            print(f"❌ 提交图片任务异常: {str(e)}")
            return None
    
    async def test_submit_staruml_task(self, staruml_path: Path) -> str:
        """测试提交StarUML任务"""
        try:
            with open(staruml_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=staruml_path.name, content_type='application/json')
                data.add_field('task_type', 'staruml')
                
                async with self.session.post(
                    f"{self.base_url}/api/tasks/submit",
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        task_id = result['task_id']
                        self.test_task_ids.append(task_id)
                        print(f"✅ StarUML任务提交成功: {task_id}")
                        return task_id
                    else:
                        text = await response.text()
                        print(f"❌ StarUML任务提交失败: {response.status} - {text}")
                        return None
                
        except Exception as e:
            print(f"❌ 提交StarUML任务异常: {str(e)}")
            return None
    
    async def test_get_task_status(self, task_id: str) -> Dict[str, Any]:
        """测试获取任务状态"""
        try:
            async with self.session.get(f"{self.base_url}/api/tasks/{task_id}") as response:
                if response.status == 200:
                    task_data = await response.json()
                    print(f"✅ 获取任务状态成功: {task_id} - {task_data['status']} ({task_data['progress']}%)")
                    return task_data
                else:
                    text = await response.text()
                    print(f"❌ 获取任务状态失败: {response.status} - {text}")
                    return None
                
        except Exception as e:
            print(f"❌ 获取任务状态异常: {str(e)}")
            return None
    
    async def test_get_tasks_list(self) -> List[Dict[str, Any]]:
        """测试获取任务列表"""
        try:
            async with self.session.get(f"{self.base_url}/api/tasks") as response:
                if response.status == 200:
                    result = await response.json()
                    tasks = result['tasks']
                    total = result['total']
                    print(f"✅ 获取任务列表成功: 共 {total} 个任务")
                    return tasks
                else:
                    text = await response.text()
                    print(f"❌ 获取任务列表失败: {response.status} - {text}")
                    return []
                
        except Exception as e:
            print(f"❌ 获取任务列表异常: {str(e)}")
            return []
    
    async def test_get_stats(self) -> Dict[str, Any]:
        """测试获取系统统计"""
        try:
            async with self.session.get(f"{self.base_url}/api/stats") as response:
                if response.status == 200:
                    stats = await response.json()
                    print(f"✅ 获取系统统计成功:")
                    print(f"   - 总任务数: {stats['total_tasks']}")
                    print(f"   - 等待中: {stats['pending_tasks']}")
                    print(f"   - 处理中: {stats['processing_tasks']}")
                    print(f"   - 已完成: {stats['completed_tasks']}")
                    print(f"   - 失败: {stats['failed_tasks']}")
                    print(f"   - 队列大小: {stats['queue_size']}")
                    print(f"   - 工作进程: {stats['workers']}")
                    return stats
                else:
                    text = await response.text()
                    print(f"❌ 获取系统统计失败: {response.status} - {text}")
                    return {}
                
        except Exception as e:
            print(f"❌ 获取系统统计异常: {str(e)}")
            return {}
    
    async def wait_for_task_completion(self, task_id: str, timeout: int = 300) -> bool:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            task_data = await self.test_get_task_status(task_id)
            if not task_data:
                return False
            
            status = task_data['status']
            progress = task_data['progress']
            
            if status == 'completed':
                print(f"✅ 任务 {task_id} 完成")
                return True
            elif status == 'failed':
                error_msg = task_data.get('error_message', '未知错误')
                print(f"❌ 任务 {task_id} 失败: {error_msg}")
                return False
            else:
                print(f"⏳ 任务 {task_id} 进行中: {status} ({progress}%)")
                await asyncio.sleep(5)  # 等待5秒后再检查
        
        print(f"⏰ 任务 {task_id} 超时")
        return False
    
    async def test_download_result_files(self, task_id: str):
        """测试下载结果文件"""
        file_types = ['error_analysis', 'annotated_image', 'corrected_uml', 'corrected_image']
        
        for file_type in file_types:
            try:
                async with self.session.get(f"{self.base_url}/api/tasks/{task_id}/files/{file_type}") as response:
                    if response.status == 200:
                        # 保存文件到测试目录
                        output_path = TEST_FILES_DIR / f"{task_id}_{file_type}"
                        
                        # 根据内容类型确定文件扩展名
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            output_path = output_path.with_suffix('.json')
                        elif 'image' in content_type:
                            output_path = output_path.with_suffix('.jpg')
                        
                        content = await response.read()
                        with open(output_path, 'wb') as f:
                            f.write(content)
                        
                        print(f"✅ 下载 {file_type} 成功: {output_path}")
                        
                    elif response.status == 404:
                        print(f"⚠️  文件 {file_type} 不存在")
                    else:
                        print(f"❌ 下载 {file_type} 失败: {response.status}")
                        
            except Exception as e:
                print(f"❌ 下载 {file_type} 异常: {str(e)}")
    
    async def test_delete_task(self, task_id: str) -> bool:
        """测试删除任务"""
        try:
            async with self.session.delete(f"{self.base_url}/api/tasks/{task_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ 删除任务成功: {result['message']}")
                    return True
                else:
                    text = await response.text()
                    print(f"❌ 删除任务失败: {response.status} - {text}")
                    return False
                
        except Exception as e:
            print(f"❌ 删除任务异常: {str(e)}")
            return False
    
    async def cleanup_test_tasks(self):
        """清理测试任务"""
        print("\n🧹 清理测试任务...")
        for task_id in self.test_task_ids:
            await self.test_delete_task(task_id)
        self.test_task_ids.clear()
    
    async def run_comprehensive_test(self):
        """运行综合测试"""
        print("🚀 开始FastAPI服务器综合测试 (异步版本)")
        print("=" * 50)
        
        # 1. 设置测试文件
        print("\n📁 设置测试文件...")
        test_image_path, test_staruml_path = await self.setup_test_files()
        
        # 2. 测试服务器健康状态
        print("\n🏥 测试服务器健康状态...")
        if not await self.test_server_health():
            print("❌ 服务器不可用，测试终止")
            return False
        
        # 3. 测试系统统计
        print("\n📊 测试系统统计...")
        await self.test_get_stats()
        
        # 4. 测试任务列表
        print("\n📋 测试任务列表...")
        await self.test_get_tasks_list()
        
        # 5. 测试提交图片任务
        print("\n🖼️ 测试图片任务...")
        image_task_id = await self.test_submit_image_task(test_image_path)
        
        # 6. 测试提交StarUML任务
        print("\n⭐ 测试StarUML任务...")
        staruml_task_id = await self.test_submit_staruml_task(test_staruml_path)
        
        # 7. 等待任务完成并测试结果
        print("\n⏳ 等待任务完成...")
        
        # 并发等待任务完成
        tasks = []
        if image_task_id:
            print(f"等待图片任务 {image_task_id} 完成...")
            tasks.append(self.wait_and_download_results(image_task_id, "图片"))
        
        if staruml_task_id:
            print(f"等待StarUML任务 {staruml_task_id} 完成...")
            tasks.append(self.wait_and_download_results(staruml_task_id, "StarUML"))
        
        # 并发执行任务等待
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 8. 最终统计
        print("\n📊 最终系统统计...")
        await self.test_get_stats()
        
        # 9. 清理测试任务
        await self.cleanup_test_tasks()
        
        print("\n✅ 综合测试完成!")
        return True
    
    async def wait_and_download_results(self, task_id: str, task_type: str):
        """等待任务完成并下载结果"""
        if await self.wait_for_task_completion(task_id):
            print(f"📥 测试下载{task_type}任务结果文件...")
            await self.test_download_result_files(task_id)


async def main():
    """主测试函数 - 异步版本"""
    print("FastAPI UML服务器测试工具 (异步版本)")
    print("确保服务器已启动: python fastapi_server.py")
    print("然后运行此测试: python test_fastapi_server.py")
    
    # 等待用户确认
    input("\n按回车键开始测试...")
    
    # 使用异步上下文管理器创建测试器并运行测试
    async with FastAPIServerTester() as tester:
        try:
            success = await tester.run_comprehensive_test()
            if success:
                print("\n🎉 所有测试通过!")
            else:
                print("\n❌ 测试失败!")
        except KeyboardInterrupt:
            print("\n⚠️ 测试被用户中断")
            await tester.cleanup_test_tasks()
        except Exception as e:
            print(f"\n💥 测试过程中发生异常: {str(e)}")
            await tester.cleanup_test_tasks()


if __name__ == "__main__":
    asyncio.run(main())