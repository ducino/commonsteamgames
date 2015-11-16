import sys
import json
import urllib2

def intersect(*args):
    """ return the intersection of lists """
    if len(args) == 0:
        return []
    s = set(args[0])
    for arg in args[1:]:
        s = s & set(arg)
    return list(s)
    
def union(*args):
    """ return the union of lists """
    s = set()
    for arg in args:
        s = s | set(arg)
    return list(s)
    
def normalize_player_name(name):
    normalize_map = {"0" : "o",
                     "1" : "i",
                     "2" : "z",
                     "3" : "e",
                     "4" : "a",
                     "@" : "a",
                     "5" : "s",
                     "6" : "a",
                     "7" : "z",
                     "8" : "b",
                     "9" : "a"
                     }
    name = name.lower()
    name = name.encode("utf8")
    normalized_name = u""
    for c in name:
        if c in normalize_map:
            normalized_name += normalize_map[c]
        else:
            try:
                normalized_name += c
            except:
                pass
    return normalized_name   

class SteamAPI(object):

    def __init__(self, key):
        self.key = key
        
    def get_steam_url(self, interface, method, version, **kwargs):
        args = "&".join(["{}={}".format(key, value) for key, value in kwargs.items()])
        return "http://api.steampowered.com/{}/{}/{}/?key={}&{}"\
                .format(interface, method, version, self.key, args)
                
    def get_owned_games_list(self, steamid):
        data = self.get_owned_games(steamid)
        try:
            return [d["name"] for d in data["response"]["games"]]
        except KeyError:
            return []            
    
    def get_owned_games(self, steamid):
        return self.call("IPlayerService", "GetOwnedGames", "v0001",\
                    steamid=steamid, include_appinfo=1, include_played_free_games=1)
        
    def get_user_stats_for_game(self, gameid, steamid):
        return self.call("ISteamUserStats", "GetUserStatsForGame",\
                          "v0002", steamid=steamid, appid=gameid)
    
    def get_schema_for_game(self, appid):
        return self.call("ISteamUserStats", "GetSchemaForGame", "v2", appid=appid)
    
    def get_friend_map(self, steamid):
        friend_list = self.get_friend_list(steamid)
        friend_ids = [friend["steamid"] for friend in friend_list["friendslist"]["friends"]]
        summaries = self.get_player_summaries(friend_ids)
        return {friend["personaname"]:friend["steamid"] for friend in summaries["response"]["players"]}
    
    def get_friend_list(self, steamid):
        return self.call("ISteamUser", "GetFriendList", "v0001", steamid=steamid, relationship="friend")
        
    def get_player_summaries(self, steamids):
        return self.call("ISteamUser", "GetPlayerSummaries", "v0002", steamids=",".join(steamids))
        
    def call(self, interface, method, version, **kwargs):
        url = self.get_steam_url(interface, method, version, **kwargs)
        try:
            return json.loads(urllib2.urlopen(url).read())
        except urllib2.HTTPError, e:
            print "Error reading from", url
            print e.msg
            sys.exit(1)                   

def main():
    if len(sys.argv) < 2:
        print "Usage: {} <your_steam_id> <friend_1_name> [<friend_2_name> ...]".format(sys.argv[0])
        sys.exit(1)
    steamid = sys.argv[1]
    friends = sys.argv[2:]
    
    # Load steam api key
    steamapi_key = None
    try:
        with open("steamapi.key", "r") as f:
            steamapi_key = f.read()
    except IOError, e:
        print e
        print "Did you create the file containing your steam api key?"
        sys.exit(1)
        
    # Load default steamid
    if steamid == "self":
        try:
            with open("steam.id", "r") as f:
                steamid = f.read()
        except IOError, e:
            print e
            print "Did you create the file containing your steam id?"
            sys.exit(1)
        
    # Create steam api wrapper
    api = SteamAPI(steamapi_key)
    
    # Get friend list
    friend_map = api.get_friend_map(steamid)
    
    # Get ids for matching friends
    steamids = {}       
    for requested_friend in friends:
        candidates = {}
        for friend, id in friend_map.items():
            if normalize_player_name(friend).count(normalize_player_name(requested_friend)) > 0:
                candidates[friend] = id
        if len(candidates) > 1:
            print "Ambiguous friend {}, possible candidates: {}".format(requested_friend,\
                  ", ".join([normalize_player_name(player) for player in candidates]))
            sys.exit(1)
        if len(candidates) == 0:
            print "Unknown friend {}".format(requested_friend)
            sys.exit(1)
        friend, id = candidates.popitem()
        steamids[friend] = id
    
    # Get list of games lists
    games_list = []
    for friend, id in steamids.items():
        owned_games = api.get_owned_games_list(id)
        if len(owned_games) == 0:
            print "No games found for", friend, "(ignoring...)"
        else:
            games_list.append(owned_games)
    
    # Find common games
    print "Common games for {}".format(", ".join(steamids.keys()))
    print "\n".join(sorted(intersect(*games_list)))

if __name__ == "__main__":
    main()