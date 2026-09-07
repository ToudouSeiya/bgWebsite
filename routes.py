from bgWebsite import dbtour_app
from flask import render_template, request,url_for, redirect, session
import mariadb, redis
import random
from pymongo import MongoClient

@dbtour_app.route("/", methods=["POST","GET"])
def index():
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()

    r = redis.Redis(password="sammydavies", db=24, decode_responses=True)

    if "username" in session:
        username = session["username"]
        wishlistGames = r.lrange(r.hget("user:"+username, "wishList"), 0, -1) 
        wishlist = [];
        for game in wishlistGames:
            cur.execute("select gameName, designerName, genre, (concat(minPlayers, '-', maxPlayers)), bggRating from boardGames where gameName=?", (game,))
            gameData = cur.fetchone()
            wishlist.append(gameData)
        friends = "";
        if ( r.hexists("user:"+username, "friendList")):
            friends = r.smembers(r.hget("user:"+username, "friendList"))
        else:
           friends = {} 
    else:
        return redirect(url_for("newUser", msg=""))

    if(request.method == "GET"):
        if("msg" in request.args):
            msg=request.args["msg"]
        else:
            msg=""
        if("lastPrompt" in session):
            lastPrompt=session["lastPrompt"]
            orderBy=lastPrompt[0]
            name=lastPrompt[1]
            designer=lastPrompt[2]
            genre=lastPrompt[3]
            if(lastPrompt[4]=="0"):
                lastPrompt[4]=""
            players=lastPrompt[4]
            scroll=str(session["scroll"])
            newPrompt = [orderBy, name, designer,genre,players]
            prompt = """select gameName, releaseYear, boardGames.designerName, publisher, genre, 
                (concat(minPlayers, '-', maxPlayers)), bggRating, countryOfOrigin from 
                boardGames,gameDesigners where gameName """+name+" and boardGames.designerName=gameDesigners.designerName and gameDesigners.designerName "+designer+" and genre "+genre+" "+players+" "+orderBy+" limit 10 offset "+scroll
            cur.execute(prompt)
            
        else:
            prompt = """select gameName, releaseYear, boardGames.designerName, publisher, genre, 
            (concat(minPlayers, '-', maxPlayers)), bggRating, countryOfOrigin from 
            boardGames,gameDesigners where boardGames.designerName=gameDesigners.designerName
            limit 10"""
            cur.execute(prompt)
            scroll="0"
            session["scroll"]=0
            session["lastPrompt"]=["", "like '%'","like '%'","like '%'", ""]
            newPrompt=["","","","","0"]
    else:
        msg=""
        orderBy = request.form["order"]
        name = "like '%" + request.form["name"] + "%'"
        designer = request.form["designer"]
        if (designer=="*"):
            designer="like '%'"
        else:
            designer = "='"+designer+"'"
        genre = request.form["genre"]
        if (genre=="*"):
            genre="like '%'"
        else:
            genre = "='"+genre+"'"
        players = request.form["players"]
        if (players=="*"):
            players=""
        else:
            players="and minPlayers<="+players+" and maxPlayers >="+players
        newPrompt = [orderBy, name, designer,genre,players]
        if("lastPrompt" in session):
            if(newPrompt == session["lastPrompt"]):
                scroll = str(session["scroll"])
            else:
               scroll = "0"
               session["scroll"]=0
               session["lastPrompt"]=newPrompt
        else:
            scroll="0"
            session["scroll"]=0 
            session["lastPrompt"]=newPrompt
        prompt = """select gameName, releaseYear, boardGames.designerName, publisher, genre, 
            (concat(minPlayers, '-', maxPlayers)), bggRating, countryOfOrigin from 
            boardGames,gameDesigners where gameName """+name+" and boardGames.designerName=gameDesigners.designerName and gameDesigners.designerName "+designer+" and genre "+genre+" "+players+" "+orderBy+" limit 10 offset "+scroll
        cur.execute(prompt)
    games = cur.fetchall()
    if(len(games)==10):
        noRight=0
    else:
        noRight=1
    if(scroll=="0"):
        noLeft=1
    else:
        noLeft=0
    cur.execute("select designerName from gameDesigners")
    designers = cur.fetchall()
    cur.execute("select distinct genre from boardGames")
    genres = cur.fetchall()
    cur.execute("select max(maxPlayers) from boardGames")
    maxPlayers=cur.fetchall()[0][0]
    if(newPrompt[4]==""):
        newPrompt[4]="0"
    return render_template("dbPage.html", newPrompt=newPrompt,noLeft=noLeft, noRight=noRight, friends=friends, wishlist=wishlist, table=games, designers=designers, genres=genres, maxPlayers=maxPlayers, msg=msg, username=username, faveGenre = session["faveGenre"], faveGame=session["faveGame"], favePlayers = session["faveNumPlayers"]) 

    
