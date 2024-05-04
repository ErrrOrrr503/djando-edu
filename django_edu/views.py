from django.shortcuts import render
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse


def index(request: HttpRequest) -> HttpResponse:
    return render(request, "index.html")

g_tasks = [ "case1", "case2" ]
def tasks(request: HttpRequest, task_num: int = 0) -> HttpResponse:
    context = {}
    if not request.session.get('task_num'):
        request.session['task_num'] = 1
    if task_num != 0:
        request.session['task_num'] = task_num
    cur_active = request.session.get('task_num') or 1
    context["task_active_list"] = [ "active" if cur_active == (task_idx + 1) else "" for task_idx in range(len(g_tasks)) ]
    context["task_name"] = [g_tasks[cur_active - 1]]
    return render(request, "tasks.html", context=context)