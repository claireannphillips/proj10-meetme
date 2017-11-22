import arrow

import flask
import logging
import config
if __name__ == "__main__":
    CONFIG = config.configuration()
else:
    CONFIG = config.configuration(proxied=True)

app = flask.Flask(__name__)
app.debug=CONFIG.DEBUG
app.logger.setLevel(logging.DEBUG)
app.secret_key=CONFIG.SECRET_KEY


def availability(starttime, endtime):
    '''
    Gets the avaliable times from a calendar.
    '''
    freeblocks = []
    
    start = arrow.get(starttime)
    end = arrow.get(endtime)
    endtime_hour = int(end.format("H"))
    endtime_min = int(end.format("m"))
    
    curdate = start
    while curdate <= end:
        temp = curdate.replace(hour=endtime_hour, minute=endtime_min)
        
        freeblocks.append(
            {
                "start": curdate.isoformat(),
                "end": temp.isoformat()
            })
        curdate = curdate.shift(days=+1)
    app.logger.debug(freeblocks)    
    return freeblocks
    

def free_times(freeblock, busytimes):
    '''
    Takes the avaliable times from the avaliability function and tests the different edge cases
    to find the avalible times between the busy times.
    '''
    freetimes_in_block = []
    
    app.logger.debug("freeblock:{}".format(freeblock))
    freeblockstart = freeblock['start']
    freeblockend = freeblock['end']
    #app.logger.debug("busytimes:{}".format(busytimes))
    
    for event in busytimes:
        app.logger.debug("EVENT:{}".format(event))
        
        eventstart = event['start']
        eventend =event['end']
        
        # Case F
        if (eventstart <= freeblockstart) and (eventend >= freeblockend):
            app.logger.debug("CASE F")
            return freetimes_in_block
        # Case B
        elif (eventstart <= freeblockstart) and (eventend > freeblockstart) and (eventend < freeblockend):
            app.logger.debug("CASE B")
            freeblockstart = eventend
        # Case C
        elif (eventstart > freeblockstart) and (eventend < freeblockend):
            app.logger.debug("This is a new freeblock CASE C")
            new_freeblock = { "start": freeblockstart, "end": eventstart }
            freetimes_in_block.append(new_freeblock)
            
            freeblockstart = eventend
        # Case D
        elif (eventstart > freeblockstart) and (eventstart < freeblockend) and (eventend >= freeblockend):
            app.logger.debug("CASE D")
            freeblockend = eventstart
        else:
            app.logger.debug("SOMETHING IS WRONG!")
    
    if (freeblockstart >= freeblock['start']) and (freeblockend <= freeblock['end']):
        new_freeblock = { "start": freeblockstart, "end": freeblockend }
        freetimes_in_block.append(new_freeblock)
    else:
        return freetimes_in_block

    
    return freetimes_in_block
    
    
    
    
    
    
    
    
    
    
    