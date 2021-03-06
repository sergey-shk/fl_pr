from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, logout_user, login_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, create_engine, ARRAY
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm import relationship
from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, SelectField, StringField, PasswordField, FieldList, FormField, SubmitField

DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.secret_key = "i used to be an adventurer like you..."

engine = create_engine('postgresql://postgres:admin@localhost/pollappdb')
if not database_exists(engine.url):
    create_database(engine.url)
Base = declarative_base()
login_manager = LoginManager(app)
Session = sessionmaker(bind=engine)
Session.configure(bind=engine)
session = Session()


class Poll(Base):
    __tablename__ = 'polls'
    id = Column(Integer, primary_key=True)
    title = Column(String(150), nullable=False)
    access_group_id = Column(Integer, ForeignKey('user_groups.id'))
    voted = Column(ARRAY(Integer), default=[])
    author_id = Column(Integer)
    points = relationship('Point')

class Point(Base):
    __tablename__ = 'points'
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    votes = relationship('Vote')
    answers = relationship('Answer')
    poll_id = Column(Integer, ForeignKey('polls.id'))

class Vote(Base):
    __tablename__ = 'votes'
    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    vote_count = Column(Integer, default=0)
    point_id = Column(Integer, ForeignKey('points.id'))

class Answer(Base):
    __tablename__ = 'answers'
    id = Column(Integer, primary_key=True)
    title = Column(String(100))
    answer = Column(String(200))
    point_id = Column(Integer, ForeignKey('points.id'))


