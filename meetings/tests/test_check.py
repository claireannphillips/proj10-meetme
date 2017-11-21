from flask_main import check
import nose


def testing ():
    
    #testing for no events
    
    events = []
    start = "2017-01-01T00:00:00+00:00"
    end = "2017-02-01T00:00:00+00:00"
    result = check(events, start, end)
    assert result == "no events"

def test_ing ():
    #checking for only one event
    events = [{'summary': 'event', 'start': {'dateTime': "2017-02-01T00:00:00+00:00"}, 'end': {'dateTime': "2017-02-02T00:00:00+00:00"}}]
    start = "2017-01-31T00:00:00+00:00"
    end = "2017-02-15T00:00:00+00:00"
    result = check(events, start, end)
    assert result != []
               
def test ():
    #testing transparency 
    events = [{'transparency': 'transparent', 'summary': 'not busy'}]
    start = "2017-01-31T00:00:00+00:00"
    end = "2017-02-15T00:00:00+00:00"
    result = check(events, start, end)
    assert result == []
                                             



