# minimal metrics placeholder
metrics = {'locks_acquired': 0, 'queue_push': 0, 'queue_pop': 0}
def incr(key):
    metrics.setdefault(key,0)
    metrics[key]+=1
