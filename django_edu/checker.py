"""
Checker that checks task's solutions
"""

import subprocess
from typing import Tuple
from django.utils.translation import gettext as _

from django_edu.models import Task
from django_edu.models import Test

class Checker:
    report: str

    def __init__(self) -> None:
        """ TODO: create isolated env? """

    def check(self, task: Task, ans: str) -> bool:
        if task.ans_type == Task.AnsType.text:
            # None in ref_ans is impossible by Task design
            passed = (ans.strip() == task.ref_ans.strip()) # type: ignore[union-attr]
            if passed == True:
                self.report = _('Passed')
            else:
                self.report = _('Failed')
            return passed
        elif task.ans_type == Task.AnsType.code:
            passed = True
            summary = ''
            num_failed = 0
            for test_num, test_id in enumerate(task.tests):
                test = Test.objects.get(id=test_id)
                summary += _('Test {n}: ').format(n=test_num + 1)
                test_passed, received, expected = self.run_code_test(ans, test)
                if test_passed == True:
                    summary += _('OK\n')
                else:
                    summary += _('FAIL\n')
                    passed = False
                    num_failed += 1
            if passed == True:
                self.report = (_('Passed') + '\n\n' +
                               str(len(task.tests)) + _(' tests passed'))
            else:
                self.report = (_('Failed') + '\n\n' +
                               str(num_failed) + _(' out of ') +
                               str(len(task.tests)) + _(' tests failed:\n') +
                               summary)
        return passed


    def run_code_test(self, code: str, test: Test) -> Tuple[bool, str, str]:
        timedout = False
        proc = subprocess.Popen(args=['python3', '-c', code], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            out, err = proc.communicate(input=test.test_input.encode('utf-8'), timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            timedout = True
        out_str = out.decode('utf-8')
        status = (out_str == test.test_output) and not timedout
        if timedout == True:
            out_str += _('\nTimed out...')
        return status, out_str, test.test_output
