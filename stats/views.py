import collections

import numpy as np
from django.db.models import F
from django.db.models.functions import Coalesce
from django.shortcuts import render

from stats.models import Actor


def index(request):
    dates = Actor.objects.annotate(
        date=Coalesce(F("indexed_at__date"), F("created_at__date"))
    ).values_list(
        "date", flat=True
    )

    counter = collections.Counter(dates)
    counter = dict(counter)
    counter = collections.OrderedDict(sorted(counter.items()))

    dates = [date.strftime("%Y-%m-%d") for date in counter.keys()]
    absolute_freq = counter.values()
    cumulative_freq = np.cumsum(list(counter.values()))

    return render(request, "index.html", context={
        "absolute_freq": list(zip(dates, absolute_freq)),
        "cumulative_freq": list(zip(dates, cumulative_freq)),
    })
