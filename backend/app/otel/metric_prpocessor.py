import logging

logger = logging.getLogger(__name__)


def proces_metrics_reqeust(request) -> int:
    count = 0
    for resource_metrics in request.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            count += len(scope_metrics.metrics)
    return count
