from operator import index
from flask_login.mixins import AnonymousUserMixin, UserMixin
from flask_migrate import current
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__="users"
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(64), unique=True,index=True)
    username=db.Column(db.String(64),unique=True,index=True)
    password_hash=db.Column(db.String(128))

    # profile info
    name=db.Column(db.String(64))
    location=db.Column(db.String(64))
    about_me=db.Column(db.Text())
    memeber_since=db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen=db.Column(db.DateTime(), default=datetime.utcnow)

    # account verification
    confirmed=db.Column(db.Boolean, default=False)
    @property
    def password(self):
        raise AttributeError("Password isn't readable attribute")

    @password.setter
    def password(self,password):
        self.password_hash=generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    role_id=db.Column(db.Integer,db.ForeignKey("roles.id"))

    def __repr__(self) -> str:
        return "<User %r>" % self.username

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config["FLASK_ADMIN"]:
                self.role=Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role=Role.query.filter_by(default=True).first()
    
    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen=datetime.utcnow()
        db.session.add(self)

    def generate_confirmation_token(self,expiration=3600):
        s=Serializer(current_app.config['SECRET_KEY'],expiration)
        return s.dumps({'confirm':self.id})

    def confirm(self, token):
        s=Serializer(current_app.config['SECRET_KEY'])
        try:
            data=s.loads(token)
        except:
            return False
        
        if data.get('confirm')!=self.id:
            return False

        self.confirmed=True
        db.session.add(self)
        return True


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False



class Role(db.Model):
    __tablename__="roles"
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(64),unique=True)
    default=db.Column(db.Boolean, default=False, index=True)
    permissions=db.Column(db.Integer)
    users=db.relationship("User",backref='role', lazy='dynamic')

    def __repr__(self) -> str:
        return "<Role %r>" % self.name


    @staticmethod
    def insert_roles():
        roles={
            'User':(Permission.FOLLOW | Permission.COMMENT | Permission.WRITE_ARTICLES, True),
            'Moderator':(Permission.FOLLOW | Permission.COMMENT | Permission.WRITE_ARTICLES, False),
            'Administrator':(0xff, False)
        }
        for r in roles:
            role=Role.query.filter_by(name=r).first()
            if role is None:
                role=Role(name=r)
            role.permissions=roles[r][0]
            role.default=roles[r][1]
            db.session.add(role)
        db.session.commit()


class Permission:
    FOLLOW=0x01
    COMMENT=0x02
    WRITE_ARTICLES=0x04
    MODERATE_COMMENTS=0x08
    ADMINISTER=0x80

login_manager.anonymous_user=AnonymousUser

    