@dbtour_app.route("/add_data")
def add_data():
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    cur.execute("select designerName from gameDesigners")
    designers = cur.fetchall();
    return render_template("addData.html", designers=designers)

@dbtour_app.route("/add_designer_data")
def add_designer_data():
    return render_template("addDesignerData.html")

@dbtour_app.route("/add_data/adding")
def commit_game_data():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    name = request.args["name"]
    designer = request.args["designer"]
    publisher = request.args["publisher"]
    releaseYear = request.args["releaseYear"]
    minPlayers = request.args["minPlayers"]
    maxPlayers = request.args["maxPlayers"]
    genre = request.args["genre"]
    rating = request.args["rating"]
    try:
        cur.execute("insert into boardGames values (?, ?, ?, ?, ?, ?, ?, ?)", (name, releaseYear, designer, publisher, genre, minPlayers, maxPlayers, rating))  
        db.boardGames.insert_one({'name':name, 'numWished':0})
    except:
        return redirect(url_for("index",msg="Error: Data could not be added. No duplicates allowed."))

    conn.commit()
    
    return redirect(url_for("index", msg="Data successfully added."))

@dbtour_app.route("/add_designer_data/adding")
def commit_designer_data():
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    name = request.args["name"]
    country = request.args["country"]
    try:
        if (request.args["birthYear"]!=""):
            birthYear=request.args["birthYear"]
            cur.execute("insert into gameDesigners values (?, ?, ?)", (name, country, birthYear))
        else:
            cur.execute("insert into gameDesigners values (?, ?, Null)", (name, country))
    except:
        return redirect(url_for("index",msg="Error: Data could not be added. No duplicates allowed."))

    conn.commit()
    
    return redirect(url_for("index", msg="Data successfully added."))

@dbtour_app.route("/newUser")
def newUser():
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    cur.execute("select distinct genre from boardGames")
    genres = cur.fetchall()
    cur.execute("select max(maxPlayers) from boardGames")
    maxPlayers=cur.fetchall()[0][0]
    cur.execute("select distinct gameName from boardGames")
    games = cur.fetchall()
    return render_template("newUser.html", genres=genres, maxPlayers=maxPlayers, games=games, msg=request.args["msg"])

@dbtour_app.route("/userData")
def userData():
    r = redis.Redis(password="sammydavies",db=24, decode_responses=True)
    if (r.exists("user:"+request.args["name"])):
           return redirect(url_for("newUser", msg="Name already taken.")) 
    session["username"] = request.args["name"]
    code = "user:"+session["username"]
    r.hset(code, "name", session["username"])
    r.hset(code, "wishList", "wishlist:"+session["username"])
    r.hset(code, "friendList", "friendList:"+session["username"])
    r.hset(code, "password", request.args["password"])
    session["faveGenre"] = request.args["faveGenre"]
    r.hset(code, "genre", session["faveGenre"])
    session["faveNumPlayers"] = request.args["faveNumPlayers"]
    r.hset(code, "players", session["faveNumPlayers"])
    session["faveGame"] = request.args["faveGame"]
    r.hset(code, "game", session["faveGame"])
    return redirect(url_for("index"))

@dbtour_app.route("/userDataUpdate")
def updateData():
    r = redis.Redis(password="sammydavies", db=24, decode_responses=True)
    code = "user:"+session["username"]
    session["faveGenre"] = request.args["faveGenre"]
    r.hset(code, "genre", session["faveGenre"])
    session["faveNumPlayers"] = request.args["faveNumPlayers"]
    r.hset(code, "players", session["faveNumPlayers"])
    session["faveGame"] = request.args["faveGame"]
    r.hset(code, "game", session["faveGame"])
    return redirect(url_for("index", msg="Information updated."))

