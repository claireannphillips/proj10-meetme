import flask
from flask import render_template
from flask import request
from flask import url_for
import uuid
import pymongo
from pymongo import MongoClient
import ast
import random
import string
import sys

import json
import logging

# Date handling 
import arrow # Replacement for datetime, based on moment.js
# import datetime # But we still need time
from dateutil import tz  # For interpreting local times


from freeTimes import free_times, availability


# OAuth2  - Google library implementation for convenience
from oauth2client import client
import httplib2   # used in oauth2 flow

# Google API for services 
from apiclient import discovery

###
# Globals
###
import config
if __name__ == "__main__":
    CONFIG = config.configuration()
else:
    CONFIG = config.configuration(proxied=True)



app = flask.Flask(__name__)
app.debug=CONFIG.DEBUG
app.logger.setLevel(logging.DEBUG)
app.secret_key=CONFIG.SECRET_KEY

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = CONFIG.GOOGLE_KEY_FILE  ## You'll need this
APPLICATION_NAME = 'MeetMe class project'

MONGO_CLIENT_URL = "mongodb://{}:{}@{}:{}/{}".format(
    CONFIG.DB_USER,
    CONFIG.DB_USER_PW,
    CONFIG.DB_HOST,
    CONFIG.DB_PORT,
    CONFIG.DB)


print("Using URL '{}'".format(MONGO_CLIENT_URL))    

####
# Database connection per server process
###

try:
  dbclient = MongoClient(MONGO_CLIENT_URL)  # mongo connection string
  db = getattr(dbclient, CONFIG.DB)
  collection = db.meetings

except:
  print("Failure opening database.  Is Mongo running? Correct password?")
  sys.exit(1)

#############################
#
#  Pages (routed from URLs)
#
#############################

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Entering index")
  flask.g.url = MONGO_CLIENT_URL
  if 'begin_date' not in flask.session:
    init_session_values()
  return render_template('index.html')




@app.route("/createmeeting", methods = ["post"])
def createmeeting():
  meeting_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
  arranger_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

  flask.session['meet'] = {}

  times = request.form.getlist('interest')
  flask.session['meet']['id'] = meeting_id
  flask.session['meet']['code'] = arranger_code
  flask.session['meet']['final'] = False
  flask.session['meet']['s_range_date'] = flask.session['begin_date']
  flask.session['meet']['s_range_time'] = flask.session['start_clock']
  flask.session['meet']['e_range_date'] = flask.session['end_date']
  flask.session['meet']['e_range_time'] = flask.session['end_clock']
  flask.session['meet']['times'] = [] 
  for i in range(len(times)):
    time = times[i]
    start = time[11:36]
    app.logger.debug("TIME {} START {}".format(time[47:72], start))
    end = time[47:72]
    flask.session['meet']['times'].append({
              'name': str(i),
              'start': start,
              'end': end,
              'responses': []
      })

  meet = {'meeting': flask.session['meet']}
  collection.insert(meet)
  return flask.redirect(flask.url_for('meeting', meeting_id=meeting_id, arranger_code=arranger_code))

@app.route("/meeting/<string:meeting_id>/<string:arranger_code>")
def meeting(meeting_id, arranger_code):
  flask.session['id'] = meeting_id
  flask.session['code'] = arranger_code
  flask.session['user_link'] = flask.url_for('user_view', meeting_id=flask.session['id'])
  flask.session['admin_link'] = flask.url_for("admin_view", meeting_id=flask.session['id'], arranger_code=flask.session['code'])
  return render_template('meeting.html')

@app.route("/user_view/<string:meeting_id>")
def user_view(meeting_id):
  flask.session['times'] = []
  for meeting in collection.find():
    if meeting['meeting']['id'] == meeting_id:
      if meeting['meeting']['final'] != False:
        return flask.redirect(flask.url_for('final', meeting_id=meeting_id))
      for time in meeting['meeting']['times']:
        flask.session['times'].append({
          "start":time['start'],
          "end":time['end'],
          "responses":time['responses']
          })
        flask.session['id'] = meeting['meeting']['id']
        flask.session['begin_date'] = meeting['meeting']['s_range_date']
        flask.session['begin_time'] = meeting['meeting']['s_range_time']
        flask.session['end_date'] = meeting['meeting']['e_range_date']
        flask.session['end_time'] = meeting['meeting']['e_range_time']
        return render_template('user_view.html')
  return render_template('incorrectid.html')

