"""
Model that represents contest (in fact a list of tasks)
"""

"""
        Number of the task in a contest. Is displayed to human!
        That means starts from 1. 0 is reserved value for default
        task in a contest (i.e. last unsolved, first, saved, etc).
"""

from django.db import models
import re
import json

from django_edu.models.task import Task


class Contest(models.Model):
    """
    Model representing a contest

    Attributes
    ----------
    MAX_NAME_LENGTH : int
        Maximum length of contest name
    tasks : models.JSONField
        List of tasks in json format (for orm)
    name : models.CharField
        Contest name
    """

    class ContestNameError(ValueError):
        """ Provide ability to detect specific error """

    class ContestTextError(ValueError):
        """ Provide ability to detect specific error """

    MAX_NAME_LENGTH = 256
    pk : models.IntegerField = models.IntegerField(primary_key=True, unique=True)
    tasks: models.JSONField = models.JSONField(default=lambda: [])
    name: models.CharField = models.CharField(max_length=MAX_NAME_LENGTH)

    def set_name(self, name: str) -> None:
        if not isinstance(name, str):
            raise TypeError('"name" must be a string instance')
        if len(name) > self.MAX_NAME_LENGTH:
            raise self.ContestNameError('Too long name for a contest')
        if len(name) == 0:
            raise self.ContestNameError('Contest name must not be empty')
        if (re.search(r'<([A-Za-z][A-Za-z0-9]*)(([^>])|(\n))*>(((.)|(\n))*)</\1>', name)
                != None):
            raise self.ContestNameError('Contest name must not contain html')
        # now name is ok: not empty plaintext that fits in MAX_NAME_LENGTH.
        self.name = name

    def get_task_pks(self) -> list[int]:
        return json.loads(self.tasks)

    def get_tasks(self) -> list[Task]:
        pks_list = self.get_task_pks()
        tasks_list: list[Task] = []
        for pk in pks_list:
            tasks_list.append(Task.objects.get(pk=pk))
        return tasks_list

    def append_task(self, task_pk: int) -> None:
        pks_list = self.get_task_pks()
        pks_list.append(task_pk)
        self.tasks = json.dumps(pks_list)

