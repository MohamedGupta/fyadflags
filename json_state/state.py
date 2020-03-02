from collections import defaultdict
import json
import pickle


LOCALSTATE = "fyadflags.json"


def load():
    try:
        return json.load(open(LOCALSTATE, "r"))
    except Exception:
        return defaultdict(dict)


def save(state):
    with open(LOCALSTATE, "w") as statefile:
        statefile.write(json.dumps(state, indent=2))


def pickle_put(key, value):
    pickle.dump(value, open(f"{key}.p", "wb"))


def pickle_get(key, default=None):
    try:
        return pickle.load(open(f"{key}.p", "rb"))
    except Exception:
        return default


def put(key, value):
    state = load()
    state[key] = value
    save(state)


def pop(key):
    state = load()
    value = state.pop(key)
    save(state)
    return value


def get(key, default=None):
    state = load()
    return state.get(key, default)
