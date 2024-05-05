from typing import Any

from django.shortcuts import render
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound

from django_edu.models import Contest
from django_edu.models import Task


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "index.html")

def contests(request: HttpRequest) -> HttpResponse:
    context: dict[str, Any] = {}
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

    context["user_is_admin"] = True if request.session.get('user_is_admin') else False
    #context["user_is_admin"] = True
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
    contest = Contest.objects.get(id=contest_id)
    if not contest:
        return HttpResponseNotFound("<h1>Contest not found</h1>")

    context: dict[str, Any] = {}
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
    context["task_active_list"] = [ "active" if cur_active == (task_idx + 1) else "" for task_idx in range(len(tasks)) ]
    if len(context["task_active_list"]) == 0:
        context["task_active_list_is_empty"] = True
    else:
        context["task_name"] = tasks[cur_active - 1].name
        context["task_text"] = tasks[cur_active - 1].text
    return render(request, "tasks.html", context=context)