USERS = { 'editor' : 'editor',
          'guest' : ''}

GROUPS = { 'editor' : ['group:editors'], 'guest' : ['group:guests'] }

def groupfinder(userid, request):
    #print "Groupfinder invoked"
    if userid in USERS:
        return GROUPS.get(userid, [])