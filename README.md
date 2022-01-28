## NUjij Comments Web & IRC Live Feed

Tracks *all* comments posted on `nu.nl` and forwards them to an IRC channel, hilarity ensues.

This package consists of (all in one):

- a web application
- an IRC bot
- `nu.nl` comment monitor
- straattaal translator

## Install

```bash
virtualenv -p /usr/bin/python3 venv
source venv/bin/activate
pip install -r requirements.txt
python3 setup.py develop

cp settings.py_example settings.py
# make changes to settings.py

python3 run.py
```

## IRC

![https://i.imgur.com/Llueens.png](https://i.imgur.com/Llueens.png)

## CLI

`single.py` is a minimal example of how to get a stream of comments in the terminal, given an article id.
