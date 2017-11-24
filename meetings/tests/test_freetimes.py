import nose 
from freeTimes import availability, free_times


def test_empty():
    # Should return an empty list
    start = "2017-03-01T00:00:00+00:00"
    end = "2016-03-01T00:00:00+00:00"
    section = availability(start, end)
    assert section == []
    
def test_one_day():
    # check for one day
    start = "2017-02-02T09:00:00+00:00"
    end = "2017-02-02T17:00:00+00:00"
    section = availability(start, end)
    assert len(section) == 1
    
    
def test_week():
    # testing for a week
    start = "2017-01-01T00:00:00+00:00"
    end = "2017-01-07T17:00:00+00:00"
    section = availability(start, end)
    assert len(section) == 7



def test_month():
    # testing for a month
    start = "2017-01-01T00:00:00+00:00"
    end = "2017-01-20T17:00:00+00:00"
    blocks = availability(start, end)
    assert len(blocks) == 20
    
#TEST FREE_TIMES

def test_no_busy_times():
    # Making sure a whole block is free so no busy times
    busy = []
    section = {'start': '2017-11-24T09:00:00-08:00', 'end': '2017-11-24T17:00:00-08:00'}
    free_list = free_times(section, busy)
    assert len(free_list) == 1

    

def test_free_times():
    busy = [{'start': '2017-11-24T09:00:00-08:00', 'end': '2017-11-24T10:00:00-08:00'},
            {'start': '2017-11-24T11:00:00-08:00', 'end': '2017-11-24T14:00:00-08:00'}]

    section = {'start': '2017-11-24T08:00:00-08:00', 'end': '2017-11-24T17:00:00-08:00'}
    free_list = free_times(section, busy)
    assert len(free_list) == 3  
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    