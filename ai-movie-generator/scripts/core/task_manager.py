# Simple task manager
tasks = {}

class TaskManager:
    def get_task(self, task_id):
        return tasks.get(task_id, None)
    
    def update_progress(self, task_id, progress):
        if task_id not in tasks:
            tasks[task_id] = {}
        tasks[task_id]['progress'] = progress

task_manager = TaskManager()

def get_task(task_id):
    return task_manager.get_task(task_id)

def update_progress(task_id, progress):
    return task_manager.update_progress(task_id, progress)
