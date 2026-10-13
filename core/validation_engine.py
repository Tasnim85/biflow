"""Recalculate final BI gates from controlled execution evidence."""
def readiness_gates(cleaning, before, threshold):
    return {name:{'score':item['after']['score'],'threshold':threshold,
        'ready_for_bi':item['after']['score']>=threshold and item['after']['invalid_cells']==0 and item['after']['duplicate_rows']==0,
        'remaining_missing':item['after']['missing_cells'],
        'score_delta':round(item['after']['score']-before[name]['score'],2),
        'meaning':'Readiness is a configured demo quality gate, not a guarantee of business correctness. Missing values are disclosed.'}
        for name,item in cleaning.items()}