@app.route("/admin_view/<string:meeting_id>/<string:arranger_code>")
def admin_view(meeting_id, arranger_code):
  flask.session['id'] = meeting_id
  flask.session['code'] = arranger_code
  flask.session['times'] = []
  for meeting in collection.find():
    if meeting['meeting']['id'] == meeting_id:
      if meeting['meeting']['final'] != False:
        return flask.redirect(flask.url_for('final', meeting_id=meeting_id))
      if meeting['meeting']['code'] == arranger_code:
        for time in meeting['meeting']['times']:
          flask.session['times'].append({
            "start":time['start'],
            "end":time['end'],
            "responses":time['responses']
            })
        return render_template('admin_view.html')
  return render_template('incorrectid.html')

@app.route("/update", methods=["post"])
def update():
  selection = flask.request.form.getlist('times')
  name = flask.request.form.get('name')
  for meeting in collection.find():
    if meeting['meeting']['id'] == flask.session['id']:
      for time in selection:
        for names in meeting['meeting']['times']:
          if time == names['name']:
            update = 'meeting.times.'+time+'.responses'
            collection.update_one(
              {"meeting.id":flask.session['id']},
              {'$push': {update: name}}
              )
  return render_template('done.html')
              
@app.route("/complete", methods=["post"])
def complete():
  final_time = flask.request.form.get("times")
  if final_time == None:
    return flask.redirect(url_for('admin_view', meeting_id=flask.session['id'], arranger_code=flask.session['code']))
  flask.session['final_time'] = final_time
  meeting_id = flask.session['id']
  collection.update_one(
    {"meeting.id": meeting_id},
    {"$set": {"meeting.final": final_time}}
    )
  return flask.redirect(flask.url_for('final', meeting_id=meeting_id))

@app.route("/final/<string:meeting_id>")
def final(meeting_id):
  flask.session['id'] = meeting_id
  for meeting in collection.find():
    if meeting['meeting']['id'] == meeting_id:
      flask.session['final_time'] = meeting['meeting']['final']
      return render_template('final.html')
  return render_template('incorrectid.html')
  


@app.route("/choose")
def choose():
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    #list_events(gcal_service, flask.g.calendars)
    return render_template('index.html')

@app.route("/userchoose")
def userchoose():
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    return render_template('user_view.html')

@app.route("/choose2")
def choose2():
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    flask.g.events = list_events(gcal_service, flask.g.calendars)
    
    flask.g.free = flask.session['free']
    
    return render_template('list.html')

@app.route("/userchoose2")
def userchoose2():
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.g.calendars = list_calendars(gcal_service)
    flask.g.events = list_events(gcal_service, flask.g.calendars)
    
    flask.g.free = flask.session['free']
    
    return render_template('user_list.html')

####
#
#  Google calendar authorization:
#      Returns us to the main /choose screen after inserting
#      the calendar_service object in the session state.  May
#      redirect to OAuth server first, and may take multiple
#      trips through the oauth2 callback function.
#
#  Protocol for use ON EACH REQUEST: 
#     First, check for valid credentials
#     If we don't have valid credentials
#         Get credentials (jump to the oauth2 protocol)
#         (redirects back to /choose, this time with credentials)
#     If we do have valid credentials
#         Get the service object
#
#  The final result of successful authorization is a 'service'
#  object.  We use a 'service' object to actually retrieve data
#  from the Google services. Service objects are NOT serializable ---
#  we can't stash one in a cookie.  Instead, on each request we
#  get a fresh serivce object from our credentials, which are
#  serializable. 
#
#  Note that after authorization we always redirect to /choose;
#  If this is unsatisfactory, we'll need a session variable to use
#  as a 'continuation' or 'return address' to use instead. 
#
####

def valid_credentials():
    """
    Returns OAuth2 credentials if we have valid
    credentials in the session.  This is a 'truthy' value.
    Return None if we don't have credentials, or if they
    have expired or are otherwise invalid.  This is a 'falsy' value. 
    """
    if 'credentials' not in flask.session:
      return None

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if (credentials.invalid or
        credentials.access_token_expired):
      return None
    return credentials


def get_gcal_service(credentials):
  """
  We need a Google calendar 'service' object to obtain
  list of calendars, busy times, etc.  This requires
  authorization. If authorization is already in effect,
  we'll just return with the authorization. Otherwise,
  control flow will be interrupted by authorization, and we'll
  end up redirected back to /choose *without a service object*.
  Then the second call will succeed without additional authorization.
  """
  app.logger.debug("Entering get_gcal_service")
  http_auth = credentials.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http_auth)
  app.logger.debug("Returning service")
  return service

