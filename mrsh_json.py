from flask.json import JSONEncoder
import json as _json


class MyEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, 'to_dict'):
            return o.to_dict
        return super().default(o)


def loads(obj, **kwargs):
    return _json.loads(obj, **kwargs)


def dumps(obj, **kwargs):
    return _json.dumps(obj, cls=MyEncoder, **kwargs)
