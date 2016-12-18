# AoikLiveReload
Detect module file changes and reload the program.

Tested working with:
- Python 2.7, 3.5

Demos:
- [Bottle](/src/aoiklivereload/demo/bottle_demo.py)
- [Flask](/src/aoiklivereload/demo/flask_demo.py)
- [Sanic](/src/aoiklivereload/demo/sanic_demo.py)
- [Tornado](/src/aoiklivereload/demo/tornado_demo.py)

## Table of Contents
- [Setup](#setup)
  - [Setup via pip](#setup-via-pip)
  - [Setup via git](#setup-via-git)
- [Usage](#usage)

## Setup
- [Setup via pip](#setup-via-pip)
- [Setup via git](#setup-via-git)

### Setup via pip
Run:
```
pip install AoikLiveReload
```

### Setup via git
Run:
```
git clone https://github.com/AoiKuiyuyou/AoikLiveReload

cd AoikLiveReload

python setup.py install
```

## Usage
Add the 3 lines to your code:
```
# Import reloader class
from aoiklivereload import LiveReloader

# Create reloader
reloader = LiveReloader()

# Start watcher thread
reloader.start_watcher_thread()
```

Now when there is a module file change, the program will be reloaded.
