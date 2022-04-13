from mqtt_kube.binding.valuemap import ValueMap

class TestTopicMatcher:
    def test_miss(self):
        v = ValueMap({
            'map': {
                None: 1,
            }
        })
        assert v.lookup(2) == None

    def test_basic(self):
        v = ValueMap({
            'map': {
                None: "BUSY",
                1: "DONE"
            }
        })
        assert v.lookup(None).value == "BUSY"
        assert v.lookup(1).value == "DONE"

    def test_predicate(self):
        v = ValueMap({
            'map': {
                "lambda v: v >= 0": "+",
                "lambda v: v < 0": "-",
            }
        })
        assert v.lookup(5).value == "+"
        assert v.lookup(-3).value == "-"

    def test_fstring(self):
        v = ValueMap({
            'map': {
                "A": "Alpha {input}",
                "B": "Bravo {input}",
            }
        })
        assert v.lookup('A').value == "Alpha A"
        assert v.lookup('B').value == "Bravo B"

    def test_regex(self):
        v = ValueMap({
            'map': {
                "re:(?P<first>.*) (?P<last>.*)": "{input}: [{first}] ({last})",
            }
        })
        assert v.lookup('Mr X').value == "Mr X: [Mr] (X)"

    def test_jsonpath(self):
        v = ValueMap({
            'jsonpath': '$.key'
        })
        assert v.lookup('{"key": "value"}').value == "value"

    def test_jsonpath_map(self):
        v = ValueMap({
            'jsonpath': '$.action',
            'map': {
                'RUN': 'launch',
            }
        })
        assert v.lookup('{"action": "RUN"}').value == "launch"

    def test_format(self):
        v = ValueMap({
            'map': {
                'lambda v: True': '{value:.3f}'
            }
        })
        assert v.lookup(1/3).value == "0.333"