@app.route('/oauth2callback')
def oauth2callback():
  """
  The 'flow' has this one place to call back to.  We'll enter here
  more than once as steps in the flow are completed, and need to keep
  track of how far we've gotten. The first time we'll do the first
  step, the second time we'll skip the first step and do the second,
  and so on.
  """
  app.logger.debug("Entering oauth2callback")
  flow =  client.flow_from_clientsecrets(
      CLIENT_SECRET_FILE,
      scope= SCOPES,
      redirect_uri=flask.url_for('oauth2callback', _external=True))
  ## Note we are *not* redirecting above.  We are noting *where*
  ## we will redirect to, which is this function. 
  
  ## The *second* time we enter here, it's a callback 
  ## with 'code' set in the URL parameter.  If we don't
  ## see that, it must be the first time through, so we
  ## need to do step 1. 
  app.logger.debug("Got flow")
  if 'code' not in flask.request.args:
    app.logger.debug("Code not in flask.request.args")
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
    ## This will redirect back here, but the second time through
    ## we'll have the 'code' parameter set
  else:
    ## It's the second time through ... we can tell because
    ## we got the 'code' argument in the URL.
    app.logger.debug("Code was in flask.request.args")
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    ## Now I can build the service and execute the query,
    ## but for the moment I'll just log it and go back to
    ## the main screen
    app.logger.debug("Got credentials")
    return flask.redirect(flask.url_for('choose'))

#####
#
#  Option setting:  Buttons or forms that add some
#     information into session state.  Don't do the
#     computation here; use of the information might
#     depend on what other information we have.
#   Setting an option sends us back to the main display
#      page, where we may put the new information to use. 
#
#####

@app.route('/setrange', methods=['POST'])
def setrange():
    """
     User chose a date range with the bootstrap daterange
    widget.
    """
    
    app.logger.debug("Entering setrange")  
    flask.flash("Setrange gave us '{}' and time from '{}' to '{}'".format(
    request.form.get('daterange'), request.form.get('start_clock'), request.form.get('end_clock')))
    daterange = request.form.get('daterange')
    
    start_clock = request.form.get('start_clock')
    end_clock = request.form.get('end_clock')
    flask.session['daterange'] = daterange
    
    flask.session['start_clock'] = start_clock
    flask.session['end_clock'] = end_clock
    daterange_parts = daterange.split()
    
    
    app.logger.debug("start_clock from form: '{}'".format(start_clock))
    #start_clock = arrow.get(start_clock)
    #start_clock = start_clock.format("HH")
    #begin_time = arrow.get(flask.session["begin_time"]).format("HH")
    #flask.session["begin_time"] = interpret_time(start_clock)
    #app.logger.debug("STARTCLOCK: {}".format(start_clock))
    
    #end_clock = request.form.get("end_clock")
    #end_clock = arrow.get(flask.session["begin_time"])
    #end_clock = end_clock.format("HH")
    #begin_time = arrow.get(flask.session["begin_time"]).format("HH")
    #flask.session["begin_time"] = interpret_time(end_clock)
    

    
    flask.session['begin_date'] = interpret_date(daterange_parts[0])
    app.logger.debug('BEGIN DATE:  {}'.format(flask.session['begin_date']))
    flask.session['end_date'] = interpret_date(daterange_parts[2])
    
   
    app.logger.debug("Setrange parsed {} - {}  dates as {} - {}".format(
      daterange_parts[0], daterange_parts[1], 
      flask.session['begin_date'], flask.session['end_date']))
    return flask.redirect(flask.url_for("choose"))

@app.route("/usersetrange", methods=["post"])
def usersetrange():
  return flask.redirect(flask.url_for('userchoose'))



####
#
#   Initialize session variables 
#
####

def init_session_values():
    """
    Start with some reasonable defaults for date and time ranges.
    Note this must be run in app context ... can't call from main. 
    """
    # Default date span = tomorrow to 1 week from now
    now = arrow.now('local')     # We really should be using tz from browser
    tomorrow = now.replace(days=+1)
    nextweek = now.replace(days=+7)
    flask.session["begin_date"] = tomorrow.floor('day').isoformat()
    flask.session["end_date"] = nextweek.ceil('day').isoformat()
    flask.session["daterange"] = "{} - {}".format(
        tomorrow.format("MM/DD/YYYY"),
        nextweek.format("MM/DD/YYYY"))
    # Default time span each day, 8 to 5
    flask.session["begin_time"] = interpret_time("9am")
    flask.session["end_time"] = interpret_time("5pm")

