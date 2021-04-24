from flask_wtf import Form
from wtforms.validators import Required
from wtforms.fields import StringField, SubmitField

class NameForm(Form):
    name = StringField("what's your name", validators=[Required()])
    submit = SubmitField("Submit")