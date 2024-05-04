"""
Model that represents an educational task
"""

from django.db import models
from html5lib import HTMLParser, html5parser
import re
import json

from django_edu.models.test import Test


class Task(models.Model):
    """
    Model representing a task.

    Attributes
    ----------
    MAX_NAME_LENGTH : int
        Name length constraint
    MAX_TEXT_LENGTH : int
        Text (task condition) length constraint.
    pk : models.IntegerField
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
        list of tests pk-s.
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

    MAX_NAME_LENGTH = 256
    MAX_TEXT_LENGTH = 1000
    MAX_ANS_LENGTH = 256
    pk : models.IntegerField = models.IntegerField(primary_key=True, unique=True)
    name: models.CharField = models.CharField(max_length=MAX_NAME_LENGTH)
    text: models.TextField = models.TextField(max_length=MAX_TEXT_LENGTH)
    ans_type: models.CharField = models.CharField(max_length=1,
                                                  choices=AnsType.choices,
                                                  default=AnsType.text)
    ref_ans: models.CharField = models.CharField(max_length=MAX_ANS_LENGTH, null=True)
    tests: models.JSONField = models.JSONField(default=lambda: [], null=True)

    def __init__(self, name: str, text: str, ans_type: Task.AnsType, ref_ans: str | None = None):
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

    def get_test_pks(self) -> list[int]:
        return json.loads(self.tests)

    def get_tests(self) -> list[Test]:
        pks_list = self.get_test_pks()
        tests_list: list[Test] = []
        for pk in pks_list:
            tests_list.append(Test.objects.get(pk=pk))
        return tests_list

    def append_test(self, test_pk: int) -> None:
        pks_list = self.get_test_pks()
        pks_list.append(test_pk)
        self.tests = json.dumps(pks_list)