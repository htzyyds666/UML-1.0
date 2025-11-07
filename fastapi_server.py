#!/usr/bin/env python3
"""
FastAPI UML任务处理服务器
单文件实现，包含任务队列、JSON数据存储和完整的API接口
"""

import os
import json
import uuid
import asyncio
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import shutil

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 导入现有的UMLParser
from main import UMLParser

# ==================== 数据模型 ====================

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskType(str, Enum):
    STARUML = "staruml"
    IMAGE = "image"
    PLANTUML = "plantuml"

class TaskModel(BaseModel):
    task_id: str
    task_type: TaskType
    status: TaskStatus
    input_file_path: str
    original_filename: str
    created_at: str
    updated_at: str
    progress: int = 0
    error_message: Optional[str] = None
    
    # 结果文件路径
    error_analysis_result: Optional[str] = None
    annotated_image_path: Optional[str] = None
    corrected_uml_path: Optional[str] = None
    corrected_image_path: Optional[str] = None
    
    # 处理结果数据
    results: Optional[Dict[str, Any]] = None

class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskListResponse(BaseModel):
    tasks: List[TaskModel]
    total: int

# ==================== 数据存储管理 ====================

class JSONDatabase:
    """简单的JSON文件数据库"""
    
    def __init__(self, db_file: str = "tasks_db.json"):
        self.db_file = db_file
        self.lock = threading.Lock()
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """确保数据库文件存在"""
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump({"tasks": {}}, f, ensure_ascii=False, indent=2)
    
    def _load_data(self) -> Dict:
        """加载数据"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"tasks": {}}
    
    def _save_data(self, data: Dict):
        """保存数据"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_task(self, task: TaskModel) -> bool:
        """创建任务"""
        with self.lock:
            data = self._load_data()
            data["tasks"][task.task_id] = task.dict()
            self._save_data(data)
            return True
    
    def get_task(self, task_id: str) -> Optional[TaskModel]:
        """获取任务"""
        with self.lock:
            data = self._load_data()
            task_data = data["tasks"].get(task_id)
            if task_data:
                return TaskModel(**task_data)
            return None
    
    def update_task(self, task_id: str, updates: Dict) -> bool:
        """更新任务"""
        with self.lock:
            data = self._load_data()
            if task_id in data["tasks"]:
                data["tasks"][task_id].update(updates)
                data["tasks"][task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_data(data)
                return True
            return False
    
    def get_all_tasks(self, status_filter: Optional[str] = None) -> List[TaskModel]:
        """获取所有任务"""
        with self.lock:
            data = self._load_data()
            tasks = []
            for task_data in data["tasks"].values():
                if status_filter is None or task_data.get("status") == status_filter:
                    tasks.append(TaskModel(**task_data))
            # 按创建时间倒序排列
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            return tasks
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self.lock:
            data = self._load_data()
            if task_id in data["tasks"]:
                del data["tasks"][task_id]
                self._save_data(data)
                return True
            return False

# ==================== 任务队列管理 ====================

class TaskQueue:
    """简单的任务队列实现"""
    
    def __init__(self, max_workers: int = 2):
        self.queue = asyncio.Queue()
        self.max_workers = max_workers
        self.workers = []
        self.running = False
    
    async def start(self):
        """启动工作进程"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        print(f"✅ 任务队列已启动，工作进程数: {self.max_workers}")
    
    async def stop(self):
        """停止工作进程"""
        self.running = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        print("🛑 任务队列已停止")
    
    async def add_task(self, task_id: str):
        """添加任务到队列"""
        await self.queue.put(task_id)
        print(f"📝 任务 {task_id} 已添加到队列")
    
    async def _worker(self, worker_name: str):
        """工作进程"""
        print(f"🚀 工作进程 {worker_name} 已启动")
        
        while self.running:
            try:
                # 等待任务，超时1秒
                task_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                print(f"🔄 {worker_name} 开始处理任务 {task_id}")
                
                # 处理任务
                await self._process_task(task_id)
                
                # 标记任务完成
                self.queue.task_done()
                print(f"✅ {worker_name} 完成任务 {task_id}")
                
            except asyncio.TimeoutError:
                # 超时继续循环
                continue
            except Exception as e:
                print(f"❌ {worker_name} 处理任务时出错: {str(e)}")
    
    async def _process_task(self, task_id: str):
        """处理具体任务"""
        try:
            # 获取任务信息
            task = db.get_task(task_id)
            if not task:
                print(f"❌ 任务 {task_id} 不存在")
                return
            
            # 更新状态为处理中
            db.update_task(task_id, {
                "status": TaskStatus.PROCESSING,
                "progress": 10
            })
            
            # 初始化UMLParser
            parser = UMLParser()
            
            # 根据任务类型处理
            if task.task_type == TaskType.IMAGE:
                await self._process_image_task(task_id, task, parser)
            elif task.task_type == TaskType.STARUML:
                await self._process_staruml_task(task_id, task, parser)
            else:
                raise ValueError(f"不支持的任务类型: {task.task_type}")
            
        except Exception as e:
            print(f"❌ 处理任务 {task_id} 失败: {str(e)}")
            db.update_task(task_id, {
                "status": TaskStatus.FAILED,
                "error_message": str(e)
            })
    
    async def _process_image_task(self, task_id: str, task: TaskModel, parser: UMLParser):
        """处理图片任务"""
        try:
            # 1. 解析图片获取UML结构
            print(f"🔍 解析图片: {task.input_file_path}")
            uml_data = parser.parse_image_to_uml(task.input_file_path)
            db.update_task(task_id, {"progress": 30})
            
            # 2. 错误分析
            print(f"🔍 分析错误...")
            error_analysis = parser.analyze_uml_errors(task.input_file_path)
            db.update_task(task_id, {"progress": 50})
            
            # 3. 生成标注图像
            print(f"🎨 生成标注图像...")
            annotated_path = parser.annotate_image_with_errors(
                task.input_file_path, error_analysis
            )
            db.update_task(task_id, {"progress": 70})
            
            # 4. 生成修正后的UML代码
            print(f"🔧 生成修正代码...")
            corrected_result = parser.generate_corrected_uml(task.input_file_path)
            db.update_task(task_id, {"progress": 85})
            
            # 5. 生成修正后的图像
            print(f"🖼️ 生成修正图像...")
            corrected_image_path = None
            if corrected_result.get('corrected_plantuml'):
                corrected_image_path = parser.generate_plantuml_image(
                    corrected_result['corrected_plantuml'],
                    f"corrected_{task_id}"
                )
            db.update_task(task_id, {"progress": 95})
            
            # 6. 保存结果文件
            results_dir = Path("results") / task_id
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存错误分析结果
            error_analysis_file = results_dir / "error_analysis.json"
            with open(error_analysis_file, 'w', encoding='utf-8') as f:
                json.dump(error_analysis, f, ensure_ascii=False, indent=2)
            
            # 保存修正结果
            corrected_uml_file = results_dir / "corrected_result.json"
            with open(corrected_uml_file, 'w', encoding='utf-8') as f:
                json.dump(corrected_result, f, ensure_ascii=False, indent=2)
            
            # 7. 更新任务状态为完成
            db.update_task(task_id, {
                "status": TaskStatus.COMPLETED,
                "progress": 100,
                "error_analysis_result": str(error_analysis_file),
                "annotated_image_path": annotated_path,
                "corrected_uml_path": str(corrected_uml_file),
                "corrected_image_path": corrected_image_path,
                "results": {
                    "error_count": len(error_analysis.get("errors", [])),
                    "severity_level": error_analysis.get("summary", {}).get("severity_level", "未知"),
                    "has_corrections": bool(corrected_result.get('corrected_plantuml'))
                }
            })
            
            print(f"✅ 图片任务 {task_id} 处理完成")
            
        except Exception as e:
            raise Exception(f"图片任务处理失败: {str(e)}")
    
    async def _process_staruml_task(self, task_id: str, task: TaskModel, parser: UMLParser):
        """处理StarUML任务"""
        try:
            # 1. 解析StarUML文件
            print(f"🔍 解析StarUML文件: {task.input_file_path}")
            uml_data = parser.parse_staruml_file(task.input_file_path)
            db.update_task(task_id, {"progress": 30})
            
            # 2. 生成PlantUML代码
            print(f"📝 生成PlantUML代码...")
            plantuml_code = parser.generate_plantuml_code(uml_data)
            db.update_task(task_id, {"progress": 50})
            
            # 3. 生成图像
            print(f"🖼️ 生成UML图像...")
            image_path = parser.generate_plantuml_image(plantuml_code, f"staruml_{task_id}")
            db.update_task(task_id, {"progress": 70})
            
            # 4. 对生成的图像进行错误分析
            print(f"🔍 分析生成图像的错误...")
            error_analysis = parser.analyze_uml_errors(image_path)
            db.update_task(task_id, {"progress": 85})
            
            # 5. 生成标注图像
            print(f"🎨 生成标注图像...")
            annotated_path = parser.annotate_image_with_errors(image_path, error_analysis)
            db.update_task(task_id, {"progress": 95})
            
            # 6. 保存结果文件
            results_dir = Path("results") / task_id
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存PlantUML代码
            plantuml_file = results_dir / "generated.puml"
            with open(plantuml_file, 'w', encoding='utf-8') as f:
                f.write(plantuml_code)
            
            # 保存错误分析结果
            error_analysis_file = results_dir / "error_analysis.json"
            with open(error_analysis_file, 'w', encoding='utf-8') as f:
                json.dump(error_analysis, f, ensure_ascii=False, indent=2)
            
            # 7. 更新任务状态为完成
            db.update_task(task_id, {
                "status": TaskStatus.COMPLETED,
                "progress": 100,
                "error_analysis_result": str(error_analysis_file),
                "annotated_image_path": annotated_path,
                "corrected_uml_path": str(plantuml_file),
                "corrected_image_path": image_path,
                "results": {
                    "error_count": len(error_analysis.get("errors", [])),
                    "severity_level": error_analysis.get("summary", {}).get("severity_level", "未知"),
                    "plantuml_generated": True
                }
            })
            
            print(f"✅ StarUML任务 {task_id} 处理完成")
            
        except Exception as e:
            raise Exception(f"StarUML任务处理失败: {str(e)}")

# ==================== FastAPI应用 ====================

# 初始化数据库和任务队列
db = JSONDatabase()
task_queue = TaskQueue(max_workers=2)

# 创建FastAPI应用
app = FastAPI(
    title="UML智能批阅系统",
    description="基于AI的UML图错误检测与自动修正系统",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保必要的目录存在
os.makedirs("uploads", exist_ok=True)
os.makedirs("results", exist_ok=True)

# ==================== API接口 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化任务队列"""
    await task_queue.start()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止任务队列"""
    await task_queue.stop()

@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径 - 返回UML纠错界面"""
    try:
        # 读取HTML文件
        html_file_path = Path("uml_error_checker.html")
        if html_file_path.exists():
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return HTMLResponse(content=html_content, status_code=200)
        else:
            # 如果HTML文件不存在，返回简单的错误页面
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>UML智能纠错系统</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .error { color: #dc3545; }
                    .info { color: #6c757d; margin-top: 20px; }
                </style>
            </head>
            <body>
                <h1>UML智能纠错系统</h1>
                <p class="error">界面文件未找到</p>
                <p class="info">请确保 uml_error_checker.html 文件存在于项目根目录</p>
                <p class="info">
                    <a href="/docs">查看API文档</a> |
                    <a href="/api/stats">系统统计</a>
                </p>
            </body>
            </html>
            """, status_code=200)
    except Exception as e:
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>错误</title>
            <style>body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}</style>
        </head>
        <body>
            <h1>服务器错误</h1>
            <p>无法加载界面: {str(e)}</p>
            <p><a href="/docs">查看API文档</a></p>
        </body>
        </html>
        """, status_code=500)

@app.post("/api/tasks/submit", response_model=TaskSubmitResponse)
async def submit_task(
    file: UploadFile = File(...),
    task_type: TaskType = Form(...)
):
    """
    提交UML分析任务
    
    Args:
        file: 上传的文件（StarUML .mdj文件或图片）
        task_type: 任务类型（staruml/image）
    
    Returns:
        任务ID和状态信息
    """
    try:
        # 验证文件类型
        file_ext = Path(file.filename).suffix.lower()
        
        if task_type == TaskType.STARUML and file_ext != '.mdj':
            raise HTTPException(status_code=400, detail="StarUML任务需要.mdj文件")
        elif task_type == TaskType.IMAGE and file_ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']:
            raise HTTPException(status_code=400, detail="图片任务需要图片文件")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 保存上传的文件
        upload_dir = Path("uploads") / task_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 创建任务记录
        task = TaskModel(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            input_file_path=str(file_path),
            original_filename=file.filename,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat()
        )
        
        # 保存到数据库
        db.create_task(task)
        
        # 添加到任务队列
        await task_queue.add_task(task_id)
        
        return TaskSubmitResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="任务已提交，正在排队处理"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")

@app.get("/api/tasks", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取任务列表
    
    Args:
        status: 状态过滤（可选）
        limit: 返回数量限制
        offset: 偏移量
    
    Returns:
        任务列表
    """
    try:
        # 获取所有任务
        all_tasks = db.get_all_tasks(status_filter=status.value if status else None)
        
        # 分页
        total = len(all_tasks)
        tasks = all_tasks[offset:offset + limit]
        
        return TaskListResponse(
            tasks=tasks,
            total=total
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """
    获取任务详情和状态
    
    Args:
        task_id: 任务ID
    
    Returns:
        任务详细信息
    """
    try:
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 构建结果文件链接
        result_links = {}
        if task.status == TaskStatus.COMPLETED:
            if task.error_analysis_result:
                result_links["error_analysis"] = f"/api/tasks/{task_id}/files/error_analysis"
            if task.annotated_image_path:
                result_links["annotated_image"] = f"/api/tasks/{task_id}/files/annotated_image"
            if task.corrected_uml_path:
                result_links["corrected_uml"] = f"/api/tasks/{task_id}/files/corrected_uml"
            if task.corrected_image_path:
                result_links["corrected_image"] = f"/api/tasks/{task_id}/files/corrected_image"
        
        response = task.dict()
        response["result_links"] = result_links
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")

@app.get("/api/tasks/{task_id}/files/{file_type}")
async def get_task_file(task_id: str, file_type: str):
    """
    下载任务结果文件
    
    Args:
        task_id: 任务ID
        file_type: 文件类型（error_analysis/annotated_image/corrected_uml/corrected_image）
    
    Returns:
        文件内容
    """
    try:
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="任务尚未完成")
        
        # 根据文件类型返回对应文件
        file_path = None
        media_type = "application/octet-stream"
        
        if file_type == "error_analysis":
            file_path = task.error_analysis_result
            media_type = "application/json"
        elif file_type == "annotated_image":
            file_path = task.annotated_image_path
            media_type = "image/jpeg"
        elif file_type == "corrected_uml":
            file_path = task.corrected_uml_path
            media_type = "application/json"
        elif file_type == "corrected_image":
            file_path = task.corrected_image_path
            media_type = "image/jpeg"
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=f"{task_id}_{file_type}.{file_path.split('.')[-1]}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务及其相关文件
    
    Args:
        task_id: 任务ID
    
    Returns:
        删除结果
    """
    try:
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 删除相关文件
        upload_dir = Path("uploads") / task_id
        results_dir = Path("results") / task_id
        
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        if results_dir.exists():
            shutil.rmtree(results_dir)
        
        # 从数据库删除任务记录
        db.delete_task(task_id)
        
        return {"message": f"任务 {task_id} 已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")

@app.get("/api/stats")
async def get_stats():
    """
    获取系统统计信息
    
    Returns:
        统计数据
    """
    try:
        all_tasks = db.get_all_tasks()
        
        stats = {
            "total_tasks": len(all_tasks),
            "pending_tasks": len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            "processing_tasks": len([t for t in all_tasks if t.status == TaskStatus.PROCESSING]),
            "completed_tasks": len([t for t in all_tasks if t.status == TaskStatus.COMPLETED]),
            "failed_tasks": len([t for t in all_tasks if t.status == TaskStatus.FAILED]),
            "queue_size": task_queue.queue.qsize(),
            "workers": len(task_queue.workers)
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

# ==================== 主程序入口 ====================

if __name__ == "__main__":
    print("🚀 启动UML智能批阅系统...")
    print("📚 API文档: http://localhost:8000/docs")
    print("🔍 系统统计: http://localhost:8000/api/stats")
    
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )