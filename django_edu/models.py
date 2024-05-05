from django.db import models
import re
from html5lib import HTMLParser, html5parser


class Test(models.Model):
    """
    Model that holds input & output for a program
    """
    id : models.IntegerField = models.IntegerField(primary_key=True, unique=True)
    test_input: models.TextField = models.TextField()
    test_output: models.TextField = models.TextField()

    # TODO: checkers

    def __init__(self, test_input: str, test_output: str):
        self.set_input
        self.set_output

    def set_input(self, test_input: str) -> None:
        self.test_input = test_input

    def set_output(self, test_output: str) -> None:
        self.test_output = test_output


class Task(models.Model):
    """
    Model representing a task.

    Attributes
    ----------
    MAX_NAME_LENGTH : int
        Name length constraint
    MAX_TEXT_LENGTH : int
        Text (task condition) length constraint.
    id : models.IntegerField
        Task id (primary key)
    name : models.CharField
        Name of the task (human-readable), plain text, as allowing
        html may break page, i.e. inserting images will look strange.
    text : models.TextField
        Text of the task, plain html for inserting links, tables, etc.
    ans_type: models.CharField
        Type of the answer: test for comparison with ref, or code.
    ref_ans:
        Reference answer for test answer task.
    tests : models.JSONField
        list of tests id-s.
    TODO: eval? custom checker? ans not to be in that very situation with regex & LMS.
    """
    class AnsType(models.TextChoices):
        """ Enum in fact, representing the task answer type """
        code = 'C', 'Answer as code'
        text = 'T', 'Answer as text'

    class TaskNameError(ValueError):
        """ Provide ability to detect specific error """

    class TaskTextError(ValueError):
        """ Provide ability to detect specific error """

    class TaskRefAnsError(ValueError):
        """ Provide ability to detect specific error """

    MAX_NAME_LENGTH = 64
    MAX_TEXT_LENGTH = 1000
    MAX_ANS_LENGTH = 256
    id : models.IntegerField = models.IntegerField(primary_key=True, unique=True)
    name: models.CharField = models.CharField(max_length=MAX_NAME_LENGTH)
    text: models.TextField = models.TextField(max_length=MAX_TEXT_LENGTH)
    ans_type: models.CharField = models.CharField(max_length=1,
                                                  choices=AnsType.choices,
                                                  default=AnsType.text)
    ref_ans: models.CharField = models.CharField(max_length=MAX_ANS_LENGTH, null=True)
    tests: models.JSONField = models.JSONField(default=list, null=True)

    def __init__(self, name: str, text: str, ans_type: AnsType, ref_ans: str | None = None):
        self.set_name(name)
        self.set_text(text)
        self.ans_type = ans_type
        if self.ans_type == self.AnsType.text:
            if isinstance(ref_ans, str):
                self.set_ref_ans(ref_ans)
            else:
                raise self.TaskRefAnsError("For text answer task, ref ans is mandatory")

    def set_ref_ans(self, ref_ans: str) -> None:
        if not isinstance(ref_ans, str):
            raise TypeError('"ref_ans" must be a string instance')
        if len(ref_ans) > self.MAX_ANS_LENGTH:
            raise self.TaskRefAnsError('Too long reference answer for a task')
        if len(ref_ans) == 0:
            raise self.TaskRefAnsError('Task reference answer must not be empty')
        self.ref_ans = ref_ans

    def set_name(self, name: str) -> None:
        if not isinstance(name, str):
            raise TypeError('"name" must be a string instance')
        if len(name) > self.MAX_NAME_LENGTH:
            raise self.TaskNameError('Too long name for a task')
        if len(name) == 0:
            raise self.TaskNameError('Task name must not be empty')
        if (re.search(r'<([A-Za-z][A-Za-z0-9]*)(([^>])|(\n))*>(((.)|(\n))*)</\1>', name)
                != None):
            raise self.TaskNameError('Task name must not contain html')
        # now name is ok: not empty plaintext that fits in MAX_NAME_LENGTH.
        self.name = name

    def set_text(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError('"text" must be a string instance')
        if len(text) > self.MAX_TEXT_LENGTH:
            raise self.TaskTextError('Too long text for a task')
        if len(text) == 0:
            raise self.TaskTextError('Task text must not be empty')
        if (re.search(r'<(script)(([^>])|(\n))*>(((.)|(\n))*)</\1>', text)
                != None):
            raise self.TaskTextError('Task text must not contain script')
        html_parser = HTMLParser(strict=True)
        try:
            html_parser.parse('<!DOCTYPE html><html>' + text +' </html>')
        except html5parser.ParseError as e:
            raise self.TaskTextError('HTML error: {err}'.format(err=repr(e)))
        self.text = text

    def get_test_ids(self) -> list[int]:
        return self.tests

    def get_tests(self) -> list[Test]:
        ids_list = self.get_test_ids()
        tests_list: list[Test] = []
        for id in ids_list:
            tests_list.append(Test.objects.get(id=id))
        return tests_list

    def append_test(self, test_id: int) -> None:
        ids_list = self.get_test_ids()
        ids_list.append(test_id)
        self.tests = ids_list


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

    MAX_NAME_LENGTH = 128
    id : models.IntegerField = models.IntegerField(primary_key=True, unique=True)
    tasks: models.JSONField = models.JSONField(default=list)
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
        for contest in Contest.objects.all():
            if contest.name == name:
                raise self.ContestNameError('Contest name must be unique')
        self.name = name

    def get_task_ids(self) -> list[int]:
        return self.tasks

    def get_tasks(self) -> list[Task]:
        ids_list = self.get_task_ids()
        tasks_list: list[Task] = []
        for id in ids_list:
            tasks_list.append(Task.objects.get(id=id))
        return tasks_list

    def append_task(self, task_id: int) -> None:
        ids_list = self.get_task_ids()
        ids_list.append(task_id)
        self.tasks = ids_list
