from os.path import abspath, dirname, join

from flask import flash, Flask, Markup, redirect, render_template, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.wtf import Form
from wtforms import fields, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField
import random

#//\\//\\//\\//\\INIT//\\//\\//\\//\\

_cwd = dirname(abspath(__file__))

SECRET_KEY = 'flask-session-insecure-secret-key'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + join(_cwd, 'pw.db')
SQLALCHEMY_ECHO = True
WTF_CSRF_SECRET_KEY = 'this-should-be-more-random'


app = Flask(__name__)
app.config.from_object(__name__)

db = SQLAlchemy(app)

#//\\//\\//\\//\\Database Setup//\\//\\//\\//\\

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String)
    passwords = db.relationship('Password', backref='users', lazy='select')
    
    def __repr__(self):
        return self.user_name
    def __str__(self):
        return self.user_name

class Password(db.Model):
    __tablename__ = 'password'
    
    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __repr__(self):
        return '<%r>' % (self.password)
    
#//\\//\\//\\//\\Forms//\\//\\//\\//\\

class GenForm(Form):
    user = QuerySelectField(query_factory=User.query.all)
    minL = fields.IntegerField('Minimum Word Length  (2-4)', validators=[validators.required(), validators.NumberRange(min=2, max=4)])
    maxL = fields.IntegerField('Maximum Word Length  (4-7)', validators=[validators.required(), validators.NumberRange(min=4, max=7)])
    totL = fields.IntegerField('Maximum Totoal Length  (11-31)', validators=[validators.required(), validators.NumberRange(min=11, max=31)])
    
    caps = fields.BooleanField()
    
    swap = fields.BooleanField('Substitute: (3 == E...$ == S...etc)')
    
class UserForm(Form):
    user_name = fields.StringField()

#//\\//\\//\\//\\Views//\\//\\//\\//\\
    
@app.route("/")
def index():
    user_form = UserForm()
    gen_form = GenForm()
    return render_template("index.html",
                           user_form=user_form,
                           gen_form=gen_form)


@app.route("/user", methods=("POST", ))
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        user = User()
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
        flash("Added user")
        return redirect(url_for("index"))
    return render_template("errors.html", form=form)


@app.route("/gen", methods=("POST", ))
def get_param():
    form = GenForm()
    if form.validate_on_submit():
        pw = Password()
        PW = make(form)
        pw.password = PW
        pw.user_id = form.user.data.id
        db.session.add(pw)
        db.session.commit()
        flash("Added password for " + form.user.data.user_name)
        return redirect(url_for("index"))
    return render_template("errors.html", form=form)

#//\\//\\//\\//\\Making the Password//\\//\\//\\//\\

def getDB():  #Creates a list of strings from a text file.
    myFile = open('wordLST.txt', 'r')
    
    #Build an array of words to chose from
    words = []
    pw = []
    for i in myFile:
        line = i.strip()
        words.append(line)
        
    return words

def make(form):
    #Makes a single string of 4 words pulled from the below function, then returns the finished string.
    
    minL = int(request.form['minL'])
    maxL = int(request.form['maxL'])
    totL = int(request.form['totL'])
    
    pw = ''
    tLen = 0
    
    for i in range(0,4):
        word, t = getWord(minL, maxL, totL, tLen)

        pw = word + ' ' + pw
        tLen = t
        
    return pw
    
def getWord(minL, maxL, totL, tLen): #  returns a word to be appended to a string held in the above function
                                     #  the word is pulled from a database, and checked that it meets the
                                     #  parameters.
    words = getDB()
    
    go = False
    
    while go is False:
        index = random.randint(0,5000)
        word = words[index]
        
        if len(word) <= maxL:
            if len(word) >= minL:
                aLen = tLen + len(word)
                if aLen < totL:
                    tLen += len(word)
                    go = True
    return word, tLen

#//\\//\\//\\//\\Viewing the Users//\\//\\//\\//\\

@app.route("/users")
def view_users():  #shows all of the users in the db
    query = User.query.filter(User.id >= 0)
    data = query_to_list(query)
    data = [next(data)] + [[_make_link(cell) if i == 0 else cell for i, cell in enumerate(row)] for row in data]
    return render_template("pw_list.html", data=data, type="Users")

#//\\//\\//\\//\\Links//\\//\\//\\//\\

#  This section simplifies making links across the environment
#  It allows me to have a standard way of making links
#  One function returns an object directing to the view page,
#  The other returns a page that just runs the script to remove the user key in the db
#  then redirects to the main page ("index").

_LINK = Markup('<a href="{url}">{name}</a>')


def _make_link(user_id):
    url = url_for("view_user_pw", user_id=user_id)
    return _LINK.format(url=url, name=user_id)

def _make_rm(user_id):
    url = url_for("rm_user", user_id=user_id)
    return _LINK.format(url=url, name=user_id)

#//\\//\\//\\//\\Viewing the Users Passwords//\\//\\//\\//\\

@app.route("/user/<int:user_id>")
def view_user_pw(user_id): #shows a list of the users passwords
    user = User.query.get_or_404(user_id)
    query = Password.query.filter(Password.user_id == user_id)
    data = query_to_list(query)
    title = "Passwords for " + user.user_name
    
    return render_template("pw_list.html", data=data, type=title)

def query_to_list(query, include_field_names=True): #reads user information from the db
    column_names = []
    for i, obj in enumerate(query.all()):
        if i == 0:
            column_names = [c.name for c in obj.__table__.columns]
            if include_field_names:
                yield column_names
        yield obj_to_list(obj, column_names)


def obj_to_list(sa_obj, field_order): #returns a list of data from a SQL object
    return [getattr(sa_obj, field_name, None) for field_name in field_order]
    
#//\\//\\//\\//\\Removing a user//\\//\\//\\//\\    

@app.route("/rm")
def rm(): #redirects to a page showing the active users
    query = User.query.filter(User.id >= 0)
    data = query_to_list(query)
    data = [next(data)] + [[_make_rm(cell) if i == 0 else cell for i, cell in enumerate(row)] for row in data]
    
    return render_template("rm_list.html", data=data, type="Users")

@app.route("/rm/<int:user_id>")
def rm_user(user_id): #a page just to run a script to remove the selected user from the db
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash(user.user_name + " deleted")
    
    return redirect(url_for("index"))


#//\\//\\//\\//\\RUN//\\//\\//\\//\\

if __name__ == "__main__":
    app.debug = True
    db.create_all()
    app.run()
