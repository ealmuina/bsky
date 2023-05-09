import collections

import numpy as np
from django.shortcuts import render

from stats.models import Actor


def index(request):
    actors = Actor.objects.values(
        "created_at__date", "updated_at__date", "active"
    )
    counter = {}

    for actor_data in actors:
        if actor_data["active"]:
            date = actor_data["created_at__date"]
            delta = 1
        else:
            date = actor_data["updated_at__date"]
            delta = -1

        counter.setdefault(date, 0)
        counter[date] += delta

    counter = collections.OrderedDict(sorted(counter.items()))

    dates = [date.strftime("%Y-%m-%d") for date in counter.keys()]
    absolute_freq = counter.values()
    cumulative_freq = np.cumsum(list(counter.values()))

    return render(request, "index.html", context={
        "absolute_freq": list(zip(dates, absolute_freq)),
        "cumulative_freq": list(zip(dates, cumulative_freq)),
    })
