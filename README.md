# polygon-py

[![PyPI](https://img.shields.io/pypi/v/polygon_api)](https://pypi.org/project/polygon_api/)

Python wrapper for the [Polygon](https://polygon.codeforces.com) API.

## Installation

The package is on [PyPI](https://pypi.org/project/polygon_api/):

```sh
pip install polygon_api
```

## Usage

Create an API key in Polygon (Settings → API Keys) and pass it to `Polygon`:

```python
from polygon_api import Polygon

polygon = Polygon('https://polygon.codeforces.com/api', 'API_KEY', 'API_SECRET')

for problem in polygon.problems_list():
    print(problem.id, problem.name)

problem = polygon.problems_list(id=123456)[0]
info = problem.info()
print(info.time_limit, info.memory_limit)
for solution in problem.solutions():
    print(solution.name, solution.tag)
```

Each API method is available on `Polygon` (`polygon.problem_solutions(problem_id)`) and on the `Problem`
objects it returns (`problem.solutions()`). The full API reference is at
[codeforces.github.io/polygon-misc/API](https://codeforces.github.io/polygon-misc/API).
