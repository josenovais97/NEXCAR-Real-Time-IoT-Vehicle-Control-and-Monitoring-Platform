from flask import request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from . import api_bp
from models import db, Question, User
from schemas import question_schema, question_schema_many

@api_bp.post('/questions')
@jwt_required()
def create_question():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    text = data.get('question', '').strip()
    if not text:
        abort(400, description="Pergunta é obrigatória")
    q = Question(user_id=user_id, question=text)
    db.session.add(q)
    db.session.commit()
    return question_schema.dump(q), 201

@api_bp.get('/questions')
@jwt_required()
def list_questions():
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        qs = Question.query.order_by(Question.created_at.desc()).all()
    else:
        qs = Question.query.filter_by(user_id=user_id).order_by(Question.created_at.desc()).all()
    return question_schema_many.dump(qs), 200

@api_bp.post('/questions/<int:qid>/response')
@jwt_required()
def respond_question(qid):
    user_id = int(get_jwt_identity())
    user = User.query.get_or_404(user_id)
    if user.role != 'admin':
        abort(403, description="Sem permissão")
    q = Question.query.get_or_404(qid)
    data = request.get_json() or {}
    resp = data.get('response', '').strip()
    if not resp:
        abort(400, description="Resposta é obrigatória")
    q.response     = resp
    q.responded_at = datetime.utcnow()
    db.session.commit()
    return question_schema.dump(q), 200