def interpret_time( text ):
    """
    Read time in a human-compatible format and
    interpret as ISO format with local timezone.
    May throw exception if time can't be interpreted. In that
    case it will also flash a message explaining accepted formats.
    """
    app.logger.debug("Decoding time '{}'".format(text))
    time_formats = ["ha", "h:mma",  "h:mm a", "H:mm"]
    try: 
        as_arrow = arrow.get(text, time_formats).replace(tzinfo=tz.tzlocal())
        as_arrow = as_arrow.replace(year=2017) #HACK see below
        app.logger.debug("Succeeded interpreting time")
    except:
        app.logger.debug("Failed to interpret time")
        flask.flash("Time '{}' didn't match accepted formats 13:30 or 1:30pm"
              .format(text))
        raise
    return as_arrow.isoformat()
    #HACK #Workaround
    # isoformat() on raspberry Pi does not work for some dates
    # far from now.  It will fail with an overflow from time stamp out
    # of range while checking for daylight savings time.  Workaround is
    # to force the date-time combination into the year 2016, which seems to
    # get the timestamp into a reasonable range. This workaround should be
    # removed when Arrow or Dateutil.tz is fixed.
    # FIXME: Remove the workaround when arrow is fixed (but only after testing
    # on raspberry Pi --- failure is likely due to 32-bit integers on that platform)


def interpret_date( text ):
    """
    Convert text of date to ISO format used internally,
    with the local time zone.
    """
    try:
      as_arrow = arrow.get(text, "MM/DD/YYYY").replace(
          tzinfo=tz.tzlocal())
    except:
        flask.flash("Date '{}' didn't fit expected format 12/31/2001")
        raise
    return as_arrow.isoformat()

def next_day(isotext):
    """
    ISO date + 1 day (used in query to Google calendar)
    """
    as_arrow = arrow.get(isotext)
    return as_arrow.replace(days=+1).isoformat()

####
#
#  Functions (NOT pages) that return some information
#
####
  
def list_calendars(service):
    """
    Given a google 'service' object, return a list of
    calendars.  Each calendar is represented by a dict.
    The returned list is sorted to have
    the primary calendar first, and selected (that is, displayed in
    Google Calendars web app) calendars before unselected calendars.
    """
    app.logger.debug("Entering list_calendars")  
    calendar_list = service.calendarList().list().execute()["items"]
    result = [ ]
    for cal in calendar_list:
        kind = cal["kind"]
        id = cal["id"]
        if "description" in cal: 
            desc = cal["description"]
        else:
            desc = "(no description)"
        summary = cal["summary"]
        # Optional binary attributes with False as default
        selected = ("selected" in cal) and cal["selected"]
        primary = ("primary" in cal) and cal["primary"]
        

        result.append(
          { "kind": kind,
            "id": id,
            "summary": summary,
            "selected": selected,
            "primary": primary
            })
    return sorted(result, key=cal_sort_key)

@app.route('/list_events', methods=['GET','POST'])
def checking():
    interest = flask.request.form.getlist("interest")
    flask.session["cal_ids"] = interest
    app.logger.debug('CHECKED BOXES: {}'.format(interest)) #shows list of calendars clicked
    return flask.redirect(flask.url_for("choose2"))


@app.route('/userlist_events', methods=['GET','POST'])
def userchecking():
    interest = flask.request.form.getlist("interest")
    flask.session["cal_ids"] = interest
    app.logger.debug('CHECKED BOXES: {}'.format(interest)) #shows list of calendars clicked
    return flask.redirect(flask.url_for("userchoose2"))

    

