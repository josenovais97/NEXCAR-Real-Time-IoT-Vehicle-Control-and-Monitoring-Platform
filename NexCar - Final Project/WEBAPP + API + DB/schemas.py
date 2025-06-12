from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields
from models import User, Car, SensorData, Question

class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_relationships = True
        exclude = ("password",)

class CarSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Car
        include_fk = True
        load_instance = True

class SensorDataSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = SensorData
        include_fk = True
        load_instance = True

class QuestionSchema(SQLAlchemyAutoSchema):
    user_name = fields.Method("get_user_name")
    class Meta:
        model = Question
        include_fk = True
        load_instance = True

    def get_user_name(self, obj):
        return obj.user.username

# instâncias
user_schema            = UserSchema()
car_schema             = CarSchema()
cars_schema            = CarSchema(many=True)
sensordata_schema      = SensorDataSchema()
sensordata_schema_many = SensorDataSchema(many=True)
question_schema        = QuestionSchema()
question_schema_many   = QuestionSchema(many=True)