class User(Base, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password = Column(String)
    f_name = Column(String)
    s_name = Column(String)
    groups_id = Column(Integer, ForeignKey('user_groups.id'))

class User_group(Base):
    __tablename__ = 'user_groups'
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    users = relationship('User')
    polls = relationship('Poll')

Base.metadata.create_all(engine)


def get_user_groups():
    if session.query(User_group).all() == None:
        return []
    else:
        groups_ttl = []
        for group in session.query(User_group).all():
            groups_ttl.append(group.title)
        return groups_ttl


class Register_form(FlaskForm):
    username = StringField('username')
    password = PasswordField('password')
    password2 = PasswordField('password2')

class Login_form(FlaskForm):
    username = StringField('username')
    password = PasswordField('password')

class VoteForm(FlaskForm):
    title = StringField('vote_title')

class AnswerForm(FlaskForm):
    title = StringField('anwer_title')

class PointForm(FlaskForm):
    title = StringField('point_title')
    votes = FieldList(FormField(VoteForm), min_entries=0)
    add_vote = SubmitField(label='Add option')
    answers = FieldList(FormField(AnswerForm), min_entries=0)
    add_anwer = SubmitField(label='or add answer field')

class CreatePoll_form(FlaskForm):
    title = StringField('title')
    access_groups = SelectField('Groups', choices=get_user_groups())
    points = FieldList(FormField(PointForm), min_entries=1)
    add_point = SubmitField(label='Add point')


@login_manager.user_loader
def load_user(user_id):
    return session.query(User).filter_by(id=user_id).first()


@app.route('/', methods=['POST', 'GET'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = Register_form()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        password2 = form.password2.data
        if(session.query(User).filter_by(username=username).all() != []):
            message = 'This username is already taken'
            return render_template('index.html', form=form, message=message)
        if (25 > len(username) > 3) and (password == password2):
            hash_pass = generate_password_hash(password)

            if session.query(User_group).filter_by(title='All').first() is None:
                new_group = User_group(title='All')
                session.add(new_group)
                session.commit()

            new_user = User(groups_id=session.query(User_group).filter_by(title='All').first().id, username=username, password=hash_pass)
            session.add(new_user)
            session.commit()
            login_user(new_user)
            return redirect(url_for('home'))
        elif( password != password2 ):
            message = 'Password mismatch'
            return render_template('index.html', form=form, message=message)
        elif(24 < len(username) < 5):
            message = 'Invalid login'
            return render_template('index.html', form=form, message=message)
        else:
            message = ''
            return render_template('index.html', form=form, message=message)
    return render_template('index.html', form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = Login_form()
    if form.validate_on_submit:
        username = form.username.data
        password = form.password.data
        user = session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            if user is None and request.method == 'POST':
                message = 'Incorrect login or password'
                return render_template('login_page.html', form=form, message=message)
            if user and check_password_hash(user.password, password) == False:
                message = 'Incorrect login or password'
                return render_template('login_page.html', form=form, message=message)
    return render_template('login_page.html', form=form)


@app.route('/home')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if session.query(Poll).order_by(-Poll.id).all() is None:
        polls = None
        return render_template('home.html', polls=polls)
    else:
        polls = session.query(Poll).order_by(-Poll.id).all()
        return render_template('home.html', polls=polls)

@app.route('/home/mypolls')
def mypolls():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if session.query(Poll).filter_by(author_id=current_user.id).order_by(-Poll.id).all() is None:
        polls = None
        return render_template('home.html')
    polls = session.query(Poll).filter_by(author_id=current_user.id).order_by(-Poll.id).all()
    return render_template('home.html', polls=polls)


@app.route('/poll/<int:id>', methods=['POST','GET'])
def poll_detail(id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if request.method == 'GET':
        poll = session.query(Poll).filter_by(id=id).first()
        print(poll.voted)
        print(current_user.id)
        if current_user.id in poll.voted:
            return redirect(url_for('poll_result', id=id))
        return render_template('poll.html', poll=poll)
    else:
        poll = session.query(Poll).filter_by(id=id).first()
        poll.voted.append(current_user.id)
        session.commit()
        for point in poll.points:
            if len(point.votes) > 0:
                for vote in point.votes:
                    try:
                        if vote.title == request.form[point.title]:
                            vote.vote_count += 1
                    except:
                        pass
                for answer in point.answers:
                    try:
                        anwer.answer = request.form[answer.title]
                    except:
                        pass
        session.commit()
        return redirect(url_for('poll_result', id=id))

@app.route('/delete/<int:id>',methods=['GET'])
def delete_poll(id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    poll_id = id
    poll_to_delete = session.query(Poll).filter_by(id=poll_id).first()
    if (current_user.id == poll_to_delete.author_id) and (poll_to_delete!= None):
        session.delete(poll_to_delete)
        session.commit()
        return redirect(url_for('home'))
    else:
        return redirect(url_for('accs_error'))


@app.route('/access_error')
def accs_error():
    return render_template('a_error.html', message='Access error')


@app.route('/result/<int:id>',methods=['GET'])
def poll_result(id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if request.method == 'GET':
        poll = session.query(Poll).filter_by(id=id).first()
        vote_dict = {}
        for point in poll.points:
            vote_ctr = 0
            for vote in point.votes:
                vote_ctr += vote.vote_count
            vote_dict.update( {point.id: vote_ctr} )
        return render_template('results.html', votes_dict=vote_dict, poll=poll)
    else:
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/new_poll', methods=['GET', 'POST'])
def new_poll():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))


    if request.method == 'GET':
        form = CreatePoll_form()
        return render_template('new_poll.html', form=form)
    else:
        form = CreatePoll_form()
        if form.add_point.data:
            form.points.append_entry()
            return render_template('new_poll.html', form=form)

        for point in form.points:
            if point.add_vote.data:
                point.votes.append_entry()
                return render_template('new_poll.html', form=form)
            if point.add_anwer.data:
                point.answers.append_entry()
                return render_template('new_poll.html', form=form)

        if form.validate_on_submit:
            poll_title = form.title.data
            author_id = current_user.id
            new_poll = Poll(title=poll_title, author_id=author_id)
            session.add(new_poll)
            session.commit()
            for point in form.points.data:
                poll_id = session.query(Poll).filter_by(title=poll_title, author_id=author_id).first().id
                new_point = Point(title=point['title'], poll_id=poll_id)
                session.add(new_point)
                session.commit()
                print(new_point.id)
                for vote in point['votes']:
                    point_id = session.query(Point).filter_by(title=point['title'], poll_id=poll_id).first().id
                    new_vote = Vote(title=vote['title'], point_id=point_id)
                    session.add(new_vote)
                    session.commit()
                for answer in point['answers']:
                    point_id = session.query(Point).filter_by(title=point['title'], poll_id=poll_id).first().id
                    new_answer = Answer(title=answer['title'], point_id=point_id)
                    session.add(new_answer)
                    session.commit()
            return redirect(url_for('home'))




if __name__ == '__main__':
    app.run()