def list_events(service, calendars):
  """
  Gets a list of events, add to respective calendar, and format for printing.
  """
  app.logger.debug("Entering list_events")
  

  busytimes = []
  result = []
  selected = flask.session["cal_ids"]
  
  begin_date = flask.session["begin_date"]
  end_date = flask.session["end_date"]
  #app.logger.debug(begin_date)
  #app.logger.debug(end_date)
      
  begintime = flask.session['start_clock']
  #app.logger.debug(begintime)
  endtime = flask.session['end_clock']
  #app.logger.debug(endtime)
  
  startdate = begin_date[:11] + begintime + begin_date[19:]
  #app.logger.debug(startdate)
  enddate = end_date[:11] + endtime + end_date[19:]
  #app.logger.debug(enddate)
  
  calendar_result = []
  finalfreelist = []
  for id in selected:
      
      events = service.events().list(calendarId=id, singleEvents=True, orderBy='startTime' ).execute()["items"]
      if events == []:
          flask.flash("No events.")
      
      # Get busy times
      listevents = check(events, startdate, enddate)
      app.logger.debug("STARTDATE:{}".format(startdate))
      
      # Get free blocks
      freeblocks = availability(startdate, enddate)
      
      # Get free times
      freetimeslist = []
      
      for block in freeblocks:
          busyevents = check(events, block['start'], block['end'])
          freetimes = free_times(block, busyevents)
          app.logger.debug("Freetimes: {}".format(freetimes))
          if freetimes != []:
              for time in freetimes:
                  freetimeslist.append(time)
    
      finalfreelist.append({ "id": id, "free_times":freetimeslist})
      busytimes.append({ "id": id, "events": listevents})
    
  flask.session['free'] = finalfreelist
    
  return busytimes                                  
      

def check(events, start, end):
    '''checks the cases of if  an event should be added to busy times.
    Don't add if event is after the hours, before the starting hour, or a
    multiday event'''
    
    startdate = arrow.get(start).date()
    #app.logger.debug(startdate)
    enddate = arrow.get(end).date()
    #app.logger.debug(enddate)
    starttime = arrow.get(start).time()
    #app.logger.debug(starttime)
    endtime = arrow.get(end).time()
    #app.logger.debug(endtime)
    
    busylist = []
    if events == []:
        return "no events"
    else:
        for event in events:
            if "transparency" not in event:
                if "date" in event["start"]:
                    summary = event["summary"]
                    eventBegin = event["start"]["date"] + "00:00:00" + start[19:]
                    eventEnd = event["end"]["date"] + "23:59:00" + end[19:]
                    event_begin_date = arrow.get(eventBegin).date()
                    event_begin_time = arrow.get(eventBegin).time()
                    event_end_date = arrow.get(eventEnd).date()
                    event_end_time = arrow.get(eventEnd).time()
                else:
                    summary = event["summary"]
                    eventBegin = event["start"]['dateTime']
                    event_begin_date = arrow.get(eventBegin).date()
                    event_begin_time = arrow.get(eventBegin).time()
                    eventEnd = event["end"]['dateTime']
                    event_end_date = arrow.get(eventEnd).date()
                    event_end_time = arrow.get(eventEnd).time()
                    
                    #app.logger.debug(event_end_date)
                    #app.logger.debug(event_begin_date)
                    #app.logger.debug(event_begin_time)
                    #app.logger.debug(event_end_time)
                    
                range1 = (event_begin_date >= startdate) and (event_end_date <= enddate) and (event_begin_time >= starttime) and (event_end_time <= endtime) 
                range2 = (event_begin_date >= startdate) and (event_end_date <= enddate) and (event_begin_time < starttime) and ((event_end_time >= endtime) or (event_end_time <= endtime)) and (event_end_time > starttime)
                range3 = (event_begin_date >= startdate) and (event_end_date <= enddate) and (event_begin_time < endtime) and ((event_end_time >= endtime) or (event_end_time <= endtime)) and (event_end_time > endtime)
                
                if (range1 or range2 or range3):
                    event = {"sum": summary,
                             "start": eventBegin,
                             "end": eventEnd,
                             "selected": True}
                    busylist.append(event)
               
        
    return busylist





def cal_sort_key( cal ):
    """
    Sort key for the list of calendars:  primary calendar first,
    then other selected calendars, then unselected calendars.
    (" " sorts before "X", and tuples are compared piecewise)
    """
    if cal["selected"]:
       selected_key = " "
    else:
       selected_key = "X"
    if cal["primary"]:
       primary_key = " "
    else:
       primary_key = "X"
    return (primary_key, selected_key, cal["summary"])


#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'fmtdate' )
def format_arrow_date( date ):
    try: 
        normal = arrow.get( date )
        return normal.format("ddd MM/DD/YYYY")
    except:
        return "(bad date)"

@app.template_filter( 'fmttime' )
def format_arrow_time( time ):
    try:
        normal = arrow.get( time )
        return normal.format("HH:mm")
    except:
        return "(bad time)"
    
#############


if __name__ == "__main__":
  # App is created above so that it will
  # exist whether this is 'main' or not
  # (e.g., if we are running under green unicorn)
  app.run(port=CONFIG.PORT,host="0.0.0.0")