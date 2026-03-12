import json
import time
from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Union
from .logger import logger


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task:
    def __init__(self, task_id: str, name: str, description: str, 
                 dependencies: Optional[List[str]] = None,
                 max_retries: int = 3):
        self.task_id = task_id
        self.name = name
        self.description = description
        self.dependencies = dependencies or []
        self.max_retries = max_retries
        self.status = TaskStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration: Optional[float] = None
        self.result: Optional[Any] = None
        self.result_summary: Optional[str] = None
        self.input_data: Optional[Dict] = None
        self.error: Optional[str] = None
        self.retry_count = 0
        self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
            "input_data": self.input_data,
            "result_summary": self.result_summary,
            "error": self.error
        }


class LLMTaskManager:
    def __init__(self, name: str = "AI Movie Generator"):
        self.name = name
        self.tasks: Dict[str, Task] = {}
        self.task_order: List[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_duration: Optional[float] = None

    def add_task(self, task_id: str, name: str, description: str,
                 dependencies: Optional[List[str]] = None,
                 max_retries: int = 3) -> Task:
        """添加一个新任务"""
        task = Task(task_id, name, description, dependencies, max_retries)
        self.tasks[task_id] = task
        self.task_order.append(task_id)
        logger.info(f"📋 任务已添加: {name} ({task_id})")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def check_dependencies(self, task: Task) -> bool:
        """检查任务依赖是否已完成"""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"❌ 任务不存在: {task_id}")
            return False
        
        if not self.check_dependencies(task):
            logger.warning(f"⚠️  任务依赖未完成，跳过: {task.name}")
            task.status = TaskStatus.SKIPPED
            return False
        
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        logger.info(f"🚀 开始执行任务: {task.name}")
        return True

    def complete_task(self, task_id: str, result: Any = None, result_summary: Optional[str] = None) -> bool:
        """标记任务完成"""
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            logger.error(f"❌ 任务状态不正确: {task_id}")
            return False
        
        task.status = TaskStatus.COMPLETED
        task.end_time = datetime.now()
        task.duration = (task.end_time - task.start_time).total_seconds()
        task.result = result
        
        if result_summary:
            task.result_summary = result_summary
        else:
            task.result_summary = self._generate_result_summary(result)
        
        logger.info(f"✅ 任务完成: {task.name} (耗时: {task.duration:.2f}s)")
        logger.debug(f"📊 任务结果摘要: {task.result_summary}")
        return True
    
    def _generate_result_summary(self, result: Any) -> str:
        """生成结果摘要"""
        if result is None:
            return "None"
        if isinstance(result, bool):
            return str(result)
        if isinstance(result, (int, float)):
            return str(result)
        if isinstance(result, str):
            if len(result) > 200:
                return result[:200] + "..."
            return result
        if isinstance(result, (list, tuple)):
            return f"List[{len(result)}]"
        if isinstance(result, dict):
            return f"Dict[{len(result)} keys]"
        return str(type(result))

    def fail_task(self, task_id: str, error: str) -> bool:
        """标记任务失败"""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"❌ 任务不存在: {task_id}")
            return False
        
        task.status = TaskStatus.FAILED
        task.end_time = datetime.now()
        if task.start_time:
            task.duration = (task.end_time - task.start_time).total_seconds()
        task.error = error
        logger.error(f"❌ 任务失败: {task.name} - {error}")
        return False

    def retry_task(self, task_id: str) -> bool:
        """重试任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.retry_count >= task.max_retries:
            logger.error(f"❌ 任务已达到最大重试次数: {task.name} ({task.max_retries})")
            return False
        
        task.retry_count += 1
        task.status = TaskStatus.PENDING
        task.error = None
        logger.info(f"🔄 重试任务: {task.name} (第 {task.retry_count}/{task.max_retries} 次)")
        return True

    def execute_task(self, task_id: str, func: Callable, *args, input_data: Optional[Dict] = None, result_summary: Optional[Union[str, Callable]] = None, **kwargs) -> Any:
        """执行任务（包含重试逻辑）"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        if input_data:
            task.input_data = input_data
            logger.debug(f"📥 任务 [{task.name}] 输入数据: {json.dumps(input_data, ensure_ascii=False, default=str)}")
        
        while True:
            if not self.start_task(task_id):
                if task.status == TaskStatus.SKIPPED:
                    return None
                raise RuntimeError(f"无法启动任务: {task_id}")
            
            try:
                result = func(*args, **kwargs)
                final_result_summary = result_summary(result) if callable(result_summary) else result_summary
                self.complete_task(task_id, result, final_result_summary)
                return result
            except Exception as e:
                error_msg = str(e)
                self.fail_task(task_id, error_msg)
                
                if self.retry_task(task_id):
                    time.sleep(1)
                    continue
                else:
                    raise

    def start_workflow(self):
        """开始工作流"""
        self.start_time = datetime.now()
        logger.info(f"🎉 ===== 开始工作流: {self.name} =====")

    def end_workflow(self):
        """结束工作流"""
        self.end_time = datetime.now()
        if self.start_time:
            self.total_duration = (self.end_time - self.start_time).total_seconds()
        
        logger.info(f"🎉 ===== 工作流完成: {self.name} =====")
        logger.info(f"⏱️  总耗时: {self.total_duration:.2f}s")
        self.print_summary()

    def print_summary(self):
        """打印任务摘要"""
        logger.info("\n📊 ===== 任务摘要 =====")
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        skipped = sum(1 for t in self.tasks.values() if t.status == TaskStatus.SKIPPED)
        total = len(self.tasks)
        
        logger.info(f"总任务数: {total}")
        logger.info(f"✅ 完成: {completed}")
        logger.info(f"❌ 失败: {failed}")
        logger.info(f"⏭️  跳过: {skipped}")
        
        logger.info("\n📋 任务详情:")
        for task_id in self.task_order:
            task = self.tasks[task_id]
            status_icon = {
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.RUNNING: "🚀",
                TaskStatus.PENDING: "⏳",
                TaskStatus.SKIPPED: "⏭️"
            }.get(task.status, "?")
            duration_str = f" ({task.duration:.2f}s)" if task.duration else ""
            logger.info(f"  {status_icon} {task.name}{duration_str}")

    def save_report(self, filepath: str):
        """保存任务报告"""
        report = {
            "workflow_name": self.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": self.total_duration,
            "tasks": [t.to_dict() for t in self.tasks.values()]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 任务报告已保存: {filepath}")


def create_movie_workflow() -> LLMTaskManager:
    """创建电影生成工作流"""
    manager = LLMTaskManager("AI Movie Generator")
    
    manager.add_task(
        task_id="init_db",
        name="初始化数据库",
        description="创建并初始化 SQLite 数据库"
    )
    
    manager.add_task(
        task_id="init_ai",
        name="初始化 AI 客户端",
        description="初始化火山引擎 AI 客户端",
        dependencies=["init_db"]
    )
    
    manager.add_task(
        task_id="read_script",
        name="读取剧本",
        description="读取并解析剧本内容",
        dependencies=["init_ai"]
    )
    
    manager.add_task(
        task_id="director_plan",
        name="导演分析剧本",
        description="由大导演分析剧本并生成拍摄计划",
        dependencies=["read_script"]
    )
    
    manager.add_task(
        task_id="character_design",
        name="角色设计",
        description="为所有角色生成视觉设定和概念图",
        dependencies=["director_plan"]
    )
    
    manager.add_task(
        task_id="storyboard_design",
        name="分镜设计",
        description="为每个分镜生成首帧图",
        dependencies=["character_design"]
    )
    
    manager.add_task(
        task_id="video_generation",
        name="视频生成",
        description="为每个分镜生成视频",
        dependencies=["storyboard_design"]
    )
    
    manager.add_task(
        task_id="video_editing",
        name="视频拼接",
        description="将所有分镜视频拼接成完整电影",
        dependencies=["video_generation"]
    )
    
    manager.add_task(
        task_id="generate_project_md",
        name="生成项目文档",
        description="生成项目记录文档 project.md",
        dependencies=["video_editing"]
    )
    
    manager.add_task(
        task_id="finalization",
        name="最终整理",
        description="整理输出最终结果",
        dependencies=["generate_project_md"]
    )
    
    return manager