@dbtour_app.route("/changePreferences")
def changePreferences():
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    cur.execute("select distinct genre from boardGames")
    genres = cur.fetchall()
    cur.execute("select max(maxPlayers) from boardGames")
    maxPlayers=cur.fetchall()[0][0]
    cur.execute("select distinct gameName from boardGames")
    games = cur.fetchall()
    return render_template("changePref.html", genres=genres, games=games, maxPlayers=maxPlayers, name=session["username"], currGenre=session["faveGenre"], currGame=session["faveGame"], currPlayers=session["faveNumPlayers"])

@dbtour_app.route("/addFriend")
def addFriend():
    return render_template("addFriend.html")

@dbtour_app.route("/friendData")
def friendData():
    r = redis.Redis(password="sammydavies",db=24, decode_responses=True)
    friendName = request.args["friendName"]
    if(session["username"]==friendName):
        return redirect(url_for("index", msg="You can't friend yourself."))
    if(not r.exists("user:"+friendName)):
        return redirect(url_for("index", msg="Friend does not exist."))
    if(friendName in r.smembers(r.hget("user:"+session["username"], "friendList"))):
        return redirect(url_for("index", msg="You're already friends with this user."))
    else:
        r.sadd(r.hget("user:"+session["username"], "friendList"), friendName)
        return redirect(url_for("index", msg="Friend added."))

@dbtour_app.route("/viewFriend")
def viewFriend():
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    r = redis.Redis(password='sammydavies', db=24, decode_responses=True)
    friendName = request.args["friend"]
    genre = r.hget("user:"+friendName, "genre")
    game = r.hget("user:"+friendName, "game")
    players = r.hget("user:"+friendName, "players")
    wishGames = r.lrange(r.hget("user:"+friendName, "wishList"), 0, -1)
    wishes = []
    for wishGame in wishGames:
        cur.execute("select gameName, designerName, genre, (concat(minPlayers, '-', maxPlayers)), bggRating from boardGames where gameName=?", (wishGame,))
        wishes.append(cur.fetchone())
    return render_template("viewFriend.html", friendName=friendName, friendGenre=genre, friendGame=game, friendPlayers=players, friendWishes=wishes)

@dbtour_app.route("/addWish")
def addWish():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    game = request.args["game"] 
    r = redis.Redis(password="sammydavies",db=24, decode_responses=True)
    if(game not in r.lrange(r.hget("user:"+session["username"], "wishList"), 0, -1)):
        r.rpush(r.hget("user:"+session["username"], "wishList"), game)
        db.boardGames.update_one({'name':game}, {'$inc':{'numWished':1}})
        return redirect(url_for("index", msg=game + " added to your wish list."))
    else:
        return redirect(url_for("index", msg="Game already in wish list."))

@dbtour_app.route("/removeWish")
def removeWish():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    game = request.args["game"] 
    r = redis.Redis(password="sammydavies",db=24, decode_responses=True)
    r.lrem(r.hget("user:"+session["username"], "wishList"), 1, game)
    db.boardGames.update_one({'name':game}, {'$inc':{'numWished':-1}})
    return redirect(url_for("index", msg=game+" removed from wishlist."))

@dbtour_app.route("/removeFriend")
def removeFriend():
    friend = request.args["friend"]
    r = redis.Redis(password="sammydavies",db=24, decode_responses=True)
    r.srem(r.hget("user:"+session["username"], "friendList"), 1, friend)
    return redirect(url_for("index", msg=friend+" removed from friend list."))

@dbtour_app.route("/login")
def logIn():
    return render_template("login.html", msg=request.args["msg"])

@dbtour_app.route("/login/verify")
def verifyLogin():
    r = redis.Redis(password="sammydavies",db=24, decode_responses=True)
    if(r.exists("user:"+request.args["username"])):
        if(r.hget("user:"+request.args["username"], "password") == request.args["password"]):
            session["username"] = request.args["username"]
            session["faveGenre"] = r.hget("user:"+request.args["username"], "genre")
            session["faveNumPlayers"] = r.hget("user:"+request.args["username"], "players")
            session["faveGame"] = r.hget("user:"+request.args["username"], "game")
            return redirect(url_for("index"))
        else:
            return redirect(url_for("logIn", msg="Password or username is incorrect."))
    else:
        return redirect(url_for("logIn", msg="User does not exist."))
    return redirect(url_for("logIn", msg="ERROR"))

