from collections import defaultdict, deque

def build_execution_order(steps):
    graph = defaultdict(list)
    in_degree = defaultdict(int)

    step_map = {step.name: step for step in steps}

    for step in steps:
        for dep in step.depends_on:
            graph[dep].append(step.name)
            in_degree[step.name] += 1
    
    queue = deque()

    for step in steps:
        if in_degree[step.name] == 0:
            queue.append(step.name)

    order = []

    while queue:
        current = queue.popleft()
        order.append(step_map[current])

        for neighbor in graph[current]:
            in_degree[neighbor] -= 1

            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(order) != len(steps):
        raise Exception("Cycle detected in pipeline DAG")

    return order