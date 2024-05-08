from typing import Any

from django.shortcuts import render
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.utils.translation import gettext as _

from django_edu.models import Contest
from django_edu.models import Task


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "index.html")

def contests(request: HttpRequest) -> HttpResponse:
    context: dict[str, Any] = {}
    #context["user_is_admin"] = True if request.session.get('user_is_admin') else False
    context["user_is_admin"] = True

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
            except Exception as e:
                raise RuntimeError("Contest name checker is broken")
        elif contest_to_remove_id_str:
            # process contest deletion
            Contest.objects.get(id=int(contest_to_remove_id_str)).delete()

    context["contest_list"] = []
    for contest in Contest.objects.all():
        context["contest_list"].append((contest.id, contest.name))
    if len(context["contest_list"]) == 0:
        context["contest_list_is_empty"] = True
    return render(request, "contests.html", context=context)

"""
        task_num of the task in a contest. Is displayed to human!
        That means starts from 1. 0 is reserved value for default
        task in a contest (i.e. last unsolved, first, saved, etc).
"""
def tasks(request: HttpRequest, contest_id: int, task_num: int = 0) -> HttpResponse:
    context: dict[str, Any] = {}
    #context["user_is_admin"] = True if request.session.get('user_is_admin') else False
    context["user_is_admin"] = True
    context['ans_is_text'] = True

    try:
        contest = Contest.objects.get(id=contest_id)
    except:
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
            elif ans_type == 'code_ans':
                context['ans_is_code'] = True
                context['ans_is_text'] = False
        elif form_descr == 'task_data':
            task_name = request.POST.get('new_task_name') or ''
            task_text = request.POST.get('new_task_text') or ''
            task_ref_ans = request.POST.get('new_task_ref_ans') or ''
            try:
                new_task = Task()
                new_task.set_name(task_name)
                new_task.set_text(task_text)
                if request.POST.get('ans_is_text'):
                    new_task.set_ref_ans(task_ref_ans)
                new_task.save()
                contest.append_task(new_task.id)
                contest.save()
            except Task.TaskNameError as e:
                context['task_name_error'] = str(e)
            except Task.TaskTextError as e:
                context['task_text_error'] = str(e)
            except Task.TaskRefAnsError as e:
                context['task_ref_ans_error'] = str(e)
            except Exception as e:
                raise RuntimeError("Task __init__ (args validators) is broken")
        elif form_descr == 'task_delete':
            task_id = int(request.POST.get('task_to_delete_id'))
            Task.objects.get(id=task_id).delete()
            contest.delete_task(task_id)
            contest.save()

    # init dictionary for saved task nums.
    if not request.session.get('saved_task_nums'):
        request.session['saved_task_nums'] = {contest_id: 0}
    saved_task_nums = request.session.get('saved_task_nums')
    if not isinstance(saved_task_nums, dict):
        raise RuntimeError('"saved_task_nums" session var must be dict[contest_id:task_num], but it is {type}'.format(type=type(saved_task_nums)))
    if not saved_task_nums.get(contest_id):
        saved_task_nums[contest_id] = 0

    if task_num != 0:
        saved_task_nums[contest_id] = task_num
    cur_active = saved_task_nums[contest_id] or 1

    tasks = contest.get_tasks()
    context['task_active_list'] = [ 'active' if cur_active == (task_idx + 1) else '' for task_idx in range(len(tasks)) ]
    if len(context["task_active_list"]) == 0:
        context['task_active_list_is_empty'] = True
    else:
        context['task_name'] = tasks[cur_active - 1].name
        context['task_text'] = tasks[cur_active - 1].text
        context['task_id'] = tasks[cur_active - 1].id
    return render(request, "tasks.html", context=context)