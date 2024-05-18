"""
Django's views mechanism: generating html based on templates.
"""
from typing import Any

from django.shortcuts import render
from django.http import (HttpRequest,
                         HttpResponse,
                         HttpResponseNotFound,
                         HttpResponseRedirect)
from django.utils.translation import gettext as _
from django.contrib import auth

from django_edu.models import Contest
from django_edu.models import Task
from django_edu.models import Test
from django_edu.checker import Checker

def handle_misc_actions(request: HttpRequest) -> None:
    """
    Basically, base_page actions handler.
    Must be called at beginning of each view before context init.
    """
    if request.method == "POST":
        action = request.POST.get('misc_action')
        if action == 'logout':
            auth.logout(request)

def init_login_context(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """
    Init context part, that describes login details.
    Must be called in all views.
    """
    if request.user.is_authenticated:
        context['user_logged_in'] = True
        context['user_login'] = request.user.username
        context['user_is_admin'] = request.user.groups.filter(name='teachers')
    return context

def index(request: HttpRequest) -> HttpResponse:
    """ Index page. """
    handle_misc_actions(request)
    context: dict[str, Any] = {}
    context = init_login_context(request, context)
    return render(request, "index.html", context=context)

def login(request: HttpRequest) -> HttpResponse:
    """ Login page. """
    handle_misc_actions(request)
    context: dict[str, Any] = {}
    context = init_login_context(request, context)

    if request.method == 'GET':
        # on GET - save prev page, on POST use
        login_prev_page = request.META.get('HTTP_REFERER', '/')
        request.session['login_prev_page'] = login_prev_page

    if request.method == 'POST':
        login_prev_page = request.session.get('login_prev_page')
        username = request.POST.get('login')
        password = request.POST.get('password')
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return HttpResponseRedirect(login_prev_page)
        context['auth_error'] = True
    return render(request, "login.html", context=context)

def contests(request: HttpRequest) -> HttpResponse:
    """ Contests page. Here user choses a contest"""
    handle_misc_actions(request)
    context: dict[str, Any] = {}
    context = init_login_context(request, context)

    if request.method == "POST":
        new_contest_name = request.POST.get('new_contest_name')
        contest_to_remove_id_str = request.POST.get('delete_contest')
        if new_contest_name:
            # process adding contest
            try:
                new_contest = Contest()
                new_contest.set_name(new_contest_name)
                new_contest.save()
            except Contest.ContestNameError as e:
                context['contest_name_error'] = str(e)
        elif contest_to_remove_id_str:
            # process contest deletion
            Contest.objects.get(id=int(contest_to_remove_id_str)).delete()

    context["contest_list"] = []
    for contest in Contest.objects.all():
        context["contest_list"].append((contest.id, contest.name))
    if len(context["contest_list"]) == 0:
        context["contest_list_is_empty"] = True
    return render(request, "contests.html", context=context)

def tasks(request: HttpRequest, contest_id: int, task_num: int = 0) -> HttpResponse:
    """ Tasks page. Represents selected contest. """
    handle_misc_actions(request)
    context: dict[str, Any] = {}
    context = init_login_context(request, context)
    context['ans_is_text'] = request.session.get('ans_is_text')
    context['ans_is_code'] = request.session.get('ans_is_code')
    if context['ans_is_text'] is None:
        context['ans_is_text'] = True
    if context['ans_is_code'] is None:
        context['ans_is_code'] = False

    try:
        contest = Contest.objects.get(id=contest_id)
    except Exception:
        contest = None
    if not contest:
        return HttpResponseNotFound(_('<h1>Contest not found</h1>'))

    if request.method == "POST":
        form_descr = request.POST.get('form_descr')
        if form_descr == 'task_type':
            ans_type = request.POST.get('ans_type')
            if ans_type == 'text_ans':
                context['ans_is_text'] = True
                context['ans_is_code'] = False
                request.session['ans_is_text'] = True
                request.session['ans_is_code'] = False
            elif ans_type == 'code_ans':
                context['ans_is_code'] = True
                context['ans_is_text'] = False
                request.session['ans_is_text'] = False
                request.session['ans_is_code'] = True
        elif form_descr == 'task_data':
            task_name = request.POST.get('new_task_name') or ''
            task_text = request.POST.get('new_task_text') or ''
            task_ref_ans = request.POST.get('new_task_ref_ans') or ''
            try:
                new_task = Task()
                new_task.set_name(task_name)
                new_task.set_text(task_text)
                if request.POST.get('ans_is_text') is not None:
                    new_task.set_ref_ans(task_ref_ans)
                new_task.linked_contest = contest
                new_task.save()
                contest.append_task(new_task.id)
                contest.save()
            except Task.TaskNameError as e:
                context['task_name_error'] = str(e)
            except Task.TaskTextError as e:
                context['task_text_error'] = str(e)
            except Task.TaskRefAnsError as e:
                context['task_ref_ans_error'] = str(e)
        elif form_descr == 'task_delete':
            task_id_str = request.POST.get('task_to_delete_id')
            if task_id_str is None:
                raise RuntimeError('HTML Template is broken')
            task_id = int(task_id_str)
            Task.objects.get(id=task_id).delete()
            contest.delete_task(task_id)
            contest.save()
            return HttpResponseRedirect(request.path.rsplit('/', 1)[0])
        elif form_descr == 'task_ans':
            task_id_str = request.POST.get('task_ans_id')
            task_ans = request.POST.get('task_ans')
            if task_id_str is None or task_ans is None:
                raise RuntimeError('HTML Template is broken')
            task_id = int(task_id_str)
            task = Task.objects.get(id=task_id)
            try:
                checker = Checker()
                context['ans_is_correct'] = checker.check(task, task_ans)
                context['ans_report'] = checker.html_report()
            except Checker.CheckerAnsException as e:
                context['ans_error'] = str(e)

    # init dictionary for saved task nums.
    if not request.session.get('saved_task_nums'):
        request.session['saved_task_nums'] = {contest_id: 0}
    saved_task_nums = request.session.get('saved_task_nums')
    if not isinstance(saved_task_nums, dict):
        raise RuntimeError(
            '"saved_task_nums" session var must be dict[contest_id:task_num],'
            f' but it is {type(saved_task_nums)}'
        )
    if not saved_task_nums.get(contest_id):
        saved_task_nums[contest_id] = 0

    if task_num > 0:
        saved_task_nums[contest_id] = task_num
    cur_active = saved_task_nums[contest_id] or 1

    tasks_list = contest.get_tasks()
    context['task_active_list'] = [
        'active' if cur_active == (task_idx + 1)
        else '' for task_idx in range(len(tasks_list))
    ]
    if len(context["task_active_list"]) == 0:
        context['task_active_list_is_empty'] = True
    else:
        context['task_name'] = tasks_list[cur_active - 1].name
        context['task_text'] = tasks_list[cur_active - 1].text
        context['task_id'] = tasks_list[cur_active - 1].id
        context['task_ans_type'] = tasks_list[cur_active - 1].ans_type
    return render(request, "tasks.html", context=context)


def tests(request: HttpRequest, task_id: int) -> HttpResponse:
    """ Tests for a task editing page. """
    handle_misc_actions(request)
    context: dict[str, Any] = {}
    context = init_login_context(request, context)

    try:
        task = Task.objects.get(id=task_id)
    except Exception:
        task = None
    if not task:
        return HttpResponseNotFound(_('<h1>Task not found</h1>'))
    context['task_text'] = task.text
    context['task_name'] = task.name

    if request.method == 'GET':
        # on GET - save prev page, on POST use
        tests_prev_page = request.META.get('HTTP_REFERER', '/')
        request.session['tests_prev_page'] = tests_prev_page

    if request.method == 'POST':
        tests_prev_page = request.session.get('tests_prev_page')
        form_descr = request.POST.get('form_descr')
        if form_descr == 'test_delete':
            test_to_delete_num_str = request.POST.get('test_to_delete_num')
            if test_to_delete_num_str is None:
                raise RuntimeError('HTML Template is broken')
            test_to_delete_ind = int(test_to_delete_num_str) - 1
            test_to_delete_id = task.tests[test_to_delete_ind]
            Test.objects.get(id=test_to_delete_id).delete()
            task.delete_test(test_to_delete_id)
            task.save()
        if form_descr == 'test_add':
            new_test_input = request.POST.get('new_test_input') or ''
            new_test_output = request.POST.get('new_test_output') or ''
            try:
                new_test = Test()
                new_test.set_input(new_test_input)
                new_test.set_output(new_test_output)
                new_test.linked_task = task
                new_test.save()
                task.append_test(new_test.id)
                task.save()
            except Test.TestOutputError as e:
                context['test_output_error'] = str(e)
            except Test.TestInputError as e:
                context['test_input_error'] = str(e)
        if form_descr == 'test_editing_finished':
            return HttpResponseRedirect(tests_prev_page)

    tests_list: list[Test] = []
    for test in task.get_tests():
        tests_list.append(test)
    context['tests_list'] = tests_list

    return render(request, "tests.html", context=context)
