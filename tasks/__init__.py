"""Tasks module"""
from .manager_tasks import create_planning_task
from .developer_tasks import create_development_task
from .tester_tasks import create_testing_task
from .github_tasks import create_github_deployment_task, create_github_repository_task

__all__ = [
    'create_planning_task',
    'create_development_task',
    'create_testing_task',
    'create_github_deployment_task',
    'create_github_repository_task'
]