@dbtour_app.route("/detailPage")
def detailPage():
    if("lastPrompt" in session):
        session.pop("lastPrompt")
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    game = request.args["game"] 
    cur.execute("select releaseYear, designerName, publisher, genre,(concat(minPlayers, '-', maxPlayers)), bggRating from boardGames where gameName=?", (game,))
    mariaData = cur.fetchone()
    mongoGame = db.boardGames.find({"name":game}).next()
    numWished = mongoGame["numWished"]
    if ("images" in mongoGame):
        images = mongoGame["images"]
    else:
        images = "n/a"
    if ("comments" in mongoGame):
        comments = mongoGame["comments"]
    else:
        comments = "n/a"
    if ("ratings" in mongoGame):
        ratings = mongoGame["ratings"]
    else:
        ratings = "n/a"

    fields = []
    for field, data in mongoGame.items():
        if(field not in ['wished', 'img', 'ratings', 'name', '_id', 'comments', 'images', 'numWished']):
            fields.append([field, data])

    if("msg" in request.args):
        msg=request.args["msg"]
    else:
        msg=""
    return render_template("detailPage.html", user=session["username"], msg=msg, fields=fields, ratings=ratings,comments=comments, imgs=images, game=game, mariaData=mariaData, wished=numWished)

@dbtour_app.route("/editInfo")
def editInfo():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    game = request.args["game"] 
    mongoGame = db.boardGames.find({"name":game}).next()
    cur.execute("select releaseYear, designerName, publisher, genre, minPlayers, maxPlayers, bggRating from boardGames where gameName=?", (game,))
    mariaData = cur.fetchone()
    cur.execute("select designerName from gameDesigners")
    designers = cur.fetchall();
    if ("images" in mongoGame):
        images = mongoGame["images"]
    else:
        images = "n/a"
    fields = []
    for field, data in mongoGame.items():
        if(field not in ['wished', 'img', 'ratings', 'name', '_id', 'comments', 'images', 'numWished']):
            fields.append([field, data])
    return render_template("editInfo.html", fields=fields, imgs=images,game=game, mariaData=mariaData,designers=designers)

@dbtour_app.route("/addComment")
def addComment():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    game=request.args["game"]
    comment=request.args["comment"]
    db.boardGames.update_one({'name':game},{'$push':{'comments':{'user':session["username"], 'comment':comment}}})
    return redirect(url_for('detailPage', game=game, msg="Comment added."))

@dbtour_app.route("/addRating")
def addRating():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    game=request.args["game"]
    mongoGame=db.boardGames.find({'name':game}).next()
    rating=request.args["rating"]
    if("ratings" in mongoGame):
        userRating = list(db.boardGames.find({'name':game, 'ratings.user':session["username"]}))
        if (len(userRating) >0):
            db.boardGames.update_one({'name':game}, {'$pull':{'ratings':{'user':session['username']}}})
            db.boardGames.update_one({'name':game}, {'$push':{'ratings':{'user':session['username'], 'rating':rating}}})
            return redirect(url_for('detailPage', game=game, msg="Rating updated."))

    db.boardGames.update_one({'name':game},{'$push':{'ratings':{'user':session["username"], 'rating':rating}}})
    return redirect(url_for('detailPage', game=game, msg="Rating added."))

@dbtour_app.route("/editGameData")
def editGameData():
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()

    name = request.args["game"]
    designer = request.args["designer"]
    publisher = request.args["publisher"]
    releaseYear = request.args["releaseYear"]
    minPlayers = request.args["minPlayers"]
    maxPlayers = request.args["maxPlayers"]
    genre = request.args["genre"]
    rating = request.args["rating"]
    try:
        cur.execute("update boardGames set releaseYear=?, designerName=?, publisher=?, genre=?, minPlayers=?, maxPlayers=?, bggRating=? where gameName=?", (releaseYear, designer, publisher, genre, minPlayers, maxPlayers, rating, name))  
    except:
        return redirect(url_for("detailPage", game=name, msg="Error: Something went wrong."))

    conn.commit()
    
    return redirect(url_for("detailPage", game=name, msg="Data successfully updated."))


@dbtour_app.route("/addNewField")
def addNewField():
   mc = MongoClient("mongodb://localhost:27017")
   db = mc["slincicu_db"]
   
