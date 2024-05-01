from django.shortcuts import render
from django.core.cache import cache


def index(request):
    return render(request, "index.html")

g_tasks = [ "case1", "case2" ]
def tasks(request, task_num = 0):
    context = {}
    if not request.session.get('task_num'):
        request.session['task_num'] = 1
    if task_num != 0:
        request.session['task_num'] = task_num
    cur_active = request.session.get('task_num')
    context["task_active_list"] = [ "active" if cur_active == (task_idx + 1) else "" for task_idx in range(len(g_tasks)) ]
    context["task_name"] = g_tasks[cur_active - 1]
    return render(request, "tasks.html", context=context)