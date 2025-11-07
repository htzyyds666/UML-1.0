#!/usr/bin/env python3
"""
FastAPI UML任务处理服务器（优化版）
保留原功能，增强稳定性与性能
"""

import os
import json
import uuid
import asyncio
import threading
import shutil
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
import aiofiles
import uvicorn

# 导入原UMLParser逻辑
from main import UMLParser


# ==================== 初始化日志 ====================
os.makedirs("logs", exist_ok=True)
logger.add("logs/server.log", rotation="5 MB", retention="10 days", encoding="utf-8")
logger.info("✅ 启动 UML 智能批阅系统优化版")


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


# ==================== 数据存储管理 ====================
class JSONDatabase:
    """线程安全的JSON数据库（带自动备份与恢复）"""

    def __init__(self, db_file: str = "tasks_db.json"):
        self.db_file = db_file
        self.lock = threading.Lock()
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        if not os.path.exists(self.db_file):
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump({"tasks": {}}, f, ensure_ascii=False, indent=2)

    def _backup(self):
        """备份数据库文件"""
        backup_path = self.db_file + ".bak"
        try:
            shutil.copyfile(self.db_file, backup_path)
        except Exception as e:
            logger.warning(f"⚠️ 数据库备份失败: {e}")

    def _load_data(self) -> Dict:
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("❌ 数据库损坏，正在恢复...")
            self._ensure_db_exists()
            return {"tasks": {}}

    def _save_data(self, data: Dict):
        """安全保存数据库"""
        with self.lock:
            try:
                self._backup()
                tmp_path = self.db_file + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self.db_file)
            except Exception as e:
                logger.exception(f"数据库写入失败: {e}")

    def create_task(self, task: TaskModel):
        with self.lock:
            data = self._load_data()
            data["tasks"][task.task_id] = task.dict()
            self._save_data(data)

    def update_task(self, task_id: str, updates: Dict):
        with self.lock:
            data = self._load_data()
            if task_id not in data["tasks"]:
                return False
            data["tasks"][task_id].update(updates)
            data["tasks"][task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_data(data)
            return True

    def get_task(self, task_id: str) -> Optional[TaskModel]:
        with self.lock:
            data = self._load_data()
            t = data["tasks"].get(task_id)
            return TaskModel(**t) if t else None

    def get_all_tasks(self) -> List[TaskModel]:
        with self.lock:
            data = self._load_data()
            return [TaskModel(**t) for t in data["tasks"].values()]

    def delete_task(self, task_id: str):
        with self.lock:
            data = self._load_data()
            if task_id in data["tasks"]:
                del data["tasks"][task_id]
                self._save_data(data)


# ==================== 异步任务队列 ====================
class TaskQueue:
    def __init__(self, max_workers: int = 2):
        self.queue = asyncio.Queue()
        self.max_workers = max_workers
        self.running = False

    async def start(self):
        if self.running:
            return
        self.running = True
        for i in range(self.max_workers):
            asyncio.create_task(self._worker(i))
        logger.info(f"🚀 启动任务队列，工作进程 {self.max_workers} 个")

    async def add_task(self, task_id: str):
        await self.queue.put(task_id)
        logger.info(f"📝 新任务加入队列：{task_id}")

    async def _worker(self, idx: int):
        while self.running:
            try:
                task_id = await self.queue.get()
                await self._process_task(task_id)
                self.queue.task_done()
            except Exception as e:
                logger.exception(f"❌ Worker {idx} 出错: {e}")

    async def _process_task(self, task_id: str):
        task = db.get_task(task_id)
        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return

        parser = UMLParser()
        db.update_task(task_id, {"status": TaskStatus.PROCESSING, "progress": 5})
        try:
            if task.task_type == TaskType.IMAGE:
                uml_data = parser.parse_image_to_uml(task.input_file_path)
                error_analysis = parser.analyze_uml_errors(task.input_file_path)
                annotated = parser.annotate_image_with_errors(task.input_file_path, error_analysis)
                corrected = parser.generate_corrected_uml(task.input_file_path)
            else:
                uml_data = parser.parse_staruml_file(task.input_file_path)
                plantuml = parser.generate_plantuml_code(uml_data)
                annotated = parser.generate_plantuml_image(plantuml, task_id)
                error_analysis = parser.analyze_uml_errors(annotated)
                corrected = {"corrected_plantuml": plantuml}

            result_dir = Path("results") / task_id
            result_dir.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(result_dir / "error_analysis.json", "w", encoding="utf-8") as f:
                await f.write(json.dumps(error_analysis, ensure_ascii=False, indent=2))

            db.update_task(task_id, {
                "status": TaskStatus.COMPLETED,
                "progress": 100,
                "error_analysis_result": str(result_dir / "error_analysis.json"),
                "annotated_image_path": annotated,
                "results": {"error_count": len(error_analysis.get("errors", []))}
            })
            logger.info(f"✅ 任务 {task_id} 处理完成")
        except Exception as e:
            db.update_task(task_id, {"status": TaskStatus.FAILED, "error_message": str(e)})
            logger.exception(f"❌ 任务 {task_id} 失败: {e}")


# ==================== FastAPI 应用 ====================
db = JSONDatabase()
queue = TaskQueue()

app = FastAPI(title="UML 智能批阅系统优化版", version="1.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 可在生产时改为 ["http://localhost:5173"]
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
async def on_startup():
    await queue.start()


@app.get("/health")
async def health():
    return {"status": "ok", "queue": queue.queue.qsize()}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path("uml_error_checker.html")
    if not html_path.exists():
        return HTMLResponse("<h3>找不到前端文件</h3>")
    return html_path.read_text(encoding="utf-8")


@app.post("/api/tasks/submit")
async def submit_task(file: UploadFile = File(...), task_type: TaskType = Form(...)):
    task_id = str(uuid.uuid4())
    upload_dir = Path("uploads") / task_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / file.filename

    async with aiofiles.open(save_path, "wb") as f:
        await f.write(await file.read())

    task = TaskModel(
        task_id=task_id,
        task_type=task_type,
        status=TaskStatus.PENDING,
        input_file_path=str(save_path),
        original_filename=file.filename,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    db.create_task(task)
    await queue.add_task(task_id)
    return {"task_id": task_id, "status": "pending"}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.dict()


@app.get("/api/stats")
async def stats():
    tasks = db.get_all_tasks()
    return {
        "total": len(tasks),
        "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
        "failed": len([t for t in tasks if t.status == TaskStatus.FAILED]),
        "queue_size": queue.queue.qsize()
    }


if __name__ == "__main__":
    uvicorn.run("fastapi_server:app", host="127.0.0.1", port=8000, reload=True)
