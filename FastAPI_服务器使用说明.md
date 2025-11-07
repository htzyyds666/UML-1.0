# FastAPI UML智能批阅系统使用说明

## 🚀 系统概述

这是一个基于FastAPI的UML智能批阅系统，支持：
- StarUML文件(.mdj)解析和处理
- UML图片分析和错误检测
- 异步任务队列处理
- 完整的REST API接口
- 自动错误分析和修正建议

## 📋 功能特性

### 核心功能
1. **UML文件解析**
   - 支持StarUML (.mdj) 文件
   - 支持图片格式 (.png, .jpg, .jpeg, .bmp, .gif, .tiff)

2. **智能分析**
   - 基于GPT-4o的UML结构解析
   - 自动错误检测和分析
   - 生成修正建议

3. **结果输出**
   - 错误分析报告 (JSON格式)
   - 标注错误的图像
   - 修正后的UML代码
   - 修正后的UML图像

4. **任务管理**
   - 异步任务处理
   - 实时进度跟踪
   - 任务状态管理

## 🛠️ 安装和启动

### 1. 安装依赖
```bash
uv add fastapi uvicorn python-multipart
```

### 2. 启动服务器
```bash
uv run python fastapi_server.py
```

服务器将在 `http://localhost:8000` 启动

### 3. 访问API文档
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📡 API接口说明

### 1. 健康检查
```http
GET /
```
返回服务器基本信息

### 2. 提交任务
```http
POST /api/tasks/submit
```
**参数:**
- `file`: 上传的文件 (StarUML .mdj 或图片文件)
- `task_type`: 任务类型 (`staruml` 或 `image`)

**响应:**
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "任务已提交，正在排队处理"
}
```

### 3. 获取任务状态
```http
GET /api/tasks/{task_id}
```
**响应:**
```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-01T10:00:00Z",
  "result_links": {
    "error_analysis": "/api/tasks/uuid/files/error_analysis",
    "annotated_image": "/api/tasks/uuid/files/annotated_image",
    "corrected_uml": "/api/tasks/uuid/files/corrected_uml",
    "corrected_image": "/api/tasks/uuid/files/corrected_image"
  }
}
```

### 4. 获取任务列表
```http
GET /api/tasks?status=completed&limit=10&offset=0
```

### 5. 下载结果文件
```http
GET /api/tasks/{task_id}/files/{file_type}
```
**文件类型:**
- `error_analysis`: 错误分析报告 (JSON)
- `annotated_image`: 标注错误的图像 (JPG)
- `corrected_uml`: 修正后的UML代码 (JSON)
- `corrected_image`: 修正后的UML图像 (JPG)

### 6. 删除任务
```http
DELETE /api/tasks/{task_id}
```

### 7. 系统统计
```http
GET /api/stats
```

## 🔧 使用示例

### Python客户端示例
```python
import requests

# 1. 提交任务
with open('test.png', 'rb') as f:
    files = {'file': ('test.png', f, 'image/png')}
    data = {'task_type': 'image'}
    response = requests.post('http://localhost:8000/api/tasks/submit', 
                           files=files, data=data)
    task_id = response.json()['task_id']

# 2. 检查任务状态
response = requests.get(f'http://localhost:8000/api/tasks/{task_id}')
task_info = response.json()

# 3. 下载结果文件
if task_info['status'] == 'completed':
    # 下载错误分析报告
    response = requests.get(f'http://localhost:8000/api/tasks/{task_id}/files/error_analysis')
    with open('error_analysis.json', 'wb') as f:
        f.write(response.content)
```

### cURL示例
```bash
# 提交图片任务
curl -X POST "http://localhost:8000/api/tasks/submit" \
     -F "file=@test.png" \
     -F "task_type=image"

# 获取任务状态
curl "http://localhost:8000/api/tasks/{task_id}"

# 下载结果文件
curl "http://localhost:8000/api/tasks/{task_id}/files/error_analysis" \
     -o error_analysis.json
```

## 🧪 测试

运行测试脚本：
```bash
uv run python test_fastapi_server.py
```

测试脚本会：
1. 创建测试文件
2. 测试所有API接口
3. 验证任务处理流程
4. 下载和验证结果文件
5. 清理测试数据

## 📁 文件结构

```
UML1/
├── fastapi_server.py          # 主服务器文件
├── test_fastapi_server.py     # 测试脚本
├── main.py                    # UMLParser核心类
├── uploads/                   # 上传文件存储
├── results/                   # 处理结果存储
├── test_files/               # 测试文件和结果
└── tasks_db.json             # 任务数据库
```

## ⚙️ 配置说明

### 环境变量
在 `.env` 文件中配置：
```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 服务器配置
- 默认端口: 8000
- 最大工作进程: 2
- 支持CORS跨域请求

## 🔍 任务状态说明

- `pending`: 等待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 处理失败

## 📊 处理流程

### 图片任务流程
1. 上传图片文件
2. GPT-4o解析UML结构
3. 错误分析
4. 生成标注图像
5. 生成修正代码
6. 生成修正图像

### StarUML任务流程
1. 上传.mdj文件
2. 解析StarUML结构
3. 生成PlantUML代码
4. 生成UML图像
5. 错误分析
6. 生成标注图像

## 🚨 注意事项

1. **API密钥**: 确保设置了有效的OpenAI API密钥
2. **文件大小**: 建议图片文件不超过10MB
3. **处理时间**: 复杂的UML图可能需要几分钟处理时间
4. **并发限制**: 默认最多同时处理2个任务
5. **存储空间**: 定期清理不需要的任务和文件

## 🐛 故障排除

### 常见问题
1. **任务失败**: 检查OpenAI API密钥和网络连接
2. **PlantUML错误**: 确保安装了Java和plantuml.jar
3. **字体问题**: 系统需要支持中文字体显示

### 日志查看
服务器运行时会输出详细的处理日志，包括：
- 任务队列状态
- 处理进度
- 错误信息

## 📞 技术支持

如有问题，请检查：
1. 服务器日志输出
2. API响应错误信息
3. 测试脚本运行结果

---

**版本**: 1.0.0  
**更新时间**: 2024-10-30