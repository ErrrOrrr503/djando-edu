"""
Checker that checks task's solutions
"""

import subprocess
from typing import Tuple
from abc import ABC, abstractmethod
from django.utils.translation import gettext as _

from django_edu.models import Task
from django_edu.models import Test


class AbstractTemplate(ABC):
    """
    Interface for a template.
    A template is some info that can be represented in different ways.
    Methods here define these ways.
    """
    @abstractmethod
    def to_html(self) -> str:
        """ Return html representation """


class TemplateGlobalStatus(AbstractTemplate):
    """ A template for overall status of a task check. """
    succeeded: bool
    tests_amount: int
    passed_amount: int

    def __init__(self, succeded: bool, tests_amount: int = -1, passed_amount: int = -1):
        self.succeeded = succeded
        self.passed_amount = passed_amount
        self.tests_amount = tests_amount

    def to_html(self) -> str:
        res = ''
        if self.succeeded is True:
            res += _('<p><strong>Passed!</strong></p>')
        else:
            res += _('<p><strong>Failed!</strong></p>')
        if self.tests_amount >= 0:
            res += _('<p>{passed} tests out of {total} passed.</p>').format(
                passed=self.passed_amount,
                total=self.tests_amount
            )
        return res


class TemplateTestStatus(AbstractTemplate):
    """ A template for a single test status. """
    succeeded: bool
    test_num: int

    def __init__(self, succeded: bool, test_num: int):
        self.succeeded = succeded
        self.test_num = test_num

    def to_html(self) -> str:
        if self.succeeded is True:
            return _(
                '<div class="container d-flex">'
                '   <div>Test {n}: </div>'
                '   <div class="text-ok">OK</div>'
                '</div>'
            ).format(n=self.test_num)
        return _(
            '<div class="container d-flex">'
            '   <div>Test {n}: </div>'
            '   <div class="text-fail">FAIL</div>'
            '</div>'
        ).format(n=self.test_num)


class TemplateTestReport(AbstractTemplate):
    """ A template for a test verbose report. """
    test: Test
    received_output: str

    def __init__(self, test: Test, received_output: str):
        self.test = test
        self.received_output = received_output

    def to_html(self) -> str:
        return _(
            '<table class="table table-sm table-bordered-black">'
            '   <thead class="table-bordered-black">'
            '       <tr class="table-bordered-black">'
            '           <th class="table-bordered-black" scope="col">Received</th>'
            '           <th class="table-bordered-black" scope="col">Expected</th>'
            '       </tr>'
            '   </thead>'
            '   <tbody class="table-bordered-black">'
            '   <tr class="table-bordered-black">'
            '       <td class="table-bordered-black">'
            '           <span class="test-io-full multiline-text">{received}</span>'
            '       </td>'
            '       <td class="table-bordered-black">'
            '           <span class="test-io-full multiline-text">{expected}</span>'
            '       </td>'
            '   </tr>'
            '   </tbody>'
            '</table>'
        ).format(received=self.received_output,
                 expected=self.test.test_output)


class Checker:
    """
    Utility for checking a task answer, running tests and reporting check status.

    Attributes
    ----------
    report : list[AbstractTemplate]
        Report about check process in form of a list of templates.
    """
    class CheckerAnsException(ValueError):
        """ Provide ability to detect specific error """

    report: list[AbstractTemplate]

    def __init__(self) -> None:
        # FEATURE: create isolated env?
        # or leave creation to run_code_test method
        self.report = []

    def html_report(self) -> str:
        """ generate html report from templates (report attr). """
        res = ''
        for template in self.report:
            res += template.to_html() + '\n'
        return res

    def check(self, task: Task, ans: str) -> bool:
        """ Check if ans for the task is correct. """
        if len(ans) == 0:
            raise self.CheckerAnsException(_('Answer for a task must not be empty'))
        if task.ans_type == Task.AnsType.text:
            # None in ref_ans is impossible by Task design
            passed = (ans.strip() == task.ref_ans.strip())  # type: ignore[union-attr]
            self.report.append(TemplateGlobalStatus(passed))
        elif task.ans_type == Task.AnsType.code:
            passed = True
            num_failed = 0

            for test_num, test_id in enumerate(task.tests):
                test = Test.objects.get(id=test_id)
                test_passed, received, expected = self.run_code_test(ans, test)
                self.report.append(TemplateTestStatus(test_passed, test_num + 1))
                if test_passed is False:
                    passed = False
                    num_failed += 1
                    # FEATURE: open and closed tests
                    self.report.append(TemplateTestReport(test, received))

            self.report.insert(0, TemplateGlobalStatus(passed,
                                                       len(task.tests),
                                                       len(task.tests) - num_failed))
        return passed

    def run_code_test(self, code: str, test: Test) -> Tuple[bool, str, str]:
        """
        Run test code.
        This functionality is in fact DEMO, as code is run under the server's privileges
        and in the server's environment which can lead to dramatic damage.
        TODO: isolated env with limited privileges (unprivileged user in a container).
        FEATURE: other languages besides Python.
        """
        timedout = False
        status = False
        with (subprocess.Popen(args=['python3', '-c', code],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)) as proc:
            try:
                out, err = proc.communicate(input=test.test_input.encode('utf-8'),
                                            timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
                timedout = True
            out_str = out.decode('utf-8').strip()
            if (out_str == test.test_output.strip()) and not timedout:
                status = True
            if timedout is True:
                out_str += _('\nTimed out...')
            return status, out_str, test.test_output.strip()