#need game, fields that are lists/dicts
   game = request.args["game"]
   mongoGame = db.boardGames.find({'name':game}).next()
   fields = []
   for key, value in mongoGame.items():
        if(type(value) is list or type(value) is dict):
            if(key not in ["ratings", "comments", "images"]):
                fields.append(key)
   
   return render_template("addField.html", game=game, fields=fields)

@dbtour_app.route("/commitMongoData")
def commitMongoData():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]

    game = request.args["game"]
    mongoGame = db.boardGames.find({'name':game}).next()

#iterate through each key in the game other than the ones we don't care about to see what needs to be updated
    for field, value in mongoGame.items():
        if(field not in ["name","_id","ratings", "comments", "images", "img", "numWished", "wished"]):
            newKey = request.args[str(field)+".key"]
            if(newKey in mongoGame.keys() and newKey != field):
                return redirect(url_for('detailPage', game=game, msg="Something went wrong. Make sure no fields have the same name."))
            if(type(value) is str or value==None):
                newValue = request.args[str(field)+".value"] 
                db.boardGames.update_one({'name':game}, {'$unset':{field:""}})
                db.boardGames.update_one({'name':game}, {'$set':{newKey:newValue}})
            elif(type(value) is list):
                db.boardGames.update_one({'name':game}, {'$unset':{field:1}})
                db.boardGames.update_one({'name':game}, {'$set':{newKey:[]}})
                for elem in value:
                    newElem = request.args[str(field)+"."+elem]
                    db.boardGames.update_one({'name':game}, {'$push':{newKey:newElem}})
                #and add a new value?
                newValue = request.args[str(field)+".newValue"]
                if (newValue != ""):
                    db.boardGames.update_one({'name':game}, {'$push':{newKey:newValue}})
            else:
                db.boardGames.update_one({'name':game}, {'$unset':{field:1}})
                db.boardGames.update_one({'name':game}, {'$set':{newKey:{}}})
                for key, val in value.items():
                    newKeyKey = request.args[str(field)+"."+str(key)+".key"]
                    newValue = request.args[str(field)+"."+str(key)+".value"]
                    db.boardGames.update_one({'name':game}, {'$set':{newKey+"."+newKeyKey:newValue}})
                #and add a new value?
                newKeyKey = request.args[str(field)+".newKey"]
                newValue = request.args[str(field)+".newValue"]
                if (newValue != "" and newKeyKey != ""):
                    db.boardGames.update_one({'name':game}, {'$set':{newKey+"."+newKeyKey:newValue}})
                
    return redirect(url_for('detailPage', game=game, msg="Data updated."))

@dbtour_app.route("/removeData")
def removeData():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    
    field = request.args["field"]
    data =  request.args["data"]
    game = request.args["game"]

    if("map" not in request.args):
        db.boardGames.update_one({'name':game}, {'$pull': {field:data}})
    else:
        db.boardGames.update_one({'name':game}, {'$unset':{field+"."+data:""}})

    return redirect(url_for("editInfo", game=game, msg="Data successfully updated."))

@dbtour_app.route("/deleteGame")
def deleteGame():
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    r = redis.Redis(password="sammydavies",db=24, decode_responses=True)
    game = request.args["game"]
    
    #maria
    cur.execute("delete from boardGames where gameName=?", (game,))
    
    #redis
    #get all the wishlists using the scan command and delete the game if it's in there
    for key in r.scan_iter(match="wishlist:*"):
        r.lrem(key, 1, game)

    #mongo
    db.boardGames.delete_one({'name':game})

    conn.commit()
    
    return redirect(url_for('index', msg=game+" has been removed."))


@dbtour_app.route("/addImage")
def addImage():
    return render_template("addImage.html", game=request.args["game"])

@dbtour_app.route("/renameGame")
def renameGame():
    return render_template("renameGame.html", game=request.args["game"])

@dbtour_app.route("/commitRename")
def commitRename():
    oldName = request.args["oldName"]
    newName = request.args["newName"]
    conn = mariadb.connect(user="slincicu", password="sammydavies", host="localhost", port=3306, database="slincicu")
    cur = conn.cursor()
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    r = redis.Redis(password="sammydavies",db=24, decode_responses=True)
    
    #maria
    cur.execute("update boardGames set gameName=? where gameName=?", (newName,oldName))
    
    #redis
    #get all the wishlists using the scan command and rename the game if it's in there
    for key in r.scan_iter(match="wishlist:*"):
        if(oldName in r.lrange(key, 0, -1)):
            index = r.lpos(key, oldName)
            r.lset(key, index, newName)    

    #mongo
    db.boardGames.update_one({'name':oldName}, {'$set':{'name':newName}})

    conn.commit()
    
    return redirect(url_for('detailPage', game=newName, msg="Game has been renamed."))

@dbtour_app.route("/commitImage")
def commitImage():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]

    game = request.args["game"]
    image = request.args["image"]
    
    db.boardGames.update_one({'name':game}, {'$push':{'images':image}})

    return redirect(url_for('detailPage', game=game, msg="Image added."))

@dbtour_app.route("/commitNewField")
def commitNewField():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
   
    game = request.args["game"]
    field = request.args["field"]
    
#have to make sure it doesn't already exist
    mongoGame= db.boardGames.find({'name':game}).next()
    if (field in mongoGame.keys()):
        return redirect(url_for('detailPage', game=game, msg="Field already exists."))


    dataType = request.args["type"]
    if(dataType == 'atomic'):
        dataType=None
    elif(dataType == 'list'):
        dataType=[]
    else:
        dataType={}

    if("parent" in request.args and request.args["parent"] != "none"):
        parent=request.args["parent"]
        db.boardGames.update_one({'name':game}, {'$set':{parent:{field:dataType}}})

    else:
        db.boardGames.update_one({'name':game}, {'$set':{field:dataType}})

    return redirect(url_for('detailPage', game=game, msg="Field added."))

@dbtour_app.route("/removeMongoField")
def removeMongoField():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    
    game = request.args["game"]
    field = request.args["field"]

    db.boardGames.update_one({'name':game}, {'$unset':{field:""}})

    return redirect(url_for('editInfo', game=game, msg="Field removed."))

@dbtour_app.route("/logOut")
def logOut():
    
    session.pop("username")
    return redirect(url_for("index"))

     
@dbtour_app.route("/randomGame")
def randomGame():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    
    gameList = list(db.boardGames.find())
    length = len(gameList)
    randomNum = random.randint(0, length-1)
    randomGame = gameList[randomNum]["name"]
    return redirect(url_for("detailPage", game=randomGame, msg="")) 
  
         
@dbtour_app.route("/scroll")
def scroll():
    if(request.args["dir"]=="left" ):
        session["scroll"]-=10
    else:
        session["scroll"]+=10
    return redirect(url_for('index'))

@dbtour_app.route("/removeAccount")
def removeAccount():
    r = redis.Redis(password="sammydavies", db=24, decode_responses=True)
    
    r.delete("user:"+session["username"])
    r.delete("wishlist:"+session["username"])
    r.delete("friendList:"+session["username"])

    for key in r.scan_iter(match="friendList:*"):
        r.srem(key, session["username"])

    session.pop("username")
    if("lastPrompt" in session):
        session.pop("lastPrompt")

    return redirect(url_for('index'))

@dbtour_app.route("/editComment")
def editComment():
    comment = request.args["comment"]
    game = request.args["game"]

    return render_template('editComment.html', game=game, comment=comment)

@dbtour_app.route("/commitComment")
def commitComment():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    
    game=request.args["game"]
    newComment = request.args["newComment"]
    oldComment=request.args["oldComment"]

    mongoGame=db.boardGames.find({'name':game}).next()
    comments=mongoGame['comments']
    i = 0
    more = True;
    while (i < len(comments) and more):
        if(comments[i]["comment"]==oldComment and comments[i]["user"]==session["username"]):
            db.boardGames.update_one({'name':game}, {'$set':{'comments.'+str(i)+'.comment':newComment}})
            more = False;
        i += 1

    return redirect(url_for('detailPage', game=game, msg="Comment updated."))
    
@dbtour_app.route("/deleteComment")
def deleteComment():
    mc = MongoClient("mongodb://localhost:27017")
    db = mc["slincicu_db"]
    
    game=request.args["game"]
    comment = request.args["comment"]

    db.boardGames.update_one({'name':game}, {'$pull':{'comments':{'user':session["username"], 'comment':comment}}})

    return redirect(url_for('detailPage', game=game, msg="Comment deleted."